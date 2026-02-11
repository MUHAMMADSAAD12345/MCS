"""Abstract base for all tools."""

from __future__ import annotations

import abc
from typing import Any

from models.schemas import ToolResult


class BaseTool(abc.ABC):
    """Interface for agent tools."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        ...
