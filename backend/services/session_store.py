"""SQLite-backed persistent session / chat history store."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import aiosqlite

from config import settings

_DB_PATH = str(settings.SQLITE_DB_PATH)

# ── Schema ────────────────────────────────────────────────────────────

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    filename    TEXT NOT NULL,
    file_type   TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


async def init_db() -> None:
    """Create tables if they don't exist."""
    settings.ensure_dirs()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(_INIT_SQL)
        await db.commit()


# ── Users ─────────────────────────────────────────────────────────────

async def create_user(username: str, hashed_password: str) -> dict:
    uid = str(uuid.uuid4())
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
            (uid, username, hashed_password),
        )
        await db.commit()
    return {"id": uid, "username": username, "created_at": datetime.utcnow().isoformat()}


async def get_user_by_username(username: str) -> dict | None:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, password, created_at FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_id(user_id: str) -> dict | None:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, password, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ── Sessions ──────────────────────────────────────────────────────────

async def get_or_create_session(user_id: str, session_id: str | None = None) -> str:
    """Return existing session_id or create a new one."""
    async with aiosqlite.connect(_DB_PATH) as db:
        if session_id:
            cursor = await db.execute(
                "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
            if await cursor.fetchone():
                return session_id

        new_id = session_id or str(uuid.uuid4())
        await db.execute(
            "INSERT INTO sessions (id, user_id) VALUES (?, ?)",
            (new_id, user_id),
        )
        await db.commit()
        return new_id


# ── Messages ──────────────────────────────────────────────────────────

async def add_message(
    session_id: str, role: str, content: str, metadata: dict | None = None
) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (session_id, role, content, metadata) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps(metadata) if metadata else None),
        )
        await db.commit()


async def get_messages(session_id: str, limit: int = 10) -> list[dict]:
    """Get the last *limit* messages for a session, oldest first."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT role, content, metadata, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = [dict(r) for r in await cursor.fetchall()]
        rows.reverse()
        for r in rows:
            if r.get("metadata"):
                r["metadata"] = json.loads(r["metadata"])
        return rows


# ── Documents Tracking ────────────────────────────────────────────────

async def add_document_record(
    doc_id: str,
    user_id: str,
    filename: str,
    file_type: str,
    chunk_count: int,
) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """INSERT INTO documents (id, user_id, filename, file_type, chunk_count)
               VALUES (?, ?, ?, ?, ?)""",
            (doc_id, user_id, filename, file_type, chunk_count),
        )
        await db.commit()


async def get_user_documents(user_id: str) -> list[dict]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, filename, file_type, chunk_count, uploaded_at FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC",
            (user_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def delete_document_record(doc_id: str, user_id: str) -> bool:
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?",
            (doc_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


# ── Session listing ───────────────────────────────────────────────────

async def get_user_sessions(user_id: str, limit: int = 20) -> list[dict]:
    """Get all sessions for a user, newest first, with first message preview."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT s.id, s.created_at,
                   (SELECT content FROM messages m
                    WHERE m.session_id = s.id AND m.role = 'user'
                    ORDER BY m.id ASC LIMIT 1) as preview,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) as message_count
            FROM sessions s
            WHERE s.user_id = ?
            ORDER BY s.created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = [dict(r) for r in await cursor.fetchall()]
        return rows
