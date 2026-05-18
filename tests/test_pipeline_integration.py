"""Integration test — drives the new Pipeline with stubbed external services.

Mocks ``fetch_transcript`` (no YouTube), ``chain_clips`` (no FFmpeg), and
the LLM (FakeProvider with a callable that parses the numbered batch user
content). Exercises every stage end-to-end and asserts the resulting
:class:`RenderPlan` is structurally correct.
"""

from __future__ import annotations

import json
import re

import pytest

from src.gloss.providers.fake import FakeProvider
from src.gloss.translator import GlossTranslator
from src.gloss.word_lookup import WordLookup
from src.pipeline.models import RenderPlan
from src.pipeline.pipeline import Pipeline


_VIDEO_ID = "E-gGacOpjCA"

# 8 scripted transcript segments — five map to a gloss whose words are in
# the lookup manifest (→ ASL), three map to an unknown gloss (→ CAPTIONS).
_SCRIPTED_RAW = [
    {"segment_id": "SEG_001", "start_ms": 0,     "end_ms": 2000,  "text": "do you have any gum"},
    {"segment_id": "SEG_002", "start_ms": 2100,  "end_ms": 4500,  "text": "what kind of coffee do you like"},
    {"segment_id": "SEG_003", "start_ms": 4600,  "end_ms": 6700,  "text": "nice to meet you"},
    {"segment_id": "SEG_004", "start_ms": 6800,  "end_ms": 8900,  "text": "are you ready"},
    {"segment_id": "SEG_005", "start_ms": 9000,  "end_ms": 11600, "text": "i don't understand please slow down"},
    {"segment_id": "SEG_006", "start_ms": 11700, "end_ms": 15200, "text": "the mitochondria is the powerhouse of the cell"},
    {"segment_id": "SEG_007", "start_ms": 15300, "end_ms": 19300, "text": "quantum entanglement allows particles to be correlated"},
    {"segment_id": "SEG_008", "start_ms": 19400, "end_ms": 23200, "text": "the krebs cycle produces atp"},
]

_KEYWORD_GLOSSES = {
    "gum":        "GUM HAVE YOU",
    "coffee":     "COFFEE LIKE WHAT",
    "meet":       "NICE MEET YOU",
    "ready":      "READY YOU",
    "understand": "UNDERSTAND NOT PLEASE",
}

_AVAILABLE = {"GUM", "HAVE", "YOU", "COFFEE", "LIKE", "WHAT",
              "NICE", "MEET", "READY", "UNDERSTAND", "NOT", "PLEASE"}


def _gloss_for(text: str) -> str:
    """Return the canned gloss string for one English line."""
    t = text.lower()
    for keyword, gloss in _KEYWORD_GLOSSES.items():
        if keyword in t:
            return gloss
    return "UNKNOWN_WORD"


def _scripted_chat(system: str, user: str) -> str:
    """Parse the numbered batch input and return the matching numbered gloss output."""
    out_lines: list[str] = []
    for m in re.finditer(r"^(\d+)\.\s*(.+)$", user, flags=re.MULTILINE):
        out_lines.append(f"{m.group(1)}. {_gloss_for(m.group(2).strip())}")
    return "\n".join(out_lines) if out_lines else _gloss_for(user)


def _write_word_manifest(tmp_path, duration_ms: int = 400) -> "Path":
    """Build a word_manifest.json containing only the test's available glosses."""
    manifest = {
        "version": "1.0",
        "words": [
            {
                "word_id": f"W_{g}",
                "gloss": g,
                "source": "wlasl",
                "file_path": f"assets/words/W_{g}.mp4",
                "duration_ms": duration_ms,
            }
            for g in sorted(_AVAILABLE)
        ],
    }
    path = tmp_path / "word_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _fake_chain_clips(entries, output_name, output_dir=None):
    """Stand-in for chain_clips that skips FFmpeg."""
    found = [e for e in entries if e.get("found")]
    if not found:
        return None
    return {
        "path": f"/tmp/{output_name}.mp4",
        "rel_path": f"assets/chained/{output_name}.mp4",
        "duration_ms": sum(c["duration_ms"] for c in found),
        "clip_count": len(found),
        "glosses": [c["gloss"] for c in found],
    }


