"""FetchStage — pull a YouTube transcript and apply the short-segment filter."""

from __future__ import annotations

import logging

from src.pipeline.models import (
    FetchInput,
    FetchOutput,
    TranscriptSegment,
)
from src.pipeline.stages.base import Stage, stable_hash
from src.transcript_ingestion.fetcher import fetch_transcript

logger = logging.getLogger(__name__)


class FetchStage(Stage[FetchInput, FetchOutput]):
    """Fetch a transcript, normalize, filter short / artefact segments.

    ``fetch_transcript`` already disk-caches the raw transcript at
    ``transcripts/<video_id>.json``; this stage's cache holds the
    post-filter output so changing filter thresholds is one stage's
    worth of invalidation, not a re-download.
    """

    name = "fetch"
    output_model = FetchOutput

    def fingerprint(self, inp: FetchInput) -> str:
        return stable_hash([
            "fetch",
            inp.video_id,
            self.settings.pipeline.min_word_count,
            self.settings.pipeline.min_duration_ms,
        ])

    def process(self, inp: FetchInput) -> FetchOutput:
        raw = fetch_transcript(inp.video_id)
        min_words = self.settings.pipeline.min_word_count
        min_dur = self.settings.pipeline.min_duration_ms

        kept: list[TranscriptSegment] = []
        filtered: list[TranscriptSegment] = []
        for seg in raw:
            word_count = len(seg["text"].split())
            duration = seg["end_ms"] - seg["start_ms"]
            ts = TranscriptSegment(**seg)
            if word_count < min_words or duration < min_dur:
                logger.info(
                    "FILTERED %s — %d words, %d ms: %r",
                    seg["segment_id"], word_count, duration, seg["text"],
                )
                filtered.append(ts)
            else:
                kept.append(ts)

        if filtered:
            logger.info("Filtered %d short/artefact segments", len(filtered))
        logger.info("Fetched %d kept, %d filtered", len(kept), len(filtered))
        return FetchOutput(segments=kept, filtered=filtered)
