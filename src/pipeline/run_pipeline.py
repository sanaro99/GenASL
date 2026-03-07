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
from src.gloss.translator import GlossTranslator
from src.gloss.word_lookup import WordLookup
from src.gloss.chainer import chain_clips


# ---------------------------------------------------------------------------
# Supported-set asset catalogue (sentence_id → asset metadata)
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load and return the parsed config.yaml."""
    cfg_path = _PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_asset_catalogue() -> dict[str, dict]:
    """Load supported_set CSV and return {sentence_id: {asset_id, duration_ms, english_text, qa_status}}."""
    cfg = _load_config()
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


def _load_asset_manifest() -> dict[str, dict]:
    """Load asset_manifest_v1.json → {asset_id: {file_path, duration_ms, fps, source, …}}.

    Returns an empty dict (with a warning) if the manifest file is missing.
    """
    cfg = _load_config()
    manifest_rel = cfg.get("paths", {}).get("asset_manifest")
    if not manifest_rel:
        logger.warning("No asset_manifest path in config.yaml — clip metadata will be unavailable")
        return {}
    manifest_path = _PROJECT_ROOT / manifest_rel
    if not manifest_path.is_file():
        logger.warning("Asset manifest not found at %s — clip metadata will be unavailable", manifest_path)
        return {}
    with open(manifest_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    manifest: dict[str, dict] = {}
    for entry in data.get("assets", []):
        aid = entry.get("asset_id")
        if aid:
            manifest[aid] = {
                "file_path": entry.get("file_path"),
                "duration_ms": entry.get("duration_ms"),
                "fps": entry.get("fps"),
                "source": entry.get("source"),
                "qa_status": entry.get("qa_status"),
                "width": entry.get("width"),
                "height": entry.get("height"),
                "signer_id": entry.get("signer_id"),
            }
    logger.info("Loaded asset manifest: %d assets", len(manifest))
    return manifest


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
# Short-segment filter (Sprint 3 — Issue 4 fix)
# ---------------------------------------------------------------------------

_MIN_WORD_COUNT = 3
_MIN_DURATION_MS = 2000


def _filter_short_segments(segments: list[dict]) -> tuple[list[dict], list[dict]]:
    """Remove auto-caption artefacts that are too short to be meaningful.

    A segment is filtered when it has fewer than ``_MIN_WORD_COUNT`` words
    **or** a duration shorter than ``_MIN_DURATION_MS`` milliseconds.

    Returns ``(kept, filtered)`` — two lists of segment dicts.
    """
    kept: list[dict] = []
    filtered: list[dict] = []
    for seg in segments:
        word_count = len(seg["text"].split())
        duration = seg["end_ms"] - seg["start_ms"]
        if word_count < _MIN_WORD_COUNT or duration < _MIN_DURATION_MS:
            logger.info(
                "FILTERED %s — %d words, %d ms: %r",
                seg["segment_id"], word_count, duration, seg["text"],
            )
            filtered.append(seg)
        else:
            kept.append(seg)
    if filtered:
        logger.info("Filtered %d short/artefact segments", len(filtered))
    return kept, filtered


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_render_plan(
    run_id: str,
    video_id: str,
    matched_segments: list[dict],
    asset_catalogue: dict[str, dict],
    asset_manifest: dict[str, dict] | None = None,
    filtered_segments: list[dict] | None = None,
) -> dict:
    """Assemble a structured render-plan dict suitable for 3D mapping ingestion."""
    cfg = _load_config()
    if asset_manifest is None:
        asset_manifest = {}

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
        asset_id = asset_info.get("asset_id")

        # Manifest enrichment — actual clip metadata from QA'd files
        manifest_entry = asset_manifest.get(asset_id, {}) if asset_id else {}
        if asset_id and not manifest_entry:
            logger.warning(
                "Asset ID %s (segment %s) not found in manifest — "
                "clip metadata will be null",
                asset_id, seg["segment_id"],
            )

        is_asl = seg["action"] == "ASL"

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
                "asset_id": asset_id,
                "asset_file_path": manifest_entry.get("file_path") if is_asl else None,
                "asset_duration_ms": manifest_entry.get("duration_ms") if is_asl else None,
                "asset_fps": manifest_entry.get("fps") if is_asl else None,
                "qa_status": manifest_entry.get("qa_status") or asset_info.get("qa_status"),
            },
        }
        structured_segments.append(entry)

        # Build the ASL-only overlay track for direct 3D pipeline consumption
        if is_asl and sid:
            asl_overlay_track.append({
                "segment_id": seg["segment_id"],
                "asset_id": asset_id,
                "sentence_id": sid,
                "start_ms": start,
                "end_ms": end,
                "start_tc": _ms_to_timecode(start),
                "end_tc": _ms_to_timecode(end),
                "asset_file_path": manifest_entry.get("file_path"),
                "asset_duration_ms": manifest_entry.get("duration_ms"),
                "asset_fps": manifest_entry.get("fps"),
                "score": score,
            })

    asl_count = sum(1 for s in matched_segments if s["action"] == "ASL")
    cap_count = len(matched_segments) - asl_count
    total = len(matched_segments)
    filtered_count = len(filtered_segments) if filtered_segments else 0

    # Build filtered segment entries (action: "FILTERED")
    filtered_entries: list[dict] = []
    if filtered_segments:
        for seg in filtered_segments:
            start = seg["start_ms"]
            end = seg["end_ms"]
            dur = end - start
            filtered_entries.append({
                "segment_id": seg["segment_id"],
                "source_text": seg["text"],
                "timing": {
                    "start_ms": start,
                    "end_ms": end,
                    "duration_ms": dur,
                    "start_tc": _ms_to_timecode(start),
                    "end_tc": _ms_to_timecode(end),
                },
                "match": {"action": "FILTERED", "reason": "short_or_artefact"},
            })

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
            "filtered_segments": filtered_count,
            "asl_ratio": round(asl_count / total, 4) if total else 0.0,
        },
        "segments": structured_segments,
        "filtered_segments": filtered_entries,
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


# ---------------------------------------------------------------------------
# GenAI gloss-based render plan builder
# ---------------------------------------------------------------------------

def _build_gloss_render_plan(
    run_id: str,
    video_id: str,
    gloss_segments: list[dict],
    filtered_segments: list[dict] | None = None,
) -> dict:
    """Build a render plan from LLM-translated gloss segments with chained word clips.

    Each segment has been enriched with ``gloss_sequence``, ``word_clips``
    (from WordLookup), and ``chained_clip`` (from the chainer).
    """
    cfg = _load_config()
    generated_at = datetime.now(timezone.utc).isoformat()

    structured_segments: list[dict] = []
    asl_overlay_track: list[dict] = []
    asl_count = 0
    cap_count = 0

    for seg in gloss_segments:
        start = seg["start_ms"]
        end = seg["end_ms"]
        dur = end - start
        chained = seg.get("chained_clip")
        gloss_seq = seg.get("gloss_sequence", [])
        word_clips = seg.get("word_clips", [])
        found_count = sum(1 for wc in word_clips if wc.get("found"))

        if chained and found_count > 0:
            action = "ASL"
            asl_count += 1
            coverage = round(found_count / len(gloss_seq), 4) if gloss_seq else 0
        else:
            action = "CAPTIONS"
            cap_count += 1
            coverage = 0

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
                "action": action,
                "gloss_sequence": gloss_seq,
                "gloss_text": seg.get("gloss_text", ""),
                "word_coverage": coverage,
                "found_glosses": [wc["gloss"] for wc in word_clips if wc.get("found")],
                "missing_glosses": [wc["gloss"] for wc in word_clips if not wc.get("found")],
                "chained_clip_path": chained["rel_path"] if chained else None,
                "chained_duration_ms": chained["duration_ms"] if chained else None,
                "chained_clip_count": chained["clip_count"] if chained else 0,
            },
        }
        structured_segments.append(entry)

        if action == "ASL" and chained:
            asl_overlay_track.append({
                "segment_id": seg["segment_id"],
                "asset_id": None,
                "sentence_id": None,
                "start_ms": start,
                "end_ms": end,
                "start_tc": _ms_to_timecode(start),
                "end_tc": _ms_to_timecode(end),
                "asset_file_path": chained["rel_path"],
                "asset_duration_ms": chained["duration_ms"],
                "asset_fps": 25.0,
                "score": coverage,
                "gloss_sequence": gloss_seq,
            })

    total = asl_count + cap_count
    filtered_count = len(filtered_segments) if filtered_segments else 0

    filtered_entries: list[dict] = []
    if filtered_segments:
        for seg in filtered_segments:
            start = seg["start_ms"]
            end = seg["end_ms"]
            dur = end - start
            filtered_entries.append({
                "segment_id": seg["segment_id"],
                "source_text": seg["text"],
                "timing": {
                    "start_ms": start,
                    "end_ms": end,
                    "duration_ms": dur,
                    "start_tc": _ms_to_timecode(start),
                    "end_tc": _ms_to_timecode(end),
                },
                "match": {"action": "FILTERED", "reason": "short_or_artefact"},
            })

    return {
        "schema_version": "3.0",
        "run_id": run_id,
        "video_id": video_id,
        "generated_at": generated_at,
        "pipeline": {
            "mode": "genai_gloss",
            "provider": cfg.get("llm", {}).get("provider", "ollama"),
            "model": cfg.get("llm", {}).get(
                cfg.get("llm", {}).get("provider", "ollama"), {}
            ).get("model", "llama3.2"),
            "confidence_threshold": cfg["matcher"]["confidence_threshold"],
            "supported_set": cfg["paths"]["supported_set"],
        },
        "summary": {
            "total_segments": total,
            "asl_segments": asl_count,
            "captions_segments": cap_count,
            "filtered_segments": filtered_count,
            "asl_ratio": round(asl_count / total, 4) if total else 0.0,
        },
        "segments": structured_segments,
        "filtered_segments": filtered_entries,
        "asl_overlay_track": asl_overlay_track,
    }


def _save_render_plan(plan: dict) -> Path:
    """Write the render plan JSON and return its path."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    out_path = LOGS_DIR / f"render_plan_{plan['run_id']}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2, ensure_ascii=False)
    return out_path


