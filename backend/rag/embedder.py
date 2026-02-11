"""Embedding engine — batch embedding via Mistral API."""

from __future__ import annotations

import logging
from typing import Any

from services.mistral_client import get_mistral_client

logger = logging.getLogger(__name__)

_BATCH_SIZE = 16  # Mistral embedding batch limit


class EmbeddingEngine:
    """Embed text using Mistral's embedding model."""

    def __init__(self) -> None:
        self._client = get_mistral_client()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts in batches."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await self._client.embed(batch)
            all_embeddings.extend(embeddings)
        logger.info("Embedded %d texts in %d batches", len(texts), (len(texts) // _BATCH_SIZE) + 1)
        return all_embeddings

    async def embed_single(self, text: str) -> list[float]:
        return await self._client.embed_single(text)
