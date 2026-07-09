"""AMC Tools — register new module functions as AMC ToolRegistry tools.

Exposes our module capabilities (memory operations, graph queries,
auto-discovery routing, sandbox execution) as AMC-compatible tools
so they can be discovered and called by AMC agents.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AMCToolRegistrar:
    """Register new module functions as AMC ToolRegistry tools."""

    def __init__(self, tool_registry=None):
        self._registry = tool_registry
        self._registered: List[str] = []

    def set_registry(self, tool_registry) -> None:
        self._registry = tool_registry

    def register_all(self, memory_adapter=None, graph_tracker=None,
                     provider_hub=None, memory_system=None,
                     graph_store=None) -> int:
        count = 0
        if memory_adapter:
            count += self._register_memory_tools(memory_adapter)
        if graph_tracker or graph_store:
            count += self._register_graph_tools(graph_tracker, graph_store)
        if provider_hub:
            count += self._register_provider_tools(provider_hub)
        if memory_system:
            count += self._register_memory_system_tools(memory_system)
        return count

    def _register(self, name: str, fn: Any, description: str) -> bool:
        if not self._registry:
            return False
        try:
            if hasattr(self._registry, "register_function"):
                self._registry.register_function(
                    func=fn,
                    name=name,
                    description=description,
                    tool_type="function",
                )
                self._registered.append(name)
                return True
            elif hasattr(self._registry, "register"):
                self._registry.register(
                    tool_cls=None,
                    name=name,
                )
                self._registered.append(name)
                return True
            return False
        except Exception as exc:
            logger.warning("register_tool %s failed: %s", name, exc)
            return False

    def _register_memory_tools(self, adapter) -> int:
        def bh_memory_store(key: str, content: str,
                            tags: Optional[str] = "") -> Dict[str, Any]:
            tag_list = [t.strip() for t in tags.split(",")] if tags else []
            ok = adapter.store(key, content, tags=tag_list)
            return {"success": ok, "key": key}

        def bh_memory_search(query: str,
                             limit: int = 10) -> List[Dict[str, Any]]:
            return adapter.search(query, limit=limit)

        c = 0
        if self._register("bh_memory_store", bh_memory_store,
                          "Store a value in BlackHornet memory"):
            c += 1
        if self._register("bh_memory_search", bh_memory_search,
                          "Search BlackHornet memory by query"):
            c += 1
        return c

    def _register_graph_tools(self, tracker=None, store=None) -> int:
        def bh_graph_query(center: str = "",
                           depth: int = 1) -> Dict[str, Any]:
            if store and hasattr(store, "export_json"):
                return store.export_json()
            return {"nodes": [], "edges": []}

        def bh_graph_track_agent(agent_id: str,
                                 agent_type: str = "agent") -> Dict[str, Any]:
            if tracker:
                tracker.track_agent(agent_id, agent_type)
                return {"success": True, "agent_id": agent_id}
            return {"success": False}

        c = 0
        if self._register("bh_graph_query", bh_graph_query,
                          "Query the BlackHornet knowledge graph"):
            c += 1
        if self._register("bh_graph_track_agent", bh_graph_track_agent,
                          "Track an agent in the knowledge graph"):
            c += 1
        return c

    def _register_provider_tools(self, hub) -> int:
        def bh_discover_providers() -> Dict[str, Any]:
            return hub.scan_and_register()

        def bh_get_provider(task: str = "general") -> str:
            return hub.get_best_provider(task)

        c = 0
        if self._register("bh_discover_providers", bh_discover_providers,
                          "Scan and discover available LLM providers"):
            c += 1
        if self._register("bh_get_provider", bh_get_provider,
                          "Get best LLM provider for a task type"):
            c += 1
        return c

    def _register_memory_system_tools(self, memory_system) -> int:
        def bh_system_memory_add(key: str, content: str,
                                 tags: str = "") -> Dict[str, Any]:
            tag_list = [t.strip() for t in tags.split(",")] if tags else []
            memory_system.add(key, content, tags=tag_list)
            return {"success": True, "key": key}

        def bh_system_memory_search(
                query: str, limit: int = 10) -> List[Dict[str, Any]]:
            return memory_system.search(query, limit=limit)

        c = 0
        if self._register("bh_system_memory_add", bh_system_memory_add,
                          "Add to BlackHornet memory system"):
            c += 1
        if self._register("bh_system_memory_search", bh_system_memory_search,
                          "Search BlackHornet memory system"):
            c += 1
        return c

    def registered_tools(self) -> List[str]:
        return list(self._registered)
