from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    success: bool = True
    data: Any = None
    error: str = ""
    status_code: int = 200
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class APIBridge:
    def __init__(self, graph_store=None, memory_system=None,
                 event_bus=None, thinking=None, orchestrator=None,
                 tool_registry=None, agent_registry=None, hermes_quant=None,
                 ecosystem_orchestrator=None):
        self._graph = graph_store
        self._memory = memory_system
        self._event_bus = event_bus
        self._thinking = thinking
        self._orchestrator = orchestrator
        self._tool_registry = tool_registry
        self._agent_registry = agent_registry
        self._hermes_quant = hermes_quant
        self._ecosystem_orchestrator = ecosystem_orchestrator

    def set_services(self, graph_store=None, memory_system=None,
                     event_bus=None, thinking=None, orchestrator=None,
                     tool_registry=None, agent_registry=None, hermes_quant=None,
                     ecosystem_orchestrator=None):
        if graph_store:
            self._graph = graph_store
        if memory_system:
            self._memory = memory_system
        if event_bus:
            self._event_bus = event_bus
        if thinking:
            self._thinking = thinking
        if orchestrator:
            self._orchestrator = orchestrator
        if tool_registry:
            self._tool_registry = tool_registry
        if agent_registry:
            self._agent_registry = agent_registry
        if hermes_quant:
            self._hermes_quant = hermes_quant
        if ecosystem_orchestrator:
            self._ecosystem_orchestrator = ecosystem_orchestrator

    def get_graph(self, center: str = "", max_depth: int = 1) -> APIResponse:
        try:
            if not self._graph:
                return APIResponse(success=False, error="Graph store not available",
                                   status_code=503)
            data = self._graph.export_json()
            if center:
                from src.graph.relationship_mapper import RelationshipMapper
                mapper = RelationshipMapper(self._graph)
                sub = mapper.get_graph(center, max_depth)
                node_set = set(sub.get("nodes", []))
                data["nodes"] = [n for n in data.get("nodes", [])
                                 if n.get("label") in node_set]
                data["edges"] = sub.get("edges", [])
            return APIResponse(data={
                "nodes": data.get("nodes", []),
                "edges": data.get("edges", []),
                "stats": self._graph.stats() if hasattr(self._graph, "stats") else {},
            })
        except Exception as exc:
            logger.exception("APIBridge.get_graph error")
            return APIResponse(success=False, error=str(exc), status_code=500)

    def search_graph(self, query: str, limit: int = 20) -> APIResponse:
        try:
            if not self._graph:
                return APIResponse(success=False, error="Graph store not available",
                                   status_code=503)
            results = self._graph.search_nodes(query, limit)
            return APIResponse(data={"results": results})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_memory(self, key: str) -> APIResponse:
        try:
            if not self._memory:
                return APIResponse(success=False, error="Memory not available",
                                   status_code=503)
            data = self._memory.get(key)
            return APIResponse(data={"key": key, "value": data})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def search_memory(self, query: str, limit: int = 20) -> APIResponse:
        try:
            if not self._memory:
                return APIResponse(success=False, error="Memory not available",
                                   status_code=503)
            from src.memory.system import MemorySystem
            if isinstance(self._memory, MemorySystem):
                results = self._memory.search(query, limit=limit)
                return APIResponse(data={"results": results})
            results = []
            return APIResponse(data={"results": results})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_status(self) -> APIResponse:
        try:
            data: Dict[str, Any] = {
                "timestamp": time.time(),
                "services": {},
            }
            if self._graph:
                stats = self._graph.stats() if hasattr(self._graph, "stats") else {}
                data["services"]["graph"] = {"status": "ok", "stats": stats}
            else:
                data["services"]["graph"] = {"status": "unavailable"}
            if self._memory:
                data["services"]["memory"] = {"status": "ok"}
            else:
                data["services"]["memory"] = {"status": "unavailable"}
            if self._event_bus:
                data["services"]["event_bus"] = {
                    "status": "ok",
                    "event_counts": self._event_bus.count(),
                }
            else:
                data["services"]["event_bus"] = {"status": "unavailable"}
            return APIResponse(data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_events(self, event_type: str = "", limit: int = 50) -> APIResponse:
        try:
            if not self._event_bus:
                return APIResponse(success=False, error="Event bus not available",
                                   status_code=503)
            history = self._event_bus.get_history(event_type, limit)
            return APIResponse(data={
                "events": [{"type": e.type, "data": e.data,
                            "source": e.source, "timestamp": e.timestamp}
                           for e in history]
            })
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_agents(self, limit: int = 50) -> APIResponse:
        """Return all known agents from graph and orchestrator."""
        agents: List[Dict[str, Any]] = []
        try:
            if self._graph:
                nodes = self._graph.export_json().get("nodes", [])
                agents = [n for n in nodes if n.get("type") == "agent"]
            if self._orchestrator and hasattr(self._orchestrator, "get_stats"):
                stats = self._orchestrator.get_stats()
                agents.append({"type": "orchestrator_stats", "data": stats})
            return APIResponse(data={
                "agents": agents[:limit],
                "total": len(agents),
            })
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_ecosystem_status(self) -> APIResponse:
        """Return orchestrator ecosystem status (synchronous snapshot)."""
        try:
            data: Dict[str, Any] = {"stats": {}, "cache": {}, "agents": 0, "colonies": 0, "colony": {}}
            if self._orchestrator:
                data["stats"] = self._orchestrator.get_stats() if hasattr(self._orchestrator, "get_stats") else {}
                data["cache"] = self._orchestrator.get_status_cache() if hasattr(self._orchestrator, "get_status_cache") else {}
            if self._agent_registry and hasattr(self._agent_registry, "_agents"):
                data["agents"] = len(self._agent_registry._agents)
            if self._graph:
                nodes = self._graph.export_json().get("nodes", [])
                data["colonies"] = len([n for n in nodes if n.get("type") == "colony"])
            # ponytail: real colony subsystem snapshot (radar/mesh/health)
            eco = self._ecosystem_orchestrator
            if eco:
                data["colony"] = {
                    "radar_peers": len(getattr(eco._radar, "_peers", {}) or {}),
                    "mesh_peers": len(getattr(eco._mesh_bus, "_peers", {}) or {}),
                    "identity": str(getattr(eco._config, "colony_id", "")),
                    "running": getattr(eco, "_running", False),
                }
            return APIResponse(data=data)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    # ponytail: tasks/colonies/tools were orphaned in src/api/routes — collapsed here
    def get_tasks(self, limit: int = 50) -> APIResponse:
        try:
            tasks: List[Dict[str, Any]] = []
            if self._graph:
                nodes = self._graph.export_json().get("nodes", [])
                tasks = [n for n in nodes if n.get("type") in ("task", "goal", "episode")][:limit]
            return APIResponse(data={"tasks": tasks, "total": len(tasks)})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_tools(self, limit: int = 200) -> APIResponse:
        try:
            if not self._tool_registry or not hasattr(self._tool_registry, "list_all"):
                return APIResponse(data={"tools": [], "total": 0})
            all_tools = self._tool_registry.list_all()
            flat = [{"name": k, **v} for k, v in all_tools.items()][:limit]
            return APIResponse(data={"tools": flat, "total": len(flat)})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_colonies(self, limit: int = 50) -> APIResponse:
        try:
            colonies: List[Dict[str, Any]] = []
            if self._graph:
                nodes = self._graph.export_json().get("nodes", [])
                colonies = [n for n in nodes if n.get("type") == "colony"][:limit]
            return APIResponse(data={"colonies": colonies, "total": len(colonies)})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def get_quant(self) -> APIResponse:
        """Return BHQuant trading status (if wired)."""
        try:
            if not self._hermes_quant:
                return APIResponse(data={"trading": "unavailable", "reason": "quant not wired"})
            status = self._hermes_quant.status() if hasattr(self._hermes_quant, "status") else {}
            return APIResponse(data={"trading": "active", "status": status})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def handle_request(self, method: str, path: str,
                       body: Optional[Dict[str, Any]] = None) -> APIResponse:
        # ponytail: every real subsystem now routed — no orphaned endpoints
        if path == "/api/v1/graph" and method == "GET":
            return self.get_graph()
        elif path.startswith("/api/v1/graph/search") and method == "GET":
            query = ""
            if "?" in path:
                parts = path.split("?")[1].split("&")
                for p in parts:
                    k, _, v = p.partition("=")
                    if k == "q":
                        query = v
            return self.search_graph(query)
        elif path == "/api/v1/memory" and method == "GET":
            return self.get_status()
        elif path.startswith("/api/v1/memory/") and method == "GET":
            key = path.split("/")[-1]
            return self.get_memory(key)
        elif path == "/api/v1/status" and method == "GET":
            return self.get_status()
        elif path == "/api/v1/events" and method == "GET":
            return self.get_events()
        elif path == "/api/v1/agents" and method == "GET":
            return self.get_agents()
        elif path == "/api/v1/ecosystem" and method == "GET":
            return self.get_ecosystem_status()
        elif path == "/api/v1/tasks" and method == "GET":
            return self.get_tasks()
        elif path == "/api/v1/tools" and method == "GET":
            return self.get_tools()
        elif path == "/api/v1/colonies" and method == "GET":
            return self.get_colonies()
        elif path == "/api/v1/quant" and method == "GET":
            return self.get_quant()
        else:
            return APIResponse(success=False, error="Not found",
                               status_code=404)
