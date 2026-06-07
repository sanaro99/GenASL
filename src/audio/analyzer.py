"""Stage 2 fusion — run ASR, prosody, and emotion in parallel.

ASR is CPU-heavy, prosody is light, emotion is network-bound — they
overlap well in a small thread pool. Phase 2 — see
``docs/plan/phase-2-audio-backbone.md``.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.audio.asr import transcribe
from src.audio.emotion import classify_emotion
from src.audio.prosody import extract_prosody
from src.core.config import get_settings
from src.llm.providers import LLMProvider
from src.pipeline.models import AudioAnalysis

logger = logging.getLogger(__name__)


def analyze(
    wav_path: Path,
    duration_ms: int,
    provider: LLMProvider | None = None,
) -> AudioAnalysis:
    """Run ASR + prosody + emotion in three threads, fuse into AudioAnalysis."""
    settings = get_settings()

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_asr = pool.submit(transcribe, wav_path, settings.audio)
        f_prosody = pool.submit(extract_prosody, wav_path, settings.audio)
        asr_words = f_asr.result()
        prosody = f_prosody.result()

        # Emotion needs ASR + prosody results — submit after they finish.
        emotion = classify_emotion(
            asr_words=asr_words,
            prosody=prosody,
            duration_ms=duration_ms,
            audio_settings=settings.audio,
            interpreter_settings=settings.interpreter,
            provider=provider,
        )

    logger.info(
        "Audio analysis: %d words, %d prosody frames, %d emotion windows",
        len(asr_words), len(prosody), len(emotion),
    )
    return AudioAnalysis(
        duration_ms=duration_ms,
        asr_words=asr_words,
        prosody=prosody,
        emotion=emotion,
    )
