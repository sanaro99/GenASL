"""Ollama (local) chat-completion provider."""

from __future__ import annotations

import openai

from src.core.config import LLMProviderCfg


class OllamaProvider:
    """OpenAI-compatible client targeting a local Ollama server."""

    name = "ollama"

    def __init__(self, cfg: LLMProviderCfg) -> None:
        self.model = cfg.model
        # Ollama ignores the API key but the SDK still requires one.
        self._client = openai.OpenAI(
            base_url=cfg.base_url or "http://localhost:11434/v1",
            api_key="ollama",
        )

    def chat(self, system: str, user: str, *, max_tokens: int = 200) -> str:
        # Local gemma models don't accept the system role — fold it in.
        if self.model.startswith("gemma"):
            messages = [{"role": "user", "content": f"{system}\n\n---\n{user}"}]
        else:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
