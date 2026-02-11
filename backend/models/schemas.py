"""Pydantic schemas for request / response / internal data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from models.enums import (
    ComplexityTier,
    NetworkTier,
    ReasoningMode,
    ToolName,
    WSMessageType,
)


# ── Auth ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    username: str
    created_at: datetime


# ── Chat ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    session_id: str | None = None
    mode_override: ReasoningMode | None = None


class ChatMetadata(BaseModel):
    reasoning_mode: ReasoningMode
    network_tier: NetworkTier
    tools_used: list[ToolName] = []
    llm_calls: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0


class WSMessage(BaseModel):
    """Generic WebSocket message envelope."""
    type: WSMessageType
    content: str | None = None
    metadata: dict[str, Any] | None = None


# ── Internal: Network ─────────────────────────────────────────────────

class NetworkSnapshot(BaseModel):
    avg_latency_ms: float
    jitter_ms: float
    error_rate: float
    tier: NetworkTier


# ── Internal: Query Analysis ─────────────────────────────────────────

class ComplexityResult(BaseModel):
    tier: ComplexityTier
    score: float = Field(ge=0.0, le=1.0)
    signals: dict[str, float] = {}


# ── Internal: Reasoning Plan ─────────────────────────────────────────

class ToolCall(BaseModel):
    name: ToolName
    params: dict[str, Any] = {}
    priority: int = 0


class ReasoningPlan(BaseModel):
    mode: ReasoningMode
    intent: str = ""
    entities: list[str] = []
    tool_calls: list[ToolCall] = []
    sub_questions: list[str] | None = None
    synthesis_strategy: str | None = None


# ── Internal: Tool Result ────────────────────────────────────────────

class ToolResult(BaseModel):
    tool: ToolName
    success: bool
    data: Any = None
    latency_ms: float = 0.0
    error: str | None = None

    @classmethod
    def skipped(cls, tool: ToolName, reason: str) -> "ToolResult":
        return cls(tool=tool, success=False, data=None, error=reason)


# ── Documents ─────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentInfo
    message: str = "Document ingested successfully"
