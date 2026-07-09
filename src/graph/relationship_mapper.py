"""RelationshipMapper — map and update relationships between entities.

Discovers, infers, and maintains relationships between tracked entities
based on co-occurrence, interaction patterns, and explicit relations.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    source: str = ""
    target: str = ""
    relation: str = ""
    weight: float = 1.0
    evidence: List[str] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0


class RelationshipMapper:
    """Discover and maintain entity relationships."""

    def __init__(self, graph_store: Any = None):
        self._graph = graph_store
        self._relationships: Dict[str, Relationship] = {}

    def set_graph_store(self, graph_store: Any) -> None:
        self._graph = graph_store

    def _key(self, source: str, target: str, relation: str) -> str:
        return f"{source}|{target}|{relation}"

    def record(self, source: str, target: str, relation: str = "related_to",
               weight: float = 1.0, evidence: Optional[str] = None) -> Relationship:
        now = time.time()
        key = self._key(source, target, relation)

        if key in self._relationships:
            rel = self._relationships[key]
            rel.weight = max(rel.weight, weight)
            rel.last_seen = now
            if evidence and evidence not in rel.evidence:
                rel.evidence.append(evidence)
        else:
            rel = Relationship(
                source=source, target=target, relation=relation,
                weight=weight, evidence=[evidence] if evidence else [],
                first_seen=now, last_seen=now,
            )
            self._relationships[key] = rel

        if self._graph:
            self._sync_to_graph(rel)

        return rel

    def _sync_to_graph(self, rel: Relationship) -> None:
        try:
            src_node = self._graph.find_node(rel.source)
            tgt_node = self._graph.find_node(rel.target)
            if src_node and tgt_node:
                self._graph.add_edge(
                    src_node.id, tgt_node.id, rel.relation,
                    weight=rel.weight,
                    properties={"evidence_count": len(rel.evidence)},
                )
        except Exception as e:
            logger.warning("Failed to sync relationship: %s", e)

    def record_cooccurrence(self, entities: List[str], context: str = "") -> int:
        count = 0
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                rel = "co_occurs_with" if not context else f"co_occurs_in_{context}"
                self.record(entities[i], entities[j], rel, weight=0.5,
                           evidence=f"co-occurrence at {time.time()}")
                count += 1
        return count

    def get_related(self, entity_name: str, min_weight: float = 0.0) -> List[Relationship]:
        results: List[Relationship] = []
        for rel in self._relationships.values():
            if rel.weight < min_weight:
                continue
            if rel.source == entity_name or rel.target == entity_name:
                results.append(rel)
        results.sort(key=lambda r: r.weight, reverse=True)
        return results

    def get_graph(self, entity_name: str, max_depth: int = 1) -> Dict[str, Any]:
        nodes: Set[str] = {entity_name}
        edges: List[Dict[str, Any]] = []
        frontier = {entity_name}
        for _ in range(max_depth):
            next_frontier: Set[str] = set()
            for name in frontier:
                for rel in self.get_related(name):
                    other = rel.target if rel.source == name else rel.source
                    if other not in nodes:
                        next_frontier.add(other)
                        nodes.add(other)
                    edges.append({"source": rel.source, "target": rel.target,
                                  "relation": rel.relation, "weight": rel.weight})
            frontier = next_frontier
        return {"nodes": list(nodes), "edges": edges}

    def stats(self) -> Dict[str, Any]:
        by_relation: Dict[str, int] = {}
        for rel in self._relationships.values():
            by_relation[rel.relation] = by_relation.get(rel.relation, 0) + 1
        return {"total_relationships": len(self._relationships),
                "by_relation": by_relation}
