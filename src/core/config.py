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


class PipelineSettings(BaseModel):
    min_word_count: int = 3
    min_duration_ms: int = 2000
    batch_chunk_size: int = 10
    pause_gap_s: float = 1.5
    high_asl_ratio_warn: float = 0.90


class CompositorSettings(BaseModel):
    pip_width_ratio: float = 0.25
    disclosure_label: str = "AI-generated ASL overlay (POC)"


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
