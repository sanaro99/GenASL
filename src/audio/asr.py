"""Stage 2 — faster-whisper ASR wrapper producing word-level timings.

faster-whisper is imported lazily so that this module is free to import
in tests that don't actually run ASR. Phase 2 — see
``docs/plan/phase-2-audio-backbone.md``.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from src.core.config import AudioSettings, get_settings
from src.pipeline.models import WordTiming

logger = logging.getLogger(__name__)


# Lazily-built singleton — Whisper model load is ~1–3 s on CPU and the
# model object is thread-safe for read-only use.
_model_lock = threading.Lock()
_model_cache: dict[tuple[str, str], object] = {}


def _get_model(model_size: str, compute_type: str):
    """Return the cached ``WhisperModel`` for ``(size, compute_type)``."""
    key = (model_size, compute_type)
    with _model_lock:
        if key not in _model_cache:
            from faster_whisper import WhisperModel  # heavy import

            logger.info("Loading faster-whisper model=%s compute=%s",
                        model_size, compute_type)
            _model_cache[key] = WhisperModel(
                model_size, device="cpu", compute_type=compute_type
            )
        return _model_cache[key]


def transcribe(
    wav_path: Path,
    settings: AudioSettings | None = None,
) -> list[WordTiming]:
    """Transcribe ``wav_path`` with word-level timestamps.

    Returns an empty list rather than raising when the audio is silent
    so downstream stages can handle the no-speech case gracefully.
    """
    s = settings or get_settings().audio
    model = _get_model(s.asr_model, s.asr_compute_type)

    segments, _info = model.transcribe(
        str(wav_path),
        language=s.asr_language,
        word_timestamps=True,
        vad_filter=True,
    )

    words: list[WordTiming] = []
    for seg in segments:
        seg_words = getattr(seg, "words", None) or []
        for w in seg_words:
            if w.word is None:
                continue
            words.append(
                WordTiming(
                    word=w.word.strip(),
                    start_ms=int(w.start * 1000),
                    end_ms=int(w.end * 1000),
                )
            )

    logger.info("ASR produced %d words for %s", len(words), wav_path.name)
    return words
