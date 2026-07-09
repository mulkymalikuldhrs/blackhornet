"""CoTRetrieval — chain-of-thought reasoning path store and retrieval.

Stores reasoning traces (chains of thought) from problem-solving
episodes, indexed by problem type, outcome, and semantic content.
Supports retrieval of similar reasoning paths for few-shot prompts.
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

from src.memory.semantic import ngram_similarity

logger = logging.getLogger(__name__)


@dataclass
class CoTPath:
    id: int = 0
    problem: str = ""
    steps: List[str] = field(default_factory=list)
    reasoning: str = ""
    solution: str = ""
    outcome: str = ""
    problem_type: str = ""
    tags: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    created_at: float = 0.0
    accessed_at: float = 0.0
    use_count: int = 0


class CoTRetrieval:
    """Chain-of-thought reasoning path store and retriever."""

    def __init__(self, db_path: str = "~/.bh/thinking/cot.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cot_paths (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                problem         TEXT    NOT NULL,
                steps           TEXT    NOT NULL DEFAULT '[]',
                reasoning       TEXT    NOT NULL DEFAULT '',
                solution        TEXT    NOT NULL DEFAULT '',
                outcome         TEXT    NOT NULL DEFAULT '',
                problem_type    TEXT    NOT NULL DEFAULT '',
                tags            TEXT    NOT NULL DEFAULT '[]',
                quality_score   REAL    NOT NULL DEFAULT 0.0,
                created_at      REAL    NOT NULL,
                accessed_at     REAL    NOT NULL,
                use_count       INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_cot_outcome ON cot_paths(outcome);
            CREATE INDEX IF NOT EXISTS idx_cot_type ON cot_paths(problem_type);
            CREATE INDEX IF NOT EXISTS idx_cot_quality ON cot_paths(quality_score DESC);

            CREATE VIRTUAL TABLE IF NOT EXISTS cot_fts USING fts5(problem, reasoning, solution, content=cot_paths, content_rowid=id);

            CREATE TRIGGER IF NOT EXISTS cot_ai AFTER INSERT ON cot_paths BEGIN
                INSERT INTO cot_fts(rowid, problem, reasoning, solution) VALUES (new.id, new.problem, new.reasoning, new.solution);
            END;
            CREATE TRIGGER IF NOT EXISTS cot_ad AFTER DELETE ON cot_paths BEGIN
                INSERT INTO cot_fts(cot_fts, rowid, problem, reasoning, solution) VALUES ('delete', old.id, old.problem, old.reasoning, old.solution);
            END;
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

    def store(self, problem: str, steps: List[str], reasoning: str, solution: str,
              outcome: str = "success", problem_type: str = "", tags: Optional[List[str]] = None,
              quality_score: float = 0.5) -> int:
        now = time.time()
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO cot_paths (problem, steps, reasoning, solution, outcome, problem_type, tags, quality_score, created_at, accessed_at, use_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (problem, json.dumps(steps), reasoning, solution, outcome, problem_type,
             json.dumps(tags or []), quality_score, now, now),
        )
        conn.commit()
        return cursor.lastrowid

    def get(self, path_id: int) -> Optional[CoTPath]:
        row = self._get_conn().execute("SELECT * FROM cot_paths WHERE id = ?", (path_id,)).fetchone()
        if row is None:
            return None
        self._get_conn().execute("UPDATE cot_paths SET use_count = use_count + 1, accessed_at = ? WHERE id = ?",
                                (time.time(), path_id))
        self._get_conn().commit()
        return self._row_to_path(row)

    def search(self, query: str, limit: int = 10) -> List[CoTPath]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT c.* FROM cot_fts JOIN cot_paths c ON c.id = cot_fts.rowid
                   WHERE cot_fts MATCH ? ORDER BY rank LIMIT ?""",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute(
                "SELECT * FROM cot_paths WHERE problem LIKE ? OR reasoning LIKE ? OR solution LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [self._row_to_path(r) for r in rows]

    def search_similar(self, problem: str, threshold: float = 0.2, limit: int = 5) -> List[CoTPath]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM cot_paths").fetchall()
        scored: list[tuple[float, CoTPath]] = []
        for row in rows:
            path = self._row_to_path(row)
            sim = ngram_similarity(problem, path.problem, n=3)
            combined = sim * 0.7 + path.quality_score * 0.3
            if combined >= threshold:
                scored.append((combined, path))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def get_by_outcome(self, outcome: str, limit: int = 20) -> List[CoTPath]:
        rows = self._get_conn().execute(
            "SELECT * FROM cot_paths WHERE outcome = ? ORDER BY quality_score DESC LIMIT ?",
            (outcome, limit),
        ).fetchall()
        return [self._row_to_path(r) for r in rows]

    def get_by_type(self, problem_type: str, limit: int = 20) -> List[CoTPath]:
        rows = self._get_conn().execute(
            "SELECT * FROM cot_paths WHERE problem_type = ? ORDER BY quality_score DESC LIMIT ?",
            (problem_type, limit),
        ).fetchall()
        return [self._row_to_path(r) for r in rows]

    def remove(self, path_id: int) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM cot_paths WHERE id = ?", (path_id,))
        conn.commit()
        return cursor.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM cot_paths").fetchone()[0]
        by_outcome = {r["outcome"]: r["cnt"] for r in conn.execute("SELECT outcome, COUNT(*) AS cnt FROM cot_paths GROUP BY outcome").fetchall()}
        avg_quality = conn.execute("SELECT COALESCE(AVG(quality_score), 0.0) FROM cot_paths").fetchone()[0]
        return {"total": total, "by_outcome": by_outcome, "avg_quality": round(avg_quality, 3),
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_path(self, row: sqlite3.Row) -> CoTPath:
        return CoTPath(
            id=row["id"], problem=row["problem"], steps=json.loads(row["steps"]) if row["steps"] else [],
            reasoning=row["reasoning"], solution=row["solution"], outcome=row["outcome"],
            problem_type=row["problem_type"], tags=json.loads(row["tags"]) if row["tags"] else [],
            quality_score=row["quality_score"], created_at=row["created_at"],
            accessed_at=row["accessed_at"], use_count=row["use_count"],
        )
