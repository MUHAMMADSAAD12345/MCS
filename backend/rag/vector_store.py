"""Qdrant vector store operations — upsert, search, delete."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config import settings

logger = logging.getLogger(__name__)

_COLLECTION = settings.QDRANT_COLLECTION
_VECTOR_SIZE = 1024  # mistral-embed dimension


class VectorStore:
    """Qdrant-backed vector storage for RAG chunks."""

    def __init__(self) -> None:
        self._client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            collections = self._client.get_collections().collections
            names = [c.name for c in collections]
            if _COLLECTION not in names:
                self._client.create_collection(
                    collection_name=_COLLECTION,
                    vectors_config=VectorParams(
                        size=_VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection: %s", _COLLECTION)
            else:
                logger.info("Qdrant collection '%s' already exists.", _COLLECTION)
        except Exception as e:
            logger.warning("Could not connect to Qdrant: %s", e)

    def upsert(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        """Insert or update vectors with payloads."""
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]

        points = [
            PointStruct(id=uid, vector=vec, payload=payload)
            for uid, vec, payload in zip(ids, vectors, payloads)
        ]

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self._client.upsert(
                collection_name=_COLLECTION,
                points=batch,
            )
        logger.info("Upserted %d vectors to Qdrant", len(points))

    def search(
        self,
        query_vector: list[float],
        user_id: str = "",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors, filtered by user_id."""
        query_filter = None
        if user_id:
            query_filter = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )

        results = self._client.query_points(
            collection_name=_COLLECTION,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
        ).points

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "text": r.payload.get("text", ""),
                "source": r.payload.get("source_file", "unknown"),
                "metadata": r.payload,
            }
            for r in results
        ]

    def delete_by_document(self, doc_id: str, user_id: str) -> None:
        """Delete all vectors belonging to a specific document."""
        self._client.delete(
            collection_name=_COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                ]
            ),
        )
        logger.info("Deleted vectors for doc %s", doc_id)

    def health_check(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False
