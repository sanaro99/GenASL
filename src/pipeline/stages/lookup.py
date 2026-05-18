"""LookupStage — resolve each gloss in each segment to a WLASL clip."""

from __future__ import annotations

import logging

from src.core.paths import WORD_MANIFEST
from src.gloss.word_lookup import WordLookup
from src.pipeline.models import (
    LookedUpSegment,
    LookupInput,
    LookupOutput,
    WordClip,
)
from src.pipeline.stages.base import Stage, stable_hash

logger = logging.getLogger(__name__)


class LookupStage(Stage[LookupInput, LookupOutput]):
    """For each segment, resolve every gloss word to its clip metadata."""

    name = "lookup"
    output_model = LookupOutput

    def __init__(self, settings, cache_root=None) -> None:
        super().__init__(settings, cache_root)
        self._lookup: WordLookup | None = None

    def _get_lookup(self) -> WordLookup:
        if self._lookup is None:
            self._lookup = WordLookup()
        return self._lookup

    def _manifest_version(self) -> str:
        """Stable identifier for the current word manifest (used in the cache key)."""
        if WORD_MANIFEST.is_file():
            return str(WORD_MANIFEST.stat().st_mtime_ns)
        return "missing"

    def fingerprint(self, inp: LookupInput) -> str:
        glosses_joined = "|".join("/".join(s.gloss_sequence) for s in inp.segments)
        return stable_hash([
            "lookup",
            self._manifest_version(),
            glosses_joined,
        ])

    def process(self, inp: LookupInput) -> LookupOutput:
        lookup = self._get_lookup()
        out: list[LookedUpSegment] = []
        for seg in inp.segments:
            if seg.gloss_sequence:
                entries = lookup.lookup_sequence(seg.gloss_sequence)
                word_clips = [WordClip(**e) for e in entries]
            else:
                word_clips = []
            out.append(LookedUpSegment(
                **seg.model_dump(),
                word_clips=word_clips,
            ))
        return LookupOutput(segments=out)
