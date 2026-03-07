"""FFmpeg Picture-in-Picture overlay compositor for GenASL.

Reads the source YouTube video and the enriched render plan, then overlays
each matched ASL clip as a PiP window (bottom-right, ~25% width) at the
exact start timestamp.  A disclosure label is burned into the video.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Disclosure label text — must be visible at all times (RAI requirement)
_DISCLOSURE_LABEL = "AI-generated ASL overlay (POC)"


def _find_ffmpeg() -> str:
    """Locate the ffmpeg binary."""
    # Check common winget install path
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


def _find_ffprobe() -> str:
    """Locate the ffprobe binary."""
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / (
        r"Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\ffmpeg-8.0.1-full_build\bin\ffprobe.exe"
    )
    if winget_path.is_file():
        return str(winget_path)
    system_path = shutil.which("ffprobe")
    if system_path:
        return system_path
    raise FileNotFoundError("ffprobe not found.")


def get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Return (width, height) of the video at *video_path*."""
    ffprobe = _find_ffprobe()
    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:300]}")
    info = json.loads(result.stdout)
    stream = info["streams"][0]
    return int(stream["width"]), int(stream["height"])


def compose_pip(
    source_video: Path,
    plan: dict,
    output_path: Path | None = None,
) -> Path:
    """Overlay ASL clips onto the source video as PiP and burn in disclosure label.

    Parameters
    ----------
    source_video : Path
        Path to the original YouTube video file.
    plan : dict
        The enriched render plan dict (from ``run_pipeline.run``).
    output_path : Path, optional
        Where to write the composited video.  Defaults to
        ``logs/<run_id>_composited.mp4``.

    Returns
    -------
    Path
        The path to the output video file.
    """
    ffmpeg = _find_ffmpeg()

    if output_path is None:
        output_path = _PROJECT_ROOT / "logs" / f"{plan['run_id']}_composited.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Gather ASL overlay entries that are kept (not dropped by overlap resolution)
    overlays: List[dict] = []
    for entry in plan.get("asl_overlay_track", []):
        if not entry.get("kept", True):
            continue
        clip_path = entry.get("asset_file_path")
        if not clip_path:
            continue
        abs_clip = _PROJECT_ROOT / clip_path
        if not abs_clip.is_file():
            logger.warning("ASL clip file not found, skipping: %s", abs_clip)
            continue
        overlays.append({
            "path": str(abs_clip),
            "start_ms": entry["start_ms"],
            "end_ms": entry["end_ms"],
            "segment_id": entry["segment_id"],
        })

    if not overlays:
        logger.warning("No ASL overlay clips to composite — copying source as-is with label")

    # Get source dimensions for PiP sizing
    src_w, src_h = get_video_dimensions(source_video)
    pip_w = int(src_w * 0.25)

    # Build FFmpeg filter_complex
    #
    # Strategy:
    #   - Input 0 = source video
    #   - Input 1..N = ASL clips, each with -itsoffset to delay playback
    #     to the correct timestamp (so the clip *plays* as video at the
    #     right moment rather than showing a static first/last frame)
    #   - Chain overlays sequentially with eof_action=pass
    #   - Final: burn disclosure label with drawtext
    #
    inputs = ["-i", str(source_video)]
    for ov in overlays:
        start_s = ov["start_ms"] / 1000.0
        inputs.extend(["-itsoffset", f"{start_s:.3f}", "-i", ov["path"]])

    filter_parts: list[str] = []
    prev_label = "[0:v]"

    for idx, ov in enumerate(overlays):
        inp_idx = idx + 1
        scale_label = f"[pip{idx}]"
        out_label = f"[v{idx}]"

        # Scale the overlay clip to PiP size
        filter_parts.append(
            f"[{inp_idx}:v]scale={pip_w}:-1{scale_label}"
        )
        # Overlay at bottom-right; -itsoffset handles timing so the clip
        # plays as video starting at the correct moment.  eof_action=pass
        # ensures the main video continues after the clip ends.
        filter_parts.append(
            f"{prev_label}{scale_label}overlay="
            f"W-w-10:H-h-10:"
            f"eof_action=pass"
            f"{out_label}"
        )
        prev_label = out_label

    # Disclosure label — always visible (RAI requirement)
    label_escaped = _DISCLOSURE_LABEL.replace("'", "'\\''").replace(":", "\\:")
    filter_parts.append(
        f"{prev_label}drawtext="
        f"text='{label_escaped}':"
        f"fontsize=14:fontcolor=white:"
        f"borderw=1:bordercolor=black:"
        f"x=10:y=10"
        f"[vout]"
    )

    filter_complex = ";\n".join(filter_parts)

    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ]

    logger.info(
        "Compositing PiP overlay: %d clips onto %s → %s",
        len(overlays), source_video.name, output_path.name,
    )
    logger.debug("FFmpeg command: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.error("FFmpeg failed:\n%s", result.stderr[-1000:])
        raise RuntimeError(f"FFmpeg compositing failed: {result.stderr[-500:]}")

    logger.info("Composited video saved → %s", output_path)
    return output_path
