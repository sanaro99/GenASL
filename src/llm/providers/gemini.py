"""Gemini chat-completion provider (Google's OpenAI-compatible endpoint)."""

from __future__ import annotations

import os

import openai

from src.core.config import LLMProviderCfg


class GeminiProvider:
    """Google Gemini via the OpenAI-compatible API."""

    name = "gemini"

    def __init__(self, cfg: LLMProviderCfg) -> None:
        self.model = cfg.model
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required for the gemini provider."
            )
        self._client = openai.OpenAI(
            base_url=cfg.base_url or "https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key,
        )

    def chat(self, system: str, user: str, *, max_tokens: int = 200) -> str:
        # Gemma via the Gemini API doesn't support the "system" role.
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
