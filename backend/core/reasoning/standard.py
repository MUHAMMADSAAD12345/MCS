"""Standard mode — plan → gather → respond."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Callable, Coroutine

from core.prompts.standard_prompts import build_plan_prompt, build_respond_prompt
from core.reasoning.base import BaseReasoning
from models.enums import ReasoningMode, ToolName
from services.mistral_client import get_mistral_client

logger = logging.getLogger(__name__)


class StandardReasoning(BaseReasoning):
    """
    Step-based reasoning: Plan → Gather (1-2 tools) → Respond.
    2–3 LLM calls, ~1500 tokens.
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
        llm_calls = 0
        tools_used: list[ToolName] = []

        # ── Step 1: PLAN ──────────────────────────────────────────────
        yield {
            "type": "reasoning_step",
            "step_name": "plan",
            "step_number": 1,
            "total_steps": 3,
            "description": "Analyzing your question and planning approach...",
        }

        plan_messages = build_plan_prompt(query, chat_history)
        plan_text, tokens = await self._llm.chat(
            plan_messages,
            mode="standard",
            max_tokens=300,
            temperature=0.3,
        )
        total_tokens += tokens
        llm_calls += 1

        # Parse plan JSON
        plan = self._parse_plan(plan_text)

        # ── Step 2: GATHER ────────────────────────────────────────────
        yield {
            "type": "reasoning_step",
            "step_name": "gather",
            "step_number": 2,
            "total_steps": 3,
            "description": "Gathering information from tools...",
        }

        tool_results_text = ""
        rag_context: str | None = None
        datetime_info: str | None = None

        if self._tool_router and plan.get("tools_needed"):
            for tool_name in plan["tools_needed"][:2]:  # Max 2 tools
                if tool_name == "none":
                    continue

                yield {
                    "type": "tool_call",
                    "tool": tool_name,
                    "status": "executing",
                }

                try:
                    params: dict[str, Any] = {}
                    if tool_name == "rag":
                        params = {"query": query, "user_id": user_id, "top_k": 5}
                    elif tool_name == "web_search":
                        search_q = " ".join(plan.get("entities", [query]))
                        params = {"query": search_q}
                    elif tool_name == "datetime":
                        params = {}
                    elif tool_name == "doc_create":
                        params = {"query": query}

                    result = await self._tool_router.execute(
                        tool_name, params, "standard"
                    )

                    if result.success and result.data:
                        tool_enum = self._map_tool_name(tool_name)
                        if tool_enum:
                            tools_used.append(tool_enum)

                        if tool_name == "rag":
                            rag_context = result.data
                        elif tool_name == "datetime":
                            datetime_info = result.data
                        else:
                            tool_results_text += f"\n[{tool_name}]: {result.data}"

                except Exception as e:
                    logger.warning("Tool %s failed: %s", tool_name, e)

        # ── Step 3: RESPOND ───────────────────────────────────────────
        yield {
            "type": "reasoning_step",
            "step_name": "respond",
            "step_number": 3,
            "total_steps": 3,
            "description": "Synthesizing final answer...",
        }

        respond_messages = build_respond_prompt(
            query=query,
            plan_json=json.dumps(plan, indent=2),
            tool_results=tool_results_text,
            rag_context=rag_context,
            chat_history=chat_history,
            datetime_info=datetime_info,
        )

        full_response = ""
        async for token in self._llm.chat_stream(respond_messages, mode="standard"):
            full_response += token
            yield {"type": "token", "content": token}

        llm_calls += 1
        total_tokens += len(full_response.split()) * 2

        elapsed = (time.monotonic() - start) * 1000
        yield {
            "type": "done",
            "content": full_response,
            "metadata": {
                "reasoning_mode": ReasoningMode.STANDARD.value,
                "tools_used": [t.value for t in tools_used],
                "llm_calls": llm_calls,
                "total_tokens": total_tokens,
                "latency_ms": round(elapsed, 1),
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_plan(plan_text: str) -> dict:
        """Try to extract JSON from the LLM plan response."""
        try:
            # Strip markdown code fences if present
            text = plan_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse plan JSON, using defaults")
            return {
                "intent": "question",
                "entities": [],
                "tools_needed": ["rag"],
                "reasoning_notes": "Fallback plan",
            }

    @staticmethod
    def _map_tool_name(name: str) -> ToolName | None:
        mapping = {
            "rag": ToolName.RAG,
            "web_search": ToolName.WEB_SEARCH,
            "web_deep": ToolName.WEB_DEEP,
            "datetime": ToolName.DATETIME,
            "doc_create": ToolName.DOC_CREATE,
        }
        return mapping.get(name)
