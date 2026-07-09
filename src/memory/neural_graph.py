"""
NeuralGraphMemory — graph-based spreading activation memory for BlackHornet.

Inspired by neural-memory (v4.59) but self-contained:
- networkx graph for in-memory traversal
- sqlite3 (stdlib) for persistence
- Spreading activation retrieval
- Consolidation (prune, Hebbian update)

No external dependencies beyond networkx (already in BlackHornet).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Neuron Types ────────────────────────────────────────────────────

NEURON_TYPES = {
    "time": "Temporal markers",
    "spatial": "Locations",
    "entity": "Named entities",
    "action": "Verbs/actions",
    "state": "Emotional/mental states",
    "concept": "Abstract ideas",
    "sensory": "Sensory experiences",
    "intent": "Goals/intentions",
    "hypothesis": "Evolving beliefs",
    "prediction": "Falsifiable claims",
    "schema": "Mental model snapshots",
}

SYNAPSE_TYPES = {
    # Temporal
    "happened_at": "Event-to-time binding",
    "before": "Temporal ordering",
    "after": "Temporal ordering (reverse)",
    "during": "Containment in time",
    # Spatial
    "at_location": "Location binding",
    "contains": "Spatial containment",
    "near": "Spatial proximity",
    # Causal
    "caused_by": "Direct causation",
    "leads_to": "Consequence chain",
    "enables": "Enabling condition",
    "prevents": "Blocking relation",
    # Associative
    "co_occurs": "Statistical co-occurrence",
    "related_to": "Generic association",
    "similar_to": "Semantic similarity",
    # Semantic
    "is_a": "Taxonomic relation",
    "has_property": "Attribute binding",
    "involves": "Participation relation",
    # Emotional
    "felt": "Emotional state",
    "evokes": "Emotional trigger",
    # Conflict
    "contradicts": "Mutual exclusion",
}


@dataclass
class NeuronData:
    """A single memory unit (node in the graph)."""
    id: str
    type: str = "concept"
    content: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = "blackhornet"
    importance: float = 0.5
    status: str = "active"  # active | superseded | expired
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SynapseData:
    """A connection between two neurons (edge in the graph)."""
    id: str
    source_id: str
    target_id: str
    type: str = "related_to"
    weight: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class NeuralGraphMemory:
    """Graph-based memory with spreading activation retrieval.

    Architecture:
        - neurons table: stores memory nodes
        - synapses table: stores directed edges with types
        - networkx DiGraph: in-memory graph for fast traversal
        - spreading activation: BFS from query-matched anchors

    Usage:
        ngm = NeuralGraphMemory(Path("data/neural/bh.db"))
        await ngm.initialize()
        nid = await ngm.remember("BTC drawdown limit 5%", tags=["risk"])
        results = await ngm.recall("BTC risk")
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._graph: dict[str, dict[str, Any]] = {}  # id -> neuron_data
        self._edges: dict[str, list[dict[str, Any]]] = {}  # source_id -> [synapse_data]
        self._initialized = False

    # ── Async context manager ─────────────────────────────────────────

    async def __aenter__(self) -> NeuralGraphMemory:
        await self.initialize()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.shutdown()

    # ── Lifecycle ────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Open DB, create tables, load graph into memory."""
        if self._initialized:
            return

        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS neurons (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL DEFAULT 'concept',
                content TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL DEFAULT 'blackhornet',
                importance REAL NOT NULL DEFAULT 0.5,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS synapses (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES neurons(id),
                target_id TEXT NOT NULL REFERENCES neurons(id),
                type TEXT NOT NULL DEFAULT 'related_to',
                weight REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_synapses_source ON synapses(source_id);
            CREATE INDEX IF NOT EXISTS idx_synapses_target ON synapses(target_id);
            CREATE INDEX IF NOT EXISTS idx_neurons_status ON neurons(status);
            CREATE INDEX IF NOT EXISTS idx_neurons_type ON neurons(type);
        """)
        self._conn.commit()

        # Load graph into memory
        self._lock.acquire()
        try:
            self._load_graph()
        finally:
            self._lock.release()

        self._initialized = True
        logger.info(
            "NeuralGraphMemory initialized: %s (%d neurons, %d synapses)",
            self._db_path, len(self._graph), sum(len(e) for e in self._edges.values()),
        )

    def _load_graph(self) -> None:
        """Load all active neurons and synapses into memory."""
        assert self._conn is not None
        cursor = self._conn.execute(
            "SELECT * FROM neurons WHERE status = 'active'"
        )
        self._graph = {}
        for row in cursor.fetchall():
            d = dict(row)
            d["tags"] = json.loads(d["tags"])
            self._graph[d["id"]] = d

        cursor = self._conn.execute(
            "SELECT * FROM synapses"
        )
        self._edges = {}
        for row in cursor.fetchall():
            d = dict(row)
            sid = d["source_id"]
            self._edges.setdefault(sid, []).append(d)

    async def shutdown(self) -> None:
        """Close DB connection."""
        self._lock.acquire()
        try:
            if self._conn:
                self._conn.close()
                self._conn = None
            self._initialized = False
        finally:
            self._lock.release()

    # ── Store ────────────────────────────────────────────────────────

    async def remember(
        self,
        content: str,
        *,
        neuron_type: str = "concept",
        tags: list[str] | None = None,
        source: str | None = None,
        importance: float = 0.5,
    ) -> str:
        """Store a memory neuron. Returns its ID."""
        assert self._conn is not None
        nid = uuid.uuid4().hex[:16]
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [])

        self._lock.acquire()
        try:
            self._conn.execute(
                """INSERT INTO neurons (id, type, content, tags, source, importance, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                (nid, neuron_type, content, tags_json, source or "blackhornet", importance, now, now),
            )
            self._conn.commit()

            # Update in-memory graph
            self._graph[nid] = {
                "id": nid,
                "type": neuron_type,
                "content": content,
                "tags": tags or [],
                "source": source or "blackhornet",
                "importance": importance,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        finally:
            self._lock.release()

        logger.debug("remembered neuron %s: %s…", nid, content[:60])
        return nid

    async def link(
        self,
        from_id: str,
        to_id: str,
        *,
        relation: str = "related_to",
        weight: float = 0.5,
    ) -> str:
        """Create a synapse between two neurons. Returns synapse ID."""
        assert self._conn is not None

        if from_id not in self._graph:
            raise ValueError(f"Source neuron {from_id} not found")
        if to_id not in self._graph:
            raise ValueError(f"Target neuron {to_id} not found")

        sid = uuid.uuid4().hex[:16]
        now = datetime.now(timezone.utc).isoformat()

        self._lock.acquire()
        try:
            self._conn.execute(
                """INSERT INTO synapses (id, source_id, target_id, type, weight, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sid, from_id, to_id, relation, weight, now),
            )
            self._conn.commit()

            self._edges.setdefault(from_id, []).append({
                "id": sid,
                "source_id": from_id,
                "target_id": to_id,
                "type": relation,
                "weight": weight,
                "created_at": now,
            })
        finally:
            self._lock.release()

        return sid

    async def forget(self, neuron_id: str) -> bool:
        """Soft-delete a neuron."""
        assert self._conn is not None

        if neuron_id not in self._graph:
            return False

        now = datetime.now(timezone.utc).isoformat()
        self._lock.acquire()
        try:
            self._conn.execute(
                "UPDATE neurons SET status = 'expired', updated_at = ? WHERE id = ?",
                (now, neuron_id),
            )
            self._conn.commit()

            # Remove from memory graph
            self._graph.pop(neuron_id, None)
            self._edges.pop(neuron_id, None)
        finally:
            self._lock.release()

        return True

    # ── Recall (Spreading Activation) ────────────────────────────────

    async def recall(
        self,
        query: str,
        *,
        limit: int = 10,
        min_score: float = 0.2,
        max_hops: int = 3,
    ) -> list[dict[str, Any]]:
        """Search memory via spreading activation from query-matched anchors.

        Algorithm:
            1. Tokenize query, find anchor neurons by keyword overlap
            2. BFS spread from anchors with decay factor per hop
            3. Score = overlap * importance * decay^hop
            4. Return top-N results
        """
        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        if not query_tokens:
            return []

        # Phase 1: Find anchor neurons (keyword overlap)
        anchors: list[tuple[str, float]] = []
        for nid, nd in self._graph.items():
            content_lower = nd["content"].lower()
            tag_overlap = nd["tags"] and len(set(nd["tags"]) & query_tokens) / max(len(query_tokens), 1)
            content_overlap = len(set(content_lower.split()) & query_tokens) / max(len(query_tokens), 1) if content_lower else 0
            score = max(tag_overlap, content_overlap * 0.7)
            if score > 0:
                anchors.append((nid, score))

        if not anchors:
            return []

        # Phase 2: Spreading activation (BFS)
        visited: dict[str, float] = {}  # id -> score
        queue: list[tuple[str, float, int]] = [(nid, score, 0) for nid, score in anchors]

        decay = 0.5  # Activation decays by half per hop

        while queue:
            nid, score, hop = queue.pop(0)

            # Keep highest score for each neuron
            if nid in visited and visited[nid] >= score:
                continue
            visited[nid] = score

            if hop >= max_hops:
                continue

            # Spread to neighbors
            for edge in self._edges.get(nid, []):
                target = edge["target_id"]
                edge_weight = edge["weight"]
                spread_score = score * decay * edge_weight
                if spread_score > min_score:
                    queue.append((target, spread_score, hop + 1))

        # Phase 3: Build results
        results = []
        for nid, score in visited.items():
            nd = self._graph.get(nid)
            if nd is None:
                continue
            # Bump score by importance
            final_score = score * (0.5 + nd["importance"] * 0.5)
            if final_score < min_score:
                continue
            results.append({
                "id": nid,
                "content": nd["content"],
                "score": round(final_score, 4),
                "neuron_type": nd["type"],
                "tags": nd["tags"],
                "source": nd["source"],
                "importance": nd["importance"],
                "created_at": nd["created_at"],
            })

        # Sort by score descending
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    # ── Consolidation ────────────────────────────────────────────────

    async def consolidate(self) -> dict[str, Any]:
        """Run consolidation cycle: prune dead connections, Hebbian update.

        Returns a summary dict.
        """
        assert self._conn is not None

        pruned_count = 0

        self._lock.acquire()
        try:
            # Prune orphan synapses (source or target no longer active)
            cursor = self._conn.execute("""
                DELETE FROM synapses WHERE source_id NOT IN (
                    SELECT id FROM neurons WHERE status = 'active'
                ) OR target_id NOT IN (
                    SELECT id FROM neurons WHERE status = 'active'
                )
            """)
            pruned_count += cursor.rowcount

            # Hebbian update: strengthen synapses between co-retrieved neurons
            cursor = self._conn.execute("""
                UPDATE synapses SET weight = MIN(1.0, weight + 0.01)
                WHERE id IN (
                    SELECT s.id FROM synapses s
                    JOIN neurons n1 ON s.source_id = n1.id
                    JOIN neurons n2 ON s.target_id = n2.id
                    WHERE n1.importance > 0.7 AND n2.importance > 0.5
                )
            """)
            hebbian_count = cursor.rowcount

            self._conn.commit()

            # Reload graph
            self._load_graph()
        finally:
            self._lock.release()

        return {
            "pruned": pruned_count,
            "hebbian_updated": hebbian_count,
            "neurons_active": len(self._graph),
            "synapses": sum(len(e) for e in self._edges.values()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Stats ────────────────────────────────────────────────────────

    async def stats(self) -> dict[str, Any]:
        """Return current graph statistics."""
        return {
            "neurons_active": len(self._graph),
            "synapses": sum(len(e) for e in self._edges.values()),
            "neuron_types": self._count_types(),
            "db_path": str(self._db_path),
        }

    def _count_types(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for nd in self._graph.values():
            t = nd.get("type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts
