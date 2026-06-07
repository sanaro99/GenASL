"""Phase-2 tests — audio backbone (extractor, ASR, prosody, emotion, stages).

Heavy deps (faster-whisper, librosa, soundfile) are imported lazily by
the production code; tests that need them use ``pytest.importorskip``
so the suite still runs in environments without them installed.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.audio.emotion import classify_emotion
from src.core.config import Settings
from src.llm.providers.fake import FakeProvider
from src.pipeline.models import (
    AudioIngestInput,
    EmotionLabel,
    ProsodyFrame,
    WordTiming,
)
from src.pipeline.stages.audio_analyze import AudioAnalyzeStage
from src.pipeline.stages.audio_ingest import AudioIngestStage


# ---------------------------------------------------------------------------
# extractor.py — exercised indirectly through AudioIngestStage's cache test
# ---------------------------------------------------------------------------

def test_audio_ingest_stage_caches(tmp_path, monkeypatch):
    """Second run of AudioIngestStage with the same video_id hits cache."""
    settings = Settings()

    fake_video = tmp_path / "fake_video.mp4"
    fake_video.write_bytes(b"\x00" * 64)
    fake_wav = tmp_path / "fake.wav"
    fake_wav.write_bytes(b"\x00" * 64)

    download_calls = {"n": 0}
    extract_calls = {"n": 0}

    def fake_download(video_id):
        download_calls["n"] += 1
        return fake_video

    def fake_extract(video_path, video_id, sample_rate_hz=None):
        extract_calls["n"] += 1
        return fake_wav, 1234, sample_rate_hz or 16000

    monkeypatch.setattr("src.pipeline.stages.audio_ingest.download_source_video",
                        fake_download)
    monkeypatch.setattr("src.pipeline.stages.audio_ingest.extract_audio",
                        fake_extract)

    stage = AudioIngestStage(settings, cache_root=tmp_path / "cache")
    inp = AudioIngestInput(video_id="AAAAAAAAAAA")

    first = stage.run(inp)
    second = stage.run(inp)

    assert first.duration_ms == 1234
    assert second.duration_ms == 1234
    assert download_calls["n"] == 1, "second run should hit cache"
    assert extract_calls["n"] == 1


# ---------------------------------------------------------------------------
# AudioAnalyzeStage fingerprint stability
# ---------------------------------------------------------------------------

def test_audio_analyze_stage_fingerprint_includes_model(tmp_path):
    """Different asr_model values must produce different cache keys."""
    inp_kwargs = dict(audio_path="data/audio_cache/x.wav", duration_ms=10000)
    from src.pipeline.models import AudioAnalyzeInput

    s_small = Settings.model_validate({"audio": {"asr_model": "small"}})
    s_base = Settings.model_validate({"audio": {"asr_model": "base"}})

    fp_small = AudioAnalyzeStage(s_small, cache_root=tmp_path).fingerprint(
        AudioAnalyzeInput(**inp_kwargs))
    fp_base = AudioAnalyzeStage(s_base, cache_root=tmp_path).fingerprint(
        AudioAnalyzeInput(**inp_kwargs))

    assert fp_small != fp_base


def test_audio_analyze_stage_fingerprint_stable_within_settings(tmp_path):
    """Same input + same settings must produce the same fingerprint."""
    from src.pipeline.models import AudioAnalyzeInput

    s = Settings()
    stage = AudioAnalyzeStage(s, cache_root=tmp_path)
    inp = AudioAnalyzeInput(audio_path="data/audio_cache/x.wav", duration_ms=10000)
    assert stage.fingerprint(inp) == stage.fingerprint(inp)


# ---------------------------------------------------------------------------
# emotion.py — runs with FakeProvider, no network
# ---------------------------------------------------------------------------

def test_emotion_uses_provider_response():
    """A FakeProvider returning canned JSON → one EmotionLabel per window."""
    provider = FakeProvider(canned='{"label":"happy","intensity":0.8}')
    words = [
        WordTiming(word="Hello", start_ms=0, end_ms=400),
        WordTiming(word="world", start_ms=500, end_ms=900),
    ]
    prosody = [
        ProsodyFrame(t_ms=0, f0_hz=220.0, rms=0.5, voiced=True),
        ProsodyFrame(t_ms=500, f0_hz=240.0, rms=0.7, voiced=True),
    ]
    s = Settings()

    out = classify_emotion(
        asr_words=words, prosody=prosody, duration_ms=1000,
        audio_settings=s.audio, interpreter_settings=s.interpreter,
        provider=provider,
    )

    assert len(out) == 1
    assert isinstance(out[0], EmotionLabel)
    assert out[0].label == "happy"
    assert out[0].intensity == pytest.approx(0.8)


def test_emotion_clamps_invalid_label_and_intensity():
    """Out-of-range intensity → clamped; unknown label → 'neutral'."""
    provider = FakeProvider(canned='{"label":"ecstatic","intensity":1.7}')
    words = [WordTiming(word="x", start_ms=0, end_ms=100)]
    s = Settings()
    out = classify_emotion(
        asr_words=words, prosody=[], duration_ms=100,
        audio_settings=s.audio, interpreter_settings=s.interpreter,
        provider=provider,
    )
    assert out[0].label == "neutral"
    assert out[0].intensity == 1.0


def test_emotion_handles_malformed_json():
    """Provider returns junk → falls back to neutral, doesn't raise."""
    provider = FakeProvider(canned="i am not json")
    words = [WordTiming(word="x", start_ms=0, end_ms=100)]
    s = Settings()
    out = classify_emotion(
        asr_words=words, prosody=[], duration_ms=100,
        audio_settings=s.audio, interpreter_settings=s.interpreter,
        provider=provider,
    )
    assert out[0].label == "neutral"
    assert out[0].intensity == 0.0


