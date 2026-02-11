"""Deep mode — decompose → research → synthesize → verify."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Callable, Coroutine

from core.prompts.deep_prompts import (
    build_decompose_prompt,
    build_sub_answer_prompt,
    build_synthesize_prompt,
    build_verify_prompt,
)
from core.reasoning.base import BaseReasoning
from models.enums import ReasoningMode, ToolName
from services.mistral_client import get_mistral_client

logger = logging.getLogger(__name__)


class DeepReasoning(BaseReasoning):
    """
    Multi-step analysis: Decompose → Research → Synthesize → Verify.
    4–6 LLM calls, ~4000 tokens, full tool suite.
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
        all_sources = ""

        # ── Get datetime once ─────────────────────────────────────────
        datetime_info: str | None = None
        if self._tool_router:
            try:
                dt_result = await self._tool_router.execute("datetime", {}, "deep")
                if dt_result.success:
                    datetime_info = dt_result.data
                    tools_used.append(ToolName.DATETIME)
            except Exception:
                pass

        # ── Step 1: DECOMPOSE ─────────────────────────────────────────
        yield {
            "type": "reasoning_step",
            "step_name": "decompose",
            "step_number": 1,
            "total_steps": 4,
            "description": "Breaking down your question into sub-topics...",
        }

        decompose_messages = build_decompose_prompt(query, chat_history)
        decompose_text, tokens = await self._llm.chat(
            decompose_messages, mode="deep", max_tokens=500, temperature=0.4
        )
        total_tokens += tokens
        llm_calls += 1

        plan = self._parse_decomposition(decompose_text)
        sub_questions = plan.get("sub_questions", [])

        if not sub_questions:
            # Fallback: treat as single question
            sub_questions = [
                {"id": 1, "question": query, "tools": ["rag"], "search_queries": [query]}
            ]

        # ── Step 2: RESEARCH (parallel per sub-question) ──────────────
        yield {
            "type": "reasoning_step",
            "step_name": "research",
            "step_number": 2,
            "total_steps": 4,
            "description": f"Researching {len(sub_questions)} sub-topics in parallel...",
        }

        async def research_sub_question(sq: dict) -> dict[str, str]:
            """Research and answer a single sub-question."""
            context_parts: list[str] = []

            if self._tool_router:
                for tool in sq.get("tools", ["rag"])[:2]:
                    try:
                        if tool == "rag":
                            search_q = sq.get("search_queries", [sq["question"]])[0] if sq.get("search_queries") else sq["question"]
                            result = await self._tool_router.execute(
                                "rag",
                                {"query": search_q, "user_id": user_id, "top_k": 5},
                                "deep",
                            )
                            if result.success and result.data:
                                context_parts.append(f"[Documents]: {result.data}")
                                if ToolName.RAG not in tools_used:
                                    tools_used.append(ToolName.RAG)

                        elif tool in ("web_search", "web_deep"):
                            search_q = sq.get("search_queries", [sq["question"]])[0] if sq.get("search_queries") else sq["question"]
                            result = await self._tool_router.execute(
                                tool,
                                {"query": search_q},
                                "deep",
                            )
                            if result.success and result.data:
                                context_parts.append(f"[Web]: {result.data}")
                                tool_enum = ToolName.WEB_SEARCH if tool == "web_search" else ToolName.WEB_DEEP
                                if tool_enum not in tools_used:
                                    tools_used.append(tool_enum)
                    except Exception as e:
                        logger.warning("Tool %s failed for sub-question: %s", tool, e)

            context = "\n\n".join(context_parts) if context_parts else "No additional context available."

            messages = build_sub_answer_prompt(
                sq["question"], context, datetime_info
            )
            answer, toks = await self._llm.chat(messages, mode="deep", max_tokens=600)
            return {
                "id": sq.get("id", 0),
                "question": sq["question"],
                "answer": answer,
                "tokens": toks,
                "context": context,
            }

        # Run sub-questions concurrently
        sub_tasks = [research_sub_question(sq) for sq in sub_questions]
        sub_results = await asyncio.gather(*sub_tasks, return_exceptions=True)

        sub_answers: list[dict[str, str]] = []
        for r in sub_results:
            if isinstance(r, Exception):
                logger.warning("Sub-question research failed: %s", r)
                continue
            sub_answers.append(r)
            total_tokens += r.get("tokens", 0)
            llm_calls += 1
            all_sources += r.get("context", "") + "\n"

        # ── Step 3: SYNTHESIZE ────────────────────────────────────────
        yield {
            "type": "reasoning_step",
            "step_name": "synthesize",
            "step_number": 3,
            "total_steps": 4,
            "description": "Combining findings into a comprehensive answer...",
        }

        synth_messages = build_synthesize_prompt(query, sub_answers, datetime_info)
        draft, tokens = await self._llm.chat(synth_messages, mode="deep")
        total_tokens += tokens
        llm_calls += 1

        # ── Step 4: VERIFY & REFINE ───────────────────────────────────
        yield {
            "type": "reasoning_step",
            "step_name": "verify",
            "step_number": 4,
            "total_steps": 4,
            "description": "Verifying accuracy and refining response...",
        }

        verify_messages = build_verify_prompt(query, draft, all_sources[:3000])

        full_response = ""
        async for token in self._llm.chat_stream(verify_messages, mode="deep"):
            full_response += token
            yield {"type": "token", "content": token}

        llm_calls += 1
        total_tokens += len(full_response.split()) * 2

        elapsed = (time.monotonic() - start) * 1000
        yield {
            "type": "done",
            "content": full_response,
            "metadata": {
                "reasoning_mode": ReasoningMode.DEEP.value,
                "tools_used": [t.value for t in tools_used],
                "llm_calls": llm_calls,
                "total_tokens": total_tokens,
                "latency_ms": round(elapsed, 1),
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_decomposition(text: str) -> dict:
        try:
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
            if clean.startswith("json"):
                clean = clean[4:].strip()
            return json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse decomposition JSON")
            return {"sub_questions": [], "synthesis_strategy": "direct"}
