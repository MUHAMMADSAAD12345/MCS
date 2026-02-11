"""Main agent orchestrator — ties together network monitor, analyzer, selector, and reasoning."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from core.network_monitor import NetworkMonitor, get_network_monitor
from core.query_analyzer import QueryComplexityAnalyzer, get_query_analyzer
from core.reasoning.deep import DeepReasoning
from core.reasoning.fast import FastReasoning
from core.reasoning.standard import StandardReasoning
from core.strategy_selector import StrategySelector, get_strategy_selector
from models.enums import ReasoningMode
from services.circuit_breaker import CircuitBreakerError, get_breaker
from tools.router import ToolRouter

logger = logging.getLogger(__name__)


class Agent:
    """
    Central orchestrator for the Adaptive Reasoning Agent.

    On each user query:
    1. Probe network conditions
    2. Analyze query complexity
    3. Select reasoning mode
    4. Execute the reasoning pipeline
    5. Stream results back
    """

    def __init__(self, tool_router: ToolRouter | None = None) -> None:
        self._monitor: NetworkMonitor = get_network_monitor()
        self._analyzer: QueryComplexityAnalyzer = get_query_analyzer()
        self._selector: StrategySelector = get_strategy_selector()
        self._tool_router = tool_router

        # Reasoning pipelines
        self._pipelines = {
            ReasoningMode.FAST: FastReasoning(tool_router=tool_router),
            ReasoningMode.STANDARD: StandardReasoning(tool_router=tool_router),
            ReasoningMode.DEEP: DeepReasoning(tool_router=tool_router),
        }

        self._breaker = get_breaker("agent")

    async def process(
        self,
        query: str,
        *,
        user_id: str = "",
        chat_history: list[dict] | None = None,
        mode_override: ReasoningMode | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Process a user query through the adaptive reasoning pipeline.

        Yields streaming events (reasoning_step, tool_call, token, done).
        """
        start = time.monotonic()

        # Reset tool call counts for this request
        if self._tool_router:
            self._tool_router.reset_counts()

        # ── 1. Network probe ──────────────────────────────────────────
        try:
            network = await self._monitor.probe()
        except Exception:
            network = self._monitor.get_cached_snapshot()

        # ── 2. Query complexity ───────────────────────────────────────
        complexity = self._analyzer.analyze(query)

        # ── 3. Select mode ────────────────────────────────────────────
        mode = self._selector.select(network, complexity, mode_override)

        logger.info(
            "Processing query: mode=%s network=%s complexity=%s(%.2f)",
            mode.value, network.tier.value, complexity.tier.value, complexity.score,
        )

        # ── 4. Execute with degradation fallback ─────────────────────
        degradation_chain = self._get_degradation_chain(mode)

        for attempt_mode in degradation_chain:
            try:
                pipeline = self._pipelines[attempt_mode]
                async for event in pipeline.execute(
                    query,
                    chat_history=chat_history,
                    user_id=user_id,
                ):
                    # Inject network info into metadata
                    if event.get("type") == "done" and event.get("metadata"):
                        event["metadata"]["network_tier"] = network.tier.value
                        event["metadata"]["query_complexity"] = complexity.tier.value
                        event["metadata"]["complexity_score"] = complexity.score
                    yield event
                return  # Success — exit

            except CircuitBreakerError:
                logger.warning("Circuit breaker open for %s mode", attempt_mode.value)
                continue  # Try next mode in chain

            except Exception as e:
                logger.warning(
                    "Reasoning mode %s failed: %s — trying fallback",
                    attempt_mode.value, e,
                )
                continue

        # All modes failed
        elapsed = (time.monotonic() - start) * 1000
        yield {
            "type": "error",
            "content": "I'm having trouble processing your request right now. Please try again in a moment.",
            "metadata": {
                "reasoning_mode": mode.value,
                "network_tier": network.tier.value,
                "error": "All reasoning modes failed",
                "latency_ms": round(elapsed, 1),
            },
        }

    @staticmethod
    def _get_degradation_chain(mode: ReasoningMode) -> list[ReasoningMode]:
        """Get the fallback chain: current → simpler → simplest."""
        chains = {
            ReasoningMode.DEEP: [ReasoningMode.DEEP, ReasoningMode.STANDARD, ReasoningMode.FAST],
            ReasoningMode.STANDARD: [ReasoningMode.STANDARD, ReasoningMode.FAST],
            ReasoningMode.FAST: [ReasoningMode.FAST],
        }
        return chains.get(mode, [ReasoningMode.FAST])
