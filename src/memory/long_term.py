"""Long-term memory – SQLite + FTS5 persistent memory store.

LTM provides durable, indexed storage backed by SQLite with full-text
search (FTS5). Entries are tagged, scored by importance, and tracked
for access frequency and recency. The database is auto-created on first
use.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LTMEntry:
    """A single long-term memory entry with metadata and access tracking."""

    id: int = 0
    key: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0
    importance: float = 0.5


class LongTermMemory:
    """SQLite + FTS5 persistent memory store.

    Schema
    ------
    * ``entries`` – primary table with key, content, tags (JSON),
      metadata (JSON), timestamps, access tracking, and importance.
    * ``entries_fts`` – FTS5 virtual table indexing *content* and
      *tags* for full-text search.

    The database file is created at ``db_path`` (default
    ``~/.bh/memory/long_term.db``) and the directory is created
    automatically if it does not exist.
    """

    def __init__(self, db_path: str = "~/.bh/memory/long_term.db") -> None:
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    # ── Database initialisation ────────────────────────────────────

    def _init_db(self) -> None:
        """Create tables and indexes if they do not already exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL DEFAULT 0,
                    accessed_at REAL NOT NULL DEFAULT 0,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    importance REAL NOT NULL DEFAULT 0.5
                )
            """)

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
                USING fts5(content, tags, content=entries, content_rowid=id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_importance
                ON entries(importance DESC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_created_at
                ON entries(created_at DESC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_accessed_at
                ON entries(accessed_at DESC)
            """)

            logger.debug("Database initialised at %s", self.db_path)

    # ── CRUD operations ────────────────────────────────────────────

    def add(
        self,
        key: str,
        content: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> int:
        """Insert a new entry and return its ID.

        Args:
            key: Unique key for the entry.
            content: The memory content.
            tags: Optional list of tag strings.
            metadata: Optional structured metadata.
            importance: Importance score (0.0 trivial – 1.0 critical).

        Returns:
            The auto-generated row ID.

        Raises:
            sqlite3.IntegrityError: If *key* already exists.
        """
        now = time.time()
        tags_json = json.dumps(tags or [])
        metadata_json = json.dumps(metadata or {})

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO entries (key, content, tags, metadata,
                                     created_at, accessed_at, access_count,
                                     importance)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (key, content, tags_json, metadata_json,
                 now, now, importance),
            )
            entry_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO entries_fts (rowid, content, tags) VALUES (?, ?, ?)",
                (entry_id, content, tags_json),
            )

        logger.debug("Added LTM entry %d (key=%s)", entry_id, key)
        return entry_id

    def get(self, key: str) -> Optional[LTMEntry]:
        """Retrieve an entry by key, updating its access time and count.

        Returns ``None`` if the key does not exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM entries WHERE key = ?", (key,)
            ).fetchone()

        if row is None:
            return None

        entry = self._row_to_entry(row)

        # Update access tracking
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE entries SET accessed_at = ?, access_count = ? WHERE id = ?",
                (time.time(), entry.access_count + 1, entry.id),
            )

        entry.accessed_at = time.time()
        entry.access_count += 1
        return entry

    def get_by_id(self, id: int) -> Optional[LTMEntry]:
        """Retrieve an entry by its integer ID.

        Returns ``None`` if the ID does not exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM entries WHERE id = ?", (id,)
            ).fetchone()

        if row is None:
            return None

        return self._row_to_entry(row)

    def search(self, query: str, limit: int = 20) -> list[LTMEntry]:
        """Full-text search using FTS5 MATCH.

        Searches across *content* and *tags* columns. Returns up to
        *limit* matching entries ordered by FTS5 relevance.
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT e.* FROM entries e
                JOIN entries_fts fts ON e.id = fts.rowid
                WHERE entries_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def search_by_tag(self, tag: str, limit: int = 20) -> list[LTMEntry]:
        """Search entries containing a specific tag.

        Tags are stored as a JSON array; the query uses ``LIKE`` for
        substring matching.
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM entries
                WHERE tags LIKE ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
                """,
                (f"%{tag}%", limit),
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def update(self, id: int, **kwargs: Any) -> None:
        """Update one or more fields of an entry by ID.

        Accepted keyword arguments: ``key``, ``content``, ``tags``,
        ``metadata``, ``importance``.
        """
        allowed = {"key", "content", "tags", "metadata", "importance"}
        updates: dict[str, Any] = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return

        # Serialise complex types
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        if "metadata" in updates and isinstance(updates["metadata"], dict):
            updates["metadata"] = json.dumps(updates["metadata"])

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [id]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE entries SET {set_clause} WHERE id = ?", values
            )

            # Keep FTS index in sync if content changed
            if "content" in updates or "tags" in updates:
                row = conn.execute(
                    "SELECT content, tags FROM entries WHERE id = ?", (id,)
                ).fetchone()
                if row:
                    conn.execute(
                        "DELETE FROM entries_fts WHERE rowid = ?", (id,)
                    )
                    conn.execute(
                        "INSERT INTO entries_fts (rowid, content, tags) VALUES (?, ?, ?)",
                        (id, row[0], row[1]),
                    )

        logger.debug("Updated LTM entry %d (fields=%s)", id, list(updates))

    def remove(self, key: str) -> bool:
        """Remove an entry by key.

        Returns ``True`` if the entry existed and was removed.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id FROM entries WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return False
            entry_id = row[0]
            conn.execute("DELETE FROM entries WHERE key = ?", (key,))
            conn.execute("DELETE FROM entries_fts WHERE rowid = ?", (entry_id,))
        return True

    def remove_by_id(self, id: int) -> bool:
        """Remove an entry by its integer ID.

        Returns ``True`` if the entry existed and was removed.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id FROM entries WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM entries WHERE id = ?", (id,))
            conn.execute("DELETE FROM entries_fts WHERE rowid = ?", (id,))
        return True

    # ── Listing / querying ────────────────────────────────────────

    def list_recent(self, limit: int = 20) -> list[LTMEntry]:
        """Return the most recently *created* entries."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM entries ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def list_by_importance(
        self, min_importance: float = 0.0, limit: int = 50
    ) -> list[LTMEntry]:
        """Return entries with importance at or above *min_importance*.

        Results are ordered by importance descending.
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM entries WHERE importance >= ? "
                "ORDER BY importance DESC LIMIT ?",
                (min_importance, limit),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def all_entries(self) -> list[LTMEntry]:
        """Return every entry in the store."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM entries ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def count(self) -> int:
        """Return the total number of entries."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM entries"
            ).fetchone()
        return row[0] if row else 0

    def stats(self) -> dict[str, Any]:
        """Return usage statistics for the long-term memory store."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            row = conn.execute(
                "SELECT AVG(importance), MIN(importance), MAX(importance), "
                "AVG(access_count), SUM(access_count) FROM entries"
            ).fetchone()
            tagged = conn.execute(
                "SELECT COUNT(*) FROM entries WHERE tags != '[]'"
            ).fetchone()[0]

        avg_imp = row[0] if row and row[0] is not None else 0.0
        min_imp = row[1] if row and row[1] is not None else 0.0
        max_imp = row[2] if row and row[2] is not None else 1.0
        avg_access = row[3] if row and row[3] is not None else 0.0
        total_access = row[4] if row and row[4] is not None else 0

        return {
            "db_path": self.db_path,
            "total_entries": total,
            "tagged_entries": tagged,
            "avg_importance": round(avg_imp, 3),
            "min_importance": round(min_imp, 3),
            "max_importance": round(max_imp, 3),
            "avg_access_count": round(avg_access, 1),
            "total_access_count": total_access,
        }

    # ── Internal helpers ───────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> LTMEntry:
        """Convert a SQLite result row to an ``LTMEntry``."""
        return LTMEntry(
            id=row[0],
            key=row[1],
            content=row[2],
            tags=json.loads(row[3]) if isinstance(row[3], str) else (row[3] or []),
            metadata=json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {}),
            created_at=row[5],
            accessed_at=row[6],
            access_count=row[7],
            importance=row[8],
        )