def test_pipeline_end_to_end(tmp_path, monkeypatch):
    """Drive Pipeline.run() with stubbed I/O and assert the RenderPlan."""

    # 1. fetch_transcript -> scripted segments (no network)
    monkeypatch.setattr(
        "src.pipeline.stages.fetch.fetch_transcript",
        lambda video_id: [dict(s) for s in _SCRIPTED_RAW],
    )

    # 2. chain_clips -> no FFmpeg
    monkeypatch.setattr("src.pipeline.stages.chain.chain_clips", _fake_chain_clips)

    # 3. Build the Pipeline with its cache rooted in tmp_path so the test
    #    doesn't pollute data/cache/.
    pipeline = Pipeline(cache_root=tmp_path / "cache")

    # 4. Inject the scripted LLM provider into TranslateStage.
    pipeline.translate._translator = GlossTranslator(provider=FakeProvider(canned=_scripted_chat))

    # 5. Inject a WordLookup backed by the tmp manifest.
    pipeline.lookup._lookup = WordLookup(manifest_path=_write_word_manifest(tmp_path))

    plan = pipeline.run(_VIDEO_ID, use_cache=False)

    # --- Plan shape ---------------------------------------------------
    assert isinstance(plan, RenderPlan)
    assert plan.schema_version == "4.0"
    assert plan.video_id == _VIDEO_ID
    assert len(plan.run_id) == 12
    int(plan.run_id, 16)  # raises if not hex

    # --- Segments ------------------------------------------------------
    assert plan.summary.total_segments == 8
    assert len(plan.segments) == 8
    assert plan.summary.asl_segments == 5  # five keyword-matching sentences
    assert plan.summary.captions_segments == 3

    asl_ids = {s.segment_id for s in plan.segments if s.match.action == "ASL"}
    assert asl_ids == {"SEG_001", "SEG_002", "SEG_003", "SEG_004", "SEG_005"}

    cap_ids = {s.segment_id for s in plan.segments if s.match.action == "CAPTIONS"}
    assert cap_ids == {"SEG_006", "SEG_007", "SEG_008"}

    # --- Pipeline metadata --------------------------------------------
    assert plan.pipeline.provider == "ollama"      # default per Settings
    assert plan.pipeline.mode == "genai_gloss"

    # --- Overlay track -------------------------------------------------
    track = plan.asl_overlay_track
    assert len(track) == 5
    for entry in track:
        assert entry.asset_file_path.endswith(".mp4")
        assert entry.asset_duration_ms > 0
        assert entry.gloss_sequence
        assert entry.kept is True

    # --- ASL match details on a known segment --------------------------
    seg = next(s for s in plan.segments if s.segment_id == "SEG_001")
    assert seg.match.gloss_sequence == ["GUM", "HAVE", "YOU"]
    assert seg.match.word_coverage == 1.0
    assert seg.match.found_glosses == ["GUM", "HAVE", "YOU"]
    assert seg.match.missing_glosses == []

    # --- No timing overlaps in this fixture ----------------------------
    assert plan.summary.timing_overlaps == 0
    assert plan.summary.overlaps_resolved == 0


def test_pipeline_high_asl_ratio_warns(tmp_path, monkeypatch, caplog):
    """When asl_ratio > settings.pipeline.high_asl_ratio_warn the RAI check logs a warning."""

    # All 8 sentences map to an in-manifest gloss → ratio == 1.0
    monkeypatch.setattr(
        "src.pipeline.stages.fetch.fetch_transcript",
        lambda video_id: [
            {"segment_id": f"SEG_{i:03d}", "start_ms": i * 3000, "end_ms": i * 3000 + 2500,
             "text": "do you have any gum"}
            for i in range(1, 9)
        ],
    )
    monkeypatch.setattr("src.pipeline.stages.chain.chain_clips", _fake_chain_clips)

    pipeline = Pipeline(cache_root=tmp_path / "cache")
    pipeline.translate._translator = GlossTranslator(
        provider=FakeProvider(canned=_scripted_chat)
    )
    pipeline.lookup._lookup = WordLookup(manifest_path=_write_word_manifest(tmp_path))

    import logging
    caplog.set_level(logging.WARNING)
    plan = pipeline.run(_VIDEO_ID, use_cache=False)

    assert plan.summary.asl_ratio == 1.0
    assert any("RAI WARNING" in r.message for r in caplog.records)


def test_pipeline_resolves_timing_overlaps(tmp_path, monkeypatch):
    """When chained clips overflow into the next segment, overlap resolution drops the loser."""

    # Two segments back-to-back; clip durations are deliberately long enough
    # to overflow into the next segment.
    raw = [
        {"segment_id": "SEG_001", "start_ms": 0,    "end_ms": 2000, "text": "nice to meet you"},
        {"segment_id": "SEG_002", "start_ms": 2100, "end_ms": 4100, "text": "are you ready"},
    ]
    monkeypatch.setattr(
        "src.pipeline.stages.fetch.fetch_transcript",
        lambda video_id: [dict(s) for s in raw],
    )
    monkeypatch.setattr("src.pipeline.stages.chain.chain_clips", _fake_chain_clips)

    pipeline = Pipeline(cache_root=tmp_path / "cache")
    pipeline.translate._translator = GlossTranslator(
        provider=FakeProvider(canned=_scripted_chat)
    )
    # 1500 ms per word → 3 words = 4500 ms, overflows the 2 s windows
    pipeline.lookup._lookup = WordLookup(
        manifest_path=_write_word_manifest(tmp_path, duration_ms=1500)
    )

    plan = pipeline.run(_VIDEO_ID, use_cache=False)

    assert plan.summary.timing_overlaps >= 1
    assert plan.summary.overlaps_resolved >= 1
    kept_flags = [entry.kept for entry in plan.asl_overlay_track]
    assert kept_flags.count(False) >= 1, "At least one overlay should be dropped"
    assert kept_flags.count(True) >= 1, "At least one overlay should be kept"
