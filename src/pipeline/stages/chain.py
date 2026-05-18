"""ChainStage — FFmpeg-concatenate the per-gloss word clips per segment."""

from __future__ import annotations

import logging
from pathlib import Path

from src.gloss.chainer import chain_clips
from src.pipeline.models import (
    ChainedClip,
    ChainedSegment,
    ChainInput,
    ChainOutput,
)
from src.pipeline.stages.base import Stage, stable_hash

logger = logging.getLogger(__name__)


class ChainStage(Stage[ChainInput, ChainOutput]):
    """Concatenate the found word clips for each segment into one MP4.

    The chained MP4 itself lands at ``assets/chained/<segment_id>.mp4`` — that
    output directory has its own filesystem cache layer used by the API
    server for clip serving. This stage's disk cache is the JSON record of
    what was produced.
    """

    name = "chain"
    output_model = ChainOutput

    def fingerprint(self, inp: ChainInput) -> str:
        parts: list = ["chain"]
        for seg in inp.segments:
            parts.append(seg.segment_id)
            for wc in seg.word_clips:
                if wc.found and wc.abs_path:
                    try:
                        mtime = Path(wc.abs_path).stat().st_mtime_ns
                    except OSError:
                        mtime = 0
                    parts.append(f"{wc.gloss}:{mtime}")
                else:
                    parts.append(f"{wc.gloss}:missing")
        return stable_hash(parts)

    def process(self, inp: ChainInput) -> ChainOutput:
        out: list[ChainedSegment] = []
        for seg in inp.segments:
            wc_dicts = [w.model_dump() for w in seg.word_clips]
            chained_clip: ChainedClip | None = None
            if any(wc.get("found") for wc in wc_dicts):
                result = chain_clips(wc_dicts, seg.segment_id)
                if result is not None:
                    chained_clip = ChainedClip(**result)
            out.append(ChainedSegment(
                **seg.model_dump(),
                chained_clip=chained_clip,
            ))
        chained_count = sum(1 for s in out if s.chained_clip)
        logger.info(
            "Chained %d/%d segments",
            chained_count, len(out),
        )
        return ChainOutput(segments=out)
