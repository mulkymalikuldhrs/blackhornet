"""GraphifySyncBridge — syncs colony state into the knowledge graph.

Bridges the gap between:
  - AgentRegistry / ColonyManager (in-memory agent state)
  - LifecycleRecorder (lifecycle events)
  - Graphify GraphStore (persistent directed property graph)

Ensures every agent, colony, and lifecycle event is visible in
the UI (Cytoscape), TUI (ASCII table), and dashboard (Graphify).
"""

from __future__ import annotations

import time
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)


class GraphifySyncBridge:
    """Syncs colony agents, colonies, and lifecycle events into Graphify.

    Usage:
        bridge = GraphifySyncBridge(graph_store=my_graph_store)
        bridge.sync_agent(agent_id="agent-1", status="active", hand="code", colony="colony-alpha")
        bridge.sync_colony(colony_id="colony-alpha", health=0.92, agent_count=5)
        bridge.sync_lifecycle_event({"event_type": "boot", "id": "evt-1", ...})
        report = bridge.get_sync_report()
    """

    def __init__(self, graph_store: Any) -> None:
        self._graph = graph_store
        self._sync_counts: dict[str, int] = {
            "agents_synced": 0,
            "colonies_synced": 0,
            "events_synced": 0,
            "edges_created": 0,
        }

    @property
    def sync_report(self) -> dict[str, int]:
        return dict(self._sync_counts)

    def _ensure_node(self, label: str, node_type: str = "",
                     properties: Optional[dict[str, Any]] = None,
                     update_properties: bool = True) -> Optional[int]:
        """Find or create a node, then optionally update its properties."""
        if not self._graph:
            return None
        try:
            if hasattr(self._graph, "find_or_create"):
                node_id = self._graph.find_or_create(label, node_type, properties or {})
                if update_properties and properties and hasattr(self._graph, "update_node_properties"):
                    self._graph.update_node_properties(node_id, properties, merge=True)
                return node_id
            if hasattr(self._graph, "find_or_create_node"):
                return self._graph.find_or_create_node(label, node_type, properties or {})
        except Exception as e:
            logger.debug("graph_sync_node_error label=%s err=%s", label, e)
        return None

    def _ensure_edge(self, source_label: str, target_label: str,
                     relation: str, weight: float = 1.0) -> None:
        """Create an edge between two node labels (creates nodes if needed)."""
        if not self._graph:
            return
        try:
            if hasattr(self._graph, "add_edge_by_label"):
                self._graph.add_edge_by_label(source_label, target_label, relation, weight)
                self._sync_counts["edges_created"] += 1
            elif hasattr(self._graph, "add_edge"):
                src = source_label
                tgt = target_label
                if hasattr(self._graph, "find_node"):
                    src_node = self._graph.find_node(source_label)
                    tgt_node = self._graph.find_node(target_label)
                    if src_node and tgt_node:
                        self._graph.add_edge(src_node.id, tgt_node.id, relation, weight)
                        self._sync_counts["edges_created"] += 1
        except Exception as e:
            logger.debug("graph_sync_edge_error src=%s tgt=%s rel=%s err=%s",
                         source_label, target_label, relation, e)

    def sync_agent(self, agent_id: str, name: Optional[str] = None,
                   agent_type: str = "agent", status: str = "unknown",
                   hand: Optional[str] = None, colony: Optional[str] = None,
                   health: float = 0.0, capabilities: Optional[list[str]] = None,
                   tasks_completed: int = 0, tasks_failed: int = 0,
                   uptime: float = 0.0) -> None:
        """Sync a single agent into the knowledge graph.

        Creates/updates an agent node and links it to its colony.
        """
        props: dict[str, Any] = {
            "agent_id": agent_id,
            "name": name or agent_id,
            "type": agent_type,
            "status": status,
            "health": health,
            "tasks_completed": tasks_completed,
            "tasks_failed": tasks_failed,
            "uptime": uptime,
            "last_sync": time.time(),
        }
        if hand:
            props["hand"] = hand
        if capabilities:
            props["capabilities"] = capabilities

        label = f"agent:{agent_id}"
        node_id = self._ensure_node(label, "agent", props)

        if colony and node_id:
            colony_label = f"colony:{colony}"
            self._ensure_node(colony_label, "colony")
            self._ensure_edge(label, colony_label, "member_of")

        self._sync_counts["agents_synced"] += 1

    def sync_colony(self, colony_id: str, name: Optional[str] = None,
                    health: float = 0.0, agent_count: int = 0,
                    status: str = "active") -> None:
        """Sync a colony into the knowledge graph."""
        props: dict[str, Any] = {
            "colony_id": colony_id,
            "name": name or colony_id,
            "health": health,
            "agent_count": agent_count,
            "status": status,
            "last_sync": time.time(),
        }
        self._ensure_node(f"colony:{colony_id}", "colony", props)
        self._sync_counts["colonies_synced"] += 1

    def sync_lifecycle_event(self, event: dict[str, Any]) -> None:
        """Sync a lifecycle event into the knowledge graph as an event node."""
        event_type = event.get("event_type", "unknown")
        event_id = event.get("id", f"evt-{time.time()}")
        source = event.get("source", "system")

        props: dict[str, Any] = {
            "event_id": event_id,
            "event_type": event_type,
            "source": source,
            "data": event.get("data", {}),
            "timestamp": event.get("timestamp", time.time()),
        }
        label = f"event:{event_type}:{event_id[:16]}"
        self._ensure_node(label, "event", props)

        colony_id = event.get("colony_id")
        if colony_id:
            self._ensure_edge(label, f"colony:{colony_id}", "occurred_in")

        agent_id = event.get("data", {}).get("agent_id")
        if agent_id:
            self._ensure_edge(label, f"agent:{agent_id}", "involves")

        self._sync_counts["events_synced"] += 1

    def sync_agents_batch(self, agents: list[dict[str, Any]]) -> None:
        """Sync multiple agents in batch."""
        for agent in agents:
            self.sync_agent(
                agent_id=agent.get("agent_id", "unknown"),
                name=agent.get("name"),
                agent_type=agent.get("type", "agent"),
                status=agent.get("status", "unknown"),
                hand=agent.get("hand"),
                colony=agent.get("colony"),
                health=agent.get("health", 0.0),
                capabilities=agent.get("capabilities"),
                tasks_completed=agent.get("tasks_completed", 0),
                tasks_failed=agent.get("tasks_failed", 0),
                uptime=agent.get("uptime", 0.0),
            )

    def sync_colonies_batch(self, colonies: list[dict[str, Any]]) -> None:
        """Sync multiple colonies in batch."""
        for colony in colonies:
            self.sync_colony(
                colony_id=colony.get("colony_id", "unknown"),
                name=colony.get("name"),
                health=colony.get("health", 0.0),
                agent_count=colony.get("agent_count", 0),
                status=colony.get("status", "active"),
            )

    def sync_lifecycle_batch(self, events: list[dict[str, Any]]) -> None:
        """Sync multiple lifecycle events in batch."""
        for event in events:
            self.sync_lifecycle_event(event)

    def sync_agent_registry(self, agent_registry: Any,
                            colony_manager: Optional[Any] = None) -> int:
        """Sync all agents from an AgentRegistry into the graph.

        Returns the number of agents synced.
        """
        count = 0
        if not agent_registry:
            return 0

        try:
            agents: list[Any] = []
            if hasattr(agent_registry, "list_agents"):
                agents = agent_registry.list_agents()
            elif hasattr(agent_registry, "list_agent_info"):
                agents = agent_registry.list_agent_info()

            for agent in agents:
                agent_id = agent.get("agent_id") if isinstance(agent, dict) else getattr(agent, "agent_id", None)
                if not agent_id:
                    continue

                colony_id = None
                if colony_manager and hasattr(colony_manager, "get_agent_colony"):
                    colony = colony_manager.get_agent_colony(agent_id)
                    if colony:
                        colony_id = colony.get("colony_id") if isinstance(colony, dict) else getattr(colony, "colony_id", None)

                if isinstance(agent, dict):
                    self.sync_agent(
                        agent_id=agent_id,
                        name=agent.get("name"),
                        agent_type=agent.get("agent_type", "agent") if isinstance(agent.get("agent_type"), str) else str(agent.get("agent_type", "agent")),
                        status=agent.get("state", agent.get("status", "unknown")),
                        colony=colony_id,
                        health=agent.get("health_score", 0),
                        tasks_completed=agent.get("tasks_completed", 0),
                        tasks_failed=agent.get("tasks_failed", 0),
                    )
                else:
                    self.sync_agent(
                        agent_id=agent_id,
                        name=getattr(agent, "name", agent_id),
                        agent_type=str(getattr(agent, "agent_type", "agent")),
                        status=str(getattr(agent, "state", getattr(agent, "status", "unknown"))),
                        colony=colony_id,
                        health=getattr(agent, "health_score", 0),
                        tasks_completed=getattr(agent, "tasks_completed", 0),
                        tasks_failed=getattr(agent, "tasks_failed", 0),
                    )
                count += 1

        except Exception as e:
            logger.warning("graph_sync_registry_error err=%s", e)

        return count

    def reset_counts(self) -> None:
        for key in self._sync_counts:
            self._sync_counts[key] = 0
