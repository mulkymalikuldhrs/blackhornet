"""EntityTracker — track entities and auto-create graph nodes.

Monitors memory, thinking, and conversation modules to discover
entities and create/update graph nodes automatically.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    name: str = ""
    entity_type: str = ""
    source: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    first_seen: float = 0.0
    last_seen: float = 0.0
    mention_count: int = 1


class EntityTracker:
    """Track entities and sync to GraphStore."""

    def __init__(self, graph_store: Any = None):
        self._graph = graph_store
        self._entities: Dict[str, Entity] = {}
        self._observers: List[Callable] = []

    def set_graph_store(self, graph_store: Any) -> None:
        self._graph = graph_store

    def register_observer(self, callback: Callable) -> None:
        self._observers.append(callback)

    def _notify(self, entity: Entity) -> None:
        for cb in self._observers:
            try:
                cb(entity)
            except Exception:
                pass

    def track(self, name: str, entity_type: str = "", source: str = "",
              properties: Optional[Dict[str, Any]] = None) -> Entity:
        now = time.time()
        key = f"{entity_type}:{name}" if entity_type else name

        if key in self._entities:
            ent = self._entities[key]
            ent.last_seen = now
            ent.mention_count += 1
            if properties:
                ent.properties.update(properties)
        else:
            ent = Entity(
                name=name, entity_type=entity_type, source=source,
                properties=properties or {}, first_seen=now, last_seen=now,
            )
            self._entities[key] = ent

        if self._graph:
            self._sync_to_graph(ent)

        self._notify(ent)
        return ent

    def _sync_to_graph(self, entity: Entity) -> None:
        try:
            label = entity.name
            existing = self._graph.find_node(label)
            if existing:
                props = dict(existing.properties)
                props.update(entity.properties)
                props["mention_count"] = entity.mention_count
                props["last_seen"] = entity.last_seen
            else:
                self._graph.add_node(
                    label=label,
                    node_type=entity.entity_type,
                    properties={
                        "source": entity.source,
                        "confidence": entity.confidence,
                        "mention_count": entity.mention_count,
                        "first_seen": entity.first_seen,
                        "last_seen": entity.last_seen,
                    },
                )
        except Exception as e:
            logger.warning("Failed to sync entity to graph: %s", e)

    def get_entity(self, name: str, entity_type: str = "") -> Optional[Entity]:
        key = f"{entity_type}:{name}" if entity_type else name
        return self._entities.get(key)

    def search(self, query: str) -> List[Entity]:
        q = query.lower()
        results: List[Entity] = []
        for ent in self._entities.values():
            if q in ent.name.lower() or q in ent.entity_type.lower():
                results.append(ent)
        results.sort(key=lambda e: e.mention_count, reverse=True)
        return results[:20]

    def get_all(self) -> List[Entity]:
        return list(self._entities.values())

    def get_by_type(self, entity_type: str) -> List[Entity]:
        return [e for e in self._entities.values() if e.entity_type == entity_type]

    def count(self) -> int:
        return len(self._entities)

    def stats(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        for e in self._entities.values():
            by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1
        total_mentions = sum(e.mention_count for e in self._entities.values())
        return {"total_entities": len(self._entities), "by_type": by_type,
                "total_mentions": total_mentions}