# ---------------------------------------------------------------------------
# Timing overlap detection (Sprint 2)
# ---------------------------------------------------------------------------

def _detect_timing_overlaps(plan: dict) -> int:
    """Check consecutive ASL segments for timing overlaps.

    An overlap occurs when ``start_ms + asset_duration_ms`` of one ASL clip
    exceeds the ``start_ms`` of the next ASL clip.  This means the clip would
    still be playing when the next one is supposed to start.

    Returns the number of overlapping pairs detected.  Each overlap is logged
    as a WARNING but does not crash — the compositing layer will handle
    trimming in Sprint 3.
    """
    track = plan.get("asl_overlay_track", [])
    overlap_count = 0

    for i in range(len(track) - 1):
        cur = track[i]
        nxt = track[i + 1]

        asset_dur = cur.get("asset_duration_ms")
        if asset_dur is None:
            continue

        cur_end = cur["start_ms"] + asset_dur
        if cur_end > nxt["start_ms"]:
            overlap_ms = cur_end - nxt["start_ms"]
            overlap_count += 1
            logger.warning(
                "TIMING OVERLAP: %s (start=%d + dur=%d = %d) overflows into "
                "%s (start=%d) by %d ms",
                cur["segment_id"], cur["start_ms"], asset_dur, cur_end,
                nxt["segment_id"], nxt["start_ms"], overlap_ms,
            )

    if overlap_count:
        logger.warning("Total timing overlaps detected: %d", overlap_count)
    else:
        logger.info("Timing validation passed — no overlaps detected")

    # Store in plan summary for downstream consumers
    plan["summary"]["timing_overlaps"] = overlap_count
    return overlap_count


