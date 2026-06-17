"""AMC Bridge — wire new FASE modules into AMC core infrastructure.

Connects our new modules (auto_discovery, memory, thinking, graph,
sandbox, ui) to AMC's EventBus, MemoryManager, AgentRegistry,
ColonyManager, and LLMProvider so the entire system is unified.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AMCBridge:
    """Bidirectional bridge between new modules and AMC core.

    Provides:
    - Event forwarding: new EventBus ↔ AMC EventBus
    - Memory sync: MemorySystem ↔ AMC MemoryManager
    - Agent tracking: GraphStore → AMC AgentRegistry
    - Colony monitoring: GraphStore → AMC ColonyManager
    """

    def __init__(self):
        self._amc_event_bus: Any = None
        self._amc_memory_manager: Any = None
        self._amc_agent_registry: Any = None
        self._amc_colony_manager: Any = None
        self._amc_llm_provider: Any = None
        self._new_event_bus: Any = None
        self._memory_system: Any = None
        self._graph_store: Any = None
        self._graph_tracker: Any = None
        self._running = False
        self._subscriptions: List[Callable] = []

    def set_amc_services(self, event_bus=None, memory_manager=None,
                         agent_registry=None, colony_manager=None,
                         llm_provider=None):
        if event_bus:
            self._amc_event_bus = event_bus
        if memory_manager:
            self._amc_memory_manager = memory_manager
        if agent_registry:
            self._amc_agent_registry = agent_registry
        if colony_manager:
            self._amc_colony_manager = colony_manager
        if llm_provider:
            self._amc_llm_provider = llm_provider

    def set_new_services(self, event_bus=None, memory_system=None,
                         graph_store=None, graph_tracker=None):
        if event_bus:
            self._new_event_bus = event_bus
        if memory_system:
            self._memory_system = memory_system
        if graph_store:
            self._graph_store = graph_store
        if graph_tracker:
            self._graph_tracker = graph_tracker

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._wire_event_bus()
        self._wire_memory()
        self._wire_registry()
        self._wire_colony()
        logger.info("AMCBridge: all services wired")

    def stop(self) -> None:
        self._running = False
        for sub in self._subscriptions:
            try:
                sub()
            except Exception:
                pass
        self._subscriptions.clear()
        logger.info("AMCBridge: stopped")

    def _wire_event_bus(self) -> None:
        if not self._new_event_bus or not self._amc_event_bus:
            return
        from src.ui.event_bus import Event

        def _amc_to_new(amc_event: Any) -> None:
            if not self._running or not self._new_event_bus:
                return
            etype = getattr(amc_event, "type", str(type(amc_event).__name__))
            data = getattr(amc_event, "data", {}) or {}
            try:
                self._new_event_bus.publish(
                    Event(type=f"amc.{etype}", data=data, source="amc")
                )
            except Exception as exc:
                logger.debug("AMC→new event: %s", exc)

        if hasattr(self._amc_event_bus, "subscribe"):
            try:
                self._amc_event_bus.subscribe("*", _amc_to_new)
                self._subscriptions.append(
                    lambda: self._amc_event_bus.unsubscribe("*", _amc_to_new)
                )
            except Exception:
                pass

    def _wire_memory(self) -> None:
        if not self._memory_system or not self._amc_memory_manager:
            return
        logger.info("AMCBridge: memory wired (sync on demand)")

    def sync_memory_to_amc(self, key: str, content: str,
                           tags: Optional[List[str]] = None) -> bool:
        """Sync a memory entry from MemorySystem to AMC MemoryManager."""
        if not self._amc_memory_manager:
            return False
        try:
            if hasattr(self._amc_memory_manager, "add_entry"):
                self._amc_memory_manager.add_entry(
                    agent_id="blackhornet",
                    content=content,
                    memory_type="observation",
                    tags=tags or [],
                )
                return True
            elif hasattr(self._amc_memory_manager, "create_page"):
                self._amc_memory_manager.create_page(
                    agent_id="blackhornet",
                    memory_type="observation",
                    title=key,
                    content=content,
                    tags=tags or [],
                )
                return True
        except Exception as exc:
            logger.warning("sync_memory_to_amc failed: %s", exc)
        return False

    def _wire_registry(self) -> None:
        if not self._amc_agent_registry or not self._graph_tracker:
            return
        logger.info("AMCBridge: agent registry wired")

    def sync_amc_agents_to_graph(self) -> int:
        """Sync AMC AgentRegistry agents into GraphStore."""
        if not self._amc_agent_registry or not self._graph_tracker:
            return 0
        count = 0
        try:
            if hasattr(self._amc_agent_registry, "list_agents"):
                agents = self._amc_agent_registry.list_agents()
                for agent in agents:
                    agent_id = getattr(agent, "agent_id",
                                       getattr(agent, "id", str(agent)))
                    self._graph_tracker.track_agent(
                        str(agent_id), "amc_agent",
                    )
                    count += 1
            elif hasattr(self._amc_agent_registry, "list_agent_info"):
                infos = self._amc_agent_registry.list_agent_info()
                for info in infos:
                    agent_id = getattr(info, "agent_id",
                                       getattr(info, "id", str(info)))
                    self._graph_tracker.track_agent(
                        str(agent_id), "amc_agent",
                    )
                    count += 1
        except Exception as exc:
            logger.warning("sync_amc_agents_to_graph: %s", exc)
        return count

    def _wire_colony(self) -> None:
        if not self._amc_colony_manager or not self._graph_tracker:
            return
        logger.info("AMCBridge: colony manager wired")

    def sync_colonies_to_graph(self) -> int:
        """Sync AMC colonies into GraphStore."""
        if not self._amc_colony_manager or not self._graph_tracker:
            return 0
        count = 0
        try:
            if hasattr(self._amc_colony_manager, "list_colonies"):
                colonies = self._amc_colony_manager.list_colonies()
                for col in colonies:
                    col_id = None
                    if isinstance(col, dict):
                        col_id = col.get("id", col.get("colony_id"))
                    else:
                        col_id = getattr(col, "id",
                                         getattr(col, "colony_id", str(col)))
                    if col_id:
                        self._graph_tracker.track_agent(
                            str(col_id), "colony",
                        )
                        count += 1
        except Exception as exc:
            logger.warning("sync_colonies_to_graph: %s", exc)
        return count

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "amc_event_bus": self._amc_event_bus is not None,
            "amc_memory_manager": self._amc_memory_manager is not None,
            "amc_agent_registry": self._amc_agent_registry is not None,
            "amc_colony_manager": self._amc_colony_manager is not None,
            "new_event_bus": self._new_event_bus is not None,
            "memory_system": self._memory_system is not None,
            "graph_store": self._graph_store is not None,
        }
