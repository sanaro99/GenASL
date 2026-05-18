"""GenASL CLI entry point — fetch → translate → lookup → chain → plan.

Usage::

    python -m src.pipeline.run_pipeline <VIDEO_ID>
"""

from __future__ import annotations

import logging
import sys

from src.core.logging import setup_logging
from src.pipeline.io import append_run_log, print_summary, save_render_plan
from src.pipeline.models import RenderPlan
from src.pipeline.pipeline import Pipeline
from src.transcript_ingestion.fetcher import NoTranscriptError

logger = logging.getLogger(__name__)


def run(video_id: str, *, use_cache: bool = True) -> RenderPlan:
    """Execute the full pipeline and return the typed :class:`RenderPlan`."""
    setup_logging()
    plan = Pipeline().run(video_id, use_cache=use_cache)
    out_path = save_render_plan(plan)
    append_run_log(plan, output_file=str(out_path))
    print_summary(plan)
    return plan


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline.run_pipeline <VIDEO_ID>")
        sys.exit(1)

    setup_logging()
    vid = sys.argv[1]
    try:
        run(vid)
    except NoTranscriptError as exc:
        logger.error("No English transcript available: %s", exc)
        sys.exit(2)
    except ValueError as exc:
        logger.error("Invalid input: %s", exc)
        sys.exit(3)
