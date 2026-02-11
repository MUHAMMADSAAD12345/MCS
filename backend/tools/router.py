"""Tool router — dispatches tool calls with mode-aware constraints."""

from __future__ import annotations

import logging
from typing import Any

from models.enums import ToolName
from models.schemas import ToolResult
from tools.base import BaseTool
from tools.datetime_tool import DateTimeTool
from tools.doc_generator import DocumentGeneratorTool
from tools.web_deep import DeepWebSearchTool
from tools.web_search import WebSearchTool

logger = logging.getLogger(__name__)


# Tool spec: which modes allow which tools, and how many calls each
_TOOL_SPECS: dict[str, dict[str, Any]] = {
    "web_search": {
        "allowed_modes": ["standard", "deep"],
        "max_calls": {"standard": 1, "deep": 3},
    },
    "web_deep": {
        "allowed_modes": ["deep"],
        "max_calls": {"deep": 2},
    },
    "rag": {
        "allowed_modes": ["fast", "standard", "deep"],
        "max_calls": {"fast": 1, "standard": 1, "deep": 4},
    },
    "datetime": {
        "allowed_modes": ["fast", "standard", "deep"],
        "max_calls": {"fast": 1, "standard": 1, "deep": 1},
    },
    "doc_create": {
        "allowed_modes": ["standard", "deep"],
        "max_calls": {"standard": 1, "deep": 1},
    },
}


class ToolRouter:
    """Routes and executes tool calls with mode-aware constraints."""

    def __init__(self, rag_retriever: Any = None) -> None:
        self._tools: dict[str, BaseTool] = {
            "web_search": WebSearchTool(),
            "web_deep": DeepWebSearchTool(),
            "datetime": DateTimeTool(),
            "doc_create": DocumentGeneratorTool(),
        }
        self._rag_retriever = rag_retriever
        self._call_counts: dict[str, int] = {}

    def reset_counts(self) -> None:
        """Reset call counters for a new request."""
        self._call_counts.clear()

    async def execute(self, tool_name: str, params: dict, mode: str) -> ToolResult:
        """Execute a tool through mode-aware constraints."""
        spec = _TOOL_SPECS.get(tool_name)
        if not spec:
            return ToolResult.skipped(
                ToolName(tool_name) if tool_name in ToolName.__members__.values() else ToolName.WEB_SEARCH,
                f"Unknown tool: {tool_name}",
            )

        # Check if tool is allowed in this mode
        if mode not in spec["allowed_modes"]:
            logger.debug("Tool %s skipped — not allowed in %s mode", tool_name, mode)
            return ToolResult.skipped(
                self._to_enum(tool_name),
                f"{tool_name} not available in {mode} mode",
            )

        # Check call count limit
        max_calls = spec["max_calls"].get(mode, 1)
        current = self._call_counts.get(tool_name, 0)
        if current >= max_calls:
            logger.debug(
                "Tool %s skipped — max %d calls in %s mode reached",
                tool_name, max_calls, mode,
            )
            return ToolResult.skipped(
                self._to_enum(tool_name),
                f"{tool_name} call limit ({max_calls}) reached in {mode} mode",
            )

        # Handle RAG specially (not a BaseTool, uses retriever)
        if tool_name == "rag":
            return await self._execute_rag(params)

        # Execute the tool
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult.skipped(self._to_enum(tool_name), f"Tool {tool_name} not initialized")

        self._call_counts[tool_name] = current + 1
        result = await tool.run(**params)
        return result

    async def execute_batch(
        self, tool_calls: list[dict], mode: str
    ) -> list[ToolResult]:
        """Execute multiple tool calls. For simplicity, run sequentially."""
        results = []
        for tc in tool_calls:
            result = await self.execute(tc["name"], tc.get("params", {}), mode)
            results.append(result)
        return results

    async def _execute_rag(self, params: dict) -> ToolResult:
        """Execute RAG retrieval tool."""
        if not self._rag_retriever:
            return ToolResult.skipped(ToolName.RAG, "RAG pipeline not initialized")

        try:
            query = params.get("query", "")
            user_id = params.get("user_id", "")
            top_k = params.get("top_k", 5)

            chunks = await self._rag_retriever.retrieve(
                query=query, user_id=user_id, top_k=top_k
            )
            if not chunks:
                return ToolResult(
                    tool=ToolName.RAG,
                    success=True,
                    data="",
                    latency_ms=0.0,
                )

            # Format chunks into context string
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                source = chunk.get("source", "unknown")
                text = chunk.get("text", "")
                context_parts.append(f"[Source {i}: {source}]\n{text}")

            context = "\n\n".join(context_parts)
            self._call_counts["rag"] = self._call_counts.get("rag", 0) + 1

            return ToolResult(
                tool=ToolName.RAG,
                success=True,
                data=context,
                latency_ms=0.0,
            )
        except Exception as e:
            logger.warning("RAG retrieval failed: %s", e)
            return ToolResult(tool=ToolName.RAG, success=False, error=str(e))

    @staticmethod
    def _to_enum(name: str) -> ToolName:
        mapping = {
            "web_search": ToolName.WEB_SEARCH,
            "web_deep": ToolName.WEB_DEEP,
            "rag": ToolName.RAG,
            "datetime": ToolName.DATETIME,
            "doc_create": ToolName.DOC_CREATE,
        }
        return mapping.get(name, ToolName.WEB_SEARCH)
