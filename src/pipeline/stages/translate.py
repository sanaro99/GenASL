"""TranslateStage — LLM English-to-ASL gloss translation per segment."""

from __future__ import annotations

import logging

from src.gloss.prompts import PROMPT_VERSION
from src.gloss.translator import GlossTranslator
from src.pipeline.models import (
    GlossSegment,
    TranslateInput,
    TranslateOutput,
)
from src.pipeline.stages.base import Stage, stable_hash

logger = logging.getLogger(__name__)


class TranslateStage(Stage[TranslateInput, TranslateOutput]):
    """Run each transcript segment through the LLM gloss translator.

    Sequential translation (one LLM call per segment) preserves parity with
    the old ``run_pipeline.run()`` behaviour. The API server's bulk-translate
    path keeps using ``GlossTranslator.translate_batch`` directly.
    """

    name = "translate"
    output_model = TranslateOutput

    def __init__(self, settings, cache_root=None) -> None:
        super().__init__(settings, cache_root)
        self._translator: GlossTranslator | None = None

    def _provider_meta(self) -> tuple[str, str]:
        """Return (provider_name, model) without constructing the translator."""
        name = self.settings.llm.provider
        cfg = getattr(self.settings.llm, name)
        return name, cfg.model

    def _get_translator(self) -> GlossTranslator:
        if self._translator is None:
            self._translator = GlossTranslator()
        return self._translator

    def fingerprint(self, inp: TranslateInput) -> str:
        provider, model = self._provider_meta()
        texts_joined = "|".join(s.text for s in inp.segments)
        return stable_hash([
            "translate",
            provider, model, PROMPT_VERSION,
            self.settings.pipeline.batch_chunk_size,
            texts_joined,
        ])

    def process(self, inp: TranslateInput) -> TranslateOutput:
        translator = self._get_translator()
        out: list[GlossSegment] = []
        for seg in inp.segments:
            try:
                glosses = translator.translate(seg.text)
            except Exception as exc:
                logger.error("Gloss translation failed for %r: %s", seg.text[:60], exc)
                glosses = []
            out.append(GlossSegment(
                segment_id=seg.segment_id,
                start_ms=seg.start_ms,
                end_ms=seg.end_ms,
                text=seg.text,
                gloss_sequence=glosses,
                gloss_text=" ".join(glosses),
            ))
        translated = sum(1 for s in out if s.gloss_sequence)
        logger.info(
            "Gloss translation complete: %d/%d segments translated",
            translated, len(out),
        )
        provider, model = self._provider_meta()
        return TranslateOutput(segments=out, provider=provider, model=model)
