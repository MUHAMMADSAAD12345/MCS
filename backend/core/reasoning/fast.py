"""Fast mode — single-pass reasoning with minimal latency."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Callable, Coroutine

from core.prompts.fast_prompts import build_fast_prompt
from core.reasoning.base import BaseReasoning
from models.enums import ReasoningMode, ToolName
from services.mistral_client import get_mistral_client

logger = logging.getLogger(__name__)


class FastReasoning(BaseReasoning):
    """
    Single LLM call, ~512 tokens, minimal tools.
    Optimized for poor / fair network conditions.
    """

    def __init__(self, tool_router: Any = None) -> None:
        self._tool_router = tool_router
        self._llm = get_mistral_client()

    async def execute(
        self,
        query: str,
        *,
        chat_history: list[dict] | None = None,
        user_id: str = "",
        send_event: Callable[[dict[str, Any]], Coroutine] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        start = time.monotonic()
        total_tokens = 0
        tools_used: list[ToolName] = []

        # ── Step: quick RAG lookup (if documents exist) ───────────────
        rag_context: str | None = None
        if self._tool_router:
            try:
                rag_result = await self._tool_router.execute(
                    "rag", {"query": query, "user_id": user_id, "top_k": 3}, "fast"
                )
                if rag_result.success and rag_result.data:
                    rag_context = rag_result.data
                    tools_used.append(ToolName.RAG)
            except Exception:
                pass  # Non-critical in fast mode

        # ── Step: datetime if query mentions time ─────────────────────
        datetime_info: str | None = None
        if self._tool_router:
            try:
                dt_result = await self._tool_router.execute(
                    "datetime", {}, "fast"
                )
                if dt_result.success:
                    datetime_info = dt_result.data
                    tools_used.append(ToolName.DATETIME)
            except Exception:
                pass

        # ── Build prompt & stream response ────────────────────────────
        messages = build_fast_prompt(
            query=query,
            rag_context=rag_context,
            chat_history=chat_history,
            datetime_info=datetime_info,
        )

        yield {
            "type": "reasoning_step",
            "step_name": "respond",
            "step_number": 1,
            "total_steps": 1,
            "description": "Generating response...",
        }

        full_response = ""
        async for token in self._llm.chat_stream(messages, mode="fast"):
            full_response += token
            yield {"type": "token", "content": token}

        # Rough token estimate
        total_tokens = len(full_response.split()) * 2

        elapsed = (time.monotonic() - start) * 1000
        yield {
            "type": "done",
            "content": full_response,
            "metadata": {
                "reasoning_mode": ReasoningMode.FAST.value,
                "tools_used": [t.value for t in tools_used],
                "llm_calls": 1,
                "total_tokens": total_tokens,
                "latency_ms": round(elapsed, 1),
            },
        }
