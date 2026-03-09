"""Fetch and pre-process YouTube transcripts for the GenASL pipeline."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class NoTranscriptError(Exception):
    """Raised when no English transcript is available for a video."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Filler words removed during normalisation (matched as whole words)
_FILLER_WORDS = {"um", "uh", "like", "you know", "so", "well"}

# Multi-word fillers first so they are replaced before single-word passes
_FILLER_PATTERNS = sorted(_FILLER_WORDS, key=lambda w: -len(w.split()))

# Pause gap threshold in seconds
_PAUSE_GAP_S = 1.5

# Sentence-ending punctuation
_SENTENCE_END_RE = re.compile(r"[.!?]$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_video_id(video_id: str) -> None:
    if not isinstance(video_id, str) or not _VIDEO_ID_RE.match(video_id):
        raise ValueError(
            f"Invalid YouTube video ID: {video_id!r}. "
            "Expected an 11-character alphanumeric string."
        )


def _remove_fillers(text: str) -> str:
    """Remove standalone filler words / phrases from *text*."""
    for filler in _FILLER_PATTERNS:
        # \b word-boundary on both sides so we only remove whole words
        text = re.sub(rf"\b{re.escape(filler)}\b", "", text, flags=re.IGNORECASE)
    # Collapse multiple spaces left behind and strip
    return re.sub(r"\s{2,}", " ", text).strip()


def _strip_brackets(text: str) -> str:
    """Remove square-bracket tags such as [music], [applause], etc.

    These auto-caption artefacts dilute sentence embeddings and cause
    valid matches to score below the confidence threshold (Sprint 2
    retro Issue 2).
    """
    return re.sub(r"\[.*?\]", "", text)


def _normalise(text: str) -> str:
    """Lowercase, strip brackets, and remove filler words."""
    text = text.lower().strip()
    text = _strip_brackets(text)
    text = _remove_fillers(text)
    return text


def _merge_chunks(raw_chunks: list[dict]) -> List[Dict]:
    """Merge consecutive transcript chunks into sentence-level segments.

    A new segment boundary is created when:
    * the accumulated text ends with sentence-ending punctuation (. ! ?), OR
    * the pause gap between the current chunk and the next exceeds 1.5 s.
    """
    if not raw_chunks:
        return []

    segments: List[Dict] = []
    buf_texts: list[str] = []
    buf_start: float = raw_chunks[0]["start"]
    buf_end: float = raw_chunks[0]["start"] + raw_chunks[0]["duration"]

    def _flush() -> None:
        merged_text = " ".join(buf_texts)
        normalised = _normalise(merged_text)
        if not normalised:
            return
        seg_id = f"SEG_{len(segments) + 1:03d}"
        segments.append(
            {
                "segment_id": seg_id,
                "start_ms": int(round(buf_start * 1000)),
                "end_ms": int(round(buf_end * 1000)),
                "text": normalised,
            }
        )

    for i, chunk in enumerate(raw_chunks):
        chunk_text = chunk["text"].strip()
        chunk_start = chunk["start"]
        chunk_end = chunk["start"] + chunk["duration"]

        if i == 0:
            buf_texts.append(chunk_text)
            buf_end = chunk_end
        else:
            gap = chunk_start - buf_end
            if gap > _PAUSE_GAP_S or _SENTENCE_END_RE.search(buf_texts[-1]):
                _flush()
                buf_texts = [chunk_text]
                buf_start = chunk_start
                buf_end = chunk_end
            else:
                buf_texts.append(chunk_text)
                buf_end = max(buf_end, chunk_end)

    # Flush remaining buffer
    _flush()
    return segments


# ---------------------------------------------------------------------------
# yt-dlp subtitle fallback (handles YouTube IP blocks)
# ---------------------------------------------------------------------------

def _yt_dlp_bin() -> str:
    """Return path to yt-dlp, checking the venv first."""
    scripts_dir = Path(sys.executable).parent
    candidate = scripts_dir / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
    if candidate.is_file():
        return str(candidate)
    return "yt-dlp"


def _find_deno_dir() -> str | None:
    """Try to locate the directory containing the Deno binary.

    Checks PATH first, then the common winget install location on Windows.
    Returns the directory path or None.
    """
    import shutil

    if shutil.which("deno"):
        return None  # already on PATH, no need to augment

    if os.name == "nt":
        # winget installs Deno under this base directory
        base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        if base.is_dir():
            for pkg_dir in base.iterdir():
                if "DenoLand.Deno" in pkg_dir.name:
                    deno_exe = pkg_dir / "deno.exe"
                    if deno_exe.is_file():
                        return str(pkg_dir)
    return None


def _subprocess_env() -> dict | None:
    """Return an env dict for yt-dlp subprocesses, or None if no changes needed.

    Ensures Deno is discoverable even if the current process PATH
    wasn't refreshed after installation.
    """
    deno_dir = _find_deno_dir()
    if deno_dir:
        logger.info("Injecting Deno directory into subprocess PATH: %s", deno_dir)
        return {**os.environ, "PATH": deno_dir + os.pathsep + os.environ.get("PATH", "")}
    return None


def _fetch_via_ytdlp(video_id: str) -> list[dict]:
    """Download English subtitles via yt-dlp and parse into raw chunks.

    yt-dlp uses different request patterns than youtube-transcript-api
    and is less likely to be IP-blocked.  Returns the same list[dict]
    format as the primary path (keys: text, start, duration).
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    env = _subprocess_env()

    with tempfile.TemporaryDirectory() as tmp:
        out_template = os.path.join(tmp, "sub")
        base_cmd = [
            _yt_dlp_bin(),
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en,en-US,en-GB,en-AU,en-CA,en-orig",
            "--sub-format", "json3",
            "--output", out_template,
            url,
        ]

        # Authentication strategy: cookies.txt (with login session) > bare
        cookies_file = Path(__file__).resolve().parent.parent.parent / "cookies.txt"
        if cookies_file.is_file():
            logger.info("Using cookies.txt for yt-dlp authentication")
            base_cmd.insert(-1, "--cookies")
            base_cmd.insert(-1, str(cookies_file))

        logger.info("yt-dlp subtitle download: %s", " ".join(base_cmd[:6]))
        result = subprocess.run(base_cmd, capture_output=True, text=True, timeout=60, env=env)
        if result.returncode != 0:
            stderr = result.stderr[:500]
            logger.error("yt-dlp failed (rc=%d): %s", result.returncode, stderr)
            if "sign in" in stderr.lower():
                raise NoTranscriptError(
                    f"YouTube requires authentication for {video_id}. "
                    "Log into YouTube in Edge, then run:  python scripts/export_cookies.py\n"
                    "Or manually place a transcript in:  transcripts/{video_id}.json"
                )
            raise NoTranscriptError(
                f"yt-dlp could not fetch subtitles for {video_id}: {result.stderr[:200]}"
            )

        # yt-dlp writes  sub.en.json3  (or similar)
        json3_files = list(Path(tmp).glob("*.json3"))
        if not json3_files:
            raise NoTranscriptError(
                f"yt-dlp did not produce subtitle files for {video_id}"
            )

        sub_path = json3_files[0]
        with open(sub_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

    # json3 format: {"events": [{"tStartMs":..., "dDurationMs":..., "segs":[{"utf8":...}]}]}
    chunks: list[dict] = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        start_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 0)
        chunks.append({
            "text": text,
            "start": start_ms / 1000.0,
            "duration": dur_ms / 1000.0,
        })

    if not chunks:
        raise NoTranscriptError(
            f"yt-dlp subtitles were empty for {video_id}"
        )

    return chunks


# ---------------------------------------------------------------------------
# Transcript cache  (avoids repeat YouTube hits when IP-blocked)
# ---------------------------------------------------------------------------

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "transcripts"


def _cache_path(video_id: str) -> Path:
    return _CACHE_DIR / f"{video_id}.json"


def _load_cached(video_id: str) -> list[dict] | None:
    """Return cached raw chunks for *video_id*, or None."""
    p = _cache_path(video_id)
    if p.is_file():
        logger.info("Loading cached transcript from %s", p)
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return None


def _save_cache(video_id: str, raw_chunks: list[dict]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _cache_path(video_id)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(raw_chunks, fh, ensure_ascii=False, indent=1)
    logger.info("Cached %d raw chunks → %s", len(raw_chunks), p)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_transcript(video_id: str) -> List[Dict]:
    """Return sentence-level transcript segments for *video_id*.

    Each element is a dict with keys:
        segment_id  – e.g. "SEG_001"
        start_ms    – int, milliseconds from video start
        end_ms      – int, milliseconds from video start
        text        – normalised text string

    Tries the YouTube Transcript API first; if blocked, falls back to
    yt-dlp subtitle download.

    Raises
    ------
    ValueError
        If *video_id* is not a valid 11-char YouTube ID.
    NoTranscriptError
        If no English transcript is available for the video.
    """
    _validate_video_id(video_id)
    logger.info("Fetching transcript for video_id=%s", video_id)

    # --- Check local cache first ---
    raw_chunks = _load_cached(video_id)

    # --- Primary: YouTube Transcript API ---
    if raw_chunks is None:
        try:
            fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB", "en-AU", "en-CA"])
            raw_chunks = [
                {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
                for snippet in fetched
            ]
            logger.info("Received %d raw transcript chunks from YouTube API", len(raw_chunks))
        except NoTranscriptFound as exc:
            logger.warning("No English transcript via API for %s: %s", video_id, exc)
        except Exception as exc:
            logger.warning(
                "YouTube Transcript API failed (likely IP block) for %s: %s — "
                "falling back to yt-dlp",
                video_id, type(exc).__name__,
            )

    # --- Fallback: yt-dlp subtitle download ---
    if raw_chunks is None:
        logger.info("Trying yt-dlp subtitle fallback for %s ...", video_id)
        raw_chunks = _fetch_via_ytdlp(video_id)
        logger.info("Received %d raw chunks via yt-dlp", len(raw_chunks))

    # Persist to local cache for future runs
    _save_cache(video_id, raw_chunks)

    for i, chunk in enumerate(raw_chunks[:5]):
        logger.debug("  raw_chunk[%d]: start=%.2fs dur=%.2fs text=%r", i, chunk["start"], chunk["duration"], chunk["text"])
    if len(raw_chunks) > 5:
        logger.debug("  … (%d more raw chunks omitted)", len(raw_chunks) - 5)

    segments = _merge_chunks(raw_chunks)
    logger.info("Merged %d raw chunks → %d sentence-level segments", len(raw_chunks), len(segments))
    for seg in segments:
        logger.debug("  %s [%d–%d ms]: %r", seg["segment_id"], seg["start_ms"], seg["end_ms"], seg["text"])

    return segments


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.transcript_ingestion.fetcher <VIDEO_ID>")
        sys.exit(1)

    vid = sys.argv[1]
    segs = fetch_transcript(vid)
    print(json.dumps(segs[:5], indent=2, ensure_ascii=False))
