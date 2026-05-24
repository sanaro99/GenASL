"""Interpreter-avatar pipeline orchestrator (schema v5.0).

Audio in → analyse (ASR + prosody + emotion) → chunk semantically →
interpret with an LLM "interpreter brain" → synthesise motion + NMMs →
emit an :class:`AvatarRenderPlan` for the three.js frontend.

This module is a *partial* skeleton: Phase 2 wires the audio stages,
and a helper :meth:`run_audio_only` returns a typed
:class:`AudioAnalysis` so Phase 3 can build on top. The full
:meth:`run` still raises ``NotImplementedError`` until Phase 5 ships
motion synthesis. See ``docs/plan/`` for the per-phase roadmap.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.config import Settings, get_settings
from src.pipeline.models import (
    AudioAnalysis,
    AudioAnalyzeInput,
    AudioIngestInput,
    AvatarRenderPlan,
)
from src.pipeline.stages import AudioAnalyzeStage, AudioIngestStage

logger = logging.getLogger(__name__)


class InterpreterAvatarPipeline:
    """End-to-end audio → interpreter → 3D-avatar timeline pipeline."""

    def __init__(
        self,
        settings: Settings | None = None,
        cache_root: Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache_root = cache_root
        # Phase 2 — audio backbone:
        self.audio_ingest = AudioIngestStage(self.settings, cache_root)
        self.audio_analyze = AudioAnalyzeStage(self.settings, cache_root)
        # Phase 3 — interpreter brain (semantic_chunk, interpreter)
        # Phase 5 — motion synthesis (motion_synth, avatar_timeline)

    def run_audio_only(
        self, video_id: str, *, use_cache: bool = True
    ) -> AudioAnalysis:
        """Run Stages 1–2 only and return the :class:`AudioAnalysis`.

        Useful for Phase 3 development and for ``pytest`` integration
        tests of the audio backbone without depending on later phases.
        """
        ingest = self.audio_ingest.run(
            AudioIngestInput(video_id=video_id), use_cache=use_cache
        )
        analyzed = self.audio_analyze.run(
            AudioAnalyzeInput(
                audio_path=ingest.audio_path,
                duration_ms=ingest.duration_ms,
            ),
            use_cache=use_cache,
        )
        return analyzed.analysis

    def run(self, video_id: str, *, use_cache: bool = True) -> AvatarRenderPlan:
        raise NotImplementedError(
            "InterpreterAvatarPipeline is partial: Phases 3–5 must land "
            "before run() can produce an AvatarRenderPlan. Use "
            "run_audio_only() for Stage 1–2 output. See docs/plan/."
        )
