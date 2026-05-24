"""Stage 1 helper — rip the source video's audio to a mono 16 kHz WAV.

Reuses the system ffmpeg binary discovered via :mod:`src.core.ffmpeg`
and caches output to ``data/audio_cache/<video_id>.wav`` (path
configurable via ``settings.paths.audio_cache``). Phase 2 — see
``docs/plan/phase-2-audio-backbone.md``.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from src.core.config import get_settings
from src.core.ffmpeg import find_ffmpeg, find_ffprobe
from src.core.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


def _probe_duration_ms(path: Path) -> int:
    ffprobe = find_ffprobe()
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path.name}: {result.stderr[:200]}")
    info = json.loads(result.stdout)
    return int(float(info["format"]["duration"]) * 1000)


def extract_audio(
    video_path: Path,
    video_id: str,
    sample_rate_hz: int | None = None,
) -> tuple[Path, int, int]:
    """Rip ``video_path``'s audio to a mono WAV at ``sample_rate_hz``.

    Returns ``(wav_path, duration_ms, sample_rate_hz)``. Skips
    re-extraction when the cache file exists and is newer than the
    source video (mtime check — handles re-downloads).
    """
    settings = get_settings()
    sr = sample_rate_hz or settings.audio.sample_rate_hz

    out_dir = PROJECT_ROOT / settings.paths.audio_cache
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / f"{video_id}.wav"

    if (
        wav_path.is_file()
        and wav_path.stat().st_mtime >= video_path.stat().st_mtime
    ):
        logger.info("Audio cache HIT for %s", video_id)
        duration_ms = _probe_duration_ms(wav_path)
        return wav_path, duration_ms, sr

    logger.info("Audio cache MISS for %s — extracting via ffmpeg", video_id)
    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vn",                       # drop video
        "-ac", "1",                  # mono
        "-ar", str(sr),              # target sample rate
        "-acodec", "pcm_s16le",      # 16-bit PCM
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg audio extraction failed for {video_id}: "
            f"{result.stderr[-500:]}"
        )

    duration_ms = _probe_duration_ms(wav_path)
    logger.info("Extracted %s -> %s (%d ms @ %d Hz)",
                video_path.name, wav_path.name, duration_ms, sr)
    return wav_path, duration_ms, sr
