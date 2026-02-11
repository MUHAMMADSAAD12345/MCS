"""Chat API — WebSocket (streaming) + REST fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from auth.jwt_handler import decode_token
from auth.middleware import get_current_user
from core.agent import Agent
from models.enums import ReasoningMode
from models.schemas import ChatRequest
from services.session_store import (
    add_message,
    get_messages,
    get_or_create_session,
    get_user_sessions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Will be set by main.py after app startup
_agent: Agent | None = None


def set_agent(agent: Agent) -> None:
    global _agent
    _agent = agent


def get_agent() -> Agent:
    if _agent is None:
        raise RuntimeError("Agent not initialized")
    return _agent


# ── WebSocket endpoint (primary — streaming) ─────────────────────────

@router.websocket("/ws")
async def chat_websocket(ws: WebSocket):
    """
    Main chat endpoint with token-level streaming.

    Client sends: {"type": "chat_message", "content": "...", "session_id": "...", "mode_override": null, "token": "..."}
    Server sends: {"type": "token|reasoning_step|tool_call|done|error", ...}
    """
    await ws.accept()

    # Authenticate from first message or query param
    user: dict | None = None
    token = ws.query_params.get("token")
    if token:
        payload = decode_token(token)
        if payload:
            from services.session_store import get_user_by_id
            user = await get_user_by_id(payload.get("sub", ""))

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            # Handle auth in message if not yet authenticated
            if not user and msg.get("token"):
                payload = decode_token(msg["token"])
                if payload:
                    from services.session_store import get_user_by_id
                    user = await get_user_by_id(payload.get("sub", ""))

            if msg.get("type") != "chat_message":
                continue

            content = msg.get("content", "").strip()
            if not content:
                await ws.send_json({"type": "error", "content": "Empty message"})
                continue

            user_id = user["id"] if user else "anonymous"
            session_id = msg.get("session_id")

            # Get or create session
            session_id = await get_or_create_session(user_id, session_id)

            # Get chat history
            chat_history = await get_messages(session_id, limit=10)

            # Save user message
            await add_message(session_id, "user", content)

            # Parse mode override
            mode_override = None
            if msg.get("mode_override"):
                try:
                    mode_override = ReasoningMode(msg["mode_override"])
                except ValueError:
                    pass

            # Process through agent
            agent = get_agent()
            full_response = ""

            async for event in agent.process(
                content,
                user_id=user_id,
                chat_history=chat_history,
                mode_override=mode_override,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    full_response += event.get("content", "")

                if event_type == "done":
                    full_response = event.get("content", full_response)

                # Send event to client
                await ws.send_json(event)

            # Save assistant response
            if full_response:
                await add_message(session_id, "assistant", full_response)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await ws.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass


# ── REST fallback (non-streaming) ────────────────────────────────────

@router.post("/send")
async def chat_rest(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """Non-streaming chat endpoint (fallback)."""
    session_id = await get_or_create_session(user["id"], req.session_id)
    chat_history = await get_messages(session_id, limit=10)
    await add_message(session_id, "user", req.content)

    agent = get_agent()
    full_response = ""
    final_metadata: dict[str, Any] = {}

    async for event in agent.process(
        req.content,
        user_id=user["id"],
        chat_history=chat_history,
        mode_override=req.mode_override,
    ):
        if event.get("type") == "token":
            full_response += event.get("content", "")
        elif event.get("type") == "done":
            full_response = event.get("content", full_response)
            final_metadata = event.get("metadata", {})
        elif event.get("type") == "error":
            full_response = event.get("content", "An error occurred")
            final_metadata = event.get("metadata", {})

    await add_message(session_id, "assistant", full_response)

    return {
        "content": full_response,
        "session_id": session_id,
        "metadata": final_metadata,
    }


# ── Session history endpoints ─────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    """List all chat sessions for the current user."""
    sessions = await get_user_sessions(user["id"])
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Get messages for a specific session."""
    messages = await get_messages(session_id, limit=100)
    return {"messages": messages, "session_id": session_id}
