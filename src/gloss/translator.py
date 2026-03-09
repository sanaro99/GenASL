"""LLM-based English-to-ASL gloss translator.

Translates English sentences into ASL gloss sequences using a chat LLM.
Supports three providers (configured in ``config.yaml`` under ``llm``):

* **ollama** — local, free, no API key (default)
* **gemini** — Google free-tier, needs ``GEMINI_API_KEY`` env var
* **openai** — needs ``OPENAI_API_KEY`` env var

All three use OpenAI-compatible chat endpoints via the ``openai`` package.

Usage (standalone test)::

    python -m src.gloss.translator "Where is the library?"
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_config() -> dict:
    cfg_path = _PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_available_glosses() -> list[str]:
    """Load the list of available gloss words from the word manifest."""
    manifest_path = _PROJECT_ROOT / "assets" / "word_manifest.json"
    if not manifest_path.is_file():
        logger.warning("Word manifest not found — LLM will not be constrained to available glosses")
        return []
    with open(manifest_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    glosses = []
    for word in data.get("words", []):
        if word.get("source") != "placeholder":
            glosses.append(word["gloss"].upper())
    return sorted(set(glosses))


_SYSTEM_PROMPT_FULL = """\
You are an expert ASL (American Sign Language) linguist. Your task is to \
translate English sentences into ASL gloss sequences.

ASL GRAMMAR RULES:
- ASL uses topic-comment structure (topic first, then comment)
- Omit articles (a, an, the), copulas (is, are, am, was, were), and prepositions when possible
- Use time indicators at the beginning (YESTERDAY, TOMORROW, NOW, etc.)
- Questions: put the question word (WHO, WHAT, WHERE, WHEN, WHY, HOW) at the END
- Negation: put NOT after the verb
- Adjectives come AFTER the noun
- Use single uppercase words separated by spaces
- Each word should be a single sign — avoid multi-word glosses

AVAILABLE SIGNS:
{available_glosses}

IMPORTANT:
- Prefer words from the AVAILABLE SIGNS list above
- If a concept has no exact match, use the closest available sign or break it into simpler signs
- Output ONLY the gloss sequence as uppercase words separated by spaces
- Do NOT include punctuation, explanations, or commentary
- Output one line per input sentence

Examples:
English: "Where is the library?"
ASL Gloss: LIBRARY WHERE

English: "I want to go to the store tomorrow."
ASL Gloss: TOMORROW STORE GO WANT

English: "She is very happy today."
ASL Gloss: TODAY HAPPY
"""

# Compact prompt (no glosses list) — ~200 tokens instead of ~4200.
# Avoids massive KV-cache fill on each new conversation with local LLMs.
_SYSTEM_PROMPT_COMPACT = """\
You are an ASL gloss translator. Convert English to ASL gloss notation.

Rules: topic-comment order, drop articles/copulas/prepositions, time words first, \
question words last, NOT after verb, adjectives after noun.

Output ONLY uppercase words separated by spaces. No punctuation or commentary.

