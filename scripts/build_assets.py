"""Master orchestration script — build all 50 ASL asset clips.

Reads keyword_map.csv, looks up each keyword in the WLASL index,
downloads / trims / standardises clips from a preferred signer, and
falls back to placeholder only when **all** instances are exhausted.

Changes vs v1
--------------
* Signer preference chain (default: 9 → 109 → 12 → any) for visual
  consistency across clips.
* Multi-instance retry — every viable instance is attempted before
  falling back to placeholder.
* Descriptive filenames: ``A001_S001_GUM.mp4`` instead of ``A001.mp4``.
* ``signer_id`` recorded in manifest.

Usage::

    python scripts/build_assets.py
"""

from __future__ import annotations

import csv
import glob
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

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
CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load config.yaml and return parsed dict."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from a URL, or return None."""
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})', url or '')
    return m.group(1) if m else None


def _safe_filename_keyword(keyword: str) -> str:
    """Sanitise a keyword for use in a filename (spaces/hyphens → underscores)."""
    return re.sub(r'[^A-Za-z0-9_]', '_', keyword.replace("-", "_").replace(" ", "_")).upper()


def _rank_instances(
    instances: list[dict],
    preferred_signers: list[int],
) -> list[dict]:
    """Return **all** viable instances ranked by signer preference then quality.

    Scoring (ascending = better):
        0. signer_rank  — index in ``preferred_signers`` list; len+1 for unknown
        1. ts_priority  — 0 if valid timestamps, 1 otherwise
        2. split_rank   — 0 for train, 1 for other
        3. span         — frame count (shorter better); 9999 for whole-clip
    """
    if not instances:
        return []

    signer_lookup = {sid: idx for idx, sid in enumerate(preferred_signers)}
    fallback_rank = len(preferred_signers) + 1

    scored: list[tuple] = []
    for inst in instances:
        url = inst.get("url", "")
        if not url:
            continue
        signer_id = inst.get("signer_id")
        signer_rank = signer_lookup.get(signer_id, fallback_rank)

        frame_start = inst.get("frame_start", 0) or 0
        frame_end = inst.get("frame_end", -1)
        has_good_ts = (frame_end > frame_start) if frame_end != -1 else True
        ts_priority = 0 if has_good_ts else 1
        split_rank = 0 if inst.get("split") == "train" else 1
        span = (frame_end - frame_start) if (frame_end > 0 and frame_end > frame_start) else 9999

        scored.append((signer_rank, ts_priority, split_rank, span, inst))

    scored.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    return [s[4] for s in scored]


