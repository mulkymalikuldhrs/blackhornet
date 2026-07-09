"""PreferenceLearner — learn user preferences from interaction patterns.

Analyzes feedback, topic engagement, and interaction history to build
and update a preference model for each user. Integrates with
FeedbackCollector and UserProfile.
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
class Preference:
    key: str = ""
    value: Any = None
    confidence: float = 0.0
    source: str = ""
    updated_at: float = 0.0


@dataclass
class PreferenceModel:
    user_id: str = ""
    preferences: Dict[str, Preference] = field(default_factory=dict)
    learned_topics: List[str] = field(default_factory=list)
    communication_style: str = ""
    expertise_level: Dict[str, float] = field(default_factory=dict)
    interaction_patterns: Dict[str, Any] = field(default_factory=dict)


class PreferenceLearner:
    """Learn and manage user preferences from interactions."""

    def __init__(self, db_path: str = "~/.bh/users/preferences.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS preferences (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                key         TEXT    NOT NULL,
                value       TEXT    NOT NULL DEFAULT '',
                confidence  REAL    NOT NULL DEFAULT 0.0,
                source      TEXT    NOT NULL DEFAULT '',
                updated_at  REAL    NOT NULL,
                UNIQUE(user_id, key)
            );
            CREATE INDEX IF NOT EXISTS idx_pref_user ON preferences(user_id);

            CREATE TABLE IF NOT EXISTS learned_topics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                topic       TEXT    NOT NULL,
                score       REAL    NOT NULL DEFAULT 0.0,
                source      TEXT    NOT NULL DEFAULT '',
                updated_at  REAL    NOT NULL,
                UNIQUE(user_id, topic)
            );
            CREATE INDEX IF NOT EXISTS idx_topics_user ON learned_topics(user_id);

            CREATE TABLE IF NOT EXISTS expertise_levels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                domain      TEXT    NOT NULL,
                level       REAL    NOT NULL DEFAULT 0.0,
                evidence    TEXT    NOT NULL DEFAULT '[]',
                updated_at  REAL    NOT NULL,
                UNIQUE(user_id, domain)
            );
            CREATE INDEX IF NOT EXISTS idx_expert_user ON expertise_levels(user_id);
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

    def record_preference(self, user_id: str, key: str, value: Any,
                          confidence: float = 0.5, source: str = "") -> None:
        now = time.time()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO preferences (user_id, key, value, confidence, source, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, key, value_str, confidence, source, now),
        )
        conn.commit()

    def get_preference(self, user_id: str, key: str) -> Optional[Preference]:
        row = self._get_conn().execute(
            "SELECT * FROM preferences WHERE user_id = ? AND key = ?", (user_id, key)
        ).fetchone()
        if not row:
            return None
        return Preference(key=row["key"], value=row["value"], confidence=row["confidence"],
                          source=row["source"], updated_at=row["updated_at"])

    def get_all_preferences(self, user_id: str) -> List[Preference]:
        rows = self._get_conn().execute(
            "SELECT * FROM preferences WHERE user_id = ? ORDER BY confidence DESC", (user_id,)
        ).fetchall()
        return [Preference(key=r["key"], value=r["value"], confidence=r["confidence"],
                          source=r["source"], updated_at=r["updated_at"]) for r in rows]

    def learn_topic(self, user_id: str, topic: str, score: float = 0.5, source: str = "") -> None:
        now = time.time()
        self._get_conn().execute(
            "INSERT OR REPLACE INTO learned_topics (user_id, topic, score, source, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, topic, score, source, now),
        )
        self._get_conn().commit()

    def get_topics(self, user_id: str, min_score: float = 0.1) -> List[Dict[str, Any]]:
        rows = self._get_conn().execute(
            "SELECT * FROM learned_topics WHERE user_id = ? AND score >= ? ORDER BY score DESC",
            (user_id, min_score),
        ).fetchall()
        return [{"topic": r["topic"], "score": r["score"], "source": r["source"]} for r in rows]

    def set_expertise(self, user_id: str, domain: str, level: float,
                      evidence: Optional[List[str]] = None) -> None:
        now = time.time()
        self._get_conn().execute(
            "INSERT OR REPLACE INTO expertise_levels (user_id, domain, level, evidence, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, domain, level, json.dumps(evidence or []), now),
        )
        self._get_conn().commit()

    def get_expertise(self, user_id: str) -> Dict[str, float]:
        rows = self._get_conn().execute(
            "SELECT domain, level FROM expertise_levels WHERE user_id = ? ORDER BY level DESC",
            (user_id,),
        ).fetchall()
        return {r["domain"]: r["level"] for r in rows}

    def get_model(self, user_id: str) -> PreferenceModel:
        prefs = self.get_all_preferences(user_id)
        pref_dict = {p.key: p for p in prefs}
        topics = self.get_topics(user_id)
        expertise = self.get_expertise(user_id)
        style_pref = self.get_preference(user_id, "communication_style")
        return PreferenceModel(
            user_id=user_id,
            preferences=pref_dict,
            learned_topics=[t["topic"] for t in topics],
            communication_style=style_pref.value if style_pref else "",
            expertise_level=expertise,
        )

    def learn_from_feedback(self, user_id: str, rating: float, category: str) -> None:
        pref_key = f"prefers_{category}"
        existing = self.get_preference(user_id, pref_key)
        if existing:
            new_conf = min(1.0, existing.confidence + 0.1)
            new_val = max(0.0, existing.confidence * 0.7 + rating * 0.3)
            self.record_preference(user_id, pref_key, new_val, confidence=new_conf, source="feedback")
        else:
            self.record_preference(user_id, pref_key, rating, confidence=0.3, source="feedback")

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM preferences").fetchone()[0]
        prefs = conn.execute("SELECT COUNT(*) FROM preferences").fetchone()[0]
        topics = conn.execute("SELECT COUNT(*) FROM learned_topics").fetchone()[0]
        expertise = conn.execute("SELECT COUNT(*) FROM expertise_levels").fetchone()[0]
        return {"users": users, "preferences": prefs, "topics": topics,
                "expertise_entries": expertise,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}
