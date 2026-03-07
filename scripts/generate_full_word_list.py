"""Generate a complete word_download_list.csv from ALL glosses in the WLASL index.

Reads data/wlasl_index.json and produces a CSV covering every gloss in the
dataset.  The existing 241 words are preserved with their original IDs; new
glosses receive sequential IDs starting after the last existing one.

Usage::

    python scripts/generate_full_word_list.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

WLASL_INDEX_PATH = _PROJECT_ROOT / "data" / "wlasl_index.json"
EXISTING_LIST_PATH = _PROJECT_ROOT / "scripts" / "word_download_list.csv"
OUTPUT_PATH = _PROJECT_ROOT / "scripts" / "word_download_list.csv"


def main() -> None:
    # Load WLASL index
    if not WLASL_INDEX_PATH.is_file():
        print(f"WLASL index not found at {WLASL_INDEX_PATH}")
        print("Run first:  python scripts/download_wlasl_index.py")
        sys.exit(1)

    with open(WLASL_INDEX_PATH, "r", encoding="utf-8") as fh:
        wlasl = json.load(fh)

    all_glosses: set[str] = set()
    for entry in wlasl:
        gloss = entry.get("gloss", "").strip().upper()
        if gloss:
            all_glosses.add(gloss)

    print(f"Total WLASL glosses: {len(all_glosses)}")

    # Load existing list to preserve IDs
    existing: dict[str, dict] = {}  # gloss -> {word_id, category}
    if EXISTING_LIST_PATH.is_file():
        with open(EXISTING_LIST_PATH, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing[row["gloss"].strip().upper()] = {
                    "word_id": row["word_id"],
                    "category": row["category"],
                }
    print(f"Existing words: {len(existing)}")

    # Find the highest existing numeric ID
    max_num = 0
    for info in existing.values():
        try:
            num = int(info["word_id"].lstrip("W"))
            max_num = max(max_num, num)
        except ValueError:
            pass

    # Build combined list: existing first, then new
    rows: list[dict] = []
    seen_glosses: set[str] = set()

    # Preserve existing entries in their original order
    if EXISTING_LIST_PATH.is_file():
        with open(EXISTING_LIST_PATH, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                gloss = row["gloss"].strip().upper()
                rows.append({
                    "word_id": row["word_id"],
                    "gloss": gloss,
                    "category": row["category"],
                })
                seen_glosses.add(gloss)

    # Add new glosses
    next_num = max_num + 1
    new_count = 0
    for gloss in sorted(all_glosses):
        if gloss in seen_glosses:
            continue
        word_id = f"W{next_num:04d}"
        rows.append({
            "word_id": word_id,
            "gloss": gloss,
            "category": "wlasl",
        })
        next_num += 1
        new_count += 1

    # Write output
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["word_id", "gloss", "category"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"New glosses added: {new_count}")
    print(f"Total words in list: {len(rows)}")
    print(f"Written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
