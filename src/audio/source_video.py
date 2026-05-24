"""Download source YouTube video for overlay compositing."""

from __future__ import annotations

import logging
import re
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DOWNLOADS_DIR = _PROJECT_ROOT / "assets" / "downloads"

# yt-dlp writes intermediate fragments as `<id>.fNNN.<ext>` before merging
# to `<id>.mp4`. Those fragments are audio-only or video-only and break
# downstream ffprobe; exclude them when picking the merged output.
_FRAGMENT_RE = re.compile(r"\.f\d+\.[A-Za-z0-9]+$")
_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov"}


def _find_ytdlp() -> str:
    """Return the path to yt-dlp, preferring the venv copy."""
    venv_path = _PROJECT_ROOT / ".venv" / "Scripts" / "yt-dlp.exe"
    if venv_path.is_file():
        return str(venv_path)
    system_path = shutil.which("yt-dlp")
    if system_path:
        return system_path
    raise FileNotFoundError("yt-dlp not found in venv or on PATH")


def download_source_video(video_id: str, max_height: int = 720) -> Path:
    """Download the YouTube video at up to *max_height* resolution.

    Returns the path to the downloaded file.
    """
    _DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    out_template = str(_DOWNLOADS_DIR / f"{video_id}.%(ext)s")
    ytdlp = _find_ytdlp()

    cmd = [
        ytdlp,
        "-f", f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]",
        "--merge-output-format", "mp4",
        "-o", out_template,
        "--no-playlist",
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    logger.info("Downloading source video %s (≤%dp) …", video_id, max_height)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.error("yt-dlp failed:\n%s", result.stderr)
        raise RuntimeError(f"yt-dlp download failed for {video_id}: {result.stderr[:500]}")

    # Find the merged downloaded file. yt-dlp may leave intermediate
    # `<id>.fNNN.<ext>` fragments alongside the merged output; the merged
    # file is the one without an `.fNNN.` infix.
    all_files = list(_DOWNLOADS_DIR.glob(f"{video_id}.*"))
    candidates = [
        p for p in all_files
        if not _FRAGMENT_RE.search(p.name) and p.suffix.lower() in _VIDEO_EXTS
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No merged video file found for {video_id} "
            f"(found {len(all_files)} fragment(s) only)"
        )

    # Prefer .mp4, then newest mtime.
    candidates.sort(key=lambda p: (p.suffix.lower() != ".mp4", -p.stat().st_mtime))
    out_path = candidates[0]
    logger.info("Downloaded source video → %s", out_path)
    return out_path
