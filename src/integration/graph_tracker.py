from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphTracker:
    """Track BH agents, tasks, and swarm nodes in the graph store.

    Watches BH modules and syncs their state into src/graph/ GraphStore
    for unified visualization and querying.
    """

    def __init__(self, graph_store=None, relationship_mapper=None):
        self._graph = graph_store
        self._mapper = relationship_mapper
        self._tracked: Dict[str, Dict[str, Any]] = {}

    def set_stores(self, graph_store=None, relationship_mapper=None):
        if graph_store:
            self._graph = graph_store
        if relationship_mapper:
            self._mapper = relationship_mapper

    def track_agent(self, agent_id: str, agent_type: str = "agent",
                    properties: Optional[Dict[str, Any]] = None) -> str:
        if self._graph:
            node = self._graph.find_or_create(
                agent_id,
                agent_type,
                properties or {},
            )
        self._tracked[agent_id] = {
            "type": agent_type,
            "updated": time.time(),
        }
        return agent_id

    def track_swarm_node(self, node_id: str, hostname: str = "",
                         capabilities: Optional[List[str]] = None) -> str:
        return self.track_agent(
            node_id,
            "swarm_node",
            {"hostname": hostname, "capabilities": capabilities or []},
        )

    def track_task(self, task_id: str, description: str = "",
                   status: str = "pending",
                   agent_id: str = "") -> str:
        node = None
        if self._graph:
            node = self._graph.find_or_create(
                task_id,
                "task",
                {"description": description, "status": status},
            )
        if self._mapper and agent_id:
            self._mapper.record_relationship(
                agent_id, "assigned", task_id,
            )
        return node.get("id", task_id) if isinstance(node, dict) else str(node)

    def relate_agents(self, source_id: str, relation: str,
                      target_id: str) -> None:
        if self._mapper:
            self._mapper.record_relationship(source_id, relation, target_id)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tracked_count": len(self._tracked),
            "tracked": dict(self._tracked),
        }
