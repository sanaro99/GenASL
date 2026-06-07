"""Stage 3 — split AudioAnalysis into InterpreterChunks (Phase 3).

Thin wrapper around :func:`src.interpreter.chunker.chunk` so the
work stays cacheable on disk. The fingerprint captures the chunker's
tunables (``max_chunk_chars``, ``min_chunk_chars``,
``vad_min_silence_ms``) plus an input shape summary, so re-running
the pipeline on the same audio is a JSON read.
"""

from __future__ import annotations

import logging

from src.interpreter.chunker import chunk as chunk_audio
from src.pipeline.models import SemanticChunkInput, SemanticChunkOutput
from src.pipeline.stages.base import Stage, stable_hash

logger = logging.getLogger(__name__)


class SemanticChunkStage(Stage[SemanticChunkInput, SemanticChunkOutput]):
    name = "semantic_chunk"
    output_model = SemanticChunkOutput

    def fingerprint(self, inp: SemanticChunkInput) -> str:
        s = self.settings
        analysis = inp.analysis
        return stable_hash([
            "semantic_chunk",
            analysis.duration_ms,
            len(analysis.asr_words),
            # Include first/last word to detect content drift cheaply.
            analysis.asr_words[0].word if analysis.asr_words else "",
            analysis.asr_words[-1].word if analysis.asr_words else "",
            s.interpreter.max_chunk_chars,
            s.interpreter.min_chunk_chars,
            s.audio.vad_min_silence_ms,
        ])

    def process(self, inp: SemanticChunkInput) -> SemanticChunkOutput:
        chunks = chunk_audio(
            inp.analysis,
            settings=self.settings.interpreter,
            audio_settings=self.settings.audio,
        )
        logger.info("SemanticChunkStage emitted %d chunks", len(chunks))
        return SemanticChunkOutput(chunks=chunks)
