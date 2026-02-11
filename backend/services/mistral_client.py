"""Async wrapper around the Mistral API for chat completions and embeddings."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from mistralai import Mistral

from config import settings

logger = logging.getLogger(__name__)


# Per-mode generation parameters
MODE_CONFIGS: dict[str, dict[str, Any]] = {
    "fast": {
        "max_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.9,
    },
    "standard": {
        "max_tokens": 1500,
        "temperature": 0.5,
        "top_p": 0.95,
    },
    "deep": {
        "max_tokens": 4000,
        "temperature": 0.7,
        "top_p": 0.95,
    },
}


class MistralClient:
    """Thin async wrapper for Mistral chat + embed endpoints."""

    def __init__(self) -> None:
        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self.model = settings.MISTRAL_CHAT_MODEL
        self.embed_model = settings.MISTRAL_EMBED_MODEL

    # ── Chat (non-streaming) ──────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        mode: str = "standard",
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> tuple[str, int]:
        """
        Send a chat completion request.

        Returns:
            (response_text, total_tokens_used)
        """
        cfg = MODE_CONFIGS.get(mode, MODE_CONFIGS["standard"])
        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or cfg["max_tokens"],
            "temperature": temperature or cfg["temperature"],
            "top_p": cfg["top_p"],
        }
        if response_format:
            params["response_format"] = response_format

        start = time.monotonic()
        response = await self._client.chat.complete_async(**params)
        elapsed = (time.monotonic() - start) * 1000

        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        logger.debug(
            "Mistral chat: mode=%s tokens=%d latency=%.0fms", mode, tokens, elapsed
        )
        return text, tokens

    # ── Chat (streaming) ──────────────────────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        mode: str = "standard",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Yield token chunks as they arrive from the Mistral API."""
        cfg = MODE_CONFIGS.get(mode, MODE_CONFIGS["standard"])
        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or cfg["max_tokens"],
            "temperature": temperature or cfg["temperature"],
            "top_p": cfg["top_p"],
        }

        response = await self._client.chat.stream_async(**params)
        async for event in response:
            chunk = event.data.choices[0].delta.content
            if chunk:
                yield chunk

    # ── Embeddings ────────────────────────────────────────────────────

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts (max ~16 at a time for rate limits)."""
        response = await self._client.embeddings.create_async(
            model=self.embed_model,
            inputs=texts,
        )
        return [item.embedding for item in response.data]

    async def embed_single(self, text: str) -> list[float]:
        vecs = await self.embed([text])
        return vecs[0]


# Singleton instance
_client: MistralClient | None = None


def get_mistral_client() -> MistralClient:
    global _client
    if _client is None:
        _client = MistralClient()
    return _client
