"""Integration test — runs the full pipeline with a mocked YouTube transcript.

Mocks only the YouTubeTranscriptApi so no real network calls are made.
The FAISS index and sentence-transformer model are loaded for real to validate
end-to-end semantic matching behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.run_pipeline import run, LOGS_DIR

# ── Scripted 8-segment transcript ──────────────────────────────────────────
# 5 on-list segments (close to S001–S005 english_text so they match at ≥ 0.80)
# 3 deliberately off-list segments
_SCRIPTED_SNIPPETS = [
    # On-list (S001) — "Do you have any gum?"
    MagicMock(text="Do you have any gum?", start=0.0, duration=2.0),
    # On-list (S005) — "What kind of coffee do you like?"
    MagicMock(text="What kind of coffee do you like?", start=2.1, duration=2.4),
    # On-list (S014) — "Nice to meet you."
    MagicMock(text="Nice to meet you.", start=4.6, duration=1.8),
    # On-list (S024) — "Are you ready?"
    MagicMock(text="Are you ready?", start=6.5, duration=1.8),
    # On-list (S020) — "I don't understand. Please slow down."
    MagicMock(text="I don't understand. Please slow down.", start=8.4, duration=2.6),
    # Off-list 1
    MagicMock(text="The mitochondria is the powerhouse of the cell.", start=11.1, duration=3.5),
    # Off-list 2
    MagicMock(text="Quantum entanglement allows particles to be correlated over vast distances.", start=14.7, duration=4.0),
    # Off-list 3
    MagicMock(text="The Krebs cycle produces ATP through oxidative phosphorylation.", start=18.8, duration=3.8),
]

_VIDEO_ID = "E-gGacOpjCA"


@patch("src.transcript_ingestion.fetcher.YouTubeTranscriptApi")
def test_full_pipeline_integration(mock_api_cls, tmp_path, monkeypatch):
    """End-to-end pipeline run with 5 on-list + 3 off-list segments."""

    # Wire mock to return our scripted snippets
    mock_api_cls.return_value.fetch.return_value = _SCRIPTED_SNIPPETS

    # Redirect logs dir to tmp_path so we don't pollute the repo
    monkeypatch.setattr("src.pipeline.run_pipeline.LOGS_DIR", tmp_path)

    plan = run(_VIDEO_ID)

    # ── 1. Exactly 8 segments ──────────────────────────────────────────
    assert plan["total_segments"] == 8, (
        f"Expected 8 segments, got {plan['total_segments']}"
    )
    assert len(plan["segments"]) == 8

    # ── 2. The 5 matched segments have action="ASL" ────────────────────
    asl_segs = [s for s in plan["segments"] if s["action"] == "ASL"]
    assert plan["asl_segments"] >= 5, (
        f"Expected at least 5 ASL segments, got {plan['asl_segments']}"
    )

    # ── 3. The 3 off-list segments have action="CAPTIONS" (RAI gate) ───
    captions_segs = [s for s in plan["segments"] if s["action"] == "CAPTIONS"]
    assert plan["captions_segments"] >= 3, (
        f"Expected at least 3 CAPTIONS segments, got {plan['captions_segments']}"
    )
    # Verify at least the most obviously off-list text fell back
    captions_texts = [s["text"] for s in captions_segs]
    assert any("mitochondria" in t for t in captions_texts), (
        "Off-list sentence about mitochondria should be CAPTIONS"
    )

    # ── 4. run_id looks like a valid hex UUID fragment ─────────────────
    assert len(plan["run_id"]) == 12
    int(plan["run_id"], 16)  # raises ValueError if not valid hex

    # ── 5. Output file written to logs/ ────────────────────────────────
    render_files = list(tmp_path.glob("render_plan_*.json"))
    assert len(render_files) == 1
    with open(render_files[0], "r") as fh:
        saved = json.load(fh)
    assert saved["run_id"] == plan["run_id"]

    # ── 6. run_log.jsonl has a new entry ───────────────────────────────
    log_file = tmp_path / "run_log.jsonl"
    assert log_file.exists()
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["run_id"] == plan["run_id"]
    assert entry["video_id"] == _VIDEO_ID