def _try_download_trim_standardise(inst: dict, aid: str, final_path: str) -> bool:
    """Attempt full pipeline (download → trim → standardise) for one instance.

    Returns True on success, False on any failure.
    """
    url = inst.get("url", "")
    yt_id = _extract_youtube_id(url)
    wlasl_vid_id = inst.get("video_id", "")
    fps_src = inst.get("fps", 25) or 25
    frame_start = inst.get("frame_start", 0) or 0
    frame_end = inst.get("frame_end", -1)
    whole_clip = (frame_end == -1)

    if whole_clip:
        start_sec = 0.0
        end_sec = 0.0
    else:
        start_sec = frame_start / fps_src
        end_sec = frame_end / fps_src

    cache_key = wlasl_vid_id or (yt_id or aid)
    raw_path = str(RAW_DIR / f"{cache_key}.mp4")
    trimmed_path = str(TRIMMED_DIR / f"{aid}_trimmed.mp4")

    # Step A: Download (skip if cached)
    dl_ok = False
    if os.path.isfile(raw_path):
        logger.info("  Raw clip cached: %s", raw_path)
        dl_ok = True
    elif yt_id:
        dl_ok = download_clip(yt_id, raw_path)
    elif url:
        dl_ok = download_url(url, raw_path)
    else:
        logger.warning("  No URL for instance video_id=%s", wlasl_vid_id)

    if not dl_ok:
        return False

    # Step B: Trim (skip for whole-clip entries)
    if not whole_clip and end_sec > start_sec:
        trim_ok = trim_clip(raw_path, trimmed_path, start_sec, end_sec)
    else:
        trimmed_path = raw_path
        trim_ok = True

    if not trim_ok:
        return False

    # Step C: Standardise
    return standardize_clip(trimmed_path, final_path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_all() -> None:
    """Download, trim, standardise all 50 asset clips."""
    cfg = _load_config()
    preferred_signers: list[int] = cfg.get("build", {}).get("preferred_signer_ids", [9, 109, 12])
    logger.info("Preferred signer chain: %s", preferred_signers)

    supported = _load_supported_set()
    kw_map = _load_keyword_map()
    wlasl = _load_wlasl_index()

    # Ensure dirs exist
    for d in [RAW_DIR, TRIMMED_DIR, FINAL_DIR]:
        os.makedirs(d, exist_ok=True)

    # Clean old final clips (filenames are changing)
    old_clips = glob.glob(str(FINAL_DIR / "*.mp4"))
    if old_clips:
        logger.info("Cleaning %d old final clips …", len(old_clips))
        for f in old_clips:
            os.remove(f)

    if not PLACEHOLDER_PATH.is_file():
        logger.error(
            "Placeholder clip not found at %s. Run create_placeholder.py first.",
            PLACEHOLDER_PATH,
        )
        sys.exit(1)

    manifest_assets: list[dict] = []
    stats = {"wlasl": 0, "placeholder": 0}

    for row in supported:
        sid = row["sentence_id"]
        aid = row["asset_id"]
        kw_info = kw_map.get(sid, {})
        keyword = kw_info.get("asl_keyword", "")
        safe_kw = _safe_filename_keyword(keyword)

        logger.info("─" * 50)
        logger.info("Processing %s / %s  keyword=%s", sid, aid, keyword)

        # New filename convention: A001_S001_GUM.mp4
        final_name = f"{aid}_{sid}_{safe_kw}.mp4"
        final_path = str(FINAL_DIR / final_name)

        asset_entry = {
            "asset_id": aid,
            "sentence_id": sid,
            "asl_keyword": keyword,
            "source": "placeholder",
            "file_path": f"assets/final/{final_name}",
            "fps": 25,
            "duration_ms": 0,
            "width": 320,
            "height": 240,
            "qa_status": "pending",
            "qa_issues": [],
            "wlasl_video_id": "",
            "signer_id": None,
            "notes": kw_info.get("notes", ""),
        }

        # Try to find keyword in WLASL
        instances = wlasl.get(keyword, [])
        if not instances:
            instances = wlasl.get(keyword.replace("-", " "), [])

        success = False
        if instances:
            ranked = _rank_instances(instances, preferred_signers)
            total_instances = len(ranked)
            for idx, inst in enumerate(ranked, 1):
                signer = inst.get("signer_id")
                url = inst.get("url", "")[:60]
                logger.info(
                    "  Trying instance %d/%d  signer=%s  url=%s",
                    idx, total_instances, signer, url,
                )
                if _try_download_trim_standardise(inst, aid, final_path):
                    yt_id = _extract_youtube_id(inst.get("url", ""))
                    asset_entry["source"] = "wlasl"
                    asset_entry["wlasl_video_id"] = yt_id or inst.get("video_id", "")
                    asset_entry["signer_id"] = signer
                    stats["wlasl"] += 1
                    logger.info(
                        "✓ %s from WLASL  signer=%s  (instance %d/%d)",
                        aid, signer, idx, total_instances,
                    )
                    success = True
                    break
                else:
                    logger.info("  ✗ Instance %d/%d failed — trying next", idx, total_instances)

        if not success:
            if instances:
                logger.warning(
                    "All %d instances failed for %s/%s — using placeholder",
                    len(instances), aid, keyword,
                )
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
        "version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_assets": len(manifest_assets),
        "preferred_signer_ids": preferred_signers,
        "assets": manifest_assets,
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    logger.info("Manifest written → %s", MANIFEST_PATH)

    # ── Summary ──────────────────────────────────────────────────────
    signer_counts: dict[int | None, int] = {}
    for a in manifest_assets:
        if a["source"] == "wlasl":
            s = a.get("signer_id")
            signer_counts[s] = signer_counts.get(s, 0) + 1

    print("\n" + "=" * 50)
    print("  Asset Build Summary")
    print("=" * 50)
    print(f"  Total assets  : {len(manifest_assets)}")
    print(f"  From WLASL    : {stats['wlasl']}")
    print(f"  Placeholder   : {stats['placeholder']}")
    if signer_counts:
        print("  Signer breakdown:")
        for s, c in sorted(signer_counts.items(), key=lambda x: -x[1]):
            print(f"    signer {str(s):>4s}  : {c}" if s is not None else f"    unknown     : {c}")
    print("=" * 50)


if __name__ == "__main__":
    build_all()
