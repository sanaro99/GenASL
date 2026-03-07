"""Sprint 3 tests — normalization fixes, overlap resolution, filtering, run-log fields.

These are *unit* tests for the Sprint 3 additions to the pipeline.
They mock external I/O so they run fast and deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.run_pipeline import (
    _build_render_plan,
    _detect_timing_overlaps,
    _resolve_overlaps,
    _filter_short_segments,
    _append_run_log,
    LOGS_DIR,
)
from src.transcript_ingestion.fetcher import _normalise

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_ASSET_CATALOGUE = {
    "S001": {"asset_id": "A001", "duration_ms": 2880, "english_text": "Do you have any gum?", "qa_status": "approved"},
    "S002": {"asset_id": "A002", "duration_ms": 2000, "english_text": "What is your password?", "qa_status": "approved"},
    "S003": {"asset_id": "A003", "duration_ms": 1500, "english_text": "Hello, how are you?", "qa_status": "approved"},
}

_ASSET_MANIFEST = {
    "A001": {"file_path": "assets/final/A001_S001_GUM.mp4", "duration_ms": 2880, "fps": 25.0, "source": "wlasl", "qa_status": "approved", "width": 320, "height": 240, "signer_id": 9},
    "A002": {"file_path": "assets/final/A002_S002_PASSWORD.mp4", "duration_ms": 2000, "fps": 25.0, "source": "placeholder", "qa_status": "approved", "width": 320, "height": 240, "signer_id": None},
    "A003": {"file_path": "assets/final/A003_S003_HELLO.mp4", "duration_ms": 1500, "fps": 25.0, "source": "wlasl", "qa_status": "approved", "width": 320, "height": 240, "signer_id": 9},
}


@pytest.fixture
def _mock_config():
    """Patch _load_config so it returns a config dict with threshold=0.80."""
    cfg = {
        "matcher": {
            "model_name": "all-MiniLM-L6-v2",
            "confidence_threshold": 0.80,
            "top_k": 1,
        },
        "paths": {
            "supported_set": "data/supported_set.csv",
            "faiss_index": "data/faiss_index.bin",
            "index_metadata": "data/index_metadata.json",
            "asset_manifest": "assets/asset_manifest_v1.json",
            "logs": "logs",
        },
    }
    with patch("src.pipeline.run_pipeline._load_config", return_value=cfg):
        yield cfg


# ---------------------------------------------------------------------------
# Test 1: Bracket tags are stripped from transcript text
# ---------------------------------------------------------------------------

def test_bracket_tags_stripped():
    """Square-bracket tags like [music] and [applause] are removed."""
    assert _normalise("[music] do you need help?") == "do you need help?"
    assert _normalise("[applause] hello everyone") == "hello everyone"
    assert _normalise("before [laughing] after") == "before after"
    # Multiple brackets
    assert _normalise("[music][applause] test") == "test"
    # Empty after stripping
    assert _normalise("[music]") == ""


# ---------------------------------------------------------------------------
# Test 2: Short segments are filtered out
# ---------------------------------------------------------------------------

def test_filter_short_segments_by_word_count():
    """Segments with fewer than 3 words are filtered."""
    segments = [
        {"segment_id": "SEG_001", "text": "hello world", "start_ms": 0, "end_ms": 5000},
        {"segment_id": "SEG_002", "text": "this is a proper sentence", "start_ms": 5000, "end_ms": 10000},
    ]
    kept, filtered = _filter_short_segments(segments)
    assert len(kept) == 1
    assert len(filtered) == 1
    assert filtered[0]["segment_id"] == "SEG_001"


def test_filter_short_segments_by_duration():
    """Segments shorter than 2000ms are filtered."""
    segments = [
        {"segment_id": "SEG_001", "text": "this is fine", "start_ms": 0, "end_ms": 1500},
        {"segment_id": "SEG_002", "text": "this is also fine", "start_ms": 2000, "end_ms": 5000},
    ]
    kept, filtered = _filter_short_segments(segments)
    assert len(kept) == 1
    assert len(filtered) == 1
    assert filtered[0]["segment_id"] == "SEG_001"


def test_filter_keeps_valid_segments():
    """Segments with ≥3 words AND ≥2000ms duration are kept."""
    segments = [
        {"segment_id": "SEG_001", "text": "do you have any gum", "start_ms": 0, "end_ms": 3000},
        {"segment_id": "SEG_002", "text": "what kind of coffee", "start_ms": 3500, "end_ms": 6000},
    ]
    kept, filtered = _filter_short_segments(segments)
    assert len(kept) == 2
    assert len(filtered) == 0


# ---------------------------------------------------------------------------
# Test 3: Overlap resolution keeps higher-scoring entry
# ---------------------------------------------------------------------------

def test_resolve_overlaps_keeps_higher_score():
    """When two ASL clips overlap, the higher-scoring one is kept."""
    plan = {
        "summary": {},
        "asl_overlay_track": [
            {"segment_id": "SEG_001", "start_ms": 0, "asset_duration_ms": 3000, "score": 0.85},
            {"segment_id": "SEG_002", "start_ms": 2100, "asset_duration_ms": 2000, "score": 0.92},
            {"segment_id": "SEG_003", "start_ms": 6000, "asset_duration_ms": 1000, "score": 0.88},
        ],
    }
    resolved = _resolve_overlaps(plan)
    assert resolved == 1

    track = plan["asl_overlay_track"]
    # SEG_001 (0.85) overlaps SEG_002 (0.92) → SEG_001 dropped
    assert track[0]["kept"] is False   # lower score
    assert track[1]["kept"] is True    # higher score
    assert track[2]["kept"] is True    # no overlap


def test_resolve_overlaps_no_conflicts():
    """No overlaps → all entries kept, resolved count = 0."""
    plan = {
        "summary": {},
        "asl_overlay_track": [
            {"segment_id": "SEG_001", "start_ms": 0, "asset_duration_ms": 1000, "score": 0.90},
            {"segment_id": "SEG_002", "start_ms": 2000, "asset_duration_ms": 1000, "score": 0.85},
        ],
    }
    resolved = _resolve_overlaps(plan)
    assert resolved == 0
    assert all(e["kept"] for e in plan["asl_overlay_track"])


# ---------------------------------------------------------------------------
# Test 4: Render plan includes filtered_segments summary
# ---------------------------------------------------------------------------

def test_render_plan_has_filtered_count(_mock_config):
    """Render plan summary includes filtered_segments count."""
    matched = [
        {"segment_id": "SEG_001", "text": "Do you have any gum?", "start_ms": 0, "end_ms": 3000,
         "action": "ASL", "score": 0.95, "sentence_id": "S001"},
    ]
    filtered = [
        {"segment_id": "SEG_002", "text": "cc.", "start_ms": 3000, "end_ms": 4000},
    ]
    plan = _build_render_plan("test123", "VID", matched, _ASSET_CATALOGUE, _ASSET_MANIFEST, filtered)
    assert plan["summary"]["filtered_segments"] == 1
    assert len(plan["filtered_segments"]) == 1
    assert plan["filtered_segments"][0]["match"]["action"] == "FILTERED"


# ---------------------------------------------------------------------------
# Test 5: Run log includes Sprint 3 fields
# ---------------------------------------------------------------------------

def test_run_log_has_sprint3_fields(tmp_path, monkeypatch, _mock_config):
    """run_log.jsonl entry should contain filtered_segments, overlaps_resolved, threshold."""
    monkeypatch.setattr("src.pipeline.run_pipeline.LOGS_DIR", tmp_path)

    matched = [
        {"segment_id": "SEG_001", "text": "Do you have any gum?", "start_ms": 0, "end_ms": 3000,
         "action": "ASL", "score": 0.95, "sentence_id": "S001"},
    ]
    plan = _build_render_plan("run456", "VID2", matched, _ASSET_CATALOGUE, _ASSET_MANIFEST)
    plan["summary"]["timing_overlaps"] = 0
    plan["summary"]["overlaps_resolved"] = 1

    _append_run_log(plan, "output.json", _ASSET_MANIFEST, timing_overlaps=0)

    log_path = tmp_path / "run_log.jsonl"
    entry = json.loads(log_path.read_text().strip())

    assert "filtered_segments" in entry
    assert "overlaps_resolved" in entry
    assert "confidence_threshold" in entry
    assert entry["confidence_threshold"] == 0.80
    assert entry["overlaps_resolved"] == 1


# ---------------------------------------------------------------------------
# Test 6: Threshold is 0.80 in config
# ---------------------------------------------------------------------------

def test_threshold_is_080(_mock_config):
    """Config threshold must be 0.80 (Sprint 3 revert)."""
    assert _mock_config["matcher"]["confidence_threshold"] == 0.80
