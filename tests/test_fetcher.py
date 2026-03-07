"""Unit tests for src.transcript_ingestion.fetcher."""

from unittest.mock import MagicMock, patch

import pytest

from src.transcript_ingestion.fetcher import (
    NoTranscriptError,
    fetch_transcript,
)

# Re-usable video ID (valid 11-char string)
_VID = "dQw4w9WgXcQ"


def _snippet(text: str, start: float, duration: float) -> MagicMock:
    """Create a mock FetchedTranscriptSnippet."""
    s = MagicMock()
    s.text = text
    s.start = start
    s.duration = duration
    return s


# ------------------------------------------------------------------
# 1. Normal transcript → correctly formatted segments
# ------------------------------------------------------------------

@patch("src.transcript_ingestion.fetcher._save_cache")
@patch("src.transcript_ingestion.fetcher._load_cached", return_value=None)
@patch("src.transcript_ingestion.fetcher.YouTubeTranscriptApi")
def test_normal_transcript_returns_formatted_segments(mock_api_cls, _mc, _sc):
    """Segments have the expected keys, types, and SEG_NNN id format."""
    snippets = [
        _snippet("Hello everyone.", 0.0, 2.0),
        _snippet("Welcome to the channel.", 2.0, 2.5),
    ]
    mock_api_cls.return_value.fetch.return_value = snippets

    segments = fetch_transcript(_VID)

    assert len(segments) >= 1
    seg = segments[0]
    assert set(seg.keys()) == {"segment_id", "start_ms", "end_ms", "text"}
    assert seg["segment_id"].startswith("SEG_")
    assert isinstance(seg["start_ms"], int)
    assert isinstance(seg["end_ms"], int)
    assert isinstance(seg["text"], str)
    assert seg["text"]  # not empty


# ------------------------------------------------------------------
# 2. Filler words are stripped
# ------------------------------------------------------------------

@patch("src.transcript_ingestion.fetcher._save_cache")
@patch("src.transcript_ingestion.fetcher._load_cached", return_value=None)
@patch("src.transcript_ingestion.fetcher.YouTubeTranscriptApi")
def test_filler_words_are_removed(mock_api_cls, _mc, _sc):
    """Standalone filler words (um, uh, like, you know, so, well) are removed."""
    snippets = [
        _snippet("Um so you know like I uh went to the well store.", 0.0, 4.0),
    ]
    mock_api_cls.return_value.fetch.return_value = snippets

    segments = fetch_transcript(_VID)

    text = segments[0]["text"]
    # None of the filler words should remain as standalone words
    assert "um" not in text.split()
    assert "uh" not in text.split()
    assert "you know" not in text
    assert text  # still has content


# ------------------------------------------------------------------
# 3. Chunks within 1.5 s gap are merged into one segment
# ------------------------------------------------------------------

@patch("src.transcript_ingestion.fetcher._save_cache")
@patch("src.transcript_ingestion.fetcher._load_cached", return_value=None)
@patch("src.transcript_ingestion.fetcher.YouTubeTranscriptApi")
def test_chunks_within_gap_are_merged(mock_api_cls, _mc, _sc):
    """Consecutive chunks with < 1.5 s gap and no sentence-ending punctuation
    are merged into a single segment."""
    snippets = [
        _snippet("hello everyone", 0.0, 1.0),       # ends at 1.0
        _snippet("welcome to the channel", 1.2, 1.5),  # starts at 1.2 → gap 0.2 s
    ]
    mock_api_cls.return_value.fetch.return_value = snippets

    segments = fetch_transcript(_VID)

    # Both chunks should merge into one segment
    assert len(segments) == 1
    assert "hello everyone" in segments[0]["text"]
    assert "welcome to the channel" in segments[0]["text"]


# ------------------------------------------------------------------
# 4. NoTranscriptError raised when no English transcript exists
# ------------------------------------------------------------------

@patch("src.transcript_ingestion.fetcher._save_cache")
@patch("src.transcript_ingestion.fetcher._load_cached", return_value=None)
@patch("src.transcript_ingestion.fetcher._fetch_via_ytdlp", side_effect=NoTranscriptError("yt-dlp also failed"))
@patch("src.transcript_ingestion.fetcher.YouTubeTranscriptApi")
def test_no_english_transcript_raises_error(mock_api_cls, mock_ytdlp, _mc, _sc):
    """NoTranscriptError is raised when both the API and yt-dlp fail."""
    from youtube_transcript_api import NoTranscriptFound

    mock_api_cls.return_value.fetch.side_effect = NoTranscriptFound(
        "dQw4w9WgXcQ", ["de"], {}
    )

    with pytest.raises(NoTranscriptError):
        fetch_transcript(_VID)
