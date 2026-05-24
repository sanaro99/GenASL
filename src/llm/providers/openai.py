"""OpenAI chat-completion provider."""

from __future__ import annotations

import os

import openai

from src.core.config import LLMProviderCfg


class OpenAIProvider:
    """OpenAI's hosted models."""

    name = "openai"

    def __init__(self, cfg: LLMProviderCfg) -> None:
        self.model = cfg.model
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for the openai provider."
            )
        kwargs: dict = {"api_key": api_key}
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        self._client = openai.OpenAI(**kwargs)

    def chat(self, system: str, user: str, *, max_tokens: int = 200) -> str:
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
