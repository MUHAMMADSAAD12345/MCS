"""Document ingestion pipeline — parse, chunk, embed, store."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from rag.chunker import RecursiveChunker
from rag.embedder import EmbeddingEngine
from rag.parser import DocumentParser
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """End-to-end document ingestion: parse → chunk → embed → store."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingEngine,
    ) -> None:
        self._parser = DocumentParser()
        self._chunker = RecursiveChunker(chunk_size=512, chunk_overlap=64)
        self._embedder = embedder
        self._store = vector_store

    async def ingest(
        self,
        filepath: Path,
        user_id: str,
        doc_id: str | None = None,
    ) -> tuple[str, int]:
        """
        Ingest a document into the vector store.

        Returns:
            (doc_id, chunk_count)
        """
        doc_id = doc_id or str(uuid.uuid4())
        filename = filepath.name

        logger.info("Ingesting document: %s (user=%s)", filename, user_id)

        # 1. Parse
        text, parse_meta = self._parser.parse(filepath)
        if not text.strip():
            raise ValueError(f"No text extracted from {filename}")

        # 2. Chunk
        chunks = self._chunker.chunk(
            text,
            source_file=filename,
            extra_metadata=parse_meta,
        )
        if not chunks:
            raise ValueError(f"No chunks produced from {filename}")

        # 3. Embed
        chunk_texts = [c.text for c in chunks]
        embeddings = await self._embedder.embed_batch(chunk_texts)

        # 4. Build payloads
        payloads = []
        for chunk in chunks:
            payload = {
                "text": chunk.text,
                "doc_id": doc_id,
                "user_id": user_id,
                "source_file": filename,
                **chunk.metadata,
            }
            payloads.append(payload)

        # 5. Upsert to Qdrant
        self._store.upsert(vectors=embeddings, payloads=payloads)

        logger.info(
            "Ingested %s: %d chunks, doc_id=%s", filename, len(chunks), doc_id
        )
        return doc_id, len(chunks)
