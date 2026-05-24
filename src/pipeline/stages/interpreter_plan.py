"""Stage 4 — LLM interpreter brain (Phase 3).

Wraps :func:`src.interpreter.planner.plan_chunks`. The cache fingerprint
folds in ``PROMPT_VERSION``, the LLM provider+model, and the chunk
contents — so iterating on the prompt invalidates exactly this stage
without touching the upstream audio cache.
"""

from __future__ import annotations

import logging

from src.interpreter.planner import plan_chunks
from src.interpreter.prompt import PROMPT_VERSION
from src.pipeline.models import InterpreterPlanInput, InterpreterPlanOutput
from src.pipeline.stages.base import Stage, stable_hash

logger = logging.getLogger(__name__)


class InterpreterPlanStage(Stage[InterpreterPlanInput, InterpreterPlanOutput]):
    name = "interpreter_plan"
    output_model = InterpreterPlanOutput

    def fingerprint(self, inp: InterpreterPlanInput) -> str:
        s = self.settings
        provider_model = getattr(s.llm, s.llm.provider).model
        return stable_hash([
            "interpreter_plan",
            PROMPT_VERSION,
            s.llm.provider,
            provider_model,
            s.interpreter.temperature,
            s.interpreter.include_role_shifts,
            s.interpreter.include_classifiers,
            [c.chunk_id for c in inp.chunks],
            [c.text for c in inp.chunks],
        ])

    def process(self, inp: InterpreterPlanInput) -> InterpreterPlanOutput:
        segments, provider, model = plan_chunks(
            inp.chunks, settings=self.settings.interpreter
        )
        logger.info(
            "InterpreterPlanStage: %d segments via %s/%s",
            len(segments), provider, model,
        )
        return InterpreterPlanOutput(
            segments=segments, provider=provider, model=model
        )
