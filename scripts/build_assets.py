"""Master orchestration script — build all 50 ASL asset clips.

Reads keyword_map.csv, looks up each keyword in the WLASL index,
downloads / trims / standardizes clips, and falls back to placeholder
when a keyword is not found in WLASL.

Usage::

    python scripts/build_assets.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

import re

from scripts.trim_and_standardize import (
    download_clip,
    download_url,
    trim_clip,
    standardize_clip,
    run_qa_check,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
SUPPORTED_SET_PATH = _PROJECT_ROOT / "data" / "supported_set_v1.csv"
KEYWORD_MAP_PATH = _PROJECT_ROOT / "scripts" / "keyword_map.csv"
WLASL_INDEX_PATH = _PROJECT_ROOT / "data" / "wlasl_index.json"
MANIFEST_PATH = _PROJECT_ROOT / "assets" / "asset_manifest_v1.json"
RAW_DIR = _PROJECT_ROOT / "assets" / "raw"
TRIMMED_DIR = _PROJECT_ROOT / "assets" / "trimmed"
FINAL_DIR = _PROJECT_ROOT / "assets" / "final"
PLACEHOLDER_PATH = _PROJECT_ROOT / "assets" / "placeholders" / "placeholder.mp4"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_supported_set() -> list[dict]:
    with open(SUPPORTED_SET_PATH, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _load_keyword_map() -> dict[str, dict]:
    """Return {sentence_id: {asl_keyword, english_text, notes}}."""
    kw_map: dict[str, dict] = {}
    with open(KEYWORD_MAP_PATH, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            kw_map[row["sentence_id"]] = {
                "asl_keyword": row["asl_keyword"].strip().upper(),
                "english_text": row["english_text"],
                "notes": row.get("notes", ""),
            }
    return kw_map


def _load_wlasl_index() -> dict[str, list]:
    """Return {GLOSS: [instances]} from the WLASL dataset JSON."""
    with open(WLASL_INDEX_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    index: dict[str, list] = {}
    for entry in raw:
        gloss = entry.get("gloss", "").strip().upper()
        instances = entry.get("instances", [])
        if gloss:
            index[gloss] = instances
            # Also store without hyphen for fallback matching
            alt = gloss.replace("-", " ")
            if alt != gloss:
                index[alt] = instances
    return index


def _extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from a URL, or return None."""
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})', url or '')
    return m.group(1) if m else None


