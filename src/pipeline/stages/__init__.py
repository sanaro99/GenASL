"""Pipeline stages — each stage is a typed, cacheable unit of work.

All stages share the abstract :class:`Stage` base in :mod:`stages.base`.
Concrete stages for the ``interpreter_avatar`` pipeline land in Phases 2–5
and will be imported here as they arrive (see ``docs/plan/``).
"""

from src.pipeline.stages.base import Stage, stable_hash

__all__ = [
    "Stage",
    "stable_hash",
    # Concrete stages added in Phases 2–5:
    #   AudioIngestStage, AudioAnalyzeStage,
    #   SemanticChunkStage, InterpreterPlanStage,
    #   MotionSynthStage, AvatarTimelineStage,
]
