"""Recursive text chunker — splits documents into overlapping chunks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Separators in priority order (split at the most semantic boundary first)
SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]


@dataclass
class Chunk:
    text: str
    index: int
    metadata: dict = field(default_factory=dict)


class RecursiveChunker:
    """Split text into overlapping chunks respecting semantic boundaries."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self.chunk_size = chunk_size  # in characters (approx ~128 tokens)
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        text: str,
        source_file: str = "",
        extra_metadata: dict | None = None,
    ) -> list[Chunk]:
        """Split text into chunks with overlap."""
        if not text.strip():
            return []

        raw_chunks = self._recursive_split(text, SEPARATORS)

        # Merge small chunks and enforce overlap
        merged = self._merge_chunks(raw_chunks)

        chunks = []
        for i, chunk_text in enumerate(merged):
            meta = {
                "source_file": source_file,
                "chunk_index": i,
                "total_chunks": len(merged),
            }
            if extra_metadata:
                meta.update(extra_metadata)
            chunks.append(Chunk(text=chunk_text.strip(), index=i, metadata=meta))

        logger.info(
            "Chunked '%s' into %d chunks (size=%d, overlap=%d)",
            source_file, len(chunks), self.chunk_size, self.chunk_overlap,
        )
        return chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using increasingly fine separators."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        if not separators:
            # Last resort: hard split
            return self._hard_split(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        parts = text.split(sep)
        result: list[str] = []
        current = ""

        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    result.append(current)
                # If this single part is too large, split it further
                if len(part) > self.chunk_size:
                    sub_parts = self._recursive_split(part, remaining_seps)
                    result.extend(sub_parts)
                    current = ""
                else:
                    current = part

        if current:
            result.append(current)

        return result

    def _hard_split(self, text: str) -> list[str]:
        """Character-level split as last resort."""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i : i + self.chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def _merge_chunks(self, chunks: list[str]) -> list[str]:
        """Merge small chunks and add overlap between adjacent chunks."""
        if not chunks:
            return []

        # First pass: merge very small chunks
        merged: list[str] = []
        current = ""
        for chunk in chunks:
            if len(current) + len(chunk) <= self.chunk_size:
                current = current + " " + chunk if current else chunk
            else:
                if current:
                    merged.append(current)
                current = chunk
        if current:
            merged.append(current)

        # Second pass: add overlap
        if len(merged) <= 1:
            return merged

        result: list[str] = []
        for i, chunk in enumerate(merged):
            if i > 0:
                # Prepend overlap from previous chunk
                prev = merged[i - 1]
                overlap = prev[-self.chunk_overlap :] if len(prev) > self.chunk_overlap else prev
                chunk = overlap + " " + chunk
            result.append(chunk)

        return result
