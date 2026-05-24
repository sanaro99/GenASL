"""Typed application settings loaded from ``config.yaml``.

All magic numbers that used to live as module-level constants in
``run_pipeline.py``, ``server.py``, ``compositor.py``, etc. are absorbed
here. Modules should call :func:`get_settings` rather than re-parsing the
YAML file.

API keys (e.g. ``GEMINI_API_KEY``) are intentionally *not* part of this
model — they're resolved by each provider at construction time from the
process environment so secrets never touch the typed config.
"""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.core.paths import CONFIG_YAML


class LLMProviderCfg(BaseModel):
    model: str
    base_url: str | None = None


class LLMSettings(BaseModel):
    provider: Literal["ollama", "gemini", "openai"] = "ollama"
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


PipelineMode = Literal["genai_gloss", "interpreter_avatar"]


class PipelineSettings(BaseModel):
    mode: PipelineMode = "genai_gloss"
    min_word_count: int = 3
    min_duration_ms: int = 2000
    batch_chunk_size: int = 10
    pause_gap_s: float = 1.5
    high_asl_ratio_warn: float = 0.90


class CompositorSettings(BaseModel):
    pip_width_ratio: float = 0.25
    disclosure_label: str = "AI-generated ASL overlay (POC)"


class AudioSettings(BaseModel):
    """Audio analysis stage tunables (interpreter_avatar mode)."""

    asr_model: str = "small"            # faster-whisper size: tiny | base | small | medium
    asr_compute_type: str = "int8"      # int8 | int8_float16 | float16 | float32
    asr_language: str = "en"
    sample_rate_hz: int = 16000
    vad_min_silence_ms: int = 500       # silence ≥ this is a chunk boundary
    prosody_frame_ms: int = 50          # prosody frame stride
    emotion_window_ms: int = 4000       # min text window the emotion classifier sees


class InterpreterSettings(BaseModel):
    """Interpreter-brain LLM stage tunables (interpreter_avatar mode)."""

    max_chunk_chars: int = 240          # cap per interpreter call
    min_chunk_chars: int = 20
    temperature: float = 0.2            # low — we want structured plans
    include_role_shifts: bool = True
    include_classifiers: bool = True


class AvatarSettings(BaseModel):
    """3D avatar / motion synthesis tunables (interpreter_avatar mode)."""

    rig: Literal["vrm"] = "vrm"
    vrm_model_url: str = "https://models.readyplayer.me/64bfa15f0e72c63d7c3934a6.glb"
    frame_rate: int = 30                # motion timeline fps
    sign_default_duration_ms: int = 600 # fallback when pose library has no timing
    transition_ms: int = 120            # spline transition length between signs
    pip_width_ratio: float = 0.30       # frontend canvas width fraction


class ApiSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8794
    response_cache_max: int = 500


class BuildSettings(BaseModel):
    preferred_signer_ids: list[int] = Field(default_factory=lambda: [9, 109, 12])


class PathsSettings(BaseModel):
    """Repo-relative paths. Defaults are used when YAML omits the key."""

    word_manifest: str = "assets/word_manifest.json"
    logs: str = "logs"
    cache_dir: str = "data/cache"
    chained_clips: str = "assets/chained"
    words: str = "assets/words"
    transcripts: str = "transcripts"
    # interpreter_avatar mode
    audio_cache: str = "data/audio_cache"
    pose_library: str = "assets/pose_library"
    avatar_plans: str = "logs"

    # Tolerate dead-leg path entries (supported_set, faiss_index, …) during
    # the transition. Phase G removes them from config.yaml.
    model_config = ConfigDict(extra="ignore")


class Settings(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    compositor: CompositorSettings = Field(default_factory=CompositorSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    build: BuildSettings = Field(default_factory=BuildSettings)
    paths: PathsSettings = Field(default_factory=PathsSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    interpreter: InterpreterSettings = Field(default_factory=InterpreterSettings)
    avatar: AvatarSettings = Field(default_factory=AvatarSettings)

    # Tolerate top-level legacy sections (``matcher``, ``test_videos``, …).
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
