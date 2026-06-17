"""SessionRecorder — record and export session data to the graph.

Subscribes to EventBus events and records them to the graph store
via AutoGraphUpdater. Also provides direct sync recording methods.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionRecorder:
    """Record session data to the graph and export it."""

    def __init__(
        self,
        auto_updater: Any = None,
        graph_store: Any = None,
        entity_tracker: Any = None,
        relationship_mapper: Any = None,
        event_bus: Any = None,
    ):
        self._updater = auto_updater
        self._graph = graph_store
        self._tracker = entity_tracker
        self._mapper = relationship_mapper
        self._event_bus = event_bus
        self._session_data: List[Dict[str, Any]] = []
        self._export_dir: str = "/sdcard/dhaherlabs/blackhornet-worktree/data/session-export"

    def start(self) -> None:
        if self._event_bus is None:
            return
        try:
            self._event_bus.subscribe("action", self._on_event)
            self._event_bus.subscribe("observation", self._on_event)
            logger.info("SessionRecorder subscribed to EventBus")
        except Exception as e:
            logger.warning("Failed to subscribe to EventBus: %s", e)

    async def _on_event(self, event: Any) -> None:
        try:
            event_type = getattr(event, "event_type", None)
            if event_type is None:
                return
            type_str = event_type.value if hasattr(event_type, "value") else str(event_type)
            source = getattr(event, "source", "unknown") or "unknown"
            data = getattr(event, "data", {}) or {}

            if self._updater:
                self._updater.on_episode(source, type_str, str(data))
                if "conversation" in type_str.lower():
                    topic = data.get("topic", "unknown")
                    summary = data.get("summary", "")
                    participants = data.get("participants", [])
                    self._updater.on_conversation(topic, summary, participants)
                elif "decision" in type_str.lower():
                    agent_id = data.get("agent_id", source)
                    decision = data.get("decision", "")
                    context = data.get("context", "")
                    confidence = data.get("confidence", 0.5)
                    self._updater.on_decision(agent_id, decision, context, confidence)

            self._session_data.append({
                "type": type_str,
                "source": source,
                "data": data,
                "timestamp": time.time(),
            })
        except Exception as e:
            logger.warning("SessionRecorder event handler failed: %s", e)

    def record_conversation(
        self, topic: str, summary: str,
        entities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if self._updater:
            self._updater.on_conversation(topic, summary, entities or [])
        record: Dict[str, Any] = {
            "type": "conversation",
            "topic": topic,
            "summary": summary,
            "entities": entities or [],
            "timestamp": time.time(),
        }
        self._session_data.append(record)
        return record

    def record_decision(
        self, agent_id: str, decision: str,
        context: str, confidence: float = 0.5,
    ) -> Dict[str, Any]:
        if self._updater:
            self._updater.on_decision(agent_id, decision, context, confidence)
        record: Dict[str, Any] = {
            "type": "decision",
            "agent_id": agent_id,
            "decision": decision,
            "context": context,
            "confidence": confidence,
            "timestamp": time.time(),
        }
        self._session_data.append(record)
        return record

    def auto_export(self, export_dir: Optional[str] = None) -> Dict[str, Any]:
        target = export_dir or self._export_dir
        try:
            target = os.path.expanduser(target)
            os.makedirs(target, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            session_path = os.path.join(target, f"session_{timestamp}.json")
            with open(session_path, "w") as f:
                json.dump(self._session_data, f, indent=2)

            result: Dict[str, Any] = {
                "session_path": session_path,
                "records": len(self._session_data),
            }
            if self._updater:
                graph_result = self._updater.auto_export(target)
                result.update(graph_result)
            return result
        except Exception as e:
            logger.warning("Session export failed: %s", e)
            return {"error": str(e)}

    def get_session_data(self) -> List[Dict[str, Any]]:
        return list(self._session_data)
