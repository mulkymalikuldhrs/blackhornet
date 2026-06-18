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
                 event_bus=None, thinking=None, orchestrator=None):
        self._graph = graph_store
        self._memory = memory_system
        self._event_bus = event_bus
        self._thinking = thinking
        self._orchestrator = orchestrator

    def set_services(self, graph_store=None, memory_system=None,
                     event_bus=None, thinking=None, orchestrator=None):
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
            if not self._orchestrator:
                return APIResponse(success=False, error="Orchestrator not available",
                                   status_code=503)
            stats = self._orchestrator.get_stats() if hasattr(self._orchestrator, "get_stats") else {}
            cache = self._orchestrator.get_status_cache() if hasattr(self._orchestrator, "get_status_cache") else {}
            return APIResponse(data={"stats": stats, "cache": cache})
        except Exception as exc:
            return APIResponse(success=False, error=str(exc), status_code=500)

    def handle_request(self, method: str, path: str,
                       body: Optional[Dict[str, Any]] = None) -> APIResponse:
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
        else:
            return APIResponse(success=False, error="Not found",
                               status_code=404)
