"""Sprint 2 tests — asset enrichment, timing overlap, and run-log fields.

These are *unit* tests for the Sprint 2 additions to ``run_pipeline.py``.
They mock external I/O (config, manifest, FAISS, transcript) so they run
fast and deterministically.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.run_pipeline import (
    _build_render_plan,
    _detect_timing_overlaps,
    _append_run_log,
    _load_asset_manifest,
    LOGS_DIR,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_ASSET_CATALOGUE = {
    "S001": {"asset_id": "A001", "duration_ms": 2880, "english_text": "Do you have any gum?", "qa_status": "approved"},
    "S002": {"asset_id": "A002", "duration_ms": 2000, "english_text": "What is your password?", "qa_status": "approved"},
    "S003": {"asset_id": "A003", "duration_ms": 1500, "english_text": "Hello, how are you?", "qa_status": "approved"},
}

_ASSET_MANIFEST = {
    "A001": {"file_path": "assets/final/A001.mp4", "duration_ms": 2880, "fps": 25.0, "source": "wlasl", "qa_status": "approved", "width": 320, "height": 240},
    "A002": {"file_path": "assets/final/A002.mp4", "duration_ms": 2000, "fps": 25.0, "source": "placeholder", "qa_status": "approved", "width": 320, "height": 240},
    "A003": {"file_path": "assets/final/A003.mp4", "duration_ms": 1500, "fps": 25.0, "source": "wlasl", "qa_status": "approved", "width": 320, "height": 240},
}

_MATCHED_SEGMENTS = [
    {"segment_id": "seg-01", "text": "Do you have any gum?", "start_ms": 0, "end_ms": 2000, "action": "ASL", "score": 0.95, "sentence_id": "S001"},
    {"segment_id": "seg-02", "text": "What is your password?", "start_ms": 2100, "end_ms": 4500, "action": "ASL", "score": 0.88, "sentence_id": "S002"},
    {"segment_id": "seg-03", "text": "Quantum physics is fascinating.", "start_ms": 4600, "end_ms": 6000, "action": "CAPTIONS", "score": 0.30, "sentence_id": None},
    {"segment_id": "seg-04", "text": "Hello, how are you?", "start_ms": 6100, "end_ms": 7800, "action": "ASL", "score": 0.92, "sentence_id": "S003"},
]


@pytest.fixture
def _mock_config():
    """Patch _load_config so it returns a minimal config dict."""
    cfg = {
        "matcher": {
            "model_name": "all-MiniLM-L6-v2",
            "confidence_threshold": 0.70,
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
# Test 1: ASL segments have manifest metadata
# ---------------------------------------------------------------------------

def test_asl_segments_have_asset_metadata(_mock_config):
    """ASL segments must include asset_file_path, asset_duration_ms, asset_fps."""
    plan = _build_render_plan("abc123", "VIDEO1", _MATCHED_SEGMENTS, _ASSET_CATALOGUE, _ASSET_MANIFEST)

    asl_segments = [s for s in plan["segments"] if s["match"]["action"] == "ASL"]
    assert len(asl_segments) == 3

    for seg in asl_segments:
        m = seg["match"]
        assert m["asset_file_path"] is not None, f"{seg['segment_id']} missing asset_file_path"
        assert m["asset_duration_ms"] is not None, f"{seg['segment_id']} missing asset_duration_ms"
        assert m["asset_fps"] is not None, f"{seg['segment_id']} missing asset_fps"
        assert m["asset_file_path"].startswith("assets/final/")

    # Verify exact values for first ASL segment
    first = asl_segments[0]["match"]
    assert first["asset_file_path"] == "assets/final/A001.mp4"
    assert first["asset_duration_ms"] == 2880
    assert first["asset_fps"] == 25.0


# ---------------------------------------------------------------------------
# Test 2: CAPTIONS segments have null clip metadata
# ---------------------------------------------------------------------------

def test_captions_segments_have_null_metadata(_mock_config):
    """CAPTIONS segments must have null for asset_file_path, asset_duration_ms, asset_fps."""
    plan = _build_render_plan("abc123", "VIDEO1", _MATCHED_SEGMENTS, _ASSET_CATALOGUE, _ASSET_MANIFEST)

    cap_segments = [s for s in plan["segments"] if s["match"]["action"] == "CAPTIONS"]
    assert len(cap_segments) == 1

    m = cap_segments[0]["match"]
    assert m["asset_file_path"] is None
    assert m["asset_duration_ms"] is None
    assert m["asset_fps"] is None


# ---------------------------------------------------------------------------
# Test 3: Timing overlap detection
# ---------------------------------------------------------------------------

def test_detect_timing_overlaps_finds_overlap():
    """When an ASL clip's duration extends past the next clip start, flag it."""
    plan = {
        "summary": {},
        "asl_overlay_track": [
            {"segment_id": "seg-01", "start_ms": 0, "asset_duration_ms": 3000},
            {"segment_id": "seg-02", "start_ms": 2100, "asset_duration_ms": 2000},
            {"segment_id": "seg-03", "start_ms": 6000, "asset_duration_ms": 1000},
        ],
    }
    count = _detect_timing_overlaps(plan)
    assert count == 1, f"Expected 1 overlap, got {count}"
    assert plan["summary"]["timing_overlaps"] == 1


