"""GenASL CLI entry point — runs the ``interpreter_avatar`` pipeline.

The pipeline runs six stages — audio_ingest → audio_analyze →
semantic_chunk → interpreter_plan → motion_synth → avatar_timeline —
and emits an :class:`AvatarRenderPlan` (v5.0) that the Chrome extension's
three.js consumer plays.

Usage::

    python -m src.pipeline.run_pipeline <VIDEO_ID>

Until Phases 2–5 land, :class:`InterpreterAvatarPipeline.run` raises
:class:`NotImplementedError` so a mis-routed call fails loudly. See
``docs/plan/`` for the implementation roadmap.
"""

from __future__ import annotations

import logging
import sys

from src.core.logging import setup_logging
from src.pipeline.io import print_summary, save_avatar_plan
from src.pipeline.models import AvatarRenderPlan
from src.pipeline.pipeline_avatar import InterpreterAvatarPipeline

logger = logging.getLogger(__name__)


def run(video_id: str, *, use_cache: bool = True) -> AvatarRenderPlan:
    """Execute the interpreter_avatar pipeline and return the typed plan."""
    setup_logging()
    plan = InterpreterAvatarPipeline().run(video_id, use_cache=use_cache)
    save_avatar_plan(plan)
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
    except NotImplementedError as exc:
        logger.error("Pipeline not fully wired yet — see docs/plan/: %s", exc)
        sys.exit(4)
    except ValueError as exc:
        logger.error("Invalid input: %s", exc)
        sys.exit(3)
