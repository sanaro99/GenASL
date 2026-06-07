"""Stage 2 — emotion classification over text + prosody summary.

Calls the configured LLM provider (Ollama / Gemini / OpenAI) with one
short prompt per emotion window — avoids shipping a second ~1 GB HF
audio model on CPU. Phase 2 — see ``docs/plan/phase-2-audio-backbone.md``.
"""

from __future__ import annotations

import json
import logging
import re

from src.core.config import AudioSettings, InterpreterSettings, get_settings
from src.llm.providers import LLMProvider, make_provider
from src.pipeline.models import EmotionLabel, ProsodyFrame, WordTiming

logger = logging.getLogger(__name__)


_ALLOWED_LABELS = {
    "neutral", "happy", "sad", "angry",
    "anxious", "questioning", "emphatic",
}

_SYSTEM_PROMPT = (
    "You classify the emotional tone of a short speech window. "
    "Reply with ONE JSON object on a single line: "
    '{"label": "<one of neutral|happy|sad|angry|anxious|questioning|emphatic>", '
    '"intensity": <float 0..1>}. '
    "Do not add commentary, code fences, or extra fields."
)


def _window_indices(
    words: list[WordTiming],
    window_ms: int,
    duration_ms: int,
) -> list[tuple[int, int, list[int]]]:
    """Return [(window_start_ms, window_end_ms, word_indices)] across the audio."""
    if window_ms <= 0:
        return []
    if not words:
        return [(0, duration_ms, [])]
    spans = []
    cursor = 0
    end_bound = max(duration_ms, words[-1].end_ms)
    while cursor < end_bound:
        win_end = min(cursor + window_ms, end_bound)
        idxs = [
            i for i, w in enumerate(words)
            if w.start_ms < win_end and w.end_ms > cursor
        ]
        spans.append((cursor, win_end, idxs))
        cursor = win_end
    return spans


def _prosody_summary(
    prosody: list[ProsodyFrame], start_ms: int, end_ms: int
) -> dict[str, float]:
    in_window = [p for p in prosody if start_ms <= p.t_ms < end_ms]
    if not in_window:
        return {"f0_mean_hz": 0.0, "rms_max": 0.0, "voiced_ratio": 0.0}
    voiced = [p for p in in_window if p.voiced and p.f0_hz > 0]
    f0_mean = sum(p.f0_hz for p in voiced) / len(voiced) if voiced else 0.0
    rms_max = max(p.rms for p in in_window)
    voiced_ratio = len(voiced) / len(in_window)
    return {
        "f0_mean_hz": round(f0_mean, 1),
        "rms_max": round(rms_max, 3),
        "voiced_ratio": round(voiced_ratio, 3),
    }


def _parse_response(text: str) -> tuple[str, float]:
    """Pull a (label, intensity) tuple out of a model response, robustly."""
    if not text:
        return "neutral", 0.0
    # Strip code fences if any.
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(),
                     flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort — find the first {...} block in the string.
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not m:
            return "neutral", 0.0
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return "neutral", 0.0
    label = str(data.get("label", "neutral")).strip().lower()
    if label not in _ALLOWED_LABELS:
        label = "neutral"
    try:
        intensity = float(data.get("intensity", 0.0))
    except (TypeError, ValueError):
        intensity = 0.0
    return label, max(0.0, min(1.0, intensity))


def classify_emotion(
    asr_words: list[WordTiming],
    prosody: list[ProsodyFrame],
    duration_ms: int,
    audio_settings: AudioSettings | None = None,
    interpreter_settings: InterpreterSettings | None = None,
    provider: LLMProvider | None = None,
) -> list[EmotionLabel]:
    """Emit one :class:`EmotionLabel` per ``emotion_window_ms`` slice."""
    s_audio = audio_settings or get_settings().audio
    s_interp = interpreter_settings or get_settings().interpreter
    prov = provider or make_provider()

    out: list[EmotionLabel] = []
    for start_ms, end_ms, word_idxs in _window_indices(
        asr_words, s_audio.emotion_window_ms, duration_ms
    ):
        text = " ".join(asr_words[i].word for i in word_idxs).strip()
        if not text:
            out.append(EmotionLabel(
                start_ms=start_ms, end_ms=end_ms,
                label="neutral", intensity=0.0,
            ))
            continue

        summary = _prosody_summary(prosody, start_ms, end_ms)
        user_prompt = (
            f"Text: {text!r}\n"
            f"Prosody summary: {json.dumps(summary)}\n"
            f"Temperature hint: {s_interp.temperature}"
        )
        try:
            reply = prov.chat(_SYSTEM_PROMPT, user_prompt, max_tokens=60)
        except Exception as exc:  # pragma: no cover — network / quota
            logger.warning("Emotion call failed (%s); defaulting to neutral", exc)
            reply = ""
        label, intensity = _parse_response(reply)
        out.append(EmotionLabel(
            start_ms=start_ms, end_ms=end_ms,
            label=label, intensity=intensity,
        ))

    logger.info("Emotion classifier produced %d windows", len(out))
    return out
