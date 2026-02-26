"""Download the WLASL dataset index and check coverage against our keyword map.

Usage::

    python scripts/download_wlasl_index.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import requests

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

WLASL_URL = "https://raw.githubusercontent.com/dxli94/WLASL/master/start_kit/WLASL_v0.3.json"
OUTPUT_PATH = _PROJECT_ROOT / "data" / "wlasl_index.json"
KEYWORD_MAP_PATH = _PROJECT_ROOT / "scripts" / "keyword_map.csv"


def download_wlasl_json() -> list:
    """Download WLASL_v0.3.json and save to data/wlasl_index.json."""
    print(f"Downloading WLASL index from:\n  {WLASL_URL}")
    resp = requests.get(WLASL_URL, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    print(f"Saved to: {OUTPUT_PATH}")
    print(f"Total ASL glosses (words) in WLASL: {len(data)}")
    return data


def load_keywords() -> list[dict]:
    """Read keyword_map.csv and return list of {sentence_id, asl_keyword}."""
    keywords: list[dict] = []
    with open(KEYWORD_MAP_PATH, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            keywords.append({
                "sentence_id": row["sentence_id"],
                "asl_keyword": row["asl_keyword"].strip().upper(),
                "english_text": row["english_text"],
            })
    return keywords


def check_coverage(wlasl_data: list, keywords: list[dict]) -> None:
    """Print coverage report: which keywords are in WLASL, which are not."""
    # Build a set of all glosses in WLASL (uppercased for comparison)
    wlasl_glosses: set[str] = set()
    for entry in wlasl_data:
        gloss = entry.get("gloss", "").strip().upper()
        if gloss:
            wlasl_glosses.add(gloss)

    print(f"\nWLASL contains {len(wlasl_glosses)} unique glosses")
    print(f"Our keyword map has {len(keywords)} entries")
    print()

    # De-duplicate keywords (some sentences share the same keyword)
    unique_kw = sorted(set(k["asl_keyword"] for k in keywords))
    found: list[str] = []
    missing: list[str] = []

    for kw in unique_kw:
        if kw in wlasl_glosses:
            found.append(kw)
        else:
            # Try without hyphen (e.g. THANK-YOU → THANK YOU)
            alt = kw.replace("-", " ")
            if alt in wlasl_glosses:
                found.append(kw)
            else:
                missing.append(kw)

    print("=" * 50)
    print("  WLASL Coverage Report")
    print("=" * 50)
    print(f"  Unique keywords : {len(unique_kw)}")
    print(f"  Found in WLASL  : {len(found)}")
    print(f"  NOT found       : {len(missing)}")
    print()

    if found:
        print("FOUND keywords:")
        for kw in found:
            sids = [k["sentence_id"] for k in keywords if k["asl_keyword"] == kw]
            print(f"  ✓ {kw:<15s}  (used by {', '.join(sids)})")

    if missing:
        print("\nMISSING keywords (will use placeholder clips):")
        for kw in missing:
            sids = [k["sentence_id"] for k in keywords if k["asl_keyword"] == kw]
            print(f"  ✗ {kw:<15s}  (used by {', '.join(sids)})")

    print()
    pct = len(found) / len(unique_kw) * 100 if unique_kw else 0
    print(f"Coverage: {len(found)}/{len(unique_kw)} unique keywords = {pct:.0f}%")


def main() -> None:
    wlasl_data = download_wlasl_json()
    keywords = load_keywords()
    check_coverage(wlasl_data, keywords)


if __name__ == "__main__":
    main()