def _pick_best_instance(instances: list[dict]) -> dict | None:
    """Pick the best WLASL instance.

    Priority:
    1. Prefer instances with valid timestamps (frame_end > frame_start > 0)
    2. Prefer split=train
    3. Prefer shorter clips (fewer frames)
    """
    if not instances:
        return None
    scored = []
    for inst in instances:
        url = inst.get("url", "")
        if not url:
            continue
        frame_start = inst.get("frame_start", 0) or 0
        frame_end = inst.get("frame_end", -1)
        # frame_end == -1 means "whole clip" — still valid
        has_good_timestamps = (frame_end > frame_start) if frame_end != -1 else True
        split_priority = 0 if inst.get("split") == "train" else 1
        # For sorting: prefer short clips; whole-clip entries get a large number
        span = (frame_end - frame_start) if (frame_end > 0 and frame_end > frame_start) else 9999
        ts_priority = 0 if has_good_timestamps else 1
        scored.append((ts_priority, split_priority, span, inst))
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], x[1], x[2]))
    return scored[0][3]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_all() -> None:
    """Download, trim, standardize all 50 asset clips."""
    supported = _load_supported_set()
    kw_map = _load_keyword_map()
    wlasl = _load_wlasl_index()

    # Ensure dirs exist
    for d in [RAW_DIR, TRIMMED_DIR, FINAL_DIR]:
        os.makedirs(d, exist_ok=True)

    if not PLACEHOLDER_PATH.is_file():
        logger.error(
            "Placeholder clip not found at %s. Run create_placeholder.py first.",
            PLACEHOLDER_PATH,
        )
        sys.exit(1)

    manifest_assets: list[dict] = []
    stats = {"wlasl": 0, "placeholder": 0, "failed": 0}

    for row in supported:
        sid = row["sentence_id"]
        aid = row["asset_id"]
        kw_info = kw_map.get(sid, {})
        keyword = kw_info.get("asl_keyword", "")
        english = kw_info.get("english_text", row["english_text"])

        logger.info("─" * 50)
        logger.info("Processing %s / %s  keyword=%s", sid, aid, keyword)

        asset_entry = {
            "asset_id": aid,
            "sentence_id": sid,
            "asl_keyword": keyword,
            "source": "placeholder",
            "file_path": f"assets/final/{aid}.mp4",
            "fps": 25,
            "duration_ms": 0,
            "width": 320,
            "height": 240,
            "qa_status": "pending",
            "qa_issues": [],
            "wlasl_video_id": "",
            "notes": kw_info.get("notes", ""),
        }

        final_path = str(FINAL_DIR / f"{aid}.mp4")

        # Try to find keyword in WLASL
        instances = wlasl.get(keyword, [])
        if not instances:
            # Try without hyphen
            instances = wlasl.get(keyword.replace("-", " "), [])

        if instances:
            inst = _pick_best_instance(instances)
            if inst:
                url = inst.get("url", "")
                yt_id = _extract_youtube_id(url)
                wlasl_vid_id = inst.get("video_id", "")
                fps_src = inst.get("fps", 25) or 25
                frame_start = inst.get("frame_start", 0) or 0
                frame_end = inst.get("frame_end", -1)
                whole_clip = (frame_end == -1)

                if whole_clip:
                    start_sec = 0.0
                    end_sec = 0.0  # will skip trim step
                else:
                    start_sec = frame_start / fps_src
                    end_sec = frame_end / fps_src

                # Use a cache key based on wlasl instance video_id
                cache_key = wlasl_vid_id or (yt_id or aid)
                raw_path = str(RAW_DIR / f"{cache_key}.mp4")
                trimmed_path = str(TRIMMED_DIR / f"{aid}_trimmed.mp4")

                # Step A: Download (skip if already cached)
                dl_ok = False
                if os.path.isfile(raw_path):
                    logger.info("Raw clip cached: %s", raw_path)
                    dl_ok = True
                elif yt_id:
                    dl_ok = download_clip(yt_id, raw_path)
                elif url:
                    dl_ok = download_url(url, raw_path)
                else:
                    logger.warning("No URL for %s instance", keyword)

                # Step B: Trim (skip if whole_clip — go straight to standardize)
                if dl_ok and not whole_clip and end_sec > start_sec:
                    trim_ok = trim_clip(raw_path, trimmed_path, start_sec, end_sec)
                elif dl_ok:
                    # Whole clip or no timestamps: skip trim, standardize from raw
                    trimmed_path = raw_path
                    trim_ok = True
                else:
                    trim_ok = False

                # Step C: Standardize
                std_ok = False
                if trim_ok:
                    std_ok = standardize_clip(trimmed_path, final_path)

                if std_ok:
                    asset_entry["source"] = "wlasl"
                    asset_entry["wlasl_video_id"] = yt_id or wlasl_vid_id
                    stats["wlasl"] += 1
                    logger.info("✓ %s from WLASL (url=%s)", aid, url[:60])
                else:
                    # Fall back to placeholder
                    logger.warning("Pipeline failed for %s — using placeholder", aid)
                    shutil.copy2(str(PLACEHOLDER_PATH), final_path)
                    stats["placeholder"] += 1
            else:
                logger.warning("No usable WLASL instance for %s", keyword)
                shutil.copy2(str(PLACEHOLDER_PATH), final_path)
                stats["placeholder"] += 1
        else:
            logger.info("Keyword %s not in WLASL — using placeholder", keyword)
            shutil.copy2(str(PLACEHOLDER_PATH), final_path)
            stats["placeholder"] += 1

        # QA the final clip
        qa = run_qa_check(final_path)
        asset_entry["duration_ms"] = qa["duration_ms"]
        asset_entry["width"] = qa["width"]
        asset_entry["height"] = qa["height"]
        asset_entry["fps"] = qa["fps"]
        asset_entry["qa_status"] = "approved" if qa["passed"] else "needs_review"
        asset_entry["qa_issues"] = qa["issues"]

        manifest_assets.append(asset_entry)

    # ── Write manifest ───────────────────────────────────────────────
    manifest = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_assets": len(manifest_assets),
        "assets": manifest_assets,
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    logger.info("Manifest written → %s", MANIFEST_PATH)

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("  Asset Build Summary")
    print("=" * 50)
    print(f"  Total assets  : {len(manifest_assets)}")
    print(f"  From WLASL    : {stats['wlasl']}")
    print(f"  Placeholder   : {stats['placeholder']}")
    print(f"  Failed        : {stats['failed']}")
    print("=" * 50)


if __name__ == "__main__":
    build_all()
