"""Deep web search tool — Tavily for thorough research (optional)."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from config import settings
from models.enums import ToolName
from models.schemas import ToolResult
from tools.base import BaseTool

logger = logging.getLogger(__name__)


class DeepWebSearchTool(BaseTool):
    """Tavily-powered deep search for comprehensive research results."""

    @property
    def name(self) -> str:
        return "web_deep"

    async def run(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        start = time.monotonic()

        if not query:
            return ToolResult(
                tool=ToolName.WEB_DEEP, success=False, error="No query provided"
            )

        if not settings.TAVILY_API_KEY:
            # Fallback to DuckDuckGo if Tavily key not available
            logger.info("No Tavily API key — falling back to DuckDuckGo for deep search")
            from tools.web_search import WebSearchTool
            fallback = WebSearchTool()
            result = await fallback.run(query=query, max_results=8)
            result.tool = ToolName.WEB_DEEP
            return result

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "search_depth": "advanced",
                        "max_results": 5,
                        "include_answer": True,
                    },
                )
                response.raise_for_status()
                data = response.json()

            parts = []
            if data.get("answer"):
                parts.append(f"**Summary:** {data['answer']}")

            for i, r in enumerate(data.get("results", []), 1):
                parts.append(
                    f"{i}. **{r.get('title', 'No title')}**\n"
                    f"   {r.get('content', 'No content')}\n"
                    f"   Source: {r.get('url', 'N/A')}"
                )

            result_text = "\n\n".join(parts) if parts else "No results found."
            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                tool=ToolName.WEB_DEEP,
                success=True,
                data=result_text,
                latency_ms=round(elapsed, 1),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning("Deep web search failed: %s", e)
            return ToolResult(
                tool=ToolName.WEB_DEEP,
                success=False,
                error=str(e),
                latency_ms=round(elapsed, 1),
            )