Examples:
"Where is the library?" → LIBRARY WHERE
"I want to go to the store tomorrow." → TOMORROW STORE GO WANT
"She is very happy today." → TODAY HAPPY
"""


# ---------------------------------------------------------------------------
# Provider resolution
# ---------------------------------------------------------------------------

_PROVIDER_DEFAULTS = {
    "ollama": {
        "model": "llama3.2",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",  # Ollama ignores the key but the client requires one
        "env_key": None,
    },
    "gemini": {
        "model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": None,
        "env_key": "GEMINI_API_KEY",
    },
    "openai": {
        "model": "gpt-4o-mini",
        "base_url": None,  # default OpenAI endpoint
        "api_key": None,
        "env_key": "OPENAI_API_KEY",
    },
}


def _resolve_provider(cfg: dict) -> tuple[str, str, str | None, str]:
    """Return (provider, model, base_url, api_key) from config + env."""
    llm_cfg = cfg.get("llm", {})
    provider = llm_cfg.get("provider", "ollama").lower()

    if provider not in _PROVIDER_DEFAULTS:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            f"Supported: {', '.join(_PROVIDER_DEFAULTS)}"
        )

    defaults = _PROVIDER_DEFAULTS[provider]
    provider_cfg = llm_cfg.get(provider, {})

    model = provider_cfg.get("model", defaults["model"])
    base_url = provider_cfg.get("base_url", defaults["base_url"])

    # API key: config value > env var > hardcoded default
    api_key = provider_cfg.get("api_key") or ""
    if not api_key and defaults["env_key"]:
        api_key = os.environ.get(defaults["env_key"], "")
    if not api_key:
        api_key = defaults.get("api_key") or ""

    if not api_key and provider != "ollama":
        env_name = defaults["env_key"]
        raise ValueError(
            f"API key required for provider '{provider}'. "
            f"Set the {env_name} environment variable."
        )

    # Ollama always needs a dummy key for the openai client
    if provider == "ollama" and not api_key:
        api_key = "ollama"

    return provider, model, base_url, api_key


class GlossTranslator:
    """Translates English sentences to ASL gloss sequences using an LLM."""

    def __init__(self, api_key: str | None = None) -> None:
        cfg = _load_config()
        provider, model, base_url, resolved_key = _resolve_provider(cfg)

        self._provider = provider
        self._model = model
        self._api_key = api_key or resolved_key

        # Gemma models served via the Gemini API don't support the
        # "system" role (developer instructions).  We fold the system
        # prompt into the first user message instead.
        self._system_as_user = model.startswith("gemma")

        # Use compact prompt for local models (saves ~4000 tokens of prompt
        # processing on every call), full prompt for cloud providers.
        if provider == "ollama":
            self._system_prompt = _SYSTEM_PROMPT_COMPACT
        else:
            available = _load_available_glosses()
            if available:
                gloss_str = ", ".join(available)
            else:
                gloss_str = "(full WLASL vocabulary — no constraint)"
            self._system_prompt = _SYSTEM_PROMPT_FULL.format(available_glosses=gloss_str)

        try:
            import openai
            client_kwargs: dict = {"api_key": self._api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            self._client = openai.OpenAI(**client_kwargs)
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        logger.info(
            "GlossTranslator initialised: provider=%s  model=%s  prompt_mode=%s",
            provider, self._model,
            "compact" if provider == "ollama" else "full",
        )

    def translate(self, english_text: str) -> list[str]:
        """Translate a single English sentence to ASL gloss sequence.

        Parameters
        ----------
        english_text : str
            The English sentence to translate.

        Returns
        -------
        list[str]
            Ordered list of ASL gloss words, e.g. ["LIBRARY", "WHERE"].
        """
        if self._system_as_user:
            messages = [
                {"role": "user", "content": (
                    self._system_prompt
                    + "\n\n---\n"
                    + "Now translate the following English text to ASL gloss. "
                    + "Output ONLY the uppercase gloss words, nothing else.\n\n"
                    + 'English: "' + english_text.strip() + '"\n'
                    + "ASL Gloss:"
                )},
            ]
        else:
            messages = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": english_text.strip()},
            ]

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        import re
        glosses = [
            re.sub(r'[^A-Z0-9\-]', '', w.strip().upper())
            for w in raw.split()
            if w.strip()
        ]
        glosses = [g for g in glosses if g]  # drop empty after stripping

        logger.info(
            "Translated: %r -> %s",
            english_text[:80], " ".join(glosses),
        )
        return glosses

    def translate_segments(self, segments: list[dict]) -> list[dict]:
        """Translate multiple transcript segments to ASL gloss sequences.

        Each segment dict gets new fields: ``gloss_sequence`` (list[str])
        and ``gloss_text`` (str, space-separated).

        Parameters
        ----------
        segments : list[dict]
            Transcript segments with at least a ``text`` field.

        Returns
        -------
        list[dict]
            Segments enriched with gloss data.
        """
        results = []
        for seg in segments:
            enriched = dict(seg)
            try:
                glosses = self.translate(seg["text"])
                enriched["gloss_sequence"] = glosses
                enriched["gloss_text"] = " ".join(glosses)
            except Exception as exc:
                logger.error("Gloss translation failed for %r: %s", seg["text"][:60], exc)
                enriched["gloss_sequence"] = []
                enriched["gloss_text"] = ""
            results.append(enriched)

        translated = sum(1 for r in results if r["gloss_sequence"])
        logger.info(
            "Gloss translation complete: %d/%d segments translated",
            translated, len(results),
        )
        return results


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python -m src.gloss.translator \"English sentence here\"")
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    translator = GlossTranslator()
    glosses = translator.translate(text)
    print(f"Input:  {text}")
    print(f"Gloss:  {' '.join(glosses)}")
