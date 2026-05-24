"""GenASL CLI entry point.

Dispatches to either pipeline based on ``settings.pipeline.mode``:

* ``genai_gloss`` (default) — word-level WLASL clip stitching
  (fetch → translate → lookup → chain → plan).
* ``interpreter_avatar`` — audio-driven 3D-avatar pipeline
  (audio → analyse → chunk → interpret → motion → avatar timeline).

Usage::

    python -m src.pipeline.run_pipeline <VIDEO_ID>
"""

from __future__ import annotations

import logging
import sys

from src.core.config import get_settings
from src.core.logging import setup_logging
from src.pipeline.io import append_run_log, print_summary, save_render_plan
from src.pipeline.models import AvatarRenderPlan, RenderPlan
from src.pipeline.pipeline import Pipeline
from src.pipeline.pipeline_avatar import InterpreterAvatarPipeline
from src.transcript_ingestion.fetcher import NoTranscriptError

logger = logging.getLogger(__name__)


def run(video_id: str, *, use_cache: bool = True) -> RenderPlan | AvatarRenderPlan:
    """Execute the configured pipeline and return its typed plan."""
    setup_logging()
    mode = get_settings().pipeline.mode

    if mode == "interpreter_avatar":
        logger.info("Pipeline mode: interpreter_avatar")
        plan = InterpreterAvatarPipeline().run(video_id, use_cache=use_cache)
        # avatar-mode I/O helpers land in Phase 7; for now return the plan
        # so callers can persist it themselves.
        return plan

    logger.info("Pipeline mode: genai_gloss")
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
    except NotImplementedError as exc:
        logger.error("%s", exc)
        sys.exit(4)
