"""Stage 3 — split AudioAnalysis into InterpreterChunks for the brain (Phase 3).

Walks ``analysis.asr_words`` in order, emitting a chunk on the nearest
soft boundary (sentence punctuation) once a hard boundary (VAD silence)
is crossed or the running text grows past ``max_chunk_chars``. Each
emitted chunk is annotated with the dominant emotion, prosody summary,
speaking rate, and an end-of-chunk pause flag.
"""

from __future__ import annotations

import logging
from typing import Sequence

from src.core.config import AudioSettings, InterpreterSettings, get_settings
from src.pipeline.models import (
    AudioAnalysis,
    EmotionLabel,
    InterpreterChunk,
    ProsodyFrame,
    WordTiming,
)

logger = logging.getLogger(__name__)


_SOFT_BOUNDARY_CHARS = (".", "?", "!", ";")


def _ends_with_soft_boundary(word: str) -> bool:
    stripped = word.rstrip(" \"'”’)")
    return bool(stripped) and stripped[-1] in _SOFT_BOUNDARY_CHARS


def _gap_to_next_ms(words: Sequence[WordTiming], idx: int) -> int:
    """ms of silence between word ``idx`` and word ``idx+1`` (0 if last)."""
    if idx + 1 >= len(words):
        return 0
    return max(0, words[idx + 1].start_ms - words[idx].end_ms)


def _dominant_emotion(
    emotions: Sequence[EmotionLabel], centroid_ms: int
) -> tuple[str, float]:
    for em in emotions:
        if em.start_ms <= centroid_ms < em.end_ms:
            return em.label, em.intensity
    # Fall back to whichever window is closest if none strictly contain
    # the centroid (e.g. centroid lands exactly on the last boundary).
    if not emotions:
        return "neutral", 0.0
    nearest = min(
        emotions,
        key=lambda e: min(abs(e.start_ms - centroid_ms), abs(e.end_ms - centroid_ms)),
    )
    return nearest.label, nearest.intensity


def _prosody_span(
    prosody: Sequence[ProsodyFrame], start_ms: int, end_ms: int
) -> tuple[tuple[float, float], float]:
    in_span = [p for p in prosody if start_ms <= p.t_ms < end_ms]
    if not in_span:
        return (0.0, 0.0), 0.0
    voiced = [p.f0_hz for p in in_span if p.voiced and p.f0_hz > 0]
    f0_range = (min(voiced), max(voiced)) if voiced else (0.0, 0.0)
    rms_mean = sum(p.rms for p in in_span) / len(in_span)
    return f0_range, rms_mean


def _emit_chunk(
    *,
    chunk_index: int,
    words: Sequence[WordTiming],
    word_indices: list[int],
    analysis: AudioAnalysis,
    ended_with_pause: bool,
) -> InterpreterChunk | None:
    if not word_indices:
        return None
    span_words = [words[i] for i in word_indices]
    text = " ".join(w.word for w in span_words).strip()
    if not text:
        return None
    start_ms = span_words[0].start_ms
    end_ms = span_words[-1].end_ms
    centroid_ms = (start_ms + end_ms) // 2
    label, intensity = _dominant_emotion(analysis.emotion, centroid_ms)
    f0_range, rms_mean = _prosody_span(analysis.prosody, start_ms, end_ms)
    span_s = max((end_ms - start_ms) / 1000.0, 1e-6)
    wps = len(span_words) / span_s
    return InterpreterChunk(
        chunk_id=f"c{chunk_index}",
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        dominant_emotion=label,
        emotion_intensity=round(intensity, 3),
        f0_range_hz=(round(f0_range[0], 1), round(f0_range[1], 1)),
        rms_mean=round(rms_mean, 4),
        speaking_rate_wps=round(wps, 3),
        ended_with_pause=ended_with_pause,
    )


def chunk(
    analysis: AudioAnalysis,
    settings: InterpreterSettings | None = None,
    audio_settings: AudioSettings | None = None,
) -> list[InterpreterChunk]:
    """Split ``analysis`` into a list of :class:`InterpreterChunk`.

    Boundaries:
      * Hard — silence ≥ ``audio.vad_min_silence_ms`` after the current word.
      * Soft — sentence punctuation (.?!;) anywhere in the current word.

    A chunk is emitted whenever we cross a hard boundary, OR when the
    running text exceeds ``max_chunk_chars`` and we have just passed a
    soft boundary. Chunks shorter than ``min_chunk_chars`` are dropped.
    """
    s_interp = settings or get_settings().interpreter
    s_audio = audio_settings or get_settings().audio
    words = analysis.asr_words
    if not words:
        return []

    chunks: list[InterpreterChunk] = []
    pending: list[int] = []
    pending_chars = 0
    next_id = 0

    for i, word in enumerate(words):
        pending.append(i)
        pending_chars += len(word.word) + 1  # +1 for the joining space

        gap_ms = _gap_to_next_ms(words, i)
        is_last = i == len(words) - 1
        hard = is_last or gap_ms >= s_audio.vad_min_silence_ms
        soft = _ends_with_soft_boundary(word.word)
        over_cap = pending_chars >= s_interp.max_chunk_chars

        should_emit = hard or (over_cap and soft)
        if not should_emit:
            continue

        ended_with_pause = hard and not is_last
        emitted = _emit_chunk(
            chunk_index=next_id,
            words=words,
            word_indices=pending,
            analysis=analysis,
            ended_with_pause=ended_with_pause,
        )
        if emitted is not None and len(emitted.text) >= s_interp.min_chunk_chars:
            chunks.append(emitted)
            next_id += 1
        else:
            logger.debug(
                "Dropping chunk (len=%d < min %d)",
                len(emitted.text) if emitted else 0,
                s_interp.min_chunk_chars,
            )
        pending = []
        pending_chars = 0

    # Flush any trailing words that never crossed a boundary above.
    if pending:
        emitted = _emit_chunk(
            chunk_index=next_id,
            words=words,
            word_indices=pending,
            analysis=analysis,
            ended_with_pause=False,
        )
        if emitted is not None and len(emitted.text) >= s_interp.min_chunk_chars:
            chunks.append(emitted)

    logger.info("Chunker produced %d interpreter chunks", len(chunks))
    return chunks
