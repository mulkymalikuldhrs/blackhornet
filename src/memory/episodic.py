"""EpisodicMemory – timeline-based episodic memory with parent-child
relationships, per-agent and per-type indexing, FTS5 summary search,
and chain-of-episode reconstruction for replay and analysis.

Events are stored as a flat timeline and linked through a parent_id
field so that complex multi-step interactions can be replayed or
analysed as a chain.
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


# ── Data model ────────────────────────────────────────────────────

@dataclass
class Episode:
    """A single episode (event) in episodic memory.

    Attributes
    ----------
    id : int
        Database rowid (auto-increment, 0 before insertion).
    agent_id : str
        Identifier of the agent that produced this episode.
    event_type : str
        Categorical type — one of ``"message"``, ``"tool_call"``,
        ``"decision"``, ``"error"``, ``"learning"``.
    summary : str
        Human-readable summary of the episode.
    context : dict[str, Any]
        Arbitrary structured context data attached to the episode.
    parent_id : int
        Rowid of the parent episode (0 for root episodes).
    timestamp : float
        Unix timestamp of when the episode occurred.
    duration_ms : float
        How long the episode took to execute (milliseconds).
    outcome : str
        Result label — ``"success"``, ``"failure"``, ``"partial"``,
        or ``""`` if unknown.
    """
    id: int = 0
    agent_id: str = ""
    event_type: str = ""
    summary: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    parent_id: int = 0
    timestamp: float = 0.0
    duration_ms: float = 0.0
    outcome: str = ""


# ── Episodic Memory ───────────────────────────────────────────────

class EpisodicMemory:
    """Timeline-based episodic memory with sqlite3 storage.

    Stores events (episodes) in a flat timeline.  Episodes may form
    trees via ``parent_id`` so that multi-step workflows can be traced
    from leaf back to root.

    Indexes are maintained on ``(agent_id, timestamp)`` and
    ``(event_type, timestamp)`` for efficient filtered timeline
    queries.  FTS5 is used for full-text search over episode summaries.

    Parameters
    ----------
    db_path : str
        Filesystem path for the sqlite database.  ``~`` is expanded.
    """

    def __init__(self, db_path: str = "~/.bh/memory/episodic.db") -> None:
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    # ── Database init ────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS episodes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id    TEXT    NOT NULL DEFAULT '',
                event_type  TEXT    NOT NULL DEFAULT '',
                summary     TEXT    NOT NULL DEFAULT '',
                context     TEXT    NOT NULL DEFAULT '{}',
                parent_id   INTEGER NOT NULL DEFAULT 0,
                timestamp   REAL    NOT NULL,
                duration_ms REAL    NOT NULL DEFAULT 0.0,
                outcome     TEXT    NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_episodes_agent_ts
                ON episodes(agent_id, timestamp DESC);

            CREATE INDEX IF NOT EXISTS idx_episodes_type_ts
                ON episodes(event_type, timestamp DESC);

            CREATE INDEX IF NOT EXISTS idx_episodes_parent
                ON episodes(parent_id);

            CREATE INDEX IF NOT EXISTS idx_episodes_timestamp
                ON episodes(timestamp DESC);

            -- FTS5 virtual table for summary search
            CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts
                USING fts5(summary, content=episodes, content_rowid=id);

            -- Triggers to keep FTS index in sync
            CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
                INSERT INTO episodes_fts(rowid, summary)
                VALUES (new.id, new.summary);
            END;

            CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
                INSERT INTO episodes_fts(episodes_fts, rowid, summary)
                VALUES ('delete', old.id, old.summary);
            END;

            CREATE TRIGGER IF NOT EXISTS episodes_au AFTER UPDATE ON episodes BEGIN
                INSERT INTO episodes_fts(episodes_fts, rowid, summary)
                VALUES ('delete', old.id, old.summary);
                INSERT INTO episodes_fts(rowid, summary)
                VALUES (new.id, new.summary);
            END;
        """)
        conn.commit()
        logger.debug("EpisodicMemory db ready at %s", self.db_path)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> EpisodicMemory:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── CRUD ─────────────────────────────────────────────────────

    def add(
        self,
        agent_id: str,
        event_type: str,
        summary: str,
        context: Optional[Dict[str, Any]] = None,
        parent_id: int = 0,
        duration_ms: float = 0.0,
        outcome: str = "",
    ) -> int:
        """Record a new episode.

        Parameters
        ----------
        agent_id : str
            Identifier of the agent.
        event_type : str
            Type label (``"message"``, ``"tool_call"``, ``"decision"``,
            ``"error"``, ``"learning"``).
        summary : str
            Human-readable summary.
        context : dict or None
            Optional structured context.
        parent_id : int
            Rowid of parent episode (0 for root).
        duration_ms : float
            Wall-clock duration in milliseconds.
        outcome : str
            Outcome label (``"success"``, ``"failure"``, ``"partial"``).

        Returns
        -------
        int
            The new episode's rowid.
        """
        now = time.time()
        context_json = json.dumps(context or {})

        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO episodes
               (agent_id, event_type, summary, context, parent_id,
                timestamp, duration_ms, outcome)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, event_type, summary, context_json, parent_id,
             now, duration_ms, outcome),
        )
        conn.commit()
        ep_id = cursor.lastrowid
        logger.debug("Added episode %d: agent=%s type=%s", ep_id, agent_id, event_type)
        return ep_id

    def get(self, id: int) -> Optional[Episode]:
        """Retrieve a single episode by rowid.

        Parameters
        ----------
        id : int
            Episode rowid.

        Returns
        -------
        Episode or None
            The episode, or ``None`` if not found.
        """
        row = self._get_conn().execute(
            "SELECT * FROM episodes WHERE id = ?", (id,)
        ).fetchone()
        return self._row_to_episode(row) if row else None

    def remove(self, id: int) -> bool:
        """Delete an episode by rowid.

        Children of the deleted episode have their ``parent_id`` set
        to 0 (orphaned).

        Parameters
        ----------
        id : int
            Episode rowid.

        Returns
        -------
        bool
            ``True`` if the episode existed and was deleted.
        """
        conn = self._get_conn()
        # Orphan children
        conn.execute("UPDATE episodes SET parent_id = 0 WHERE parent_id = ?", (id,))
        cursor = conn.execute("DELETE FROM episodes WHERE id = ?", (id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug("Removed episode %d", id)
        return deleted

    # ── Queries ──────────────────────────────────────────────────

    def get_by_agent(self, agent_id: str, limit: int = 50) -> List[Episode]:
        """Get episodes for a specific agent, most recent first.

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        limit : int
            Maximum results (default 50).

        Returns
        -------
        list[Episode]
        """
        rows = self._get_conn().execute(
            "SELECT * FROM episodes WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def get_by_type(self, event_type: str, limit: int = 50) -> List[Episode]:
        """Get episodes of a specific type, most recent first.

        Parameters
        ----------
        event_type : str
            Event type filter.
        limit : int
            Maximum results (default 50).

        Returns
        -------
        list[Episode]
        """
        rows = self._get_conn().execute(
            "SELECT * FROM episodes WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            (event_type, limit),
        ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def get_timeline(
        self,
        start: float,
        end: float,
        limit: int = 100,
    ) -> List[Episode]:
        """Get episodes within a time window.

        Parameters
        ----------
        start : float
            Start Unix timestamp (inclusive).
        end : float
            End Unix timestamp (inclusive).
        limit : int
            Maximum results (default 100).

        Returns
        -------
        list[Episode]
            Episodes sorted by timestamp ascending.
        """
        rows = self._get_conn().execute(
            "SELECT * FROM episodes WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC LIMIT ?",
            (start, end, limit),
        ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def get_recent(self, limit: int = 20) -> List[Episode]:
        """Get the most recent episodes across all agents.

        Parameters
        ----------
        limit : int
            Maximum results (default 20).

        Returns
        -------
        list[Episode]
        """
        rows = self._get_conn().execute(
            "SELECT * FROM episodes ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def get_children(self, parent_id: int) -> List[Episode]:
        """Get all direct children of a given episode.

        Parameters
        ----------
        parent_id : int
            Parent episode rowid.

        Returns
        -------
        list[Episode]
            Children sorted by timestamp ascending.
        """
        rows = self._get_conn().execute(
            "SELECT * FROM episodes WHERE parent_id = ? ORDER BY timestamp ASC",
            (parent_id,),
        ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def get_chain(self, episode_id: int) -> List[Episode]:
        """Walk the parent chain from *episode_id* back to the root.

        The returned list starts with the root ancestor and ends with
        the requested episode (chronological order).

        Parameters
        ----------
        episode_id : int
            Starting episode rowid (leaf).

        Returns
        -------
        list[Episode]
            Chain from root to leaf (empty if *episode_id* does not
            exist).  If the episode is a root itself, a single-element
            list is returned.
        """
        chain: List[Episode] = []
        current_id = episode_id
        # Use a set to guard against cycles in malformed data
        seen: set[int] = set()

        while current_id != 0 and current_id not in seen:
            seen.add(current_id)
            row = self._get_conn().execute(
                "SELECT * FROM episodes WHERE id = ?", (current_id,)
            ).fetchone()
            if row is None:
                break
            episode = self._row_to_episode(row)
            chain.append(episode)
            current_id = episode.parent_id

        chain.reverse()
        return chain

    def search(self, query: str, limit: int = 20) -> List[Episode]:
        """Full-text search over episode summaries using FTS5.

        Parameters
        ----------
        query : str
            FTS5 query string (supports ``*``, ``"..."``, etc).
        limit : int
            Maximum results (default 20).

        Returns
        -------
        list[Episode]
            Matching episodes sorted by FTS5 rank.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT e.*
                   FROM episodes_fts
                   JOIN episodes e ON e.id = episodes_fts.rowid
                   WHERE episodes_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [self._row_to_episode(r) for r in rows]

    # ── Aggregate counts / stats ────────────────────────────────

    def count(self) -> int:
        """Return total number of episodes."""
        row = self._get_conn().execute("SELECT COUNT(*) AS cnt FROM episodes").fetchone()
        return row["cnt"] if row else 0

    def stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the episodic store.

        Returns
        -------
        dict
            Keys: ``total_episodes``, ``by_agent``, ``by_type``,
            ``by_outcome``, ``time_range``, ``db_size_bytes``.
        """
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) AS cnt FROM episodes").fetchone()["cnt"]

        by_agent = {
            r["agent_id"]: r["cnt"]
            for r in conn.execute(
                "SELECT agent_id, COUNT(*) AS cnt FROM episodes GROUP BY agent_id"
            ).fetchall()
        }

        by_type = {
            r["event_type"]: r["cnt"]
            for r in conn.execute(
                "SELECT event_type, COUNT(*) AS cnt FROM episodes GROUP BY event_type"
            ).fetchall()
        }

        by_outcome = {
            r["outcome"]: r["cnt"]
            for r in conn.execute(
                "SELECT outcome, COUNT(*) AS cnt FROM episodes GROUP BY outcome"
            ).fetchall()
        }

        time_row = conn.execute(
            "SELECT MIN(timestamp) AS first, MAX(timestamp) AS last FROM episodes"
        ).fetchone()

        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        return {
            "total_episodes": total,
            "by_agent": by_agent,
            "by_type": by_type,
            "by_outcome": by_outcome,
            "first_timestamp": time_row["first"] if time_row else None,
            "last_timestamp": time_row["last"] if time_row else None,
            "db_size_bytes": db_size,
        }

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _row_to_episode(row: sqlite3.Row) -> Episode:
        """Convert a sqlite3.Row to an Episode."""
        return Episode(
            id=row["id"],
            agent_id=row["agent_id"],
            event_type=row["event_type"],
            summary=row["summary"],
            context=json.loads(row["context"]) if row["context"] else {},
            parent_id=row["parent_id"],
            timestamp=row["timestamp"],
            duration_ms=row["duration_ms"],
            outcome=row["outcome"],
        )
