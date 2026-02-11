"""DateTime tool — returns current date/time information."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.enums import ToolName
from models.schemas import ToolResult
from tools.base import BaseTool


class DateTimeTool(BaseTool):
    """Provides current date, time, and timezone info. Zero network cost."""

    @property
    def name(self) -> str:
        return "datetime"

    async def run(self, **kwargs: Any) -> ToolResult:
        now = datetime.now(timezone.utc)
        info = (
            f"Current UTC date/time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"Day of week: {now.strftime('%A')}\n"
            f"ISO format: {now.isoformat()}"
        )
        return ToolResult(tool=ToolName.DATETIME, success=True, data=info, latency_ms=0.0)
