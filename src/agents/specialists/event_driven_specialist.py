"""Event-driven specialist — Event-driven architecture and streaming."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class EventDrivenSpecialist(BaseAgent):
    """Specialist agent for event-driven architecture and streaming.

    Handles event sourcing, CQRS, event streaming, saga orchestration,
    and reactive system patterns.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.CODER, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._event_stores: Dict[str, List[Dict[str, Any]]] = {}
        self._projections: Dict[str, Dict[str, Any]] = {}
        self._event_handlers: Dict[str, List[str]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_event_store":
            return await self._create_event_store(task)
        elif action == "append_event":
            return await self._append_event(task)
        elif action == "create_projection":
            return await self._create_projection(task)
        elif action == "subscribe":
            return await self._subscribe(task)
        elif action == "replay_events":
            return await self._replay_events(task)
        elif action == "process_stream":
            return await self._process_stream(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "event":
            store = message.get("payload", {}).get("store", "default")
            event = message.get("payload", {}).get("event", {})
            self._event_stores.setdefault(store, []).append({**event, "received_at": time.time()})
            return {"event_received": True}
        elif msg_type == "event_query":
            store = message.get("payload", {}).get("store", "default")
            events = self._event_stores.get(store, [])
            return {"event_count": len(events), "events": events[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "event_sourcing", "cqrs", "event_streaming",
            "saga_orchestration", "event_store_management", "projection_management",
            "reactive_patterns", "event_replay",
        ]

    async def _create_event_store(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_store")
        self._event_stores[name] = []
        return {"success": True, "event_store": name, "status": "created"}

    async def _append_event(self, task: Task) -> Dict[str, Any]:
        store = task.payload.get("store", "default")
        event_type = task.payload.get("event_type", "unknown")
        data = task.payload.get("data", {})
        aggregate_id = task.payload.get("aggregate_id", "default")

        if store not in self._event_stores:
            self._event_stores[store] = []

        event = {
            "event_id": f"evt-{int(time.time() * 1000)}",
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "data": data,
            "timestamp": time.time(),
            "version": len(self._event_stores[store]) + 1,
        }
        self._event_stores[store].append(event)
        return {"success": True, "event": event}

    async def _create_projection(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_projection")
        source_store = task.payload.get("source_store", "default")
        handler = task.payload.get("handler", "default_handler")

        projection = {
            "name": name,
            "source_store": source_store,
            "handler": handler,
            "status": "active",
            "last_offset": 0,
            "created_at": time.time(),
        }
        self._projections[name] = projection
        return {"success": True, "projection": name, "config": projection}

    async def _subscribe(self, task: Task) -> Dict[str, Any]:
        event_type = task.payload.get("event_type", "*")
        handler_name = task.payload.get("handler", "default_handler")
        store = task.payload.get("store", "default")

        if store not in self._event_handlers:
            self._event_handlers[store] = []
        self._event_handlers[store].append(handler_name)

        return {"success": True, "event_type": event_type, "handler": handler_name, "store": store}

    async def _replay_events(self, task: Task) -> Dict[str, Any]:
        store = task.payload.get("store", "default")
        from_version = task.payload.get("from_version", 0)
        to_version = task.payload.get("to_version", -1)

        events = self._event_stores.get(store, [])
        if to_version == -1:
            to_version = len(events)

        replayed = events[from_version:to_version]
        return {"success": True, "store": store, "events_replayed": len(replayed), "events": replayed}

    async def _process_stream(self, task: Task) -> Dict[str, Any]:
        store = task.payload.get("store", "default")
        processor = task.payload.get("processor", "default")
        batch_size = task.payload.get("batch_size", 100)

        events = self._event_stores.get(store, [])
        processed = min(batch_size, len(events))

        return {
            "success": True,
            "store": store,
            "processor": processor,
            "events_processed": processed,
            "total_events": len(events),
        }

    def _monitor(self) -> Dict[str, Any]:
        total_events = sum(len(e) for e in self._event_stores.values())
        return {
            "success": True,
            "metrics": {
                "event_stores": len(self._event_stores),
                "total_events": total_events,
                "projections": len(self._projections),
                "subscribers": sum(len(h) for h in self._event_handlers.values()),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "event_driven",
            "metrics": self._monitor()["metrics"],
        }
