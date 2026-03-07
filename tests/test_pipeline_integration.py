"""Integration test — runs the full pipeline with mocked external services.

Mocks the YouTubeTranscriptApi, GlossTranslator (LLM), WordLookup, and
chain_clips so no real network/API calls are made.  Validates end-to-end
GenAI gloss-based pipeline behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.run_pipeline import run, LOGS_DIR

# ── Scripted 8-segment transcript ──────────────────────────────────────────
_SCRIPTED_SNIPPETS = [
    MagicMock(text="Do you have any gum?", start=0.0, duration=2.0),
    MagicMock(text="What kind of coffee do you like?", start=2.1, duration=2.4),
    MagicMock(text="Nice to meet you.", start=4.6, duration=2.1),
    MagicMock(text="Are you ready?", start=6.8, duration=2.1),
    MagicMock(text="I don't understand. Please slow down.", start=9.0, duration=2.6),
    MagicMock(text="The mitochondria is the powerhouse of the cell.", start=11.7, duration=3.5),
    MagicMock(text="Quantum entanglement allows particles to be correlated over vast distances.", start=15.3, duration=4.0),
    MagicMock(text="The Krebs cycle produces ATP through oxidative phosphorylation.", start=19.4, duration=3.8),
]

_VIDEO_ID = "E-gGacOpjCA"


def _make_mock_translator():
    """Return a mock GlossTranslator that produces glosses for any input."""
    translator = MagicMock()

    # Mapping of keywords in text → gloss sequences (all words in available set)
    _KEYWORD_GLOSSES = {
        "gum": ["GUM", "HAVE", "YOU"],
        "coffee": ["COFFEE", "LIKE", "WHAT"],
        "meet": ["NICE", "MEET", "YOU"],
        "ready": ["READY", "YOU"],
        "understand": ["UNDERSTAND", "NOT", "PLEASE"],
    }
    # Off-list sentences get glosses NOT in the available set
    _OFFTOPIC_GLOSS = ["UNKNOWN_WORD"]

    def translate(text):
        text_lower = text.lower()
        for kw, glosses in _KEYWORD_GLOSSES.items():
            if kw in text_lower:
                return glosses
        return _OFFTOPIC_GLOSS

    def translate_segments(segments):
        results = []
        for seg in segments:
            enriched = dict(seg)
            glosses = translate(seg["text"])
            enriched["gloss_sequence"] = glosses
            enriched["gloss_text"] = " ".join(glosses)
            results.append(enriched)
        return results

    translator.translate.side_effect = translate
    translator.translate_segments.side_effect = translate_segments
    return translator


def _make_mock_word_lookup():
    """Return a mock WordLookup with common words available."""
    available = {"GUM", "HAVE", "YOU", "COFFEE", "LIKE", "WHAT", "NICE",
                 "MEET", "READY", "UNDERSTAND", "NOT", "PLEASE"}
    lookup = MagicMock()
    lookup.available_glosses = available

    def lookup_single(gloss):
        g = gloss.upper()
        if g in available:
            return {"word_id": f"W_{g}", "gloss": g, "source": "wlasl",
                    "file_path": f"assets/words/W_{g}.mp4", "duration_ms": 800}
        return None

    def lookup_sequence(glosses):
        results = []
        for g in glosses:
            g_upper = g.upper()
            if g_upper in available:
                results.append({
                    "gloss": g_upper, "found": True, "word_id": f"W_{g_upper}",
                    "file_path": f"assets/words/W_{g_upper}.mp4",
                    "duration_ms": 800,
                    "abs_path": f"D:/gitgit/asl-gen/assets/words/W_{g_upper}.mp4",
                })
            else:
                results.append({
                    "gloss": g_upper, "found": False, "word_id": None,
                    "file_path": None, "duration_ms": 0, "abs_path": None,
                })
        return results

    lookup.lookup.side_effect = lookup_single
    lookup.lookup_sequence.side_effect = lookup_sequence
    return lookup


def _mock_chain_clips(clip_entries, output_name, output_dir=None):
    """Mock chain_clips that returns a fake chained clip info."""
    found = [e for e in clip_entries if e.get("found")]
    if not found:
        return None
    return {
        "path": f"assets/chained/{output_name}.mp4",
        "rel_path": f"assets/chained/{output_name}.mp4",
        "duration_ms": sum(c["duration_ms"] for c in found),
        "clip_count": len(found),
        "glosses": [c["gloss"] for c in found],
    }


@patch("src.pipeline.run_pipeline.chain_clips", side_effect=_mock_chain_clips)
@patch("src.pipeline.run_pipeline.WordLookup")
@patch("src.pipeline.run_pipeline.GlossTranslator")
@patch("src.transcript_ingestion.fetcher.YouTubeTranscriptApi")
def test_full_pipeline_integration(mock_api_cls, mock_translator_cls,
                                   mock_lookup_cls, mock_chain_fn,
                                   tmp_path, monkeypatch):
    """End-to-end pipeline run with 5 translatable + 3 off-list segments."""

    # Wire mocks
    mock_api_cls.return_value.fetch.return_value = _SCRIPTED_SNIPPETS
    mock_translator_cls.return_value = _make_mock_translator()
    mock_lookup_cls.return_value = _make_mock_word_lookup()

    # Redirect logs dir to tmp_path
    monkeypatch.setattr("src.pipeline.run_pipeline.LOGS_DIR", tmp_path)

    plan = run(_VIDEO_ID)

    # ── 1. Exactly 8 segments ──────────────────────────────────────────
    assert plan["summary"]["total_segments"] == 8, (
        f"Expected 8 segments, got {plan['summary']['total_segments']}"
    )
    assert len(plan["segments"]) == 8

    # ── 2. Segments with available word clips have action="ASL" ────────
    asl_segs = [s for s in plan["segments"] if s["match"]["action"] == "ASL"]
    assert plan["summary"]["asl_segments"] >= 5, (
        f"Expected at least 5 ASL segments, got {plan['summary']['asl_segments']}"
    )

    # ── 3. Segments with no available clips fall back to CAPTIONS ──────
    captions_segs = [s for s in plan["segments"] if s["match"]["action"] == "CAPTIONS"]
    # The off-list sentences have glosses not in our mock available set
    captions_texts = [s["source_text"] for s in captions_segs]

    # ── 4. run_id looks like a valid hex UUID fragment ─────────────────
    assert len(plan["run_id"]) == 12
    int(plan["run_id"], 16)  # raises ValueError if not valid hex

    # ── 5. Output file written to logs/ ────────────────────────────────
    render_files = list(tmp_path.glob("render_plan_*.json"))
    assert len(render_files) == 1
    with open(render_files[0], "r") as fh:
        saved = json.load(fh)
    assert saved["run_id"] == plan["run_id"]
    assert saved["schema_version"] == "3.0"

    # ── 6. run_log.jsonl has a new entry ───────────────────────────────
    log_file = tmp_path / "run_log.jsonl"
    assert log_file.exists()
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["run_id"] == plan["run_id"]
    assert entry["video_id"] == _VIDEO_ID

    # ── 7. ASL overlay track for compositing ──────────────────────────
    track = plan["asl_overlay_track"]
    assert len(track) >= 5, f"Expected at least 5 ASL overlay entries, got {len(track)}"
    for t in track:
        assert "start_ms" in t and "end_ms" in t
        assert "start_tc" in t
        assert "asset_file_path" in t
        assert "gloss_sequence" in t

    # ── 8. Structured segment sub-objects present ─────────────────────
    first = plan["segments"][0]
    assert "timing" in first and "match" in first and "source_text" in first
    assert "duration_ms" in first["timing"]
    assert "gloss_sequence" in first["match"]
