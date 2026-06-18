"""Colony Lifecycle Recorder — makes the colony self-aware.

Records every significant lifecycle event into memory:
  - Colony boot/shutdown
  - Agent spawn/terminate
  - Task assignment/complete/fail
  - Configuration changes
  - Error/failure events
  - Peer discovery/loss
  - Deploy/upgrade events

The recorder feeds into the knowledge graph and memory systems,
giving the colony an evolving sense of its own history and state.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)


class LifecycleEventType(str, Enum):
    BOOT = "boot"
    SHUTDOWN = "shutdown"
    AGENT_SPAWN = "agent_spawn"
    AGENT_TERMINATE = "agent_terminate"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    CONFIG_CHANGE = "config_change"
    ERROR = "error"
    PEER_DISCOVERED = "peer_discovered"
    PEER_LOST = "peer_lost"
    DEPLOY = "deploy"
    UPGRADE = "upgrade"
    HEALTH_CHANGE = "health_change"
    MILESTONE = "milestone"


class LifecycleRecorder:
    """Records colony lifecycle events into memory and optional persistence.

    Usage:
        recorder = LifecycleRecorder(colony_id="colony-1")
        await recorder.record(LifecycleEventType.BOOT, {"version": "5.0.0"})
        await recorder.record(LifecycleEventType.AGENT_SPAWN, {"agent_id": "a1", "type": "coder"})
        events = await recorder.get_history()
        summary = await recorder.get_summary()
    """

    def __init__(
        self,
        colony_id: str,
        memory_system: Any = None,
        graph_store: Any = None,
        persist_path: Optional[str] = None,
        max_events: int = 10000,
    ) -> None:
        self._colony_id = colony_id
        self._memory_system = memory_system
        self._graph_store = graph_store
        self._persist_path = persist_path
        self._max_events = max_events

        self._events: list[dict[str, Any]] = []
        self._counts: dict[str, int] = defaultdict(int)
        self._first_event: Optional[float] = None
        self._last_event: Optional[float] = None
        self._lock = asyncio.Lock()

        self._current_session: Optional[str] = None
        self._boot_count: int = 0

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def session_id(self) -> Optional[str]:
        return self._current_session

    async def start(self) -> None:
        if self._current_session is not None:
            logger.debug("lifecycle_recorder_already_running colony=%s session=%s", self._colony_id, self._current_session)
            return
        self._current_session = str(uuid.uuid4())
        self._boot_count += 1
        await self.record(
            LifecycleEventType.BOOT,
            {
                "session_id": self._current_session,
                "boot_count": self._boot_count,
                "timestamp": time.time(),
            },
        )
        logger.info("lifecycle_recorder_started colony=%s session=%s", self._colony_id, self._current_session)

    async def stop(self) -> None:
        await self.record(LifecycleEventType.SHUTDOWN, {"uptime": self._get_session_uptime()})
        await self._flush()
        logger.info(
            "lifecycle_recorder_stopped colony=%s events=%d",
            self._colony_id,
            len(self._events),
        )

    async def record(
        self,
        event_type: str | LifecycleEventType,
        data: Optional[dict[str, Any]] = None,
        source: str = "system",
    ) -> dict[str, Any]:
        if isinstance(event_type, LifecycleEventType):
            event_type_str = event_type.value
        else:
            event_type_str = event_type
        event = {
            "id": str(uuid.uuid4()),
            "colony_id": self._colony_id,
            "session_id": self._current_session,
            "event_type": event_type_str,
            "source": source,
            "data": data or {},
            "timestamp": time.time(),
            "datetime": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            self._events.append(event)
            self._counts[event_type_str] += 1
            if self._first_event is None:
                self._first_event = event["timestamp"]
            self._last_event = event["timestamp"]

            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

        await self._notify_memory(event)
        await self._notify_graph(event)

        logger.debug(
            "lifecycle_event colony=%s type=%s source=%s",
            self._colony_id,
            event_type_str,
            source,
        )

        return event

    async def record_task(
        self,
        task_id: str,
        task_type: str,
        status: str,
        agent_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        if status == "completed":
            et = LifecycleEventType.TASK_COMPLETED
        elif status == "failed":
            et = LifecycleEventType.TASK_FAILED
        else:
            et = LifecycleEventType.TASK_ASSIGNED

        return await self.record(et, {
            "task_id": task_id,
            "task_type": task_type,
            "status": status,
            "agent_id": agent_id,
            "error": error,
        })

    async def record_agent_event(
        self,
        agent_id: str,
        agent_type: str,
        event: str,
    ) -> dict[str, Any]:
        et = LifecycleEventType.AGENT_SPAWN if event == "spawn" else LifecycleEventType.AGENT_TERMINATE
        return await self.record(et, {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "event": event,
        })

    async def record_error(
        self,
        error_type: str,
        message: str,
        source: str = "system",
        context: Optional[dict] = None,
    ) -> dict[str, Any]:
        return await self.record(LifecycleEventType.ERROR, {
            "error_type": error_type,
            "message": message,
            "context": context or {},
        }, source=source)

    async def record_milestone(self, name: str, description: str) -> dict[str, Any]:
        return await self.record(LifecycleEventType.MILESTONE, {
            "milestone": name,
            "description": description,
        })

    async def get_history(
        self,
        event_type: Optional[str | LifecycleEventType] = None,
        source: Optional[str] = None,
        limit: int = 100,
        since: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            events = list(self._events)

        if event_type:
            et = event_type.value if isinstance(event_type, LifecycleEventType) else event_type
            events = [e for e in events if e["event_type"] == et]
        if source:
            events = [e for e in events if e["source"] == source]
        if since:
            events = [e for e in events if e["timestamp"] >= since]

        return events[-limit:]

    async def get_summary(self) -> dict[str, Any]:
        async with self._lock:
            counts = dict(self._counts)
            total = len(self._events)

        return {
            "colony_id": self._colony_id,
            "session_id": self._current_session,
            "boot_count": self._boot_count,
            "total_events": total,
            "event_counts": counts,
            "first_event": self._first_event,
            "last_event": self._last_event,
            "session_uptime": self._get_session_uptime(),
        }

    async def get_milestones(self) -> list[dict[str, Any]]:
        return await self.get_history(event_type=LifecycleEventType.MILESTONE, limit=100)

    async def get_errors(self, limit: int = 50) -> list[dict[str, Any]]:
        return await self.get_history(event_type=LifecycleEventType.ERROR, limit=limit)

    async def get_recent_activity(self, seconds: int = 300) -> list[dict[str, Any]]:
        since = time.time() - seconds
        return await self.get_history(since=since, limit=200)

    async def _notify_memory(self, event: dict[str, Any]) -> None:
        if not self._memory_system:
            return
        try:
            if hasattr(self._memory_system, "add"):
                if asyncio.iscoroutinefunction(self._memory_system.add):
                    await self._memory_system.add(
                        f"lifecycle:{event['event_type']}:{event['id']}",
                        json.dumps(event, default=str),
                        metadata={"type": "lifecycle", "colony": self._colony_id},
                    )
        except Exception as e:
            logger.debug("lifecycle_memory_error err=%s", e)

    async def _notify_graph(self, event: dict[str, Any]) -> None:
        if not self._graph_store:
            return
        try:
            if hasattr(self._graph_store, "find_or_create"):
                if asyncio.iscoroutinefunction(self._graph_store.find_or_create):
                    await self._graph_store.find_or_create("lifecycle_event", event["id"])
        except Exception as e:
            logger.debug("lifecycle_graph_error err=%s", e)

    async def _flush(self) -> None:
        if self._persist_path:
            try:
                os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
                async with self._lock:
                    data = {
                        "colony_id": self._colony_id,
                        "boot_count": self._boot_count,
                        "event_count": len(self._events),
                        "events": self._events[-1000:],
                        "counts": dict(self._counts),
                    }
                with open(self._persist_path, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            except Exception as e:
                logger.warning("lifecycle_flush_error err=%s", e)

    def _get_session_uptime(self) -> float:
        if self._first_event:
            return time.time() - self._first_event
        return 0.0

    def get_stats(self) -> dict[str, Any]:
        return {
            "colony_id": self._colony_id,
            "session_id": self._current_session,
            "boot_count": self._boot_count,
            "total_events": len(self._events),
            "event_counts": dict(self._counts),
            "uptime": self._get_session_uptime(),
        }