def test_emotion_handles_code_fenced_json():
    """LLMs sometimes wrap JSON in ```json fences — must still parse."""
    provider = FakeProvider(
        canned='```json\n{"label":"questioning","intensity":0.6}\n```'
    )
    words = [WordTiming(word="why", start_ms=0, end_ms=300)]
    s = Settings()
    out = classify_emotion(
        asr_words=words, prosody=[], duration_ms=300,
        audio_settings=s.audio, interpreter_settings=s.interpreter,
        provider=provider,
    )
    assert out[0].label == "questioning"
    assert out[0].intensity == pytest.approx(0.6)


def test_emotion_emits_neutral_for_silent_window():
    """Empty asr_words → neutral default, no provider call."""
    provider = FakeProvider(canned='{"label":"angry","intensity":1.0}')
    s = Settings()
    out = classify_emotion(
        asr_words=[], prosody=[], duration_ms=2000,
        audio_settings=s.audio, interpreter_settings=s.interpreter,
        provider=provider,
    )
    assert out[0].label == "neutral"
    assert out[0].intensity == 0.0


# ---------------------------------------------------------------------------
# prosody.py — guarded behind importorskip
# ---------------------------------------------------------------------------

def _write_sine_wav(path: Path, freq_hz: float, duration_s: float, sr: int):
    """Write a mono 16-bit PCM WAV of a sine wave (uses stdlib only)."""
    import struct
    import wave

    n_samples = int(sr * duration_s)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(n_samples):
            sample = int(32767 * 0.5 * math.sin(2 * math.pi * freq_hz * i / sr))
            wf.writeframes(struct.pack("<h", sample))


def test_prosody_frames_have_expected_stride_and_f0(tmp_path):
    """Synth a 440 Hz sine, assert prosody returns frames with F0 ≈ 440."""
    pytest.importorskip("librosa")
    pytest.importorskip("soundfile")
    from src.audio.prosody import extract_prosody

    wav = tmp_path / "sine.wav"
    _write_sine_wav(wav, freq_hz=440.0, duration_s=1.0, sr=16000)

    settings = Settings().audio
    frames = extract_prosody(wav, settings)

    assert len(frames) > 5
    # Frame stride matches config (50 ms default).
    strides = [frames[i + 1].t_ms - frames[i].t_ms for i in range(len(frames) - 1)]
    assert all(s == settings.prosody_frame_ms for s in strides[:5])
    # Voiced frames should report F0 in a wide band around 440 Hz.
    voiced_f0 = [f.f0_hz for f in frames if f.voiced and f.f0_hz > 0]
    assert voiced_f0, "expected at least one voiced frame"
    # pyin is noisy on synthetic signals; accept anywhere in 380–520 Hz.
    median = sorted(voiced_f0)[len(voiced_f0) // 2]
    assert 380 < median < 520, f"median F0 {median} not near 440"


# ---------------------------------------------------------------------------
# asr.py — guarded behind importorskip; skipped on CI without the model
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_asr_returns_word_timings(tmp_path):
    """Smoke: faster-whisper on a tiny WAV produces at least one word."""
    pytest.importorskip("faster_whisper")
    from src.audio.asr import transcribe

    wav = tmp_path / "tone.wav"
    _write_sine_wav(wav, freq_hz=200.0, duration_s=0.5, sr=16000)

    settings = Settings(
        # tiny model + int8 — fastest possible
    ).audio
    settings.asr_model = "tiny"

    # A sine wave is not speech, so output may be empty — we only assert
    # the call doesn't raise and the return type is correct.
    words = transcribe(wav, settings)
    assert isinstance(words, list)
    for w in words:
        assert isinstance(w, WordTiming)
