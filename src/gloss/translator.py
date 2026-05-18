"""LLM-based English-to-ASL gloss translator.

Translates English sentences into ASL gloss sequences using a chat LLM.
The actual API call is delegated to a :class:`GlossProvider` implementation
(see :mod:`src.gloss.providers`) so the translator stays provider-agnostic.

Usage (standalone test)::

    python -m src.gloss.translator "Where is the library?"
"""

from __future__ import annotations

import json
import logging
import re
import sys

from src.core.config import get_settings
from src.core.paths import WORD_MANIFEST
from src.gloss.prompts import (
    SYSTEM_PROMPT_COMPACT,
    SYSTEM_PROMPT_FULL,
    build_batch_user,
)
from src.gloss.providers import GlossProvider, make_provider

logger = logging.getLogger(__name__)


def _load_available_glosses() -> list[str]:
    """Return non-placeholder glosses from the word manifest, sorted and uniqued."""
    if not WORD_MANIFEST.is_file():
        logger.warning(
            "Word manifest not found — LLM will not be constrained to available glosses"
        )
        return []
    with open(WORD_MANIFEST, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    glosses: set[str] = set()
    for word in data.get("words", []):
        if word.get("source") != "placeholder":
            glosses.add(word["gloss"].upper())
    return sorted(glosses)


def _sanitize(words: list[str]) -> list[str]:
    cleaned = [re.sub(r"[^A-Z0-9\-]", "", w.strip().upper()) for w in words]
    return [w for w in cleaned if w]


def _parse_numbered(raw: str, n: int) -> dict[int, list[str]]:
    """Parse ``N. WORD1 WORD2`` lines into ``{0-based-idx: [words]}``."""
    parsed: dict[int, list[str]] = {}
    for line in raw.split("\n"):
        m = re.match(r"^(\d+)\.\s*(.+)$", line.strip())
        if not m:
            continue
        idx = int(m.group(1)) - 1
        if 0 <= idx < n:
            parsed[idx] = _sanitize(m.group(2).split())
    return parsed


class GlossTranslator:
    """Translate English sentences to ASL gloss sequences using an LLM provider."""

    def __init__(self, provider: GlossProvider | None = None) -> None:
        settings = get_settings()
        self._provider = provider or make_provider(settings)
        self._batch_chunk_size = settings.pipeline.batch_chunk_size

        # Compact prompt for local models (saves ~4000 prompt tokens per call);
        # full prompt — including the available-gloss list — for cloud providers.
        if self._provider.name == "ollama":
            self._system_prompt = SYSTEM_PROMPT_COMPACT
        else:
            available = _load_available_glosses()
            gloss_str = (
                ", ".join(available)
                if available
                else "(full WLASL vocabulary — no constraint)"
            )
            self._system_prompt = SYSTEM_PROMPT_FULL.format(available_glosses=gloss_str)

        logger.info(
            "GlossTranslator initialised: provider=%s  model=%s  prompt_mode=%s",
            self._provider.name,
            self._provider.model,
            "compact" if self._provider.name == "ollama" else "full",
        )

    # --- Public API ---------------------------------------------------

    def translate(self, english_text: str) -> list[str]:
        """Translate a single English sentence into an ordered ASL gloss list."""
        raw = self._provider.chat(self._system_prompt, english_text.strip())
        glosses = _sanitize(raw.split())
        logger.info("Translated: %r -> %s", english_text[:80], " ".join(glosses))
        return glosses

    def translate_batch(self, texts: list[str]) -> list[list[str]]:
        """Translate many sentences via chunked LLM calls.

        Each chunk holds at most :attr:`Settings.pipeline.batch_chunk_size`
        sentences and is sent as a numbered list. The chunk falls back to
        per-sentence calls if numbered parsing recovers fewer than 70% of lines.
        """
        if not texts:
            return []
        if len(texts) <= 2:
            return [self.translate(t) for t in texts]

        results: list[list[str]] = [[] for _ in texts]
        for start in range(0, len(texts), self._batch_chunk_size):
            chunk = texts[start : start + self._batch_chunk_size]
            chunk_results = self._translate_chunk(chunk)
            for i, glosses in enumerate(chunk_results):
                results[start + i] = glosses
        return results

    def translate_segments(self, segments: list[dict]) -> list[dict]:
        """Add ``gloss_sequence`` / ``gloss_text`` fields to each segment dict."""
        out: list[dict] = []
        for seg in segments:
            enriched = dict(seg)
            try:
                glosses = self.translate(seg["text"])
                enriched["gloss_sequence"] = glosses
                enriched["gloss_text"] = " ".join(glosses)
            except Exception as exc:
                logger.error(
                    "Gloss translation failed for %r: %s", seg["text"][:60], exc
                )
                enriched["gloss_sequence"] = []
                enriched["gloss_text"] = ""
            out.append(enriched)
        translated = sum(1 for r in out if r["gloss_sequence"])
        logger.info(
            "Gloss translation complete: %d/%d segments translated",
            translated,
            len(out),
        )
        return out

    # --- Internals ----------------------------------------------------

    def _translate_chunk(self, texts: list[str]) -> list[list[str]]:
        user_content = build_batch_user(texts)
        try:
            raw = self._provider.chat(
                self._system_prompt,
                user_content,
                max_tokens=max(200, len(texts) * 40),
            )
            logger.info("Batch chunk translated %d lines", len(texts))
            parsed = _parse_numbered(raw, len(texts))
            if len(parsed) >= len(texts) * 0.7:
                logger.info("Batch parse: %d/%d lines parsed", len(parsed), len(texts))
                return [parsed.get(i, []) for i in range(len(texts))]
            logger.warning(
                "Batch parse insufficient (%d/%d) — falling back to sequential",
                len(parsed),
                len(texts),
            )
        except Exception as exc:
            logger.warning(
                "Batch translation failed — falling back to sequential: %s", exc
            )
        return [self.translate(t) for t in texts]


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print('Usage: python -m src.gloss.translator "English sentence here"')
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    translator = GlossTranslator()
    glosses = translator.translate(text)
    print(f"Input:  {text}")
    print(f"Gloss:  {' '.join(glosses)}")
