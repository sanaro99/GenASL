"""Render-plan I/O helpers — save JSON, append to the JSONL run log, print summary.

These operate on the typed :class:`RenderPlan` model. They're separated from
the orchestrator so the Pipeline doesn't have to know about disk paths or
console formatting.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.core.paths import LOGS_DIR
from src.pipeline.models import RenderPlan

logger = logging.getLogger(__name__)


def save_render_plan(plan: RenderPlan, logs_dir: Path = LOGS_DIR) -> Path:
    """Write the render plan to ``logs/render_plan_<run_id>.json`` and return the path."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    out = logs_dir / f"render_plan_{plan.run_id}.json"
    out.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Render plan saved -> %s", out)
    return out


def append_run_log(
    plan: RenderPlan,
    output_file: str = "",
    logs_dir: Path = LOGS_DIR,
) -> None:
    """Append a single JSON line to ``logs/run_log.jsonl``."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "run_log.jsonl"
    s = plan.summary
    entry = {
        "run_id": plan.run_id,
        "video_id": plan.video_id,
        "timestamp": plan.generated_at,
        "provider": plan.pipeline.provider,
        "model": plan.pipeline.model,
        "total_segments": s.total_segments,
        "asl_segments": s.asl_segments,
        "captions_segments": s.captions_segments,
        "filtered_segments": s.filtered_segments,
        "asl_ratio": s.asl_ratio,
        "output_file": output_file,
        "timing_overlaps": s.timing_overlaps,
        "overlaps_resolved": s.overlaps_resolved,
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def print_summary(plan: RenderPlan) -> None:
    """Print a human-readable run summary to stdout."""
    s = plan.summary
    total = s.total_segments
    pct_asl = (s.asl_segments / total * 100) if total else 0
    pct_cap = (s.captions_segments / total * 100) if total else 0

    print("\n" + "=" * 50)
    print("  GenASL Pipeline — Run Summary")
    print("=" * 50)
    print(f"  Schema ver  : {plan.schema_version}")
    print(f"  Run ID      : {plan.run_id}")
    print(f"  Video ID    : {plan.video_id}")
    print(f"  Generated   : {plan.generated_at}")
    print(f"  Provider    : {plan.pipeline.provider}")
    print(f"  Model       : {plan.pipeline.model}")
    print(f"  Total segs  : {total}")
    print(f"  ASL segs    : {s.asl_segments:>4d}  ({pct_asl:5.1f}%)")
    print(f"  CAPTIONS    : {s.captions_segments:>4d}  ({pct_cap:5.1f}%)")
    print(f"  FILTERED    : {s.filtered_segments:>4d}")
    print(f"  ASL track   : {len(plan.asl_overlay_track)} entries")
    print("=" * 50 + "\n")
