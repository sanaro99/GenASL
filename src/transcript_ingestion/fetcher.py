"""Fetch and pre-process YouTube transcripts for the GenASL pipeline."""

from __future__ import annotations

import json
import re
import sys
from typing import List, Dict

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound


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


def _normalise(text: str) -> str:
    """Lowercase, strip, and remove filler words."""
    text = text.lower().strip()
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
# Public API
# ---------------------------------------------------------------------------

def fetch_transcript(video_id: str) -> List[Dict]:
    """Return sentence-level transcript segments for *video_id*.

    Each element is a dict with keys:
        segment_id  – e.g. "SEG_001"
        start_ms    – int, milliseconds from video start
        end_ms      – int, milliseconds from video start
        text        – normalised text string

    Raises
    ------
    ValueError
        If *video_id* is not a valid 11-char YouTube ID.
    NoTranscriptError
        If no English transcript is available for the video.
    """
    _validate_video_id(video_id)

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en"])
    except NoTranscriptFound as exc:
        raise NoTranscriptError(
            f"No English transcript found for video {video_id}"
        ) from exc

    # Convert FetchedTranscriptSnippets → list[dict]
    raw_chunks = [
        {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
        for snippet in fetched
    ]

    return _merge_chunks(raw_chunks)


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
