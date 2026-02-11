"""Abstract base class for all reasoning modes."""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from typing import Any, Callable, Coroutine


class BaseReasoning(abc.ABC):
    """
    Interface for reasoning pipelines.

    Each mode implements `execute()` which yields streaming events
    back to the caller (WebSocket handler).
    """

    @abc.abstractmethod
    async def execute(
        self,
        query: str,
        *,
        chat_history: list[dict] | None = None,
        user_id: str = "",
        send_event: Callable[[dict[str, Any]], Coroutine] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run the reasoning pipeline.

        Yields dicts with keys:
            - {"type": "reasoning_step", ...}
            - {"type": "tool_call", ...}
            - {"type": "token", "content": "..."}
            - {"type": "done", "metadata": {...}}

        Args:
            query: The user's question / instruction.
            chat_history: Previous messages in this session.
            user_id: For RAG filtering.
            send_event: Optional callback to push events immediately (WebSocket).
        """
        ...  # pragma: no cover
        # Required yield to make this an async generator
        if False:
            yield {}
