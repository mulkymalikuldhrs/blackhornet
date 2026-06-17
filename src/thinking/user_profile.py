"""UserProfile — store and manage user profiles with preferences and history.

Maintains persistent user profiles containing demographics, preferences,
behavioral patterns, interaction history summaries, and per-user
configuration for memory and thinking modules.
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
class UserProfile:
    id: int = 0
    user_id: str = ""
    name: str = ""
    traits: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    interaction_count: int = 0
    topics_of_interest: List[str] = field(default_factory=list)
    skill_levels: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0


class UserProfileStore:
    """Persistent user profile store using SQLite."""

    def __init__(self, db_path: str = "~/.bh/users/profiles.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           TEXT    NOT NULL UNIQUE,
                name              TEXT    NOT NULL DEFAULT '',
                traits            TEXT    NOT NULL DEFAULT '{}',
                preferences       TEXT    NOT NULL DEFAULT '{}',
                interaction_count INTEGER NOT NULL DEFAULT 0,
                topics_of_interest TEXT   NOT NULL DEFAULT '[]',
                skill_levels      TEXT    NOT NULL DEFAULT '{}',
                metadata          TEXT    NOT NULL DEFAULT '{}',
                created_at        REAL    NOT NULL,
                updated_at        REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_profiles_user ON profiles(user_id);
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

    def create_or_update(self, user_id: str, name: str = "",
                         traits: Optional[Dict[str, Any]] = None,
                         preferences: Optional[Dict[str, Any]] = None) -> UserProfile:
        now = time.time()
        conn = self._get_conn()
        existing = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()

        if existing:
            conn.execute(
                "UPDATE profiles SET name=?, traits=?, preferences=?, interaction_count=interaction_count+1, updated_at=? WHERE user_id=?",
                (name or existing["name"],
                 json.dumps(traits) if traits else existing["traits"],
                 json.dumps(preferences) if preferences else existing["preferences"],
                 now, user_id),
            )
            conn.commit()
            return self.get_by_user_id(user_id)

        traits_json = json.dumps(traits or {})
        prefs_json = json.dumps(preferences or {})
        conn.execute(
            "INSERT INTO profiles (user_id, name, traits, preferences, interaction_count, topics_of_interest, skill_levels, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, 0, '[]', '{}', '{}', ?, ?)",
            (user_id, name, traits_json, prefs_json, now, now),
        )
        conn.commit()
        return self.get_by_user_id(user_id)

    def get_by_user_id(self, user_id: str) -> Optional[UserProfile]:
        row = self._get_conn().execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return self._row_to_profile(row) if row else None

    def get(self, profile_id: int) -> Optional[UserProfile]:
        row = self._get_conn().execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return self._row_to_profile(row) if row else None

    def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        now = time.time()
        cursor = self._get_conn().execute(
            "UPDATE profiles SET preferences=?, updated_at=? WHERE user_id=?",
            (json.dumps(preferences), now, user_id),
        )
        self._get_conn().commit()
        return cursor.rowcount > 0

    def add_topic(self, user_id: str, topic: str) -> None:
        profile = self.get_by_user_id(user_id)
        if not profile:
            return
        topics = profile.topics_of_interest
        if topic not in topics:
            topics.append(topic)
        self._get_conn().execute(
            "UPDATE profiles SET topics_of_interest=?, updated_at=? WHERE user_id=?",
            (json.dumps(topics), time.time(), user_id),
        )
        self._get_conn().commit()

    def update_skill_level(self, user_id: str, skill: str, level: float) -> None:
        profile = self.get_by_user_id(user_id)
        if not profile:
            return
        skills = dict(profile.skill_levels)
        skills[skill] = level
        self._get_conn().execute(
            "UPDATE profiles SET skill_levels=?, updated_at=? WHERE user_id=?",
            (json.dumps(skills), time.time(), user_id),
        )
        self._get_conn().commit()

    def search(self, query: str, limit: int = 20) -> List[UserProfile]:
        rows = self._get_conn().execute(
            "SELECT * FROM profiles WHERE user_id LIKE ? OR name LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def count(self) -> int:
        row = self._get_conn().execute("SELECT COUNT(*) AS cnt FROM profiles").fetchone()
        return row["cnt"] if row else 0

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        total_interactions = conn.execute("SELECT COALESCE(SUM(interaction_count), 0) FROM profiles").fetchone()[0]
        return {"total_profiles": total, "total_interactions": total_interactions,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_profile(self, row: sqlite3.Row) -> UserProfile:
        return UserProfile(
            id=row["id"], user_id=row["user_id"], name=row["name"],
            traits=json.loads(row["traits"]) if row["traits"] else {},
            preferences=json.loads(row["preferences"]) if row["preferences"] else {},
            interaction_count=row["interaction_count"],
            topics_of_interest=json.loads(row["topics_of_interest"]) if row["topics_of_interest"] else [],
            skill_levels=json.loads(row["skill_levels"]) if row["skill_levels"] else {},
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"], updated_at=row["updated_at"],
        )
