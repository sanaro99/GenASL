"""Stage 2 — fused ASR + prosody + emotion analysis of the ingest WAV.

Wraps :func:`src.audio.analyzer.analyze`. Cache fingerprint includes all
relevant audio + LLM settings so a change to ``asr_model`` invalidates
just this stage's cache (not the upstream ingest). Phase 2 — see
``docs/plan/phase-2-audio-backbone.md``.
"""

from __future__ import annotations

import logging

from src.audio.analyzer import analyze
from src.core.paths import PROJECT_ROOT
from src.pipeline.models import (
    AudioAnalyzeInput,
    AudioAnalyzeOutput,
)
from src.pipeline.stages.base import Stage, stable_hash

logger = logging.getLogger(__name__)


class AudioAnalyzeStage(Stage[AudioAnalyzeInput, AudioAnalyzeOutput]):
    name = "audio_analyze"
    output_model = AudioAnalyzeOutput

    def fingerprint(self, inp: AudioAnalyzeInput) -> str:
        s = self.settings
        provider_model = getattr(s.llm, s.llm.provider).model
        return stable_hash([
            "audio_analyze",
            inp.audio_path,
            inp.duration_ms,
            s.audio.asr_model,
            s.audio.asr_compute_type,
            s.audio.asr_language,
            s.audio.prosody_frame_ms,
            s.audio.emotion_window_ms,
            s.llm.provider,
            provider_model,
        ])

    def process(self, inp: AudioAnalyzeInput) -> AudioAnalyzeOutput:
        wav_path = PROJECT_ROOT / inp.audio_path
        analysis = analyze(wav_path, inp.duration_ms)
        logger.info(
            "AudioAnalyzeStage: %d words, %d prosody frames, %d emotion windows",
            len(analysis.asr_words), len(analysis.prosody), len(analysis.emotion),
        )
        return AudioAnalyzeOutput(analysis=analysis)
