"""FeedbackCollector — collect and store feedback from interactions.

Stores user and system feedback with ratings, categories, and context.
Supports aggregation, trend analysis, and integration with the
avoidance learner and skill extractor.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Feedback:
    id: int = 0
    source: str = ""
    category: str = ""
    rating: float = 0.0
    comment: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""
    session_id: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    resolved: bool = False


class FeedbackCollector:
    """Collect and store feedback from interactions."""

    def __init__(self, db_path: str = "~/.bh/thinking/feedback.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT    NOT NULL DEFAULT '',
                category    TEXT    NOT NULL DEFAULT '',
                rating      REAL    NOT NULL DEFAULT 0.0,
                comment     TEXT    NOT NULL DEFAULT '',
                context     TEXT    NOT NULL DEFAULT '{}',
                agent_id    TEXT    NOT NULL DEFAULT '',
                session_id  TEXT    NOT NULL DEFAULT '',
                tags        TEXT    NOT NULL DEFAULT '[]',
                created_at  REAL    NOT NULL,
                resolved    INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_fb_source ON feedback(source);
            CREATE INDEX IF NOT EXISTS idx_fb_category ON feedback(category);
            CREATE INDEX IF NOT EXISTS idx_fb_agent ON feedback(agent_id);
            CREATE INDEX IF NOT EXISTS idx_fb_rating ON feedback(rating DESC);
            CREATE INDEX IF NOT EXISTS idx_fb_resolved ON feedback(resolved);
        """)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def add(self, source: str, category: str, rating: float, comment: str = "",
            context: Optional[Dict[str, Any]] = None, agent_id: str = "",
            session_id: str = "", tags: Optional[List[str]] = None) -> int:
        ctx = context or {}
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO feedback (source, category, rating, comment, context, agent_id, session_id, tags, created_at, resolved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (source, category, rating, comment, json.dumps(ctx), agent_id, session_id, json.dumps(tags or []), time.time()),
        )
        conn.commit()
        return cursor.lastrowid

    def get(self, fb_id: int) -> Optional[Feedback]:
        row = self._get_conn().execute("SELECT * FROM feedback WHERE id = ?", (fb_id,)).fetchone()
        return self._row_to_fb(row) if row else None

    def search(self, query: str, limit: int = 20) -> List[Feedback]:
        rows = self._get_conn().execute(
            "SELECT * FROM feedback WHERE comment LIKE ? OR category LIKE ? OR source LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_fb(r) for r in rows]

    def get_by_category(self, category: str, limit: int = 20) -> List[Feedback]:
        rows = self._get_conn().execute(
            "SELECT * FROM feedback WHERE category = ? ORDER BY created_at DESC LIMIT ?", (category, limit),
        ).fetchall()
        return [self._row_to_fb(r) for r in rows]

    def get_by_source(self, source: str, limit: int = 20) -> List[Feedback]:
        rows = self._get_conn().execute(
            "SELECT * FROM feedback WHERE source = ? ORDER BY created_at DESC LIMIT ?", (source, limit),
        ).fetchall()
        return [self._row_to_fb(r) for r in rows]

    def get_recent(self, limit: int = 20) -> List[Feedback]:
        rows = self._get_conn().execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_fb(r) for r in rows]

    def get_unresolved(self) -> List[Feedback]:
        rows = self._get_conn().execute("SELECT * FROM feedback WHERE resolved = 0 ORDER BY created_at DESC").fetchall()
        return [self._row_to_fb(r) for r in rows]

    def resolve(self, fb_id: int) -> bool:
        cursor = self._get_conn().execute("UPDATE feedback SET resolved = 1 WHERE id = ?", (fb_id,))
        self._get_conn().commit()
        return cursor.rowcount > 0

    def ratings_summary(self) -> Dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        if total == 0:
            return {"total": 0, "avg_rating": 0.0, "by_category": {}, "by_source": {}}
        avg = conn.execute("SELECT AVG(rating) FROM feedback").fetchone()[0]
        by_cat = {r["category"]: {"count": r["cnt"], "avg": round(r["avg"], 2)}
                  for r in conn.execute("SELECT category, COUNT(*) AS cnt, AVG(rating) AS avg FROM feedback GROUP BY category").fetchall()}
        by_src = {r["source"]: {"count": r["cnt"], "avg": round(r["avg"], 2)}
                  for r in conn.execute("SELECT source, COUNT(*) AS cnt, AVG(rating) AS avg FROM feedback GROUP BY source").fetchall()}
        return {"total": total, "avg_rating": round(avg, 2), "by_category": by_cat, "by_source": by_src,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_fb(self, row: sqlite3.Row) -> Feedback:
        return Feedback(
            id=row["id"], source=row["source"], category=row["category"],
            rating=row["rating"], comment=row["comment"],
            context=json.loads(row["context"]) if row["context"] else {},
            agent_id=row["agent_id"], session_id=row["session_id"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"], resolved=bool(row["resolved"]),
        )
