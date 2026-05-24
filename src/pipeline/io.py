"""Avatar-plan I/O helpers — save JSON, print summary.

These operate on the typed :class:`AvatarRenderPlan` model. They're
separated from the orchestrator so :class:`InterpreterAvatarPipeline`
doesn't have to know about disk paths or console formatting.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.paths import LOGS_DIR
from src.pipeline.models import AvatarRenderPlan

logger = logging.getLogger(__name__)


def save_avatar_plan(plan: AvatarRenderPlan, logs_dir: Path = LOGS_DIR) -> Path:
    """Write the avatar plan to ``logs/avatar_plan_<run_id>.json`` and return the path."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    out = logs_dir / f"avatar_plan_{plan.run_id}.json"
    out.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Avatar plan saved -> %s", out)
    return out


def print_summary(plan: AvatarRenderPlan) -> None:
    """Print a human-readable run summary to stdout."""
    print("\n" + "=" * 50)
    print("  GenASL — Interpreter-Avatar Run Summary")
    print("=" * 50)
    print(f"  Schema ver  : {plan.schema_version}")
    print(f"  Run ID      : {plan.run_id}")
    print(f"  Video ID    : {plan.video_id}")
    print(f"  Generated   : {plan.generated_at}")
    print(f"  Duration    : {plan.duration_ms / 1000:.2f}s")
    print(f"  Frame rate  : {plan.frame_rate} fps")
    print(f"  Motion frames: {len(plan.motion)}")
    print(f"  NMM frames  : {len(plan.nmm)}")
    print(f"  Plan segs   : {len(plan.plan_segments)}")
    print("=" * 50 + "\n")
