"""Typed application settings loaded from ``config.yaml``.

All tuneables for the ``interpreter_avatar`` pipeline live here. Modules
should call :func:`get_settings` rather than re-parsing the YAML file.

API keys (e.g. ``GEMINI_API_KEY``, ``OPENAI_API_KEY``) are intentionally
*not* part of this model — they're resolved by each provider at
construction time from the process environment so secrets never touch
the typed config.
"""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.core.paths import CONFIG_YAML


# ---------------------------------------------------------------------------
# LLM provider
# ---------------------------------------------------------------------------

class LLMProviderCfg(BaseModel):
    model: str
    base_url: str | None = None


class LLMSettings(BaseModel):
    provider: Literal["ollama", "gemini", "openai"] = "gemini"
    ollama: LLMProviderCfg = Field(
        default_factory=lambda: LLMProviderCfg(
            model="llama3.2", base_url="http://localhost:11434/v1"
        )
    )
    gemini: LLMProviderCfg = Field(
        default_factory=lambda: LLMProviderCfg(
            model="gemini-2.0-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    )
    openai: LLMProviderCfg = Field(
        default_factory=lambda: LLMProviderCfg(model="gpt-4o-mini")
    )


# ---------------------------------------------------------------------------
# Pipeline (orchestrator-level)
# ---------------------------------------------------------------------------

class PipelineSettings(BaseModel):
    """High-level pipeline tunables. Stage-specific tunables live under
    ``audio:``, ``interpreter:``, ``avatar:``."""

    use_disk_cache: bool = True


# ---------------------------------------------------------------------------
# Audio analysis (Stages 1–2)
# ---------------------------------------------------------------------------

class AudioSettings(BaseModel):
    asr_model: str = "small"            # faster-whisper size: tiny | base | small | medium
    asr_compute_type: str = "int8"      # int8 | int8_float16 | float16 | float32
    asr_language: str = "en"
    sample_rate_hz: int = 16000
    vad_min_silence_ms: int = 500       # silence ≥ this is a chunk boundary
    prosody_frame_ms: int = 50          # prosody frame stride
    emotion_window_ms: int = 4000       # min text window the emotion classifier sees


# ---------------------------------------------------------------------------
# Interpreter LLM (Stages 3–4)
# ---------------------------------------------------------------------------

class InterpreterSettings(BaseModel):
    max_chunk_chars: int = 240          # cap per interpreter call
    min_chunk_chars: int = 20
    temperature: float = 0.2            # low — we want structured plans
    include_role_shifts: bool = True
    include_classifiers: bool = True


# ---------------------------------------------------------------------------
# 3D avatar / motion synthesis (Stages 5–6)
# ---------------------------------------------------------------------------

class AvatarSettings(BaseModel):
    rig: Literal["vrm"] = "vrm"
    vrm_model_url: str = "https://models.readyplayer.me/64bfa15f0e72c63d7c3934a6.glb"
    frame_rate: int = 30                # motion timeline fps
    sign_default_duration_ms: int = 600 # fallback when pose library has no timing
    transition_ms: int = 120            # spline transition length between signs
    pip_width_ratio: float = 0.30       # frontend canvas width fraction


# ---------------------------------------------------------------------------
# Retrieval (Phase 4) — phrase-level corpus retrieval + lexical fallback
# ---------------------------------------------------------------------------

class RetrievalSettings(BaseModel):
    """Tunables for phrase-level + lexical retrieval over Deaf-signed corpora."""

    # SentenceTransformer model name — must match between build and query.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Above this cosine similarity, a primary (phrase-level) hit is accepted.
    phrase_threshold: float = 0.55
    # Above this similarity, a per-token secondary (lexical, ASL Citizen) hit
    # is accepted in the fallback path.
    lexical_threshold: float = 0.70
    # Maximum drift (×) between retrieved-clip duration and segment window
    # before a candidate is rejected — keeps the avatar from time-scaling
    # absurdly long or short clips into the chunk.
    max_duration_drift: float = 0.40
    # OpenASL clip duration cap — anything longer is discarded at fetch time
    # so we don't waste disk on full lectures.
    max_clip_duration_ms: int = 12000
    # Corpus directory names (relative to assets/corpus/).
    primary_corpus: str = "openasl"
    secondary_corpus: str = "aslcitizen"


# ---------------------------------------------------------------------------
# API server
# ---------------------------------------------------------------------------

class ApiSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8794
    response_cache_max: int = 500


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

class PathsSettings(BaseModel):
    """Repo-relative paths. Defaults are used when YAML omits the key."""

    logs: str = "logs"
    cache_dir: str = "data/cache"
    audio_cache: str = "data/audio_cache"
    pose_library: str = "assets/pose_library"
    avatar_plans: str = "logs"
    # Source WLASL clip directory used only by scripts/build_pose_library.py
    wlasl_clips: str = "assets/wlasl_clips"
    # Phase 4 corpus root — holds <name>/ (video bytes, gitignored),
    # <name>_poses/ (per-clip JSON, gitignored), <name>_manifest.json
    # (tracked), and <name>.faiss (tracked).
    corpus_root: str = "assets/corpus"

    # Tolerate legacy path entries during the transition.
    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class Settings(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    interpreter: InterpreterSettings = Field(default_factory=InterpreterSettings)
    avatar: AvatarSettings = Field(default_factory=AvatarSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    paths: PathsSettings = Field(default_factory=PathsSettings)

    # Tolerate top-level legacy sections (``test_videos``, etc.).
    model_config = ConfigDict(extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton :class:`Settings`, loading from disk on first call."""
    global _settings
    if _settings is None:
        _settings = _load()
    return _settings


def _load() -> Settings:
    with open(CONFIG_YAML, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return Settings.model_validate(raw)


def reset_settings() -> None:
    """Drop the cached :class:`Settings`. Useful for tests that mutate config."""
    global _settings
    _settings = None
