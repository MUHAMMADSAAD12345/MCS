"""RAG retriever — search + rerank retrieved chunks."""

from __future__ import annotations

import logging
import re
from typing import Any

from rag.embedder import EmbeddingEngine
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retrieve and rerank document chunks for a given query."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingEngine,
    ) -> None:
        self._store = vector_store
        self._embedder = embedder

    async def retrieve(
        self,
        query: str,
        user_id: str = "",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Embed query → vector search → rerank → deduplicate.

        Returns list of dicts with keys: text, source, score, metadata.
        """
        if not query.strip():
            return []

        # 1. Embed the query
        query_vec = await self._embedder.embed_single(query)

        # 2. Search with over-fetch for reranking
        try:
            raw_results = self._store.search(
                query_vector=query_vec,
                user_id=user_id,
                top_k=top_k * 2,
            )
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            return []

        if not raw_results:
            return []

        # 3. Rerank with keyword overlap boost
        reranked = self._rerank(query, raw_results)

        # 4. Deduplicate overlapping chunks
        deduped = self._deduplicate(reranked)

        return deduped[:top_k]

    def _rerank(self, query: str, results: list[dict]) -> list[dict]:
        """Rerank by combining vector similarity + keyword overlap."""
        query_words = set(self._tokenize(query))

        for r in results:
            text_words = set(self._tokenize(r.get("text", "")))
            overlap = len(query_words & text_words)
            max_possible = max(len(query_words), 1)
            keyword_score = overlap / max_possible

            # Combined score: 70% vector similarity + 30% keyword overlap
            r["combined_score"] = 0.7 * r.get("score", 0) + 0.3 * keyword_score

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results

    @staticmethod
    def _deduplicate(results: list[dict], threshold: float = 0.8) -> list[dict]:
        """Remove chunks with high text overlap."""
        seen_texts: list[str] = []
        deduped: list[dict] = []

        for r in results:
            text = r.get("text", "")
            is_dup = False
            for seen in seen_texts:
                # Simple overlap check: shared character ratio
                shorter = min(len(text), len(seen))
                if shorter == 0:
                    continue
                # Check if one is a substring of the other
                if text in seen or seen in text:
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(r)
                seen_texts.append(text)

        return deduped

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple word tokenization for keyword matching."""
        return re.findall(r"\w+", text.lower())
