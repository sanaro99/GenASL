"""Run QA checks on all 50 final asset clips and update the manifest.

Usage::

    python scripts/run_qa_all.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.trim_and_standardize import run_qa_check

MANIFEST_PATH = _PROJECT_ROOT / "assets" / "asset_manifest_v1.json"


def main() -> None:
    if not MANIFEST_PATH.is_file():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}")
        print("Run build_assets.py first to generate the manifest.")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    assets = manifest.get("assets", [])
    if not assets:
        print("No assets found in manifest.")
        sys.exit(1)

    print(f"Running QA on {len(assets)} assets …\n")

    passed_count = 0
    failed_count = 0
    all_issues: list[dict] = []

    for entry in assets:
        clip_path = str(_PROJECT_ROOT / entry["file_path"])
        qa = run_qa_check(clip_path)

        entry["duration_ms"] = qa["duration_ms"]
        entry["width"] = qa["width"]
        entry["height"] = qa["height"]
        entry["fps"] = qa["fps"]
        entry["qa_issues"] = qa["issues"]

        if qa["passed"]:
            entry["qa_status"] = "approved"
            passed_count += 1
            print(f"  ✓ {entry['asset_id']}  {qa['duration_ms']}ms  {qa['width']}x{qa['height']}  {qa['fps']}fps")
        else:
            entry["qa_status"] = "needs_review"
            failed_count += 1
            print(f"  ✗ {entry['asset_id']}  issues: {', '.join(qa['issues'])}")
            all_issues.append({
                "asset_id": entry["asset_id"],
                "path": clip_path,
                "issues": qa["issues"],
            })

    # Save updated manifest
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 50)
    print("  QA Summary")
    print("=" * 50)
    print(f"  Total clips checked : {len(assets)}")
    print(f"  Passed              : {passed_count}")
    print(f"  Needs review        : {failed_count}")

    if all_issues:
        print("\n  Issues detail:")
        for iss in all_issues:
            print(f"    {iss['asset_id']}: {', '.join(iss['issues'])}")

    print("=" * 50)

    if failed_count > 0:
        print(f"\n⚠ {failed_count} asset(s) need review. Check the issues above.")
    else:
        print("\n✓ All assets passed QA!")


if __name__ == "__main__":
    main()
