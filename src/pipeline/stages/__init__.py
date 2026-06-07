"""Pipeline stages — each stage is a typed, cacheable unit of work.

All stages share the abstract :class:`Stage` base in :mod:`stages.base`.
Concrete stages for the ``interpreter_avatar`` pipeline land in Phases 2–5
and will be imported here as they arrive (see ``docs/plan/``).
"""

from src.pipeline.stages.audio_analyze import AudioAnalyzeStage
from src.pipeline.stages.audio_ingest import AudioIngestStage
from src.pipeline.stages.base import Stage, stable_hash
from src.pipeline.stages.interpreter_plan import InterpreterPlanStage
from src.pipeline.stages.semantic_chunk import SemanticChunkStage

__all__ = [
    "Stage",
    "stable_hash",
    # Phase 2 — audio backbone
    "AudioIngestStage",
    "AudioAnalyzeStage",
    # Phase 3 — interpreter brain
    "SemanticChunkStage",
    "InterpreterPlanStage",
    # Concrete stages added in later phases:
    #   MotionSynthStage, AvatarTimelineStage      (Phase 5)
]
