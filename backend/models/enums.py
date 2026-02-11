"""Enumerations for the Adaptive Reasoning Agent."""

from enum import Enum


class NetworkTier(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class ReasoningMode(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"
    AUTO = "auto"


class ComplexityTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ToolName(str, Enum):
    WEB_SEARCH = "web_search"
    WEB_DEEP = "web_deep"
    RAG = "rag"
    DATETIME = "datetime"
    DOC_CREATE = "doc_create"


class WSMessageType(str, Enum):
    CHAT_MESSAGE = "chat_message"
    TOKEN = "token"
    REASONING_STEP = "reasoning_step"
    TOOL_CALL = "tool_call"
    DONE = "done"
    ERROR = "error"
