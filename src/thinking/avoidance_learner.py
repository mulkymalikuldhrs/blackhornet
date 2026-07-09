"""AvoidanceLearner — learn what to avoid based on failures and errors.

Tracks failure patterns, error types, and negative feedback to build
an avoidance knowledge base. Provides queries for what to avoid in
given contexts, integrating with FeedbackCollector and CoTRetrieval.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.memory.semantic import ngram_similarity

logger = logging.getLogger(__name__)


@dataclass
class AvoidanceRule:
    id: int = 0
    pattern: str = ""
    description: str = ""
    category: str = ""
    severity: str = "medium"
    trigger_context: List[str] = field(default_factory=list)
    safe_alternative: str = ""
    failure_count: int = 0
    source_feedback_ids: List[int] = field(default_factory=list)
    source_cot_ids: List[int] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    active: bool = True
    created_at: float = 0.0
    updated_at: float = 0.0


class AvoidanceLearner:
    """Learn and query avoidance patterns from failures."""

    def __init__(self, db_path: str = "~/.bh/thinking/avoidance.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS avoidance_rules (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern             TEXT    NOT NULL,
                description         TEXT    NOT NULL DEFAULT '',
                category            TEXT    NOT NULL DEFAULT '',
                severity            TEXT    NOT NULL DEFAULT 'medium',
                trigger_context     TEXT    NOT NULL DEFAULT '[]',
                safe_alternative    TEXT    NOT NULL DEFAULT '',
                failure_count       INTEGER NOT NULL DEFAULT 1,
                source_feedback_ids TEXT    NOT NULL DEFAULT '[]',
                source_cot_ids      TEXT    NOT NULL DEFAULT '[]',
                tags                TEXT    NOT NULL DEFAULT '[]',
                confidence          REAL    NOT NULL DEFAULT 0.0,
                active              INTEGER NOT NULL DEFAULT 1,
                created_at          REAL    NOT NULL,
                updated_at          REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_avoid_category ON avoidance_rules(category);
            CREATE INDEX IF NOT EXISTS idx_avoid_severity ON avoidance_rules(severity);
            CREATE INDEX IF NOT EXISTS idx_avoid_confidence ON avoidance_rules(confidence DESC);
            CREATE INDEX IF NOT EXISTS idx_avoid_active ON avoidance_rules(active);
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

    def add_rule(self, pattern: str, description: str = "", category: str = "",
                 severity: str = "medium", trigger_context: Optional[List[str]] = None,
                 safe_alternative: str = "", source_feedback_ids: Optional[List[int]] = None,
                 source_cot_ids: Optional[List[int]] = None, tags: Optional[List[str]] = None,
                 confidence: float = 0.5) -> int:
        now = time.time()
        conn = self._get_conn()

        existing = conn.execute("SELECT id, failure_count FROM avoidance_rules WHERE pattern = ? AND active = 1",
                               (pattern,)).fetchone()
        if existing:
            conn.execute("UPDATE avoidance_rules SET failure_count = failure_count + 1, updated_at = ? WHERE id = ?",
                        (now, existing["id"]))
            conn.commit()
            logger.info("Incremented avoidance rule %d: %s", existing["id"], pattern)
            return existing["id"]

        cursor = conn.execute(
            """INSERT INTO avoidance_rules (pattern, description, category, severity, trigger_context, safe_alternative, failure_count, source_feedback_ids, source_cot_ids, tags, confidence, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, 1, ?, ?)""",
            (pattern, description, category, severity, json.dumps(trigger_context or []),
             safe_alternative, json.dumps(source_feedback_ids or []), json.dumps(source_cot_ids or []),
             json.dumps(tags or []), confidence, now, now),
        )
        conn.commit()
        eid = cursor.lastrowid
        logger.debug("Added avoidance rule %d: %s", eid, pattern)
        return eid

    def get(self, rule_id: int) -> Optional[AvoidanceRule]:
        row = self._get_conn().execute("SELECT * FROM avoidance_rules WHERE id = ?", (rule_id,)).fetchone()
        return self._row_to_rule(row) if row else None

    def search(self, query: str, limit: int = 20) -> List[AvoidanceRule]:
        rows = self._get_conn().execute(
            "SELECT * FROM avoidance_rules WHERE pattern LIKE ? OR description LIKE ? OR category LIKE ? ORDER BY confidence DESC, failure_count DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def get_relevant(self, context: str, limit: int = 10) -> List[AvoidanceRule]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM avoidance_rules WHERE active = 1").fetchall()
        scored: list[tuple[float, AvoidanceRule]] = []
        for row in rows:
            rule = self._row_to_rule(row)
            context_text = " ".join(rule.trigger_context)
            sim = ngram_similarity(context, f"{rule.pattern} {rule.description} {context_text}", n=3)
            score = sim * 0.5 + rule.confidence * 0.3 + min(rule.failure_count / 10, 0.2)
            if score > 0.1:
                scored.append((score, rule))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    def get_by_severity(self, severity: str, limit: int = 20) -> List[AvoidanceRule]:
        rows = self._get_conn().execute(
            "SELECT * FROM avoidance_rules WHERE severity = ? AND active = 1 ORDER BY failure_count DESC LIMIT ?",
            (severity, limit),
        ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def deactivate(self, rule_id: int) -> bool:
        cursor = self._get_conn().execute("UPDATE avoidance_rules SET active = 0 WHERE id = ?", (rule_id,))
        self._get_conn().commit()
        return cursor.rowcount > 0

    def get_active_rules(self, limit: int = 50) -> List[AvoidanceRule]:
        rows = self._get_conn().execute(
            "SELECT * FROM avoidance_rules WHERE active = 1 ORDER BY confidence DESC, failure_count DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM avoidance_rules").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM avoidance_rules WHERE active = 1").fetchone()[0]
        by_severity = {r["severity"]: r["cnt"] for r in conn.execute("SELECT severity, COUNT(*) AS cnt FROM avoidance_rules GROUP BY severity").fetchall()}
        by_cat = {r["category"]: r["cnt"] for r in conn.execute("SELECT category, COUNT(*) AS cnt FROM avoidance_rules WHERE category != '' GROUP BY category").fetchall()}
        total_failures = conn.execute("SELECT COALESCE(SUM(failure_count), 0) FROM avoidance_rules").fetchone()[0]
        return {"total": total, "active": active, "by_severity": by_severity, "by_category": by_cat,
                "total_failures": total_failures,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_rule(self, row: sqlite3.Row) -> AvoidanceRule:
        return AvoidanceRule(
            id=row["id"], pattern=row["pattern"], description=row["description"],
            category=row["category"], severity=row["severity"],
            trigger_context=json.loads(row["trigger_context"]) if row["trigger_context"] else [],
            safe_alternative=row["safe_alternative"],
            failure_count=row["failure_count"],
            source_feedback_ids=json.loads(row["source_feedback_ids"]) if row["source_feedback_ids"] else [],
            source_cot_ids=json.loads(row["source_cot_ids"]) if row["source_cot_ids"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            confidence=row["confidence"], active=bool(row["active"]),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )
