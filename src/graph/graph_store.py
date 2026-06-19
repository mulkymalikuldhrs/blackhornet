"""GraphStore — graph database for entities and relationships.

SQLite-backed directed property graph. Supports nodes with typed
properties and directed edges with weights and labels.
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

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: int = 0
    label: str = ""
    node_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class GraphEdge:
    id: int = 0
    source_id: int = 0
    target_id: int = 0
    relation: str = ""
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0


class GraphStore:
    """SQLite-backed directed property graph."""

    def __init__(self, db_path: str = "~/.bh/graph/store.db"):
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                label      TEXT    NOT NULL,
                node_type  TEXT    NOT NULL DEFAULT '',
                properties TEXT    NOT NULL DEFAULT '{}',
                created_at REAL    NOT NULL,
                updated_at REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);

            CREATE TABLE IF NOT EXISTS edges (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id  INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                target_id  INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                relation   TEXT    NOT NULL DEFAULT '',
                weight     REAL    NOT NULL DEFAULT 1.0,
                properties TEXT    NOT NULL DEFAULT '{}',
                created_at REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
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

    def add_node(self, label: str, node_type: str = "",
                 properties: Optional[Dict[str, Any]] = None) -> int:
        now = time.time()
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO nodes (label, node_type, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (label, node_type, json.dumps(properties or {}), now, now),
        )
        conn.commit()
        return cursor.lastrowid

    def get_node(self, node_id: int) -> Optional[GraphNode]:
        row = self._get_conn().execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return self._row_to_node(row) if row else None

    def find_node(self, label: str) -> Optional[GraphNode]:
        row = self._get_conn().execute("SELECT * FROM nodes WHERE label = ?", (label,)).fetchall()
        return self._row_to_node(row[0]) if row else None

    def find_or_create(self, label: str, node_type: str = "",
                       properties: Optional[Dict[str, Any]] = None) -> int:
        existing = self._get_conn().execute("SELECT id FROM nodes WHERE label = ?", (label,)).fetchone()
        if existing:
            return existing["id"]
        return self.add_node(label, node_type, properties)

    def update_node_properties(self, node_id: int,
                                properties: Dict[str, Any],
                                merge: bool = True) -> Optional[int]:
        """Update properties of an existing node.

        Args:
            node_id: The node ID to update.
            properties: New properties to set.
            merge: If True, merge with existing properties; if False, replace entirely.

        Returns:
            The node_id if node exists, None otherwise.
        """
        node = self.get_node(node_id)
        if not node:
            return None

        if merge:
            merged = dict(node.properties)
            merged.update(properties)
        else:
            merged = dict(properties)

        self._get_conn().execute(
            "UPDATE nodes SET properties = ?, updated_at = ? WHERE id = ?",
            (json.dumps(merged), time.time(), node_id),
        )
        self._get_conn().commit()
        return node_id

    def search_nodes(self, query: str, limit: int = 50) -> List[GraphNode]:
        rows = self._get_conn().execute(
            "SELECT * FROM nodes WHERE label LIKE ? OR node_type LIKE ? OR properties LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def add_edge(self, source_id: int, target_id: int, relation: str = "",
                 weight: float = 1.0, properties: Optional[Dict[str, Any]] = None) -> int:
        now = time.time()
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM edges WHERE source_id=? AND target_id=? AND relation=?",
            (source_id, target_id, relation),
        ).fetchone()
        if existing:
            conn.execute("UPDATE edges SET weight=weight+? WHERE id=?", (weight, existing["id"]))
            conn.commit()
            return existing["id"]
        cursor = conn.execute(
            "INSERT INTO edges (source_id, target_id, relation, weight, properties, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (source_id, target_id, relation, weight, json.dumps(properties or {}), now),
        )
        conn.commit()
        return cursor.lastrowid

    def add_edge_by_label(self, source_label: str, target_label: str, relation: str = "",
                          weight: float = 1.0) -> int:
        src = self.find_node(source_label)
        tgt = self.find_node(target_label)
        if not src or not tgt:
            raise ValueError(f"Node not found: {source_label if not src else target_label}")
        return self.add_edge(src.id, tgt.id, relation, weight)

    def get_edges(self, node_id: int, direction: str = "both") -> List[GraphEdge]:
        conn = self._get_conn()
        if direction == "outgoing":
            rows = conn.execute("SELECT * FROM edges WHERE source_id = ?", (node_id,)).fetchall()
        elif direction == "incoming":
            rows = conn.execute("SELECT * FROM edges WHERE target_id = ?", (node_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
                               (node_id, node_id)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_neighbors(self, node_id: int, max_depth: int = 1) -> List[int]:
        seen: Set[int] = set()
        frontier = {node_id}
        for _ in range(max_depth):
            next_frontier: Set[int] = set()
            for nid in frontier:
                if nid in seen:
                    continue
                seen.add(nid)
                edges = self.get_edges(nid)
                for e in edges:
                    if e.source_id not in seen:
                        next_frontier.add(e.source_id)
                    if e.target_id not in seen:
                        next_frontier.add(e.target_id)
            frontier = next_frontier
        seen.discard(node_id)
        return list(seen)

    def remove_node(self, node_id: int) -> bool:
        conn = self._get_conn()
        conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
        cursor = conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        conn.commit()
        return cursor.rowcount > 0

    def export_json(self) -> Dict[str, Any]:
        conn = self._get_conn()
        nodes = [{"id": r["id"], "label": r["label"], "type": r["node_type"],
                   "properties": json.loads(r["properties"])}
                 for r in conn.execute("SELECT * FROM nodes").fetchall()]
        edges = [{"source": r["source_id"], "target": r["target_id"],
                   "relation": r["relation"], "weight": r["weight"]}
                 for r in conn.execute("SELECT * FROM edges").fetchall()]
        return {"nodes": nodes, "edges": edges}

    def add_node_property(self, node_id: int, key: str, value: Any) -> Optional[int]:
        """Convenience: set a single property on a node."""
        return self.update_node_properties(node_id, {key: value})

    def get_nodes(self, node_type: str = "", limit: int = 500) -> List[GraphNode]:
        conn = self._get_conn()
        if node_type:
            rows = conn.execute("SELECT * FROM nodes WHERE node_type = ? LIMIT ?", (node_type, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM nodes LIMIT ?", (limit,)).fetchall()
        return [self._row_to_node(r) for r in rows]

    def list_edges(self, relation: str = "", limit: int = 500) -> List[GraphEdge]:
        conn = self._get_conn()
        if relation:
            rows = conn.execute("SELECT * FROM edges WHERE relation = ? LIMIT ?", (relation, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM edges LIMIT ?", (limit,)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        nodes = self.search_nodes(query, limit=limit)
        return [{"id": n.id, "label": n.label, "type": n.node_type, "properties": n.properties} for n in nodes]

    def stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        by_type = {r["node_type"]: r["cnt"] for r in conn.execute(
            "SELECT node_type, COUNT(*) AS cnt FROM nodes WHERE node_type != '' GROUP BY node_type").fetchall()}
        return {"nodes": nodes, "edges": edges, "by_type": by_type,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0}

    def _row_to_node(self, row: sqlite3.Row) -> GraphNode:
        return GraphNode(id=row["id"], label=row["label"], node_type=row["node_type"],
                        properties=json.loads(row["properties"]) if row["properties"] else {},
                        created_at=row["created_at"], updated_at=row["updated_at"])

    def _row_to_edge(self, row: sqlite3.Row) -> GraphEdge:
        return GraphEdge(id=row["id"], source_id=row["source_id"], target_id=row["target_id"],
                        relation=row["relation"], weight=row["weight"],
                        properties=json.loads(row["properties"]) if row["properties"] else {},
                        created_at=row["created_at"])
