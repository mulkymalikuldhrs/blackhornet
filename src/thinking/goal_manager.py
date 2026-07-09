"""GoalManager — manage and track goals with states and progress.

Stores goals with states (active/paused/completed/abandoned), priority,
deadlines, dependencies, and progress tracking. Supports goal hierarchy
via parent-child relationships.
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
class Goal:
    id: int = 0
    title: str = ""
    description: str = ""
    state: str = "active"
    priority: int = 5
    category: str = ""
    deadline: Optional[float] = None
    parent_id: int = 0
    progress: float = 0.0
    dependencies: List[int] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    completed_at: Optional[float] = None


class GoalManager:
    """Manage goals with SQLite persistence."""

    def __init__(self, db_path: str = "~/.bh/initiative/goals.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT    NOT NULL DEFAULT '',
                state       TEXT    NOT NULL DEFAULT 'active',
                priority    INTEGER NOT NULL DEFAULT 5,
                category    TEXT    NOT NULL DEFAULT '',
                deadline    REAL,
                parent_id   INTEGER NOT NULL DEFAULT 0,
                progress    REAL    NOT NULL DEFAULT 0.0,
                dependencies TEXT   NOT NULL DEFAULT '[]',
                tags        TEXT    NOT NULL DEFAULT '[]',
                created_at  REAL    NOT NULL,
                updated_at  REAL    NOT NULL,
                completed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_goals_state ON goals(state);
            CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority DESC);
            CREATE INDEX IF NOT EXISTS idx_goals_category ON goals(category);
            CREATE INDEX IF NOT EXISTS idx_goals_parent ON goals(parent_id);
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

    def create(self, title: str, description: str = "", priority: int = 5,
               category: str = "", deadline: Optional[float] = None,
               parent_id: int = 0, dependencies: Optional[List[int]] = None,
               tags: Optional[List[str]] = None) -> int:
        now = time.time()
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO goals (title, description, state, priority, category, deadline, parent_id, progress, dependencies, tags, created_at, updated_at, completed_at) VALUES (?, ?, 'active', ?, ?, ?, ?, 0.0, ?, ?, ?, ?, NULL)",
            (title, description, priority, category, deadline, parent_id,
             json.dumps(dependencies or []), json.dumps(tags or []), now, now),
        )
        conn.commit()
        return cursor.lastrowid

    def get(self, goal_id: int) -> Optional[Goal]:
        row = self._get_conn().execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        return self._row_to_goal(row) if row else None

    def update_state(self, goal_id: int, state: str) -> bool:
        now = time.time()
        completed_at = now if state == "completed" else None
        cursor = self._get_conn().execute(
            "UPDATE goals SET state=?, updated_at=?, completed_at=? WHERE id=?",
            (state, now, completed_at, goal_id),
        )
        self._get_conn().commit()
        return cursor.rowcount > 0

    def update_progress(self, goal_id: int, progress: float) -> bool:
        cursor = self._get_conn().execute(
            "UPDATE goals SET progress=?, updated_at=? WHERE id=?",
            (max(0.0, min(1.0, progress)), time.time(), goal_id),
        )
        self._get_conn().commit()
        return cursor.rowcount > 0

    def get_active(self, limit: int = 20) -> List[Goal]:
        rows = self._get_conn().execute(
            "SELECT * FROM goals WHERE state = 'active' ORDER BY priority DESC, created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def get_by_state(self, state: str, limit: int = 20) -> List[Goal]:
        rows = self._get_conn().execute(
            "SELECT * FROM goals WHERE state = ? ORDER BY priority DESC, updated_at DESC LIMIT ?",
            (state, limit),
        ).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def get_children(self, parent_id: int) -> List[Goal]:
        rows = self._get_conn().execute(
            "SELECT * FROM goals WHERE parent_id = ? ORDER BY priority DESC", (parent_id,)
        ).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def get_overdue(self) -> List[Goal]:
        now = time.time()
        rows = self._get_conn().execute(
            "SELECT * FROM goals WHERE state = 'active' AND deadline IS NOT NULL AND deadline < ? ORDER BY deadline ASC",
            (now,),
        ).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def remove(self, goal_id: int) -> bool:
        cursor = self._get_conn().execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        self._get_conn().commit()
        return cursor.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        by_state = {r["state"]: r["cnt"] for r in conn.execute("SELECT state, COUNT(*) AS cnt FROM goals GROUP BY state").fetchall()}
        avg_progress = conn.execute("SELECT COALESCE(AVG(progress), 0.0) FROM goals WHERE state='active'").fetchone()[0]
        overdue = len(self.get_overdue())
        return {"total": total, "by_state": by_state, "avg_progress": round(avg_progress, 2),
                "overdue": overdue, "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_goal(self, row: sqlite3.Row) -> Goal:
        return Goal(
            id=row["id"], title=row["title"], description=row["description"],
            state=row["state"], priority=row["priority"], category=row["category"],
            deadline=row["deadline"], parent_id=row["parent_id"], progress=row["progress"],
            dependencies=json.loads(row["dependencies"]) if row["dependencies"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"], updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )
