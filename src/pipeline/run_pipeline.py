"""GenASL end-to-end pipeline — fetch transcript, match, produce render plan.

Usage::

    python -m src.pipeline.run_pipeline <VIDEO_ID>
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ensure project root is on sys.path so relative imports work when running as script
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.transcript_ingestion.fetcher import fetch_transcript, NoTranscriptError
from src.matcher.matcher import Matcher

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

LOGS_DIR = _PROJECT_ROOT / "logs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_render_plan(
    run_id: str,
    video_id: str,
    matched_segments: list[dict],
) -> dict:
    """Assemble the render-plan dict."""
    asl_segs = [s for s in matched_segments if s["action"] == "ASL"]
    cap_segs = [s for s in matched_segments if s["action"] == "CAPTIONS"]

    return {
        "run_id": run_id,
        "video_id": video_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_segments": len(matched_segments),
        "asl_segments": len(asl_segs),
        "captions_segments": len(cap_segs),
        "segments": matched_segments,
    }


def _responsible_ai_warnings(plan: dict) -> None:
    """Emit warnings for suspicious pipeline outputs."""
    total = plan["total_segments"]
    asl = plan["asl_segments"]

    if total == 0:
        logger.warning(
            "RAI WARNING: Pipeline produced 0 segments for video %s — "
            "verify the transcript is available.",
            plan["video_id"],
        )
        return

    ratio = asl / total
    if ratio > 0.90:
        logger.warning(
            "RAI WARNING: %.0f%% of segments matched to ASL (%d/%d). "
            "This is suspiciously high — review match quality.",
            ratio * 100,
            asl,
            total,
        )


def _save_render_plan(plan: dict) -> Path:
    """Write the render plan JSON and return its path."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    out_path = LOGS_DIR / f"render_plan_{plan['run_id']}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2, ensure_ascii=False)
    return out_path


def _append_run_log(plan: dict, output_file: str) -> None:
    """Append a single JSON line to ``logs/run_log.jsonl``."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = LOGS_DIR / "run_log.jsonl"
    entry = {
        "run_id": plan["run_id"],
        "video_id": plan["video_id"],
        "timestamp": plan["generated_at"],
        "total_segments": plan["total_segments"],
        "asl_segments": plan["asl_segments"],
        "captions_segments": plan["captions_segments"],
        "output_file": output_file,
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _print_summary(plan: dict) -> None:
    total = plan["total_segments"]
    asl = plan["asl_segments"]
    cap = plan["captions_segments"]
    pct_asl = (asl / total * 100) if total else 0
    pct_cap = (cap / total * 100) if total else 0

    print("\n" + "=" * 50)
    print("  GenASL Pipeline — Run Summary")
    print("=" * 50)
    print(f"  Run ID      : {plan['run_id']}")
    print(f"  Video ID    : {plan['video_id']}")
    print(f"  Generated   : {plan['generated_at']}")
    print(f"  Total segs  : {total}")
    print(f"  ASL segs    : {asl:>4d}  ({pct_asl:5.1f}%)")
    print(f"  CAPTIONS    : {cap:>4d}  ({pct_cap:5.1f}%)")
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(video_id: str) -> dict:
    """Execute the full pipeline and return the render plan dict."""
    run_id = uuid.uuid4().hex[:12]

    # 1. Fetch transcript
    logger.info("Fetching transcript for video %s …", video_id)
    segments = fetch_transcript(video_id)
    logger.info("Fetched %d segments", len(segments))

    # 2. Match against supported set
    logger.info("Loading matcher …")
    matcher = Matcher()
    matched = matcher.match_all(segments)
    logger.info("Matching complete")

    # 3. Build render plan
    plan = _build_render_plan(run_id, video_id, matched)

    # 4. Responsible-AI checks
    _responsible_ai_warnings(plan)

    # 5. Save render plan (separate try so run_log still gets written)
    output_file = ""
    try:
        out_path = _save_render_plan(plan)
        output_file = str(out_path)
        logger.info("Render plan saved → %s", out_path)
    except Exception:
        logger.exception("Failed to save render plan JSON")

    # 6. Append run log (must always succeed independently)
    try:
        _append_run_log(plan, output_file)
        logger.info("Run log entry appended → logs/run_log.jsonl")
    except Exception:
        logger.exception("Failed to append run log entry")

    # 7. Print human-readable summary
    _print_summary(plan)

    return plan


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline.run_pipeline <VIDEO_ID>")
        sys.exit(1)

    vid = sys.argv[1]
    try:
        run(vid)
    except NoTranscriptError as exc:
        logger.error("No English transcript available: %s", exc)
        sys.exit(2)
    except ValueError as exc:
        logger.error("Invalid input: %s", exc)
        sys.exit(1)
