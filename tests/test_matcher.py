"""Unit tests for src.matcher.matcher — FAISS and sentence-transformers mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# We patch heavy dependencies so the tests never load real models / indices.
# Matcher.__init__ reads config.yaml, so we also patch _load_config.

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


def _make_matcher(metadata: dict, score: float, index_pos: int = 0):
    """Return a Matcher with mocked FAISS index and model.

    Parameters
    ----------
    metadata : dict
        position-str → sentence_id mapping.
    score : float
        The cosine-similarity score FAISS will return.
    index_pos : int
        The FAISS row index returned as best match.
    """
    from src.matcher.matcher import Matcher

    mock_index = MagicMock()
    mock_index.search.return_value = (
        np.array([[score]], dtype=np.float32),
        np.array([[index_pos]], dtype=np.int64),
    )

    mock_model = MagicMock()
    mock_model.encode.return_value = np.ones((1, 384), dtype=np.float32)

    with patch("src.matcher.matcher._load_config", return_value=_FAKE_CONFIG):
        matcher = Matcher(
            index=mock_index,
            metadata=metadata,
            model=mock_model,
        )
    return matcher


# Sample segment
_SEG = {
    "segment_id": "SEG_001",
    "start_ms": 0,
    "end_ms": 2000,
    "text": "hello everyone",
}


# ------------------------------------------------------------------
# 1. High score → action="ASL" with correct sentence_id
# ------------------------------------------------------------------

def test_high_score_returns_asl():
    metadata = {"0": "S001"}
    matcher = _make_matcher(metadata, score=0.95)

    result = matcher.match(dict(_SEG))

    assert result["action"] == "ASL"
    assert result["sentence_id"] == "S001"
    assert result["score"] == 0.95


# ------------------------------------------------------------------
# 2. Low score → action="CAPTIONS", sentence_id=None
# ------------------------------------------------------------------

def test_low_score_returns_captions():
    metadata = {"0": "S001"}
    matcher = _make_matcher(metadata, score=0.60)

    result = matcher.match(dict(_SEG))

    assert result["action"] == "CAPTIONS"
    assert result["sentence_id"] is None
    assert result["score"] == 0.60


# ------------------------------------------------------------------
# 3. sentence_id NOT in metadata → forced CAPTIONS even with high score
# ------------------------------------------------------------------

def test_missing_sentence_id_forces_captions():
    # Metadata has position "0" → "S001", but FAISS returns position 5
    # which is NOT in the metadata dict → allowlist gate fires.
    metadata = {"0": "S001"}
    matcher = _make_matcher(metadata, score=0.95, index_pos=5)

    result = matcher.match(dict(_SEG))

    assert result["action"] == "CAPTIONS"
    assert result["sentence_id"] is None
    assert result["score"] == 0.95


# ------------------------------------------------------------------
# 4. match_all processes every segment
# ------------------------------------------------------------------

def test_match_all_processes_all_segments():
    metadata = {"0": "S001"}
    matcher = _make_matcher(metadata, score=0.90)

    segments = [
        {**_SEG, "segment_id": f"SEG_{i:03d}", "text": f"text {i}"}
        for i in range(1, 4)
    ]

    results = matcher.match_all(segments)

    assert len(results) == 3
    for r in results:
        assert "action" in r
        assert "sentence_id" in r
        assert "score" in r
