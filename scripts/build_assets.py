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

from scripts.trim_and_standardize import (
    download_clip,
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


def _pick_best_instance(instances: list[dict]) -> dict | None:
    """Pick the best WLASL instance (prefer split=train, shortest clip)."""
    if not instances:
        return None
    # Prefer train split, then shortest clip
    scored = []
    for inst in instances:
        split_priority = 0 if inst.get("split") == "train" else 1
        bbox = inst.get("frame_end", 0) - inst.get("frame_start", 0)
        scored.append((split_priority, bbox, inst))
    scored.sort(key=lambda x: (x[0], x[1]))
    return scored[0][2]


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
                yt_id = inst.get("video_id", "")
                # WLASL timestamps are in frames; some entries use seconds
                # The dataset uses frame_start/frame_end at ~25fps
                fps_src = inst.get("fps", 25) or 25
                frame_start = inst.get("frame_start", 0) or 0
                frame_end = inst.get("frame_end", 0) or 0
                start_sec = frame_start / fps_src
                end_sec = frame_end / fps_src

                if yt_id and end_sec > start_sec:
                    raw_path = str(RAW_DIR / f"{yt_id}.mp4")
                    trimmed_path = str(TRIMMED_DIR / f"{aid}_trimmed.mp4")

                    # Step A: Download (skip if already cached)
                    if os.path.isfile(raw_path):
                        logger.info("Raw clip cached: %s", raw_path)
                        dl_ok = True
                    else:
                        dl_ok = download_clip(yt_id, raw_path)

                    # Step B: Trim
                    trim_ok = False
                    if dl_ok:
                        trim_ok = trim_clip(raw_path, trimmed_path, start_sec, end_sec)

                    # Step C: Standardize
                    std_ok = False
                    if trim_ok:
                        std_ok = standardize_clip(trimmed_path, final_path)

                    if std_ok:
                        asset_entry["source"] = "wlasl"
                        asset_entry["wlasl_video_id"] = yt_id
                        stats["wlasl"] += 1
                        logger.info("✓ %s from WLASL (video=%s)", aid, yt_id)
                    else:
                        # Fall back to placeholder
                        logger.warning("Pipeline failed for %s — using placeholder", aid)
                        shutil.copy2(str(PLACEHOLDER_PATH), final_path)
                        stats["placeholder"] += 1
                else:
                    logger.warning("Bad WLASL entry for %s (no video_id or bad timestamps)", keyword)
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
