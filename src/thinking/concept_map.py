"""ConceptMap — semantic concept graph using SQLite.

Stores concepts as nodes and semantic relations as edges.
Supports CRUD, traversal, and similarity-based concept retrieval.
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
class ConceptNode:
    id: int = 0
    name: str = ""
    definition: str = ""
    category: str = ""
    aliases: List[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: float = 0.0
    accessed_at: float = 0.0


@dataclass
class ConceptEdge:
    id: int = 0
    source_id: int = 0
    target_id: int = 0
    relation: str = ""
    weight: float = 1.0
    created_at: float = 0.0


class ConceptMap:
    """Semantic concept graph with SQLite storage."""

    def __init__(self, db_path: str = "~/.bh/thinking/concepts.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS concepts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                definition  TEXT    NOT NULL DEFAULT '',
                category    TEXT    NOT NULL DEFAULT '',
                aliases     TEXT    NOT NULL DEFAULT '[]',
                confidence  REAL    NOT NULL DEFAULT 1.0,
                created_at  REAL    NOT NULL,
                accessed_at REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_concepts_category ON concepts(category);
            CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);

            CREATE TABLE IF NOT EXISTS concept_edges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id   INTEGER NOT NULL REFERENCES concepts(id),
                target_id   INTEGER NOT NULL REFERENCES concepts(id),
                relation    TEXT    NOT NULL DEFAULT '',
                weight      REAL    NOT NULL DEFAULT 1.0,
                created_at  REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON concept_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON concept_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_relation ON concept_edges(relation);
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

    def add_concept(self, name: str, definition: str = "", category: str = "",
                    aliases: Optional[List[str]] = None, confidence: float = 1.0) -> int:
        now = time.time()
        aliases_json = json.dumps(aliases or [])
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO concepts (name, definition, category, aliases, confidence, created_at, accessed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, definition, category, aliases_json, confidence, now, now),
            )
            conn.commit()
            cid = cursor.lastrowid
            logger.debug("Added concept %d: %s", cid, name)
            return cid
        except sqlite3.IntegrityError:
            existing = self.get_by_name(name)
            if existing:
                return existing.id
            raise

    def get(self, concept_id: int) -> Optional[ConceptNode]:
        row = self._get_conn().execute(
            "SELECT * FROM concepts WHERE id = ?", (concept_id,)
        ).fetchone()
        if row is None:
            return None
        self._get_conn().execute(
            "UPDATE concepts SET accessed_at = ? WHERE id = ?",
            (time.time(), concept_id),
        )
        self._get_conn().commit()
        return self._row_to_node(row)

    def get_by_name(self, name: str) -> Optional[ConceptNode]:
        row = self._get_conn().execute(
            "SELECT * FROM concepts WHERE name = ?", (name,)
        ).fetchone()
        return self._row_to_node(row) if row else None

    def search(self, query: str, limit: int = 20) -> List[ConceptNode]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM concepts WHERE name LIKE ? OR definition LIKE ? OR category LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def search_similar(self, text: str, threshold: float = 0.3, limit: int = 10) -> List[ConceptNode]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM concepts").fetchall()
        scored: list[tuple[float, ConceptNode]] = []
        for row in rows:
            node = self._row_to_node(row)
            sim = ngram_similarity(text, f"{node.name} {node.definition}", n=3)
            if sim >= threshold:
                scored.append((sim, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:limit]]

    def add_edge(self, source_name: str, target_name: str, relation: str, weight: float = 1.0) -> int:
        src = self.get_by_name(source_name)
        tgt = self.get_by_name(target_name)
        if not src or not tgt:
            raise ValueError(f"Concept not found: {source_name if not src else target_name}")
        now = time.time()
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO concept_edges (source_id, target_id, relation, weight, created_at) VALUES (?, ?, ?, ?, ?)",
            (src.id, tgt.id, relation, weight, now),
        )
        conn.commit()
        return cursor.lastrowid

    def get_edges(self, concept_name: str, direction: str = "both") -> List[ConceptEdge]:
        node = self.get_by_name(concept_name)
        if not node:
            return []
        conn = self._get_conn()
        if direction == "outgoing":
            rows = conn.execute(
                "SELECT * FROM concept_edges WHERE source_id = ?", (node.id,)
            ).fetchall()
        elif direction == "incoming":
            rows = conn.execute(
                "SELECT * FROM concept_edges WHERE target_id = ?", (node.id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM concept_edges WHERE source_id = ? OR target_id = ?",
                (node.id, node.id),
            ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_neighbors(self, concept_name: str, max_depth: int = 1) -> List[ConceptNode]:
        seen: Set[int] = set()
        results: List[ConceptNode] = []
        current = self.get_by_name(concept_name)
        if not current:
            return results
        frontier = [current]
        for _ in range(max_depth + 1):
            next_frontier: List[ConceptNode] = []
            for node in frontier:
                if node.id in seen:
                    continue
                seen.add(node.id)
                results.append(node)
                edges = self.get_edges(node.name, direction="outgoing")
                for edge in edges:
                    neighbor = self.get(edge.target_id)
                    if neighbor and neighbor.id not in seen:
                        next_frontier.append(neighbor)
                edges = self.get_edges(node.name, direction="incoming")
                for edge in edges:
                    neighbor = self.get(edge.source_id)
                    if neighbor and neighbor.id not in seen:
                        next_frontier.append(neighbor)
            frontier = next_frontier
        return results

    def remove_concept(self, concept_id: int) -> bool:
        conn = self._get_conn()
        conn.execute("DELETE FROM concept_edges WHERE source_id = ? OR target_id = ?", (concept_id, concept_id))
        cursor = conn.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))
        conn.commit()
        return cursor.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM concept_edges").fetchone()[0]
        categories = {
            r["category"]: r["cnt"]
            for r in conn.execute("SELECT category, COUNT(*) AS cnt FROM concepts WHERE category != '' GROUP BY category").fetchall()
        }
        return {"concepts": concepts, "edges": edges, "categories": categories, "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_node(self, row: sqlite3.Row) -> ConceptNode:
        return ConceptNode(
            id=row["id"], name=row["name"], definition=row["definition"],
            category=row["category"], aliases=json.loads(row["aliases"]) if row["aliases"] else [],
            confidence=row["confidence"], created_at=row["created_at"], accessed_at=row["accessed_at"],
        )

    def _row_to_edge(self, row: sqlite3.Row) -> ConceptEdge:
        return ConceptEdge(id=row["id"], source_id=row["source_id"], target_id=row["target_id"],
                          relation=row["relation"], weight=row["weight"], created_at=row["created_at"])
