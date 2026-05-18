"""LLM provider abstraction for the gloss translator.

Each provider implements :class:`GlossProvider` — a single ``chat`` method.
:class:`~src.gloss.translator.GlossTranslator` is provider-agnostic.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.config import Settings, get_settings


@runtime_checkable
class GlossProvider(Protocol):
    """A thin chat-completion backend for one English-to-gloss call."""

    name: str
    """Provider identifier (``"ollama"``, ``"gemini"``, ``"openai"``, ``"fake"``)."""

    model: str
    """Model identifier — surfaced in render-plan metadata and cache keys."""

    def chat(self, system: str, user: str, *, max_tokens: int = 200) -> str:
        """Run one completion and return the assistant text, already stripped."""


def make_provider(settings: Settings | None = None) -> GlossProvider:
    """Construct the provider configured in :attr:`Settings.llm.provider`."""
    s = settings or get_settings()
    name = s.llm.provider
    if name == "ollama":
        from src.gloss.providers.ollama import OllamaProvider

        return OllamaProvider(s.llm.ollama)
    if name == "gemini":
        from src.gloss.providers.gemini import GeminiProvider

        return GeminiProvider(s.llm.gemini)
    if name == "openai":
        from src.gloss.providers.openai import OpenAIProvider

        return OpenAIProvider(s.llm.openai)
    raise ValueError(f"Unknown LLM provider: {name!r}")


__all__ = ["GlossProvider", "make_provider"]
