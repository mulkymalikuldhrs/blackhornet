"""GraphifyPipeline — bridges memory events, sessions, and agent state into GraphStore."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.graph.graph_store import GraphStore

logger = logging.getLogger(__name__)


@dataclass
class GraphifyEvent:
    event_type: str = ""
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


EventHandler = Callable[[GraphifyEvent], None]


class GraphifyPipeline:
    """Bridges events from MemorySystem, SessionRecorder, EntityTracker,
    and agent lifecycle into a single GraphStore.

    External agents (Hermes, audit agents, etc.) push events via
    ``emit()``.  The pipeline auto-routes each event type to the
    appropriate graph operation.
    """

    def __init__(self, graph_store: Optional[GraphStore] = None):
        self.graph = graph_store or GraphStore()
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._event_log: List[GraphifyEvent] = []
        self._max_log = 5000

        self._register_builtins()

    def _register_builtins(self):
        self.on("memory_add", self._on_memory_add)
        self.on("concept_add", self._on_concept_add)
        self.on("conversation", self._on_conversation)
        self.on("decision", self._on_decision)
        self.on("entity", self._on_entity)
        self.on("audit_finding", self._on_audit_finding)
        self.on("agent_state", self._on_agent_state)
        self.on("session_event", self._on_session_event)

    def on(self, event_type: str, handler: EventHandler):
        self._handlers.setdefault(event_type, []).append(handler)

    def off(self, event_type: str, handler: EventHandler):
        self._handlers.get(event_type, []).remove(handler)

    def emit(self, event_type: str, source: str = "", data: Dict[str, Any] = None):
        event = GraphifyEvent(
            event_type=event_type,
            source=source,
            data=data or {},
            timestamp=time.time(),
        )
        self._event_log.append(event)
        if len(self._event_log) > self._max_log:
            self._event_log = self._event_log[-self._max_log // 2:]

        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.warning("Pipeline handler %s failed: %s", handler.__name__, e)

    # ── Built-in handlers ─────────────────────────────────────────

    def _on_memory_add(self, event: GraphifyEvent):
        node_id = self.graph.find_or_create(
            label=event.data.get("key", ""),
            node_type="memory",
        )
        if "value" in event.data:
            self.graph.add_node_property(node_id, "value_preview", str(event.data["value"])[:200])
        if event.source:
            source_id = self.graph.find_or_create(label=event.source, node_type="source")
            self.graph.add_edge(source_id, node_id, relation="produced")

    def _on_concept_add(self, event: GraphifyEvent):
        concept = event.data.get("concept", event.data.get("name", ""))
        if not concept:
            return
        node_id = self.graph.find_or_create(label=concept, node_type="concept")
        if "description" in event.data:
            self.graph.add_node_property(node_id, "description", str(event.data["description"])[:500])

    def _on_conversation(self, event: GraphifyEvent):
        session_id = event.data.get("session_id", "")
        user_msg = event.data.get("user", "")
        agent_msg = event.data.get("agent", "")

        if session_id:
            sess_node = self.graph.find_or_create(label=f"session:{session_id}", node_type="session")
            if event.source:
                src_node = self.graph.find_or_create(label=event.source, node_type="agent")
                self.graph.add_edge(src_node, sess_node, relation="participated_in")

        if user_msg:
            user_node = self.graph.find_or_create(
                label=f"msg:{hash(user_msg[:50])}",
                node_type="message",
            )
            self.graph.add_node_property(user_node, "preview", user_msg[:200])

        if agent_msg:
            agent_node = self.graph.find_or_create(
                label=f"msg:{hash(agent_msg[:50])}",
                node_type="message",
            )
            self.graph.add_node_property(agent_node, "preview", agent_msg[:200])

    def _on_decision(self, event: GraphifyEvent):
        decision = event.data.get("decision", event.data.get("action", "unknown"))
        node_id = self.graph.find_or_create(label=str(decision)[:100], node_type="decision")
        if "rationale" in event.data:
            self.graph.add_node_property(node_id, "rationale", str(event.data["rationale"])[:500])
        if event.source:
            src_id = self.graph.find_or_create(label=event.source, node_type="agent")
            self.graph.add_edge(src_id, node_id, relation="decided")

    def _on_entity(self, event: GraphifyEvent):
        entity = event.data.get("entity", event.data.get("name", ""))
        etype = event.data.get("entity_type", event.data.get("type", "unknown"))
        if not entity:
            return
        node_id = self.graph.find_or_create(label=str(entity)[:100], node_type=str(etype)[:50])
        if event.source:
            src_id = self.graph.find_or_create(label=event.source, node_type="source")
            self.graph.add_edge(src_id, node_id, relation="referenced")

    def _on_audit_finding(self, event: GraphifyEvent):
        finding = event.data.get("finding", event.data.get("title", "audit_issue"))
        severity = event.data.get("severity", "info")
        node_id = self.graph.find_or_create(label=str(finding)[:100], node_type=f"audit:{severity}")
        for k, v in event.data.items():
            self.graph.add_node_property(node_id, k, str(v)[:300])
        if event.source:
            src_id = self.graph.find_or_create(label=event.source, node_type="audit_agent")
            self.graph.add_edge(src_id, node_id, relation="reported")

    def _on_agent_state(self, event: GraphifyEvent):
        agent = event.data.get("agent", event.source)
        state = event.data.get("state", "unknown")
        if not agent:
            return
        node_id = self.graph.find_or_create(label=str(agent), node_type="agent")
        self.graph.add_node_property(node_id, "state", str(state)[:100])
        if "status" in event.data:
            self.graph.add_node_property(node_id, "status", str(event.data["status"])[:100])

    def _on_session_event(self, event: GraphifyEvent):
        session_id = event.data.get("session_id", "")
        action = event.data.get("action", "event")
        if not session_id:
            return
        node_id = self.graph.find_or_create(label=f"session:{session_id}", node_type="session_event")
        self.graph.add_node_property(node_id, "action", str(action)[:100])
        self.graph.add_node_property(node_id, "timestamp", str(event.timestamp))

    # ── Query / Export ────────────────────────────────────────────

    def export_json(self) -> Dict[str, Any]:
        return self.graph.export_json()

    def stats(self) -> Dict[str, Any]:
        gs = self.graph.stats()
        gs["event_log_size"] = len(self._event_log)
        gs["event_types"] = list(self._handlers.keys())
        return gs

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.graph.search(query, limit=limit)

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        events = self._event_log
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [
            {
                "event_type": e.event_type,
                "source": e.source,
                "data": e.data,
                "timestamp": e.timestamp,
            }
            for e in events[-limit:]
        ]

    def close(self):
        self.graph.close()
