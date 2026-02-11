"""Web search tool — DuckDuckGo for shallow/quick search."""

from __future__ import annotations

import logging
import time
from typing import Any

from models.enums import ToolName
from models.schemas import ToolResult
from tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """DuckDuckGo-powered web search for quick information retrieval."""

    @property
    def name(self) -> str:
        return "web_search"

    async def run(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)
        start = time.monotonic()

        if not query:
            return ToolResult(
                tool=ToolName.WEB_SEARCH, success=False, error="No query provided"
            )

        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return ToolResult(
                    tool=ToolName.WEB_SEARCH,
                    success=True,
                    data="No results found.",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"{i}. **{r.get('title', 'No title')}**\n"
                    f"   {r.get('body', 'No snippet')}\n"
                    f"   Source: {r.get('href', 'N/A')}"
                )
            result_text = "\n\n".join(formatted)

            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                tool=ToolName.WEB_SEARCH,
                success=True,
                data=result_text,
                latency_ms=round(elapsed, 1),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning("Web search failed: %s", e)
            return ToolResult(
                tool=ToolName.WEB_SEARCH,
                success=False,
                error=str(e),
                latency_ms=round(elapsed, 1),
            )
