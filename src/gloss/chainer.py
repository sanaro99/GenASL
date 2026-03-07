"""Word-clip chainer — concatenates multiple word-level ASL clips into one video.

Given a sequence of gloss words that have been resolved to clip paths,
this module uses FFmpeg's concat demuxer to chain them into a single
continuous video suitable for PiP overlay.

The chained clips are written to ``assets/chained/`` with filenames based
on the segment ID.
"""

from __future__ import annotations

import logging
import os
import subprocess
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CHAINED_DIR = _PROJECT_ROOT / "assets" / "chained"


def _find_ffmpeg() -> str:
    """Locate the ffmpeg binary."""
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / (
        r"Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
    )
    if winget_path.is_file():
        return str(winget_path)
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path
    raise FileNotFoundError(
        "ffmpeg not found. Install via 'winget install Gyan.FFmpeg' or add to PATH."
    )


def chain_clips(
    clip_entries: list[dict],
    output_name: str,
    output_dir: Path | None = None,
) -> dict | None:
    """Concatenate multiple word clips into a single video.

    Parameters
    ----------
    clip_entries : list[dict]
        Output from ``WordLookup.lookup_sequence`` — only entries with
        ``found=True`` are included.
    output_name : str
        Filename stem for the output (e.g. ``"SEG_001_chained"``).
    output_dir : Path, optional
        Directory for output.  Defaults to ``assets/chained/``.

    Returns
    -------
    dict or None
        Info dict with keys: path, duration_ms, clip_count, glosses.
        Returns None if no clips are available.
    """
    found_clips = [e for e in clip_entries if e.get("found")]
    if not found_clips:
        logger.warning("No clips to chain for %s", output_name)
        return None

    out_dir = output_dir or _CHAINED_DIR
    os.makedirs(out_dir, exist_ok=True)
    output_path = out_dir / f"{output_name}.mp4"

    # If only one clip, just copy it
    if len(found_clips) == 1:
        src = found_clips[0]["abs_path"]
        shutil.copy2(src, str(output_path))
        logger.info("Single clip — copied %s → %s", src, output_path)
        try:
            rel = str(output_path.relative_to(_PROJECT_ROOT))
        except ValueError:
            rel = str(output_path)
        return {
            "path": str(output_path),
            "rel_path": rel,
            "duration_ms": found_clips[0]["duration_ms"],
            "clip_count": 1,
            "glosses": [found_clips[0]["gloss"]],
        }

    # Multiple clips — use FFmpeg concat demuxer
    ffmpeg = _find_ffmpeg()

    # Write concat list to a temp file
    fd, concat_file = tempfile.mkstemp(suffix=".txt", prefix="concat_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for clip in found_clips:
                # FFmpeg concat requires single-quoted paths with escaped quotes
                safe_path = clip["abs_path"].replace("'", "'\\''")
                fh.write(f"file '{safe_path}'\n")

        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-an",
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info(
            "Chaining %d clips → %s (%s)",
            len(found_clips), output_path.name,
            " + ".join(c["gloss"] for c in found_clips),
        )

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("FFmpeg concat failed (rc=%d): %s", result.returncode, result.stderr[:500])
            return None
    finally:
        os.unlink(concat_file)

    total_duration = sum(c["duration_ms"] for c in found_clips)

    try:
        rel = str(output_path.relative_to(_PROJECT_ROOT))
    except ValueError:
        rel = str(output_path)

    return {
        "path": str(output_path),
        "rel_path": rel,
        "duration_ms": total_duration,
        "clip_count": len(found_clips),
        "glosses": [c["gloss"] for c in found_clips],
    }
