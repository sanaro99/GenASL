"""Pipeline orchestrator — chains the five typed stages."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from src.core.config import Settings, get_settings
from src.pipeline.models import (
    ChainInput,
    FetchInput,
    LookupInput,
    PlanInput,
    RenderPlan,
    TranslateInput,
)
from src.pipeline.stages import (
    ChainStage,
    FetchStage,
    LookupStage,
    PlanStage,
    TranslateStage,
)

logger = logging.getLogger(__name__)


class Pipeline:
    """End-to-end gloss pipeline: fetch → translate → lookup → chain → plan."""

    def __init__(
        self,
        settings: Settings | None = None,
        cache_root: Path | None = None,
    ) -> None:
        s = settings or get_settings()
        self.settings = s
        self.fetch = FetchStage(s, cache_root)
        self.translate = TranslateStage(s, cache_root)
        self.lookup = LookupStage(s, cache_root)
        self.chain = ChainStage(s, cache_root)
        self.plan = PlanStage(s, cache_root)

    def run(self, video_id: str, *, use_cache: bool = True) -> RenderPlan:
        logger.info("=" * 60)
        logger.info("Pipeline run for video %s (use_cache=%s)", video_id, use_cache)
        logger.info("=" * 60)

        fetch_out = self.fetch.run(FetchInput(video_id=video_id), use_cache=use_cache)
        tx_out = self.translate.run(
            TranslateInput(segments=fetch_out.segments), use_cache=use_cache
        )
        lk_out = self.lookup.run(
            LookupInput(segments=tx_out.segments), use_cache=use_cache
        )
        ch_out = self.chain.run(
            ChainInput(segments=lk_out.segments), use_cache=use_cache
        )

        run_id = uuid.uuid4().hex[:12]
        plan = self.plan.run(PlanInput(
            run_id=run_id,
            video_id=video_id,
            provider=tx_out.provider,
            model=tx_out.model,
            segments=ch_out.segments,
            filtered=fetch_out.filtered,
        ))
        return plan