# ---------------------------------------------------------------------------
# Overlap resolution (Sprint 3 — Issue 3 fix)
# ---------------------------------------------------------------------------

def _resolve_overlaps(plan: dict) -> int:
    """Resolve overlapping ASL overlay entries by keeping the higher-scoring match.

    When two consecutive ASL clips overlap in time the lower-scoring entry is
    marked ``kept: False`` so the compositor can skip it.  The higher-scoring
    entry is marked ``kept: True``.  This prevents two clips from playing
    simultaneously.

    Returns the number of conflicts resolved.
    """
    track = plan.get("asl_overlay_track", [])
    resolved = 0

    # Initialise all entries as kept
    for entry in track:
        entry.setdefault("kept", True)

    i = 0
    while i < len(track) - 1:
        cur = track[i]
        nxt = track[i + 1]

        if not cur.get("kept", True):
            i += 1
            continue

        asset_dur = cur.get("asset_duration_ms")
        if asset_dur is None:
            i += 1
            continue

        cur_end = cur["start_ms"] + asset_dur
        if cur_end > nxt["start_ms"]:
            # Overlap — keep higher score
            cur_score = cur.get("score", 0)
            nxt_score = nxt.get("score", 0)

            if cur_score >= nxt_score:
                loser, winner = nxt, cur
            else:
                loser, winner = cur, nxt

            loser["kept"] = False
            winner["kept"] = True
            resolved += 1

            logger.info(
                "OVERLAP RESOLVED: kept %s (score=%.4f), dropped %s (score=%.4f)",
                winner["segment_id"], winner.get("score", 0),
                loser["segment_id"], loser.get("score", 0),
            )

        i += 1

    if resolved:
        logger.info("Total overlaps resolved: %d", resolved)
    plan["summary"]["overlaps_resolved"] = resolved
    return resolved


