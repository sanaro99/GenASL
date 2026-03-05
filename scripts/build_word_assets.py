"""Download word-level ASL video assets from WLASL.

Reads word_download_list.csv, looks up each gloss in the WLASL index,
downloads / trims / standardises clips from a preferred signer, and
falls back to placeholder only when **all** instances are exhausted.

Assets are stored in ``assets/words/`` with filenames like ``W001_ALMOST.mp4``
and a manifest is written to ``assets/word_manifest.json``.

Re-uses the signer preference chain and multi-instance retry logic
from build_assets.py.

Usage::

    python scripts/build_word_assets.py          # build all
    python scripts/build_word_assets.py --resume  # skip existing
"""

from __future__ import annotations

import argparse
import csv
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

# ── Paths ─────────────────────────────────────────────────────────────────
WORD_LIST_PATH = _PROJECT_ROOT / "scripts" / "word_download_list.csv"
WLASL_INDEX_PATH = _PROJECT_ROOT / "data" / "wlasl_index.json"
CONFIG_PATH = _PROJECT_ROOT / "config.yaml"
RAW_DIR = _PROJECT_ROOT / "assets" / "raw"
TRIMMED_DIR = _PROJECT_ROOT / "assets" / "trimmed"
WORD_DIR = _PROJECT_ROOT / "assets" / "words"
WORD_MANIFEST_PATH = _PROJECT_ROOT / "assets" / "word_manifest.json"
PLACEHOLDER_PATH = _PROJECT_ROOT / "assets" / "placeholders" / "placeholder.mp4"


# ── Loaders ───────────────────────────────────────────────────────────────

def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_word_list() -> list[dict]:
    """Return list of {word_id, gloss, category}."""
    with open(WORD_LIST_PATH, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


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
            alt = gloss.replace("-", " ")
            if alt != gloss:
                index[alt] = instances
    return index


# ── Helpers (mirrored from build_assets.py) ───────────────────────────────

def _extract_youtube_id(url: str) -> str | None:
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})', url or '')
    return m.group(1) if m else None


def _safe_filename(keyword: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]', '_', keyword.replace("-", "_").replace(" ", "_")).upper()


def _rank_instances(
    instances: list[dict],
    preferred_signers: list[int],
) -> list[dict]:
    """Return all viable instances ranked by signer preference then quality."""
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


def _try_download_trim_standardise(
    inst: dict, word_id: str, final_path: str
) -> bool:
    """Download → trim → standardise one WLASL instance. Return True on success."""
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

    cache_key = wlasl_vid_id or (yt_id or word_id)
    raw_path = str(RAW_DIR / f"{cache_key}.mp4")
    trimmed_path = str(TRIMMED_DIR / f"{word_id}_trimmed.mp4")

    # Download
    dl_ok = False
    if os.path.isfile(raw_path):
        logger.info("    Raw clip cached: %s", raw_path)
        dl_ok = True
    elif yt_id:
        dl_ok = download_clip(yt_id, raw_path)
    elif url:
        dl_ok = download_url(url, raw_path)
    else:
        logger.warning("    No URL for instance video_id=%s", wlasl_vid_id)

    if not dl_ok:
        return False

    # Trim
    if not whole_clip and end_sec > start_sec:
        trim_ok = trim_clip(raw_path, trimmed_path, start_sec, end_sec)
    else:
        trimmed_path = raw_path
        trim_ok = True

    if not trim_ok:
        return False

    # Standardise
    return standardize_clip(trimmed_path, final_path)


# ── Main ──────────────────────────────────────────────────────────────────

