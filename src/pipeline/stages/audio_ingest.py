"""Stage 1 — download source video and extract a mono 16 kHz WAV.

Output is path-relative + duration + sample rate, ready for
:class:`AudioAnalyzeStage`. Phase 2 — see
``docs/plan/phase-2-audio-backbone.md``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.audio.extractor import extract_audio
from src.audio.source_video import download_source_video
from src.core.paths import PROJECT_ROOT
from src.pipeline.models import AudioIngestInput, AudioIngestOutput
from src.pipeline.stages.base import Stage, stable_hash

logger = logging.getLogger(__name__)


class AudioIngestStage(Stage[AudioIngestInput, AudioIngestOutput]):
    name = "audio_ingest"
    output_model = AudioIngestOutput

    def fingerprint(self, inp: AudioIngestInput) -> str:
        return stable_hash([
            "audio_ingest",
            inp.video_id,
            self.settings.audio.sample_rate_hz,
        ])

    def process(self, inp: AudioIngestInput) -> AudioIngestOutput:
        video_path = download_source_video(inp.video_id)
        wav_path, duration_ms, sr = extract_audio(
            video_path,
            inp.video_id,
            sample_rate_hz=self.settings.audio.sample_rate_hz,
        )
        rel = self._relpath(wav_path)
        logger.info("AudioIngestStage produced %s (%d ms)", rel, duration_ms)
        return AudioIngestOutput(
            audio_path=rel,
            duration_ms=duration_ms,
            sample_rate_hz=sr,
        )

    @staticmethod
    def _relpath(p: Path) -> str:
        try:
            return str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(p)
