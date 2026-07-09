"""SessionMemory – session management with context window tracking,
message history, and compaction triggers.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────

class Message(BaseModel):
    """A message in a session."""
    model_config = ConfigDict(frozen=False)

    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    role: str = "user"  # user | assistant | system | tool
    content: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
    token_count: int = 0


class Session(BaseModel):
    """A conversation / interaction session."""
    model_config = ConfigDict(frozen=False)

    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    colony_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"  # active | compacted | archived | closed
    message_count: int = 0
    total_tokens: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompactionResult(BaseModel):
    """Result of a session compaction."""
    model_config = ConfigDict(frozen=False)

    session_id: str
    messages_compacted: int = 0
    tokens_compacted: int = 0
    summary: str = ""
    remaining_messages: int = 0
    compaction_ratio: float = 0.0


# ── Session Memory ───────────────────────────────────────────────

class SessionMemory:
    """Session management with context window tracking, message history,
    and automatic compaction triggers.

    Features
    --------
    * Session creation and loading
    * Context window tracking with token counting
    * Message history with role-based organization
    * Automatic compaction when context window fills
    * Multi-session support
    * Session archival
    """

    def __init__(
        self,
        context_window_tokens: int = 8192,
        compaction_threshold: float = 0.8,
        keep_recent_messages: int = 4,
        db_path: str = "~/.bh/sessions/sessions.db",
    ) -> None:
        self.context_window_tokens = context_window_tokens
        self.compaction_threshold = compaction_threshold
        self.keep_recent_messages = keep_recent_messages

        self._db_path = os.path.expanduser(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

        # Sessions
        self._sessions: Dict[str, Session] = {}
        self._messages: Dict[str, List[Message]] = {}  # session_id -> messages
        self._compaction_summaries: Dict[str, List[str]] = {}  # session_id -> summaries

        self._init_db()
        self._load_all()

    # ── SQLite persistence ────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                agent_id    TEXT NOT NULL DEFAULT '',
                colony_id   TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                last_active TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'active',
                message_count INTEGER NOT NULL DEFAULT 0,
                total_tokens  INTEGER NOT NULL DEFAULT 0,
                metadata    TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS messages (
                message_id  TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL REFERENCES sessions(session_id),
                role        TEXT NOT NULL,
                content     TEXT NOT NULL DEFAULT '',
                timestamp   TEXT NOT NULL,
                metadata    TEXT NOT NULL DEFAULT '{}',
                token_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_msgs_session ON messages(session_id);
            CREATE TABLE IF NOT EXISTS compaction_summaries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL REFERENCES sessions(session_id),
                summary     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_comp_session ON compaction_summaries(session_id);
        """)
        conn.commit()

    def _save_session_to_db(self, session: Session):
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO sessions
               (session_id, agent_id, colony_id, created_at, last_active, status, message_count, total_tokens, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session.session_id, session.agent_id, session.colony_id,
             session.created_at, session.last_active, session.status,
             session.message_count, session.total_tokens,
             json.dumps(session.metadata)),
        )
        conn.commit()

    def _save_messages_to_db(self, session_id: str, messages: List[Message]):
        conn = self._get_conn()
        for msg in messages:
            conn.execute(
                """INSERT OR REPLACE INTO messages
                   (message_id, session_id, role, content, timestamp, metadata, token_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (msg.message_id, session_id, msg.role, msg.content,
                 msg.timestamp, json.dumps(msg.metadata), msg.token_count),
            )
        conn.commit()

    def _save_summaries_to_db(self, session_id: str, summaries: List[str]):
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        for summary in summaries:
            conn.execute(
                "INSERT INTO compaction_summaries (session_id, summary, created_at) VALUES (?, ?, ?)",
                (session_id, summary, now),
            )
        conn.commit()

    def _load_all(self):
        conn = self._get_conn()

        rows = conn.execute("SELECT * FROM sessions").fetchall()
        for row in rows:
            session = Session(
                session_id=row["session_id"],
                agent_id=row["agent_id"],
                colony_id=row["colony_id"],
                created_at=row["created_at"],
                last_active=row["last_active"],
                status=row["status"],
                message_count=row["message_count"],
                total_tokens=row["total_tokens"],
                metadata=json.loads(row["metadata"]),
            )
            self._sessions[session.session_id] = session

        msg_rows = conn.execute("SELECT * FROM messages ORDER BY timestamp").fetchall()
        for row in msg_rows:
            msg = Message(
                message_id=row["message_id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]),
                token_count=row["token_count"],
            )
            self._messages.setdefault(row["session_id"], []).append(msg)

        comp_rows = conn.execute("SELECT * FROM compaction_summaries ORDER BY id").fetchall()
        for row in comp_rows:
            self._compaction_summaries.setdefault(row["session_id"], []).append(row["summary"])

        if len(self._sessions) > 0:
            logger.info("Loaded %d sessions, %d messages from %s", len(self._sessions), len(msg_rows), self._db_path)

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def create_session(
        self,
        agent_id: str = "",
        colony_id: str = "",
        metadata: Optional[Dict] = None,
    ) -> Session:
        """Create a new session."""
        session = Session(
            agent_id=agent_id,
            colony_id=colony_id,
            metadata=metadata or {},
        )
        self._sessions[session.session_id] = session
        self._messages[session.session_id] = []
        self._compaction_summaries[session.session_id] = []

        self._save_session_to_db(session)

        logger.info("Created session %s for agent %s", session.session_id, agent_id)
        return session

    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load an existing session."""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> bool:
        """Close a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.status = "closed"
        self._save_session_to_db(session)
        return True

    async def archive_session(self, session_id: str) -> bool:
        """Archive a session (compact and mark as archived)."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        await self.compact_session(session_id)

        session.status = "archived"
        self._save_session_to_db(session)
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Permanently delete a session."""
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        self._messages.pop(session_id, None)
        self._compaction_summaries.pop(session_id, None)
        conn = self._get_conn()
        conn.execute("DELETE FROM compaction_summaries WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        return True

    # ── Message management ───────────────────────────────────────

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        token_count: Optional[int] = None,
    ) -> Optional[Message]:
        """Add a message to a session.

        If adding the message would exceed the context window threshold,
        auto-compaction is triggered.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if session.status not in ("active", "compacted"):
            return None

        # Estimate token count
        if token_count is None:
            token_count = max(1, len(content) // 4)

        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
            token_count=token_count,
        )

        self._messages[session_id].append(message)

        self._save_messages_to_db(session_id, [message])

        session.message_count += 1
        session.total_tokens += token_count
        session.last_active = datetime.now(timezone.utc).isoformat()

        # Check compaction trigger
        usage_ratio = session.total_tokens / self.context_window_tokens
        if usage_ratio >= self.compaction_threshold:
            await self.compact_session(session_id)

        return message

    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        role: Optional[str] = None,
    ) -> List[Message]:
        """Get messages from a session."""
        messages = self._messages.get(session_id, [])

        if role:
            messages = [m for m in messages if m.role == role]

        if limit:
            messages = messages[-limit:]

        return messages

    async def get_context_window(self, session_id: str) -> Dict[str, Any]:
        """Get the current context window state for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        messages = self._messages.get(session_id, [])
        summaries = self._compaction_summaries.get(session_id, [])

        # Build context: summaries + recent messages
        context_parts = []
        for summary in summaries:
            context_parts.append({"role": "system", "content": f"[Previous context summary]: {summary}"})

        for msg in messages:
            context_parts.append({"role": msg.role, "content": msg.content})

        return {
            "session_id": session_id,
            "messages": len(messages),
            "total_tokens": session.total_tokens,
            "context_capacity": self.context_window_tokens,
            "usage_ratio": round(session.total_tokens / self.context_window_tokens, 3),
            "compaction_count": len(summaries),
            "context": context_parts,
        }

    # ── Compaction ───────────────────────────────────────────────

    async def compact_session(self, session_id: str) -> CompactionResult:
        """Compact a session's messages, keeping recent ones.

        Older messages are summarized and the summaries are stored.
        The most recent ``keep_recent_messages`` are kept in full.
        """
        session = self._sessions.get(session_id)
        messages = self._messages.get(session_id, [])

        if not session or not messages:
            return CompactionResult(session_id=session_id)

        # Determine split point
        keep_count = min(self.keep_recent_messages, len(messages))
        compact_messages = messages[:-keep_count] if keep_count < len(messages) else []
        keep_messages = messages[-keep_count:] if keep_count > 0 else messages

        if not compact_messages:
            return CompactionResult(session_id=session_id)

        # Generate summary
        summary = self._generate_compaction_summary(compact_messages)
        tokens_compacted = sum(m.token_count for m in compact_messages)

        # Store summary
        self._compaction_summaries[session_id].append(summary)
        self._save_summaries_to_db(session_id, [summary])

        self._messages[session_id] = keep_messages

        session.total_tokens -= tokens_compacted
        session.message_count = len(keep_messages)
        session.status = "compacted"

        self._save_session_to_db(session)

        compaction_ratio = tokens_compacted / max(1, tokens_compacted + session.total_tokens)

        result = CompactionResult(
            session_id=session_id,
            messages_compacted=len(compact_messages),
            tokens_compacted=tokens_compacted,
            summary=summary[:200],
            remaining_messages=len(keep_messages),
            compaction_ratio=round(compaction_ratio, 3),
        )

        logger.info(
            "Compacted session %s: %d messages -> summary (%d tokens freed)",
            session_id, len(compact_messages), tokens_compacted,
        )

        return result

    # ── Query / Search ───────────────────────────────────────────

    async def search_messages(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
    ) -> List[Message]:
        """Search messages in a session by content."""
        messages = self._messages.get(session_id, [])
        q = query.lower()

        results = []
        for msg in messages:
            if q in msg.content.lower():
                results.append(msg)

        return results[:limit]

    async def get_message_by_id(self, session_id: str, message_id: str) -> Optional[Message]:
        """Get a specific message by ID."""
        messages = self._messages.get(session_id, [])
        for msg in messages:
            if msg.message_id == message_id:
                return msg
        return None

    # ── Multi-session ────────────────────────────────────────────

    def list_sessions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List sessions with optional filters."""
        sessions = list(self._sessions.values())

        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        if status:
            sessions = [s for s in sessions if s.status == status]

        return [s.model_dump() for s in sessions]

    def get_active_sessions(self, agent_id: Optional[str] = None) -> List[Session]:
        """Get all active sessions."""
        sessions = [s for s in self._sessions.values() if s.status in ("active", "compacted")]
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        return sessions

    # ── Statistics ───────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate session statistics."""
        total_messages = sum(len(msgs) for msgs in self._messages.values())
        total_tokens = sum(s.total_tokens for s in self._sessions.values())

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": sum(1 for s in self._sessions.values() if s.status in ("active", "compacted")),
            "archived_sessions": sum(1 for s in self._sessions.values() if s.status == "archived"),
            "closed_sessions": sum(1 for s in self._sessions.values() if s.status == "closed"),
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "context_window_capacity": self.context_window_tokens,
            "compaction_threshold": self.compaction_threshold,
        }

    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        messages = self._messages.get(session_id, [])
        summaries = self._compaction_summaries.get(session_id, [])

        return {
            "session_id": session_id,
            "agent_id": session.agent_id,
            "status": session.status,
            "message_count": len(messages),
            "total_tokens": session.total_tokens,
            "compaction_count": len(summaries),
            "usage_ratio": round(session.total_tokens / self.context_window_tokens, 3),
            "created_at": session.created_at,
            "last_active": session.last_active,
            "roles": list(set(m.role for m in messages)),
        }

    # ── Internal helpers ─────────────────────────────────────────

    @staticmethod
    def _generate_compaction_summary(messages: List[Message]) -> str:
        """Generate a summary from a list of messages being compacted."""
        parts = []

        # Group by role
        by_role: Dict[str, List[str]] = {}
        for msg in messages:
            by_role.setdefault(msg.role, []).append(msg.content)

        for role, contents in by_role.items():
            # Take first 100 chars of each, up to 5 per role
            content_parts = [c[:100] for c in contents[:5]]
            parts.append(f"{role}: {'; '.join(content_parts)}")

        summary = " | ".join(parts)

        # Add stats
        summary += f" [{len(messages)} messages compacted]"

        return summary[:1024]
