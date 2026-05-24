"""LLM provider abstraction for the interpreter pipeline.

Each provider implements :class:`LLMProvider` — a single ``chat`` method
covering one system + user prompt → completion. The interpreter brain
(``src/interpreter/planner.py``) and any future LLM-driven stage call
into the provider returned by :func:`make_provider`.

The ``GlossProvider`` name is kept as an alias for backwards compatibility
with tests that pre-date the move from ``src.gloss.providers``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.config import Settings, get_settings


@runtime_checkable
class LLMProvider(Protocol):
    """A thin chat-completion backend for one LLM call."""

    name: str
    """Provider identifier (``"ollama"``, ``"gemini"``, ``"openai"``, ``"fake"``)."""

    model: str
    """Model identifier — surfaced in plan metadata and cache keys."""

    def chat(self, system: str, user: str, *, max_tokens: int = 200) -> str:
        """Run one completion and return the assistant text, already stripped."""


# Backwards-compat alias — older tests import GlossProvider.
GlossProvider = LLMProvider


def make_provider(settings: Settings | None = None) -> LLMProvider:
    """Construct the provider configured in :attr:`Settings.llm.provider`."""
    s = settings or get_settings()
    name = s.llm.provider
    if name == "ollama":
        from src.llm.providers.ollama import OllamaProvider

        return OllamaProvider(s.llm.ollama)
    if name == "gemini":
        from src.llm.providers.gemini import GeminiProvider

        return GeminiProvider(s.llm.gemini)
    if name == "openai":
        from src.llm.providers.openai import OpenAIProvider

        return OpenAIProvider(s.llm.openai)
    raise ValueError(f"Unknown LLM provider: {name!r}")


__all__ = ["LLMProvider", "GlossProvider", "make_provider"]