def test_detect_timing_overlaps_none():
    """No overlaps when clips fit within their time windows."""
    plan = {
        "summary": {},
        "asl_overlay_track": [
            {"segment_id": "seg-01", "start_ms": 0, "asset_duration_ms": 1000},
            {"segment_id": "seg-02", "start_ms": 2000, "asset_duration_ms": 1000},
        ],
    }
    count = _detect_timing_overlaps(plan)
    assert count == 0
    assert plan["summary"]["timing_overlaps"] == 0


def test_detect_timing_overlaps_null_duration_skips():
    """If asset_duration_ms is None, skip that pair (no crash)."""
    plan = {
        "summary": {},
        "asl_overlay_track": [
            {"segment_id": "seg-01", "start_ms": 0, "asset_duration_ms": None},
            {"segment_id": "seg-02", "start_ms": 100, "asset_duration_ms": 1000},
        ],
    }
    count = _detect_timing_overlaps(plan)
    assert count == 0


# ---------------------------------------------------------------------------
# Test 4: Missing asset_id logs warning but doesn't crash
# ---------------------------------------------------------------------------

def test_missing_asset_id_warns_but_succeeds(_mock_config, caplog):
    """A segment referencing a manifest-missing asset_id should warn, not crash."""
    # A004 is not in the manifest
    catalogue_extra = {
        **_ASSET_CATALOGUE,
        "S099": {"asset_id": "A099", "duration_ms": 999, "english_text": "Ghost entry", "qa_status": "approved"},
    }
    segments = [
        *_MATCHED_SEGMENTS,
        {"segment_id": "seg-99", "text": "Ghost entry", "start_ms": 8000, "end_ms": 9000, "action": "ASL", "score": 0.80, "sentence_id": "S099"},
    ]

    with caplog.at_level(logging.WARNING, logger="src.pipeline.run_pipeline"):
        plan = _build_render_plan("abc123", "VIDEO1", segments, catalogue_extra, _ASSET_MANIFEST)

    # Should not crash — plan returned with all segments
    assert len(plan["segments"]) == 5

    # The warning about A099 should be in logs
    assert any("A099" in record.message for record in caplog.records), (
        "Expected a warning about missing asset A099 in manifest"
    )

    # The segment should still exist with null metadata
    ghost_seg = [s for s in plan["segments"] if s["segment_id"] == "seg-99"][0]
    assert ghost_seg["match"]["asset_file_path"] is None
    assert ghost_seg["match"]["asset_duration_ms"] is None


# ---------------------------------------------------------------------------
# Test 5: Run log includes Sprint 2 fields
# ---------------------------------------------------------------------------

def test_run_log_has_sprint2_fields(tmp_path, monkeypatch, _mock_config):
    """run_log.jsonl entry should contain assets_used, placeholder_count, timing_overlaps."""
    monkeypatch.setattr("src.pipeline.run_pipeline.LOGS_DIR", tmp_path)

    plan = _build_render_plan("run123", "VID1", _MATCHED_SEGMENTS, _ASSET_CATALOGUE, _ASSET_MANIFEST)
    plan["summary"]["timing_overlaps"] = 1  # simulate

    _append_run_log(plan, "output.json", _ASSET_MANIFEST, timing_overlaps=1)

    log_path = tmp_path / "run_log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())

    assert "assets_used" in entry
    assert "placeholder_count" in entry
    assert "timing_overlaps" in entry
    assert entry["assets_used"] == 3  # A001, A002, A003
    assert entry["placeholder_count"] == 1  # A002 is placeholder
    assert entry["timing_overlaps"] == 1


# ---------------------------------------------------------------------------
# Test 6: ASL overlay track has manifest fields
# ---------------------------------------------------------------------------

def test_asl_overlay_track_enriched(_mock_config):
    """Each asl_overlay_track entry should carry file_path, duration_ms, fps."""
    plan = _build_render_plan("abc123", "VIDEO1", _MATCHED_SEGMENTS, _ASSET_CATALOGUE, _ASSET_MANIFEST)

    track = plan["asl_overlay_track"]
    assert len(track) == 3  # 3 ASL segments

    for t in track:
        assert t["asset_file_path"] is not None
        assert t["asset_duration_ms"] is not None
        assert t["asset_fps"] is not None
        assert isinstance(t["asset_fps"], float)
