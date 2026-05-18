"""Verify GlossProvider conformance + provider-specific routing.

We don't make real network calls — providers are constructed with their
config but the OpenAI SDK is patched out so each ``chat()`` returns a
canned response. The point is to verify:

  - Each concrete provider implements the :class:`GlossProvider` Protocol.
  - The "fold system into user" branch fires for gemma-* models in the
    providers that have it (Ollama, Gemini), and never fires elsewhere.
  - FakeProvider is a valid GlossProvider too.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import LLMProviderCfg
from src.gloss.providers import GlossProvider, make_provider
from src.gloss.providers.fake import FakeProvider
from src.gloss.providers.gemini import GeminiProvider
from src.gloss.providers.ollama import OllamaProvider
from src.gloss.providers.openai import OpenAIProvider


def _patched_openai_returning(content: str):
    """Return a context manager that patches openai.OpenAI to yield canned content."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content

    client = MagicMock()
    client.chat.completions.create.return_value = mock_response

    return client


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

def test_fake_provider_satisfies_protocol():
    p = FakeProvider(canned="X")
    assert isinstance(p, GlossProvider)
    assert p.name == "fake"
    assert p.chat("system", "user") == "X"


def test_ollama_provider_satisfies_protocol():
    with patch("src.gloss.providers.ollama.openai.OpenAI", return_value=_patched_openai_returning("LIBRARY")):
        p = OllamaProvider(LLMProviderCfg(model="llama3.2"))
    assert isinstance(p, GlossProvider)
    assert p.name == "ollama"
    assert p.model == "llama3.2"


def test_openai_provider_satisfies_protocol(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("src.gloss.providers.openai.openai.OpenAI", return_value=_patched_openai_returning("LIBRARY")):
        p = OpenAIProvider(LLMProviderCfg(model="gpt-4o-mini"))
    assert isinstance(p, GlossProvider)
    assert p.name == "openai"


def test_gemini_provider_satisfies_protocol(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("src.gloss.providers.gemini.openai.OpenAI", return_value=_patched_openai_returning("LIBRARY")):
        p = GeminiProvider(LLMProviderCfg(model="gemini-2.0-flash"))
    assert isinstance(p, GlossProvider)
    assert p.name == "gemini"


# ---------------------------------------------------------------------------
# API-key enforcement
# ---------------------------------------------------------------------------

def test_openai_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIProvider(LLMProviderCfg(model="gpt-4o-mini"))


def test_gemini_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiProvider(LLMProviderCfg(model="gemini-2.0-flash"))


# ---------------------------------------------------------------------------
# Gemma system-as-user routing
# ---------------------------------------------------------------------------

def _captured_messages(mock_client) -> list[dict]:
    """Pull the messages= kwarg from the mock client's last create() call."""
    call = mock_client.chat.completions.create.call_args
    return call.kwargs["messages"]


def test_ollama_routes_gemma_into_user_message():
    client = _patched_openai_returning("FOO")
    with patch("src.gloss.providers.ollama.openai.OpenAI", return_value=client):
        p = OllamaProvider(LLMProviderCfg(model="gemma3:4b"))
    p.chat("system text", "user text")
    msgs = _captured_messages(client)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert "system text" in msgs[0]["content"]
    assert "user text" in msgs[0]["content"]


def test_ollama_keeps_system_role_for_non_gemma():
    client = _patched_openai_returning("FOO")
    with patch("src.gloss.providers.ollama.openai.OpenAI", return_value=client):
        p = OllamaProvider(LLMProviderCfg(model="llama3.2"))
    p.chat("system text", "user text")
    msgs = _captured_messages(client)
    assert [m["role"] for m in msgs] == ["system", "user"]


def test_gemini_routes_gemma_into_user_message(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = _patched_openai_returning("FOO")
    with patch("src.gloss.providers.gemini.openai.OpenAI", return_value=client):
        p = GeminiProvider(LLMProviderCfg(model="gemma-3-27b-it"))
    p.chat("system text", "user text")
    msgs = _captured_messages(client)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


def test_openai_never_folds_system_into_user(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = _patched_openai_returning("FOO")
    with patch("src.gloss.providers.openai.openai.OpenAI", return_value=client):
        p = OpenAIProvider(LLMProviderCfg(model="gpt-4o-mini"))
    p.chat("system text", "user text")
    msgs = _captured_messages(client)
    assert [m["role"] for m in msgs] == ["system", "user"]


# ---------------------------------------------------------------------------
# make_provider factory
# ---------------------------------------------------------------------------

def test_make_provider_constructs_configured_provider():
    """The factory returns the provider type matching settings.llm.provider."""
    from src.core.config import Settings

    s = Settings()  # defaults: provider="ollama"
    with patch("src.gloss.providers.ollama.openai.OpenAI", return_value=MagicMock()):
        p = make_provider(s)
    assert p.name == "ollama"
