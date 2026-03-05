"""Utility functions for downloading, trimming, and standardizing ASL video clips.

Uses yt-dlp for downloading and FFmpeg/ffprobe for media processing.
All functions return True/False on success/failure and log errors.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _yt_dlp_bin() -> str:
    """Return the path to the yt-dlp executable.

    Looks in the same directory as the running Python interpreter first
    (handles virtualenvs on Windows where Scripts/ may not be on PATH).
    """
    scripts_dir = Path(sys.executable).parent
    candidate = scripts_dir / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
    if candidate.is_file():
        return str(candidate)
    return "yt-dlp"  # fall back to PATH lookup


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_clip(youtube_id: str, output_path: str) -> bool:
    """Download a YouTube video using yt-dlp.

    Parameters
    ----------
    youtube_id : str
        11-character YouTube video ID.
    output_path : str
        Destination file path (e.g. ``assets/raw/abc123.mp4``).

    Returns
    -------
    bool
        True if the download succeeded.
    """
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    cmd = [
        _yt_dlp_bin(),
        "--no-playlist",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_path,
        "--no-overwrites",
        "--socket-timeout", "30",
        "--retries", "3",
        url,
    ]
    logger.info("Downloading %s → %s", url, output_path)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            logger.error("yt-dlp failed (rc=%d): %s", result.returncode, result.stderr[:500])
            return False
        logger.info("Download complete: %s", output_path)
        return True
    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Download timed out for %s", youtube_id)
        return False


def download_url(url: str, output_path: str) -> bool:
    """Download a video directly from a URL (non-YouTube sources).

    Uses yt-dlp which supports many sites, or falls back to requests for
    direct .mp4 links.

    Parameters
    ----------
    url : str
        Direct video URL (aslbricks, aslsignbank, etc.).
    output_path : str
        Destination file path.

    Returns
    -------
    bool
        True if the download succeeded.
    """
    # Try yt-dlp first (handles many sites)
    cmd = [
        _yt_dlp_bin(),
        "--no-playlist",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_path,
        "--no-overwrites",
        "--socket-timeout", "30",
        "--retries", "3",
        url,
    ]
    logger.info("Downloading (direct) %s → %s", url, output_path)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logger.info("Download complete: %s", output_path)
            return True
        logger.warning("yt-dlp failed for direct URL, trying requests: %s", result.stderr[:300])
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("yt-dlp issue for direct URL: %s", exc)

    # Fallback: plain HTTP download for direct .mp4 links
    try:
        import requests
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        logger.info("Download (requests) complete: %s", output_path)
        return True
    except Exception as exc:
        logger.error("Direct download failed for %s: %s", url, exc)
        return False


# ---------------------------------------------------------------------------
# Trim
# ---------------------------------------------------------------------------

def trim_clip(
    input_path: str,
    output_path: str,
    start_sec: float,
    end_sec: float,
) -> bool:
    """Trim a video to the specified time range using FFmpeg.

    Parameters
    ----------
    input_path : str
        Source video file.
    output_path : str
        Destination trimmed file.
    start_sec : float
        Start time in seconds.
    end_sec : float
        End time in seconds.

    Returns
    -------
    bool
        True if trimming succeeded.
    """
    if not os.path.isfile(input_path):
        logger.error("Input file not found: %s", input_path)
        return False

    duration = end_sec - start_sec
    if duration <= 0:
        logger.error("Invalid trim range: start=%.2f end=%.2f", start_sec, end_sec)
        return False

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-i", input_path,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path,
    ]
    logger.info("Trimming %s [%.2f–%.2f s] → %s", input_path, start_sec, end_sec, output_path)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error("FFmpeg trim failed (rc=%d): %s", result.returncode, result.stderr[:500])
            return False
        return True
    except FileNotFoundError:
        logger.error("FFmpeg not found. Please install FFmpeg and add it to PATH.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg trim timed out for %s", input_path)
        return False


# ---------------------------------------------------------------------------
# Standardize
# ---------------------------------------------------------------------------

def standardize_clip(
    input_path: str,
    output_path: str,
    width: int = 320,
    height: int = 240,
    fps: int = 25,
    max_duration_sec: float = 4.0,
) -> bool:
    """Standardize a clip: scale, set FPS, cap duration.

    Parameters
    ----------
    input_path : str
        Source video file.
    output_path : str
        Destination standardized file.
    width, height : int
        Target resolution.
    fps : int
        Target frame rate.
    max_duration_sec : float
        Maximum duration; longer clips are truncated.

    Returns
    -------
    bool
        True if standardization succeeded.
    """
    if not os.path.isfile(input_path):
        logger.error("Input file not found: %s", input_path)
        return False

    vf_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", f"{max_duration_sec:.3f}",
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-an",                       # drop audio — ASL overlay is silent
        "-movflags", "+faststart",
        output_path,
    ]
    logger.info("Standardizing %s → %s (%dx%d @ %dfps, max %.1fs)", input_path, output_path, width, height, fps, max_duration_sec)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error("FFmpeg standardize failed (rc=%d): %s", result.returncode, result.stderr[:500])
            return False
        return True
    except FileNotFoundError:
        logger.error("FFmpeg not found. Please install FFmpeg and add it to PATH.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg standardize timed out for %s", input_path)
        return False


# ---------------------------------------------------------------------------
# QA check
# ---------------------------------------------------------------------------

def run_qa_check(clip_path: str) -> dict:
    """Run a quality-assurance check on a video clip using ffprobe.

    Returns
    -------
    dict
        Keys: path, duration_ms, width, height, fps, passed, issues.
    """
    result = {
        "path": clip_path,
        "duration_ms": 0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "passed": False,
        "issues": [],
    }

    if not os.path.isfile(clip_path):
        result["issues"].append("File not found")
        return result

    # Probe the file with ffprobe (JSON output)
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        clip_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            result["issues"].append(f"ffprobe failed (rc={proc.returncode})")
            return result
        probe = json.loads(proc.stdout)
    except FileNotFoundError:
        result["issues"].append("ffprobe not found — install FFmpeg")
        return result
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        result["issues"].append(f"ffprobe error: {exc}")
        return result

    # Extract duration
    fmt = probe.get("format", {})
    dur_s = float(fmt.get("duration", 0))
    result["duration_ms"] = int(round(dur_s * 1000))

    # Extract video stream info
    video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    if not video_streams:
        result["issues"].append("No video stream found")
        return result

    vs = video_streams[0]
    result["width"] = int(vs.get("width", 0))
    result["height"] = int(vs.get("height", 0))

    # Parse FPS from r_frame_rate (e.g. "25/1")
    rfr = vs.get("r_frame_rate", "0/1")
    try:
        num, den = rfr.split("/")
        result["fps"] = round(int(num) / int(den), 2) if int(den) else 0.0
    except (ValueError, ZeroDivisionError):
        result["fps"] = 0.0

    # ── QA Checks ────────────────────────────────────────────────────
    # Duration: must be 0.5–5.0 seconds
    if dur_s < 0.5:
        result["issues"].append(f"Too short: {dur_s:.2f}s (min 0.5s)")
    if dur_s > 5.0:
        result["issues"].append(f"Too long: {dur_s:.2f}s (max 5.0s)")

    # Resolution: 320×240 expected
    if result["width"] != 320 or result["height"] != 240:
        result["issues"].append(f"Resolution {result['width']}x{result['height']} (expected 320x240)")

    # FPS: 25 expected (allow ±1)
    if abs(result["fps"] - 25.0) > 1.0:
        result["issues"].append(f"FPS {result['fps']} (expected ~25)")

    result["passed"] = len(result["issues"]) == 0
    return result