def _append_run_log(
    plan: dict,
    output_file: str,
    asset_manifest: dict[str, dict] | None = None,
    timing_overlaps: int = 0,
) -> None:
    """Append a single JSON line to ``logs/run_log.jsonl``."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = LOGS_DIR / "run_log.jsonl"
    summary = plan["summary"]
    if asset_manifest is None:
        asset_manifest = {}

    # Count unique asset IDs used in ASL segments
    asset_ids_used: set[str] = set()
    placeholder_count = 0
    for seg in plan.get("segments", []):
        match = seg.get("match", {})
        if match.get("action") == "ASL":
            aid = match.get("asset_id")
            if aid:
                asset_ids_used.add(aid)
                manifest_entry = asset_manifest.get(aid, {})
                if manifest_entry.get("source") == "placeholder":
                    placeholder_count += 1

    entry = {
        "run_id": plan["run_id"],
        "video_id": plan["video_id"],
        "timestamp": plan["generated_at"],
        "total_segments": summary["total_segments"],
        "asl_segments": summary["asl_segments"],
        "captions_segments": summary["captions_segments"],
        "filtered_segments": summary.get("filtered_segments", 0),
        "output_file": output_file,
        "assets_used": len(asset_ids_used),
        "placeholder_count": placeholder_count,
        "timing_overlaps": timing_overlaps,
        "overlaps_resolved": summary.get("overlaps_resolved", 0),
        "confidence_threshold": plan.get("pipeline", {}).get("confidence_threshold"),
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _print_summary(plan: dict) -> None:
    summary = plan["summary"]
    total = summary["total_segments"]
    asl = summary["asl_segments"]
    cap = summary["captions_segments"]
    filt = summary.get("filtered_segments", 0)
    pct_asl = (asl / total * 100) if total else 0
    pct_cap = (cap / total * 100) if total else 0

    pipeline_info = plan.get("pipeline", {})
    mode = pipeline_info.get("mode", "legacy")

    print("\n" + "=" * 50)
    print("  GenASL Pipeline — Run Summary")
    print("=" * 50)
    print(f"  Schema ver  : {plan['schema_version']}")
    print(f"  Run ID      : {plan['run_id']}")
    print(f"  Video ID    : {plan['video_id']}")
    print(f"  Generated   : {plan['generated_at']}")
    print(f"  Mode        : {mode}")
    print(f"  Model       : {pipeline_info.get('model', 'n/a')}")
    print(f"  Total segs  : {total}")
    print(f"  ASL segs    : {asl:>4d}  ({pct_asl:5.1f}%)")
    print(f"  CAPTIONS    : {cap:>4d}  ({pct_cap:5.1f}%)")
    print(f"  FILTERED    : {filt:>4d}")
    print(f"  ASL track   : {len(plan['asl_overlay_track'])} entries")
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(video_id: str) -> dict:
    """Execute the full pipeline and return the render plan dict.

    Uses the GenAI gloss-based flow:
      1. Fetch transcript
      2. Filter short segments
      3. LLM translates each segment → ASL gloss sequence
      4. Word lookup → map each gloss to word clip
      5. Chain word clips → one chained video per segment
      6. Build render plan
      7. RAI checks + overlap resolution
    """
    run_id = uuid.uuid4().hex[:12]
    cfg = _load_config()

    # 0. Load legacy asset catalogue for backward compat logging
    asset_catalogue = _load_asset_catalogue()
    logger.info("Loaded asset catalogue: %d phrases", len(asset_catalogue))

    # 1. Fetch transcript
    logger.info("=" * 60)
    logger.info("STEP 1 — Fetching transcript for video %s", video_id)
    logger.info("=" * 60)
    segments = fetch_transcript(video_id)
    logger.info("Fetched %d sentence-level segments", len(segments))

    # 1b. Filter short / artefact segments (Sprint 3 — Issue 4)
    logger.info("Filtering short / artefact segments ...")
    segments, filtered_segments = _filter_short_segments(segments)
    logger.info(
        "After filter: %d kept, %d filtered",
        len(segments), len(filtered_segments),
    )

    # 2. LLM Gloss Translation (GenAI)
    logger.info("=" * 60)
    logger.info("STEP 2 — LLM English-to-ASL gloss translation")
    logger.info("=" * 60)
    translator = GlossTranslator()
    gloss_segments = translator.translate_segments(segments)

    # 3. Word Lookup — resolve each gloss to a word clip
    logger.info("=" * 60)
    logger.info("STEP 3 — Word-level clip lookup")
    logger.info("=" * 60)
    word_lookup = WordLookup()
    for seg in gloss_segments:
        glosses = seg.get("gloss_sequence", [])
        if glosses:
            seg["word_clips"] = word_lookup.lookup_sequence(glosses)
        else:
            seg["word_clips"] = []

    # 4. Chain word clips into one video per segment
    logger.info("=" * 60)
    logger.info("STEP 4 — Chaining word clips per segment")
    logger.info("=" * 60)
    for seg in gloss_segments:
        word_clips = seg.get("word_clips", [])
        if word_clips and any(wc.get("found") for wc in word_clips):
            chained = chain_clips(word_clips, seg["segment_id"])
            seg["chained_clip"] = chained
        else:
            seg["chained_clip"] = None

    # 5. Per-segment detail table for evaluators
    logger.info("=" * 60)
    logger.info("STEP 5 — Segment detail table")
    logger.info("=" * 60)
    for seg in gloss_segments:
        chained = seg.get("chained_clip")
        word_clips = seg.get("word_clips", [])
        found = sum(1 for wc in word_clips if wc.get("found"))
        total_g = len(seg.get("gloss_sequence", []))
        logger.info(
            "  %-8s | gloss=%s | clips=%d/%d | chained=%s | %d-%d ms | %r",
            seg["segment_id"],
            seg.get("gloss_text", "")[:40],
            found, total_g,
            "yes" if chained else "no",
            seg["start_ms"],
            seg["end_ms"],
            seg["text"][:60],
        )

    # 6. Build render plan
    logger.info("=" * 60)
    logger.info("STEP 6 — Building render plan")
    logger.info("=" * 60)
    plan = _build_gloss_render_plan(run_id, video_id, gloss_segments, filtered_segments)

    # 7. Responsible-AI checks
    logger.info("Running responsible-AI checks ...")
    _responsible_ai_warnings(plan)

    # 7b. Timing overlap validation (Sprint 2)
    logger.info("Running timing overlap validation ...")
    timing_overlaps = _detect_timing_overlaps(plan)

    # 7c. Resolve overlaps (Sprint 3)
    logger.info("Resolving timing overlaps ...")
    _resolve_overlaps(plan)

    # 8. Save render plan
    output_file = ""
    try:
        out_path = _save_render_plan(plan)
        output_file = str(out_path)
        logger.info("Render plan saved -> %s", out_path)
    except Exception:
        logger.exception("Failed to save render plan JSON")

    # 9. Append run log
    try:
        _append_run_log(plan, output_file, timing_overlaps=timing_overlaps)
        logger.info("Run log entry appended -> logs/run_log.jsonl")
    except Exception:
        logger.exception("Failed to append run log entry")

    # 10. Print human-readable summary
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
