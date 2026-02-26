"""RAI allowlist gate tests — verify the responsible-AI safety mechanisms.

These tests ensure that the allowlist gate and suspicious-ratio warnings
work correctly regardless of FAISS scores.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── Shared config mock (avoids reading config.yaml in some tests) ──────────

_FAKE_CONFIG = {
    "matcher": {
        "model_name": "all-MiniLM-L6-v2",
        "confidence_threshold": 0.80,
        "top_k": 1,
    },
    "paths": {
        "supported_set": "data/supported_set_v1.csv",
        "faiss_index": "data/faiss_index.bin",
        "index_metadata": "data/index_metadata.json",
        "logs": "logs/",
    },
}


def _mock_matcher(metadata: dict, score: float, index_pos: int = 0):
    """Build a Matcher with mocked FAISS + model."""
    from src.matcher.matcher import Matcher

    mock_index = MagicMock()
    mock_index.search.return_value = (
        np.array([[score]], dtype=np.float32),
        np.array([[index_pos]], dtype=np.int64),
    )
    mock_model = MagicMock()
    mock_model.encode.return_value = np.ones((1, 384), dtype=np.float32)

    with patch("src.matcher.matcher._load_config", return_value=_FAKE_CONFIG):
        return Matcher(
            index=mock_index,
            metadata=metadata,
            model=mock_model,
        )


_SEG = {
    "segment_id": "SEG_001",
    "start_ms": 0,
    "end_ms": 2000,
    "text": "some random text",
}


# ------------------------------------------------------------------
# 1. sentence_id not in metadata → CAPTIONS even at score 0.95
# ------------------------------------------------------------------

def test_unknown_sentence_id_forced_captions():
    metadata = {"0": "S001"}
    matcher = _mock_matcher(metadata, score=0.95, index_pos=99)

    result = matcher.match(dict(_SEG))

    assert result["action"] == "CAPTIONS"
    assert result["sentence_id"] is None
    assert result["score"] == 0.95


# ------------------------------------------------------------------
# 2. 10 off-list sentences → ALL produce CAPTIONS, zero ASL
# ------------------------------------------------------------------

def test_ten_offlist_sentences_all_captions():
    metadata = {"0": "S001"}
    # FAISS returns position 42 which is NOT in the tiny metadata dict
    matcher = _mock_matcher(metadata, score=0.50, index_pos=42)

    off_list = [
        {**_SEG, "segment_id": f"SEG_{i:03d}", "text": f"off-list sentence {i}"}
        for i in range(1, 11)
    ]

    results = matcher.match_all(off_list)

    asl_results = [r for r in results if r["action"] == "ASL"]
    cap_results = [r for r in results if r["action"] == "CAPTIONS"]
    assert len(asl_results) == 0, "No off-list sentence should be ASL"
    assert len(cap_results) == 10, "All 10 should be CAPTIONS"


# ------------------------------------------------------------------
# 3. asl_segments / total > 0.90 → suspicious match rate WARNING
# ------------------------------------------------------------------

def test_high_asl_ratio_triggers_warning(caplog):
    from src.pipeline.run_pipeline import _responsible_ai_warnings

    plan = {
        "video_id": "test12345ab",
        "total_segments": 10,
        "asl_segments": 10,
        "captions_segments": 0,
        "segments": [],
    }

    with caplog.at_level(logging.WARNING):
        _responsible_ai_warnings(plan)

    assert any("suspiciously high" in rec.message.lower() for rec in caplog.records), (
        "Expected a 'suspiciously high' warning when ASL ratio > 0.90"
    )


# ------------------------------------------------------------------
# 4. Empty transcript → total_segments == 0 WARNING
# ------------------------------------------------------------------

def test_zero_segments_triggers_warning(caplog):
    from src.pipeline.run_pipeline import _responsible_ai_warnings

    plan = {
        "video_id": "test12345ab",
        "total_segments": 0,
        "asl_segments": 0,
        "captions_segments": 0,
        "segments": [],
    }

    with caplog.at_level(logging.WARNING):
        _responsible_ai_warnings(plan)

    assert any("0 segments" in rec.message for rec in caplog.records), (
        "Expected a '0 segments' warning for empty transcript"
    )
