"""AutoGraphUpdater — automatically update graph on changes.

Listens to memory, thinking, and entity events and automatically
updates the graph store with new nodes, edges, and relationships.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AutoGraphUpdater:
    """Automatically update graph from system events."""

    def __init__(self, graph_store: Any = None, entity_tracker: Any = None,
                 relationship_mapper: Any = None):
        self._graph = graph_store
        self._tracker = entity_tracker
        self._mapper = relationship_mapper
        self._update_count: int = 0

    def set_stores(self, graph_store: Any = None, entity_tracker: Any = None,
                   relationship_mapper: Any = None) -> None:
        if graph_store:
            self._graph = graph_store
        if entity_tracker:
            self._tracker = entity_tracker
        if relationship_mapper:
            self._mapper = relationship_mapper

    def on_memory_add(self, key: str, content: str, tags: Optional[List[str]] = None) -> int:
        count = 0
        if not self._graph:
            return 0
        try:
            node_id = self._graph.find_or_create(f"memory:{key}", "memory",
                                                  {"key": key, "content_preview": content[:100]})
            count += 1
            if tags:
                for tag in tags:
                    tag_node = self._graph.find_or_create(f"tag:{tag}", "tag")
                    self._graph.add_edge(node_id, tag_node, "tagged")
                    count += 1
        except Exception as e:
            logger.warning("Graph update from memory failed: %s", e)
        self._update_count += count
        return count

    def on_concept_add(self, concept_name: str, category: str = "") -> int:
        count = 0
        if not self._graph:
            return 0
        try:
            node_id = self._graph.find_or_create(f"concept:{concept_name}", "concept",
                                                  {"category": category})
            count += 1
            if category:
                cat_node = self._graph.find_or_create(f"category:{category}", "category")
                self._graph.add_edge(node_id, cat_node, "belongs_to")
                count += 1
        except Exception as e:
            logger.warning("Graph update from concept failed: %s", e)
        self._update_count += count
        return count

    def on_episode(self, agent_id: str, event_type: str, summary: str) -> int:
        count = 0
        if not self._graph:
            return 0
        try:
            agent_node = self._graph.find_or_create(f"agent:{agent_id}", "agent")
            ep_node = self._graph.find_or_create(f"episode:{summary[:50]}", "episode",
                                                  {"summary": summary[:200]})
            self._graph.add_edge(agent_node, ep_node, event_type)
            count += 2
        except Exception as e:
            logger.warning("Graph update from episode failed: %s", e)
        self._update_count += count
        return count

    def on_entity_event(self, entity: Any) -> int:
        count = 0
        if not self._graph or not self._tracker or not self._mapper:
            return 0
        try:
            self._tracker.track(entity.name, entity.entity_type,
                                properties=entity.properties)
            count += 1
        except Exception as e:
            logger.warning("Graph update from entity event failed: %s", e)
        self._update_count += count
        return count

    def get_update_count(self) -> int:
        return self._update_count

    def stats(self) -> Dict[str, Any]:
        return {"total_updates": self._update_count}
