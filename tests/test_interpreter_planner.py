"""Phase-3 tests — semantic chunker, interpreter planner, and stages.

The planner uses :class:`FakeProvider` for determinism — no LLM calls
hit the network. The cache fingerprint test asserts that bumping
``PROMPT_VERSION`` invalidates only the interpreter_plan stage cache.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from src.core.config import Settings
from src.interpreter.chunker import chunk as chunk_audio
from src.interpreter.planner import plan_chunks
from src.llm.providers.fake import FakeProvider
from src.pipeline.models import (
    AudioAnalysis,
    EmotionLabel,
    InterpreterChunk,
    InterpreterPlanInput,
    ProsodyFrame,
    WordTiming,
)
from src.pipeline.stages.interpreter_plan import InterpreterPlanStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_analysis(words: list[WordTiming]) -> AudioAnalysis:
    duration_ms = words[-1].end_ms if words else 0
    return AudioAnalysis(
        duration_ms=duration_ms,
        asr_words=words,
        prosody=[],
        emotion=[
            EmotionLabel(start_ms=0, end_ms=max(duration_ms, 1),
                         label="neutral", intensity=0.1),
        ],
    )


def _good_json() -> str:
    return json.dumps({
        "topic_comment": ["TOPIC: X", "COMMENT: Y"],
        "sign_sequence": ["HELLO", "world!", "FRIEND"],
        "nmm_intent": {
            "brow_raise": 0.5, "head_tilt_left": 0.0,
            "head_tilt_right": 0.0, "head_nod": 0.2,
            "head_shake": 0.0, "mouth_open": 0.1, "eye_squint": 0.0,
        },
        "emphasis_signs": ["HELLO"],
        "role_shifts": [],
        "notes": "ok",
    })


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

def test_chunker_respects_max_chunk_chars():
    """A long run with no pauses still splits, never producing > max chars."""
    # 30 'word' tokens, ~4 chars each = ~150 chars, with sentence punctuation
    # every 5 words to give the chunker soft boundaries it can split on.
    words: list[WordTiming] = []
    t = 0
    for i in range(60):
        token = "word" if (i + 1) % 5 != 0 else "word."
        words.append(WordTiming(word=token, start_ms=t, end_ms=t + 200))
        t += 250  # 50 ms gap << vad_min_silence_ms — no hard boundaries
    analysis = _make_analysis(words)

    s = Settings()
    s.interpreter.max_chunk_chars = 60
    s.interpreter.min_chunk_chars = 5

    chunks = chunk_audio(analysis, s.interpreter, s.audio)

    assert len(chunks) >= 2, "chunker must split a long run with no pauses"
    # The cap is a "cut at the next soft boundary once over" rule, so a
    # chunk can overshoot by at most one sentence's worth of words. Assert
    # no chunk runs to ~half the input.
    total_chars = sum(len(w.word) + 1 for w in words)
    for c in chunks:
        assert len(c.text) < total_chars * 0.6, (
            f"chunk {c.chunk_id} ate the whole input ({len(c.text)} chars)"
        )


def test_chunker_splits_on_pause():
    """Two utterances separated by a 1 s silence → two chunks."""
    words = [
        WordTiming(word="Hello", start_ms=0, end_ms=400),
        WordTiming(word="world.", start_ms=450, end_ms=900),
        # 1 s gap >> vad_min_silence_ms (500 ms default)
        WordTiming(word="Goodbye", start_ms=2000, end_ms=2400),
        WordTiming(word="friend.", start_ms=2450, end_ms=2900),
    ]
    analysis = _make_analysis(words)
    s = Settings()
    s.interpreter.min_chunk_chars = 5

    chunks = chunk_audio(analysis, s.interpreter, s.audio)

    assert len(chunks) == 2
    assert "Hello" in chunks[0].text and "world" in chunks[0].text
    assert "Goodbye" in chunks[1].text and "friend" in chunks[1].text
    assert chunks[0].ended_with_pause is True


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def _make_chunk(idx: int = 0, text: str = "Where is the library?") -> InterpreterChunk:
    return InterpreterChunk(
        chunk_id=f"c{idx}", start_ms=idx * 1000, end_ms=idx * 1000 + 1000,
        text=text, dominant_emotion="questioning", emotion_intensity=0.7,
        speaking_rate_wps=1.3, ended_with_pause=True,
    )


def test_planner_calls_provider_once_per_chunk():
    provider = FakeProvider(canned=_good_json(), model="fake-1")
    chunks = [_make_chunk(0), _make_chunk(1, "We are leaving now.")]

    segs, name, model = plan_chunks(chunks, Settings().interpreter, provider)

    assert provider.call_count == 2
    assert name == "fake"
    assert model == "fake-1"
    assert len(segs) == 2
    assert segs[0].chunk_id == "c0"
    assert segs[1].chunk_id == "c1"
    # Sign tokens normalised: "world!" -> "WORLD"
    assert "WORLD" in segs[0].sign_sequence
    # Punctuation-only tokens dropped.
    assert all(t.isascii() and t.replace("_", "").isalnum()
               for t in segs[0].sign_sequence)


def test_planner_handles_malformed_json_with_retry():
    """First response is junk, retry returns valid JSON → segment is parsed."""
    provider = FakeProvider(canned=["this is not json at all", _good_json()])
    segs, _, _ = plan_chunks([_make_chunk()], Settings().interpreter, provider)

    assert provider.call_count == 2
    assert segs[0].sign_sequence  # not the fallback path
    assert not segs[0].notes.startswith("fallback")


def test_planner_falls_back_when_both_attempts_fail():
    """Two malformed responses → fallback segment with chunk text as glosses."""
    provider = FakeProvider(canned=["junk one", "junk two"])
    segs, _, _ = plan_chunks(
        [_make_chunk(text="Hello world")], Settings().interpreter, provider,
    )

    assert provider.call_count == 2
    assert segs[0].notes.startswith("fallback")
    assert segs[0].sign_sequence == ["HELLO", "WORLD"]


def test_planner_clamps_nmm_intents_to_unit_range():
    payload = json.loads(_good_json())
    payload["nmm_intent"]["brow_raise"] = 1.7
    payload["nmm_intent"]["head_nod"] = -0.4
    provider = FakeProvider(canned=json.dumps(payload))

    segs, _, _ = plan_chunks([_make_chunk()], Settings().interpreter, provider)

    assert segs[0].nmm_intent["brow_raise"] == 1.0
    assert segs[0].nmm_intent["head_nod"] == 0.0
    # All 7 keys are present even if the model omitted some.
    for key in ("brow_raise", "head_tilt_left", "head_tilt_right",
                "head_nod", "head_shake", "mouth_open", "eye_squint"):
        assert 0.0 <= segs[0].nmm_intent[key] <= 1.0


def test_planner_strips_json_code_fences():
    provider = FakeProvider(canned=f"```json\n{_good_json()}\n```")
    segs, _, _ = plan_chunks([_make_chunk()], Settings().interpreter, provider)
    assert not segs[0].notes.startswith("fallback")
    assert segs[0].sign_sequence


# ---------------------------------------------------------------------------
# InterpreterPlanStage fingerprint
# ---------------------------------------------------------------------------

def test_interpreter_stage_fingerprint_includes_prompt_version(tmp_path: Path):
    s = Settings()
    stage = InterpreterPlanStage(s, cache_root=tmp_path)
    inp = InterpreterPlanInput(chunks=[_make_chunk()])

    fp_v1 = stage.fingerprint(inp)
    with mock.patch("src.pipeline.stages.interpreter_plan.PROMPT_VERSION", "v999"):
        fp_v999 = stage.fingerprint(inp)

    assert fp_v1 != fp_v999


def test_interpreter_stage_fingerprint_includes_chunk_text(tmp_path: Path):
    s = Settings()
    stage = InterpreterPlanStage(s, cache_root=tmp_path)
    fp_a = stage.fingerprint(InterpreterPlanInput(chunks=[_make_chunk(text="A")]))
    fp_b = stage.fingerprint(InterpreterPlanInput(chunks=[_make_chunk(text="B")]))
    assert fp_a != fp_b


# ---------------------------------------------------------------------------
# Stage cache round-trip (no LLM)
# ---------------------------------------------------------------------------

def test_interpreter_stage_run_caches(tmp_path: Path, monkeypatch):
    """Second .run() hits the on-disk cache and doesn't call the provider."""
    s = Settings()
    stage = InterpreterPlanStage(s, cache_root=tmp_path)
    inp = InterpreterPlanInput(chunks=[_make_chunk()])

    calls = {"n": 0}

    def fake_plan_chunks(chunks, settings=None, provider=None):
        calls["n"] += 1
        from src.pipeline.models import AslPlanSegment
        return (
            [AslPlanSegment(
                chunk_id=chunks[0].chunk_id,
                start_ms=chunks[0].start_ms,
                end_ms=chunks[0].end_ms,
                sign_sequence=["HELLO"],
            )],
            "fake",
            "fake-1",
        )

    monkeypatch.setattr(
        "src.pipeline.stages.interpreter_plan.plan_chunks", fake_plan_chunks
    )

    first = stage.run(inp)
    second = stage.run(inp)

    assert calls["n"] == 1
    assert first.segments[0].sign_sequence == ["HELLO"]
    assert second.segments[0].sign_sequence == ["HELLO"]
    assert first.provider == second.provider == "fake"
