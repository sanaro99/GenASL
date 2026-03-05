"""Generate placeholder MP4 clips for sentences without WLASL source clips.

Creates:
  assets/placeholders/placeholder.mp4        — generic "ASL signing in progress"
  assets/placeholders/generic_placeholder.mp4 — same as above (alias)
  assets/placeholders/placeholder_<KEYWORD>.mp4 — one per missing keyword

Usage::

    python scripts/create_placeholder.py
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDERS_DIR = _PROJECT_ROOT / "assets" / "placeholders"
MANIFEST_PATH = _PROJECT_ROOT / "assets" / "asset_manifest_v1.json"


def _check_ffmpeg() -> bool:
    """Return True if FFmpeg is available on PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=10,
        )
        return True
    except FileNotFoundError:
        return False


def create_placeholder(
    output_path: str,
    text: str = "ASL signing in progress",
    duration: float = 2.0,
    width: int = 320,
    height: int = 240,
    fps: int = 25,
) -> bool:
    """Generate a solid-color placeholder MP4 with centered white text.

    Parameters
    ----------
    output_path : str
        Destination MP4 file.
    text : str
        Text to overlay on the blue background.
    duration : float
        Clip duration in seconds.
    width, height, fps : int
        Video parameters.

    Returns
    -------
    bool
        True if creation succeeded.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Escape single quotes in text for FFmpeg drawtext filter
    safe_text = text.replace("'", "'\\''").replace(":", "\\:")

    # FFmpeg: generate a blue background with white text overlay
    vf = (
        f"color=c=0x1a5276:s={width}x{height}:d={duration}:r={fps},"
        f"drawtext=text='{safe_text}'"
        f":fontcolor=white:fontsize=16"
        f":x=(w-text_w)/2:y=(h-text_h)/2"
        f":font=Arial"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x1a5276:s={width}x{height}:d={duration}:r={fps}",
        "-vf", (
            f"drawtext=text='{safe_text}'"
            f":fontcolor=white:fontsize=16"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  ERROR creating placeholder: {result.stderr[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  ERROR: FFmpeg timed out creating {output_path}")
        return False


def main() -> None:
    if not _check_ffmpeg():
        print("ERROR: FFmpeg is not installed or not on PATH.")
        print("Install FFmpeg: https://ffmpeg.org/download.html")
        print("  Windows: winget install FFmpeg")
        print("  macOS:   brew install ffmpeg")
        sys.exit(1)

    os.makedirs(PLACEHOLDERS_DIR, exist_ok=True)

    # 1. Generic placeholder
    generic_path = str(PLACEHOLDERS_DIR / "generic_placeholder.mp4")
    print("Creating generic placeholder …")
    if create_placeholder(generic_path, text="ASL signing in progress"):
        print(f"  ✓ {generic_path}")
    else:
        print("  ✗ Failed to create generic placeholder")
        sys.exit(1)

    # 2. Copy as the default placeholder.mp4
    default_path = str(PLACEHOLDERS_DIR / "placeholder.mp4")
    shutil.copy2(generic_path, default_path)
    print(f"  ✓ {default_path} (copy of generic)")

    # 3. Per-keyword placeholders for missing keywords
    _create_keyword_placeholders()

    print("\nPlaceholder clips created successfully.")


def _create_keyword_placeholders() -> None:
    """Create labeled placeholders for each keyword that fell back to placeholder."""
    if not MANIFEST_PATH.is_file():
        print("\n  ℹ Manifest not found — skipping per-keyword placeholders.")
        print("    Run build_assets.py first, then re-run this script.")
        return

    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    # Collect unique keywords that used placeholder source
    placeholder_keywords: set[str] = set()
    for asset in manifest.get("assets", []):
        if asset.get("source") == "placeholder":
            kw = asset.get("asl_keyword", "").strip()
            if kw:
                placeholder_keywords.add(kw)

    if not placeholder_keywords:
        print("\n  ℹ No placeholder keywords found — all assets sourced from WLASL.")
        return

    print(f"\nCreating {len(placeholder_keywords)} per-keyword placeholders …")
    for kw in sorted(placeholder_keywords):
        out_path = str(PLACEHOLDERS_DIR / f"placeholder_{kw}.mp4")
        if os.path.isfile(out_path):
            print(f"  ⊘ {kw:15s} — already exists")
            continue
        ok = create_placeholder(out_path, text=kw)
        if ok:
            print(f"  ✓ {kw:15s} → placeholder_{kw}.mp4")
        else:
            print(f"  ✗ {kw:15s} — failed")


if __name__ == "__main__":
    main()
