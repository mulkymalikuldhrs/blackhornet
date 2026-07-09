"""TaskScheduler — schedule and prioritize tasks with time-aware planning.

Manages a task queue with scheduling, priority weighting, dependency
resolution, and time-aware execution planning. Integrates with
GoalManager for goal-derived tasks.
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
class Task:
    id: int = 0
    title: str = ""
    description: str = ""
    state: str = "pending"
    priority: int = 5
    task_type: str = ""
    goal_id: int = 0
    estimated_duration: float = 0.0
    scheduled_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    dependencies: List[int] = field(default_factory=list)
    result: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0


class TaskScheduler:
    """Schedule and manage tasks with SQLite persistence."""

    def __init__(self, db_path: str = "~/.bh/initiative/tasks.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                title            TEXT    NOT NULL,
                description      TEXT    NOT NULL DEFAULT '',
                state            TEXT    NOT NULL DEFAULT 'pending',
                priority         INTEGER NOT NULL DEFAULT 5,
                task_type        TEXT    NOT NULL DEFAULT '',
                goal_id          INTEGER NOT NULL DEFAULT 0,
                estimated_duration REAL  NOT NULL DEFAULT 0.0,
                scheduled_at     REAL,
                started_at       REAL,
                completed_at     REAL,
                dependencies     TEXT    NOT NULL DEFAULT '[]',
                result           TEXT    NOT NULL DEFAULT '',
                tags             TEXT    NOT NULL DEFAULT '[]',
                created_at       REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC);
            CREATE INDEX IF NOT EXISTS idx_tasks_scheduled ON tasks(scheduled_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_goal ON tasks(goal_id);
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

    def add(self, title: str, description: str = "", priority: int = 5,
            task_type: str = "", goal_id: int = 0, estimated_duration: float = 0.0,
            scheduled_at: Optional[float] = None,
            dependencies: Optional[List[int]] = None,
            tags: Optional[List[str]] = None) -> int:
        now = time.time()
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO tasks (title, description, state, priority, task_type, goal_id, estimated_duration, scheduled_at, dependencies, tags, created_at) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)",
            (title, description, priority, task_type, goal_id, estimated_duration,
             scheduled_at, json.dumps(dependencies or []), json.dumps(tags or []), now),
        )
        conn.commit()
        return cursor.lastrowid

    def get(self, task_id: int) -> Optional[Task]:
        row = self._get_conn().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def update_state(self, task_id: int, state: str, result: str = "") -> bool:
        now = time.time()
        conn = self._get_conn()
        if state == "in_progress":
            cursor = conn.execute(
                "UPDATE tasks SET state=?, result=?, started_at=COALESCE(started_at, ?) WHERE id=?",
                (state, result, now, task_id),
            )
        elif state == "completed":
            cursor = conn.execute(
                "UPDATE tasks SET state=?, result=?, completed_at=? WHERE id=?",
                (state, result, now, task_id),
            )
        else:
            cursor = conn.execute(
                "UPDATE tasks SET state=?, result=? WHERE id=?",
                (state, result, task_id),
            )
        conn.commit()
        return cursor.rowcount > 0

    def get_next(self, limit: int = 10) -> List[Task]:
        conn = self._get_conn()
        all_pending = conn.execute(
            "SELECT * FROM tasks WHERE state = 'pending' AND (scheduled_at IS NULL OR scheduled_at <= ?) ORDER BY priority DESC, created_at ASC",
            (time.time(),),
        ).fetchall()
        ready: List[Task] = []
        for row in all_pending:
            task = self._row_to_task(row)
            deps_met = all(
                conn.execute("SELECT state FROM tasks WHERE id = ?", (dep_id,)).fetchone()["state"] in ("completed", "skipped")
                for dep_id in task.dependencies
            ) if task.dependencies else True
            if deps_met:
                ready.append(task)
                if len(ready) >= limit:
                    break
        return ready

    def get_by_goal(self, goal_id: int) -> List[Task]:
        rows = self._get_conn().execute(
            "SELECT * FROM tasks WHERE goal_id = ? ORDER BY priority DESC", (goal_id,)
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get_by_state(self, state: str, limit: int = 20) -> List[Task]:
        rows = self._get_conn().execute(
            "SELECT * FROM tasks WHERE state = ? ORDER BY priority DESC, created_at DESC LIMIT ?",
            (state, limit),
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def remove(self, task_id: int) -> bool:
        cursor = self._get_conn().execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._get_conn().commit()
        return cursor.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        by_state = {r["state"]: r["cnt"] for r in conn.execute("SELECT state, COUNT(*) AS cnt FROM tasks GROUP BY state").fetchall()}
        pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE state='pending'").fetchone()[0]
        return {"total": total, "by_state": by_state, "pending": pending,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"], title=row["title"], description=row["description"],
            state=row["state"], priority=row["priority"], task_type=row["task_type"],
            goal_id=row["goal_id"], estimated_duration=row["estimated_duration"],
            scheduled_at=row["scheduled_at"], started_at=row["started_at"],
            completed_at=row["completed_at"],
            dependencies=json.loads(row["dependencies"]) if row["dependencies"] else [],
            result=row["result"], tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"],
        )
