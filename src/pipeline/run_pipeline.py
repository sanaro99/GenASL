"""GenASL end-to-end pipeline — fetch transcript, match, produce render plan.

Usage::

    python -m src.pipeline.run_pipeline <VIDEO_ID>
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ensure project root is on sys.path so relative imports work when running as script
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.transcript_ingestion.fetcher import fetch_transcript, NoTranscriptError
from src.matcher.matcher import Matcher


# ---------------------------------------------------------------------------
# Supported-set asset catalogue (sentence_id → asset metadata)
# ---------------------------------------------------------------------------

def _load_asset_catalogue() -> dict[str, dict]:
    """Load supported_set CSV and return {sentence_id: {asset_id, duration_ms, english_text, qa_status}}."""
    cfg_path = _PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    csv_path = _PROJECT_ROOT / cfg["paths"]["supported_set"]
    catalogue: dict[str, dict] = {}
    with open(csv_path, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            catalogue[row["sentence_id"]] = {
                "asset_id": row["asset_id"],
                "duration_ms": int(row["duration_ms"]),
                "english_text": row["english_text"],
                "qa_status": row["qa_status"],
            }
    return catalogue


def _ms_to_timecode(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS.mmm timecode string."""
    total_s, millis = divmod(ms, 1000)
    mins, secs = divmod(total_s, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Logging configuration — console + file
# ---------------------------------------------------------------------------
LOGS_DIR = _PROJECT_ROOT / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

_LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"

# Root logger at DEBUG so file handler captures everything
logging.basicConfig(level=logging.DEBUG, format=_LOG_FORMAT, handlers=[])

# Console handler — INFO level (concise output)
_console_h = logging.StreamHandler()
_console_h.setLevel(logging.INFO)
_console_h.setFormatter(logging.Formatter(_LOG_FORMAT))
logging.getLogger().addHandler(_console_h)

# File handler — DEBUG level (full trace for evaluators)
_file_h = logging.FileHandler(LOGS_DIR / "pipeline_debug.log", mode="w", encoding="utf-8")
_file_h.setLevel(logging.DEBUG)
_file_h.setFormatter(logging.Formatter(_LOG_FORMAT))
logging.getLogger().addHandler(_file_h)

logger.info("Log file: %s", LOGS_DIR / "pipeline_debug.log")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_render_plan(
    run_id: str,
    video_id: str,
    matched_segments: list[dict],
    asset_catalogue: dict[str, dict],
) -> dict:
    """Assemble a structured render-plan dict suitable for 3D mapping ingestion."""
    cfg_path = _PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    generated_at = datetime.now(timezone.utc).isoformat()

    # ── Build structured segments ────────────────────────────────
    structured_segments: list[dict] = []
    asl_overlay_track: list[dict] = []

    for seg in matched_segments:
        start = seg["start_ms"]
        end = seg["end_ms"]
        dur = end - start

        # Confidence label
        score = seg["score"]
        if score >= 0.95:
            confidence = "high"
        elif score >= cfg["matcher"]["confidence_threshold"]:
            confidence = "medium"
        else:
            confidence = "low"

        # Asset lookup for ASL matches
        sid = seg.get("sentence_id")
        asset_info = asset_catalogue.get(sid, {}) if sid else {}

        entry = {
            "segment_id": seg["segment_id"],
            "source_text": seg["text"],
            "timing": {
                "start_ms": start,
                "end_ms": end,
                "duration_ms": dur,
                "start_tc": _ms_to_timecode(start),
                "end_tc": _ms_to_timecode(end),
            },
            "match": {
                "action": seg["action"],
                "score": score,
                "confidence": confidence,
                "sentence_id": sid,
                "matched_english": asset_info.get("english_text"),
                "asset_id": asset_info.get("asset_id"),
                "asset_duration_ms": asset_info.get("duration_ms"),
                "qa_status": asset_info.get("qa_status"),
            },
        }
        structured_segments.append(entry)

        # Build the ASL-only overlay track for direct 3D pipeline consumption
        if seg["action"] == "ASL" and sid:
            asl_overlay_track.append({
                "segment_id": seg["segment_id"],
                "asset_id": asset_info.get("asset_id"),
                "sentence_id": sid,
                "start_ms": start,
                "end_ms": end,
                "start_tc": _ms_to_timecode(start),
                "end_tc": _ms_to_timecode(end),
                "asset_duration_ms": asset_info.get("duration_ms"),
                "score": score,
            })

    asl_count = sum(1 for s in matched_segments if s["action"] == "ASL")
    cap_count = len(matched_segments) - asl_count
    total = len(matched_segments)

    return {
        "schema_version": "2.0",
        "run_id": run_id,
        "video_id": video_id,
        "generated_at": generated_at,
        "pipeline": {
            "model": cfg["matcher"]["model_name"],
            "confidence_threshold": cfg["matcher"]["confidence_threshold"],
            "supported_set": cfg["paths"]["supported_set"],
            "index_vectors": 150,
            "unique_phrases": len(asset_catalogue),
        },
        "summary": {
            "total_segments": total,
            "asl_segments": asl_count,
            "captions_segments": cap_count,
            "asl_ratio": round(asl_count / total, 4) if total else 0.0,
        },
        "segments": structured_segments,
        "asl_overlay_track": asl_overlay_track,
    }


def _responsible_ai_warnings(plan: dict) -> None:
    """Emit warnings for suspicious pipeline outputs."""
    summary = plan["summary"]
    total = summary["total_segments"]
    asl = summary["asl_segments"]

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
    summary = plan["summary"]
    entry = {
        "run_id": plan["run_id"],
        "video_id": plan["video_id"],
        "timestamp": plan["generated_at"],
        "total_segments": summary["total_segments"],
        "asl_segments": summary["asl_segments"],
        "captions_segments": summary["captions_segments"],
        "output_file": output_file,
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _print_summary(plan: dict) -> None:
    summary = plan["summary"]
    total = summary["total_segments"]
    asl = summary["asl_segments"]
    cap = summary["captions_segments"]
    pct_asl = (asl / total * 100) if total else 0
    pct_cap = (cap / total * 100) if total else 0

    print("\n" + "=" * 50)
    print("  GenASL Pipeline — Run Summary")
    print("=" * 50)
    print(f"  Schema ver  : {plan['schema_version']}")
    print(f"  Run ID      : {plan['run_id']}")
    print(f"  Video ID    : {plan['video_id']}")
    print(f"  Generated   : {plan['generated_at']}")
    print(f"  Model       : {plan['pipeline']['model']}")
    print(f"  Threshold   : {plan['pipeline']['confidence_threshold']}")
    print(f"  Total segs  : {total}")
    print(f"  ASL segs    : {asl:>4d}  ({pct_asl:5.1f}%)")
    print(f"  CAPTIONS    : {cap:>4d}  ({pct_cap:5.1f}%)")
    print(f"  ASL track   : {len(plan['asl_overlay_track'])} entries")
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(video_id: str) -> dict:
    """Execute the full pipeline and return the render plan dict."""
    run_id = uuid.uuid4().hex[:12]

    # 0. Load asset catalogue for enrichment
    asset_catalogue = _load_asset_catalogue()
    logger.info("Loaded asset catalogue: %d phrases", len(asset_catalogue))

    # 1. Fetch transcript
    logger.info("=" * 60)
    logger.info("STEP 1 — Fetching transcript for video %s", video_id)
    logger.info("=" * 60)
    segments = fetch_transcript(video_id)
    logger.info("Fetched %d sentence-level segments", len(segments))

    # 2. Match against supported set
    logger.info("=" * 60)
    logger.info("STEP 2 — Semantic matching against supported ASL set")
    logger.info("=" * 60)
    logger.info("Loading matcher …")
    matcher = Matcher()
    matched = matcher.match_all(segments)

    # 3. Per-segment detail table for evaluators
    logger.info("=" * 60)
    logger.info("STEP 3 — Segment detail table")
    logger.info("=" * 60)
    for seg in matched:
        logger.info(
            "  %-8s | %-8s | score=%.4f | sid=%-6s | %d–%d ms | %r",
            seg["segment_id"],
            seg["action"],
            seg["score"],
            seg.get("sentence_id") or "—",
            seg["start_ms"],
            seg["end_ms"],
            seg["text"][:60],
        )

    # 4. Build render plan
    logger.info("=" * 60)
    logger.info("STEP 4 — Building render plan")
    logger.info("=" * 60)
    plan = _build_render_plan(run_id, video_id, matched, asset_catalogue)

    # 5. Responsible-AI checks
    logger.info("Running responsible-AI checks …")
    _responsible_ai_warnings(plan)

    # 6. Save render plan (separate try so run_log still gets written)
    output_file = ""
    try:
        out_path = _save_render_plan(plan)
        output_file = str(out_path)
        logger.info("Render plan saved → %s", out_path)
    except Exception:
        logger.exception("Failed to save render plan JSON")

    # 7. Append run log (must always succeed independently)
    try:
        _append_run_log(plan, output_file)
        logger.info("Run log entry appended → logs/run_log.jsonl")
    except Exception:
        logger.exception("Failed to append run log entry")

    # 8. Print human-readable summary
    _print_summary(plan)
    logger.info("Full debug log written to: %s", LOGS_DIR / "pipeline_debug.log")

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
