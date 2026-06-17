"""SkillExtractor — extract reusable skills from successful task executions.

Analyzes successful CoT paths, feedback, and episodes to identify
patterns that can be extracted as reusable skills. Skills are stored
with preconditions, steps, expected outcomes, and metadata.
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
class Skill:
    id: int = 0
    name: str = ""
    description: str = ""
    category: str = ""
    steps: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    source_cot_ids: List[int] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    use_count: int = 0
    success_rate: float = 0.0
    created_at: float = 0.0
    updated_at: float = 0.0


class SkillExtractor:
    """Extract and manage reusable skills."""

    def __init__(self, db_path: str = "~/.bh/thinking/skills.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT    NOT NULL UNIQUE,
                description     TEXT    NOT NULL DEFAULT '',
                category        TEXT    NOT NULL DEFAULT '',
                steps           TEXT    NOT NULL DEFAULT '[]',
                preconditions   TEXT    NOT NULL DEFAULT '[]',
                expected_outcome TEXT   NOT NULL DEFAULT '',
                source_cot_ids  TEXT    NOT NULL DEFAULT '[]',
                tags            TEXT    NOT NULL DEFAULT '[]',
                confidence      REAL    NOT NULL DEFAULT 0.0,
                use_count       INTEGER NOT NULL DEFAULT 0,
                success_rate    REAL    NOT NULL DEFAULT 0.0,
                created_at      REAL    NOT NULL,
                updated_at      REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
            CREATE INDEX IF NOT EXISTS idx_skills_confidence ON skills(confidence DESC);
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

    def add(self, name: str, description: str = "", category: str = "",
            steps: Optional[List[str]] = None, preconditions: Optional[List[str]] = None,
            expected_outcome: str = "", source_cot_ids: Optional[List[int]] = None,
            tags: Optional[List[str]] = None, confidence: float = 0.5) -> int:
        now = time.time()
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO skills (name, description, category, steps, preconditions, expected_outcome, source_cot_ids, tags, confidence, use_count, success_rate, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0.0, ?, ?)""",
                (name, description, category, json.dumps(steps or []), json.dumps(preconditions or []),
                 expected_outcome, json.dumps(source_cot_ids or []), json.dumps(tags or []),
                 confidence, now, now),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            existing = self.get_by_name(name)
            if existing:
                return existing.id
            raise

    def get(self, skill_id: int) -> Optional[Skill]:
        row = self._get_conn().execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        return self._row_to_skill(row) if row else None

    def get_by_name(self, name: str) -> Optional[Skill]:
        row = self._get_conn().execute("SELECT * FROM skills WHERE name = ?", (name,)).fetchone()
        return self._row_to_skill(row) if row else None

    def search(self, query: str, limit: int = 20) -> List[Skill]:
        rows = self._get_conn().execute(
            "SELECT * FROM skills WHERE name LIKE ? OR description LIKE ? OR category LIKE ? ORDER BY confidence DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def search_similar(self, description: str, threshold: float = 0.2, limit: int = 10) -> List[Skill]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM skills").fetchall()
        scored: list[tuple[float, Skill]] = []
        for row in rows:
            skill = self._row_to_skill(row)
            sim = ngram_similarity(description, f"{skill.name} {skill.description}", n=3)
            combined = sim * 0.6 + skill.confidence * 0.4
            if combined >= threshold:
                scored.append((combined, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    def record_usage(self, skill_id: int, success: bool) -> None:
        now = time.time()
        conn = self._get_conn()
        conn.execute(
            "UPDATE skills SET use_count = use_count + 1, updated_at = ? WHERE id = ?",
            (now, skill_id),
        )
        skill = self.get(skill_id)
        if skill:
            rate = ((skill.success_rate * skill.use_count) + (1.0 if success else 0.0)) / (skill.use_count + 1)
            conn.execute("UPDATE skills SET success_rate = ? WHERE id = ?", (rate, skill_id))
        conn.commit()

    def get_top_skills(self, limit: int = 20) -> List[Skill]:
        rows = self._get_conn().execute(
            "SELECT * FROM skills ORDER BY confidence * 0.4 + success_rate * 0.3 + use_count * 0.3 DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def remove(self, skill_id: int) -> bool:
        cursor = self._get_conn().execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        self._get_conn().commit()
        return cursor.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        by_cat = {r["category"]: r["cnt"] for r in conn.execute("SELECT category, COUNT(*) AS cnt FROM skills WHERE category != '' GROUP BY category").fetchall()}
        avg_conf = conn.execute("SELECT COALESCE(AVG(confidence), 0.0) FROM skills").fetchone()[0]
        avg_sr = conn.execute("SELECT COALESCE(AVG(success_rate), 0.0) FROM skills").fetchone()[0]
        total_uses = conn.execute("SELECT COALESCE(SUM(use_count), 0) FROM skills").fetchone()[0]
        return {"total": total, "by_category": by_cat, "avg_confidence": round(avg_conf, 3),
                "avg_success_rate": round(avg_sr, 3), "total_uses": total_uses,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_skill(self, row: sqlite3.Row) -> Skill:
        return Skill(
            id=row["id"], name=row["name"], description=row["description"],
            category=row["category"], steps=json.loads(row["steps"]) if row["steps"] else [],
            preconditions=json.loads(row["preconditions"]) if row["preconditions"] else [],
            expected_outcome=row["expected_outcome"],
            source_cot_ids=json.loads(row["source_cot_ids"]) if row["source_cot_ids"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            confidence=row["confidence"], use_count=row["use_count"],
            success_rate=row["success_rate"], created_at=row["created_at"], updated_at=row["updated_at"],
        )
