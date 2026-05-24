"""Interpreter-avatar pipeline orchestrator (schema v5.0).

Mirrors :class:`src.pipeline.pipeline.Pipeline` but for the
``interpreter_avatar`` mode: audio in → analyse → chunk → interpret →
synthesise motion → emit an :class:`AvatarRenderPlan` for the three.js
frontend.

This module is a *skeleton* — concrete stages land in subsequent phases.
Until then, :meth:`InterpreterAvatarPipeline.run` raises
``NotImplementedError`` so a mis-routed call fails loudly rather than
silently returning an empty plan.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.config import Settings, get_settings
from src.pipeline.models import AvatarRenderPlan

logger = logging.getLogger(__name__)


class InterpreterAvatarPipeline:
    """End-to-end audio → interpreter → 3D-avatar timeline pipeline.

    Stage wiring is filled in across Phases 2–5. The constructor is kept
    side-effect-free so that importing the class never instantiates the
    heavier stage models (faster-whisper, mediapipe).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        cache_root: Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache_root = cache_root
        # Stages will be wired in subsequent phases:
        #   self.audio_ingest    (Phase 2)
        #   self.audio_analyze   (Phase 2)
        #   self.semantic_chunk  (Phase 3)
        #   self.interpreter     (Phase 3)
        #   self.motion_synth    (Phase 5)
        #   self.avatar_timeline (Phase 5)

    def run(self, video_id: str, *, use_cache: bool = True) -> AvatarRenderPlan:
        raise NotImplementedError(
            "InterpreterAvatarPipeline is a skeleton. "
            "Stage wiring lands in Phases 2–5; "
            "use pipeline.mode='genai_gloss' until then."
        )