def build_words(resume: bool = False) -> None:
    """Download, trim, and standardise all word-level ASL assets."""
    cfg = _load_config()
    preferred_signers: list[int] = cfg.get("build", {}).get(
        "preferred_signer_ids", [9, 109, 12]
    )
    logger.info("Preferred signer chain: %s", preferred_signers)

    word_list = _load_word_list()
    wlasl = _load_wlasl_index()

    for d in [RAW_DIR, TRIMMED_DIR, WORD_DIR]:
        os.makedirs(d, exist_ok=True)

    if not PLACEHOLDER_PATH.is_file():
        logger.error(
            "Placeholder not found at %s — run create_placeholder.py first.",
            PLACEHOLDER_PATH,
        )
        sys.exit(1)

    # Load existing manifest for resume
    existing_manifest: dict[str, dict] = {}
    if resume and WORD_MANIFEST_PATH.is_file():
        prev = json.load(open(WORD_MANIFEST_PATH, "r", encoding="utf-8"))
        for a in prev.get("words", []):
            existing_manifest[a["word_id"]] = a
        logger.info("Resume mode — %d existing assets loaded", len(existing_manifest))

    manifest_words: list[dict] = []
    stats = {"wlasl": 0, "placeholder": 0, "skipped": 0}

    for row in word_list:
        word_id = row["word_id"]
        gloss = row["gloss"].strip().upper()
        category = row["category"]
        safe_name = _safe_filename(gloss)

        final_name = f"{word_id}_{safe_name}.mp4"
        final_path = str(WORD_DIR / final_name)

        # Resume: skip if file exists and was from WLASL
        if resume and word_id in existing_manifest:
            prev_entry = existing_manifest[word_id]
            if prev_entry["source"] == "wlasl" and os.path.isfile(
                str(_PROJECT_ROOT / prev_entry["file_path"])
            ):
                logger.info("─ %s %s — skipped (already downloaded)", word_id, gloss)
                manifest_words.append(prev_entry)
                stats["skipped"] += 1
                continue

        logger.info("─" * 50)
        logger.info("Processing %s  gloss=%s  (%s)", word_id, gloss, category)

        word_entry: dict = {
            "word_id": word_id,
            "gloss": gloss,
            "category": category,
            "source": "placeholder",
            "file_path": f"assets/words/{final_name}",
            "fps": 25.0,
            "duration_ms": 0,
            "width": 320,
            "height": 240,
            "qa_status": "pending",
            "qa_issues": [],
            "wlasl_video_id": "",
            "signer_id": None,
        }

        instances = wlasl.get(gloss, [])
        if not instances:
            instances = wlasl.get(gloss.replace("-", " "), [])

        success = False
        if instances:
            ranked = _rank_instances(instances, preferred_signers)
            total = len(ranked)
            for idx, inst in enumerate(ranked, 1):
                signer = inst.get("signer_id")
                url = inst.get("url", "")[:60]
                logger.info(
                    "  Trying instance %d/%d  signer=%s  url=%s",
                    idx, total, signer, url,
                )
                if _try_download_trim_standardise(inst, word_id, final_path):
                    yt_id = _extract_youtube_id(inst.get("url", ""))
                    word_entry["source"] = "wlasl"
                    word_entry["wlasl_video_id"] = yt_id or inst.get("video_id", "")
                    word_entry["signer_id"] = signer
                    stats["wlasl"] += 1
                    logger.info(
                        "✓ %s %s from WLASL  signer=%s  (instance %d/%d)",
                        word_id, gloss, signer, idx, total,
                    )
                    success = True
                    break
                else:
                    logger.info("  ✗ Instance %d/%d failed — trying next", idx, total)

        if not success:
            if instances:
                logger.warning(
                    "All %d instances failed for %s/%s — placeholder",
                    len(instances), word_id, gloss,
                )
            else:
                logger.info("Gloss %s not in WLASL — placeholder", gloss)
            shutil.copy2(str(PLACEHOLDER_PATH), final_path)
            stats["placeholder"] += 1

        # QA
        qa = run_qa_check(final_path)
        word_entry["duration_ms"] = qa["duration_ms"]
        word_entry["width"] = qa["width"]
        word_entry["height"] = qa["height"]
        word_entry["fps"] = qa["fps"]
        word_entry["qa_status"] = "approved" if qa["passed"] else "needs_review"
        word_entry["qa_issues"] = qa["issues"]

        manifest_words.append(word_entry)

    # ── Write manifest ────────────────────────────────────────────────
    manifest = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_words": len(manifest_words),
        "preferred_signer_ids": preferred_signers,
        "words": manifest_words,
    }
    with open(WORD_MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    logger.info("Word manifest written → %s", WORD_MANIFEST_PATH)

    # ── Summary ───────────────────────────────────────────────────────
    signer_counts: dict[int | None, int] = {}
    for w in manifest_words:
        if w["source"] == "wlasl":
            s = w.get("signer_id")
            signer_counts[s] = signer_counts.get(s, 0) + 1

    print("\n" + "=" * 50)
    print("  Word Asset Build Summary")
    print("=" * 50)
    print(f"  Total words   : {len(manifest_words)}")
    print(f"  From WLASL    : {stats['wlasl']}")
    print(f"  Placeholder   : {stats['placeholder']}")
    if stats["skipped"]:
        print(f"  Skipped(resume): {stats['skipped']}")
    if signer_counts:
        print("  Signer breakdown:")
        for s, c in sorted(signer_counts.items(), key=lambda x: -x[1]):
            label = f"signer {str(s):>4s}" if s is not None else "unknown    "
            print(f"    {label}  : {c}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build word-level ASL assets")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip words that already have WLASL assets from a previous run.",
    )
    args = parser.parse_args()
    build_words(resume=args.resume)
