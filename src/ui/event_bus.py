from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from src.core.event_bus import EventBus as CoreEventBus

logger = logging.getLogger(__name__)


@dataclass
class Event:
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


EventHandler = Callable[[Event], None]


class EventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = 500
        self._core = CoreEventBus.get_instance()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event: Event) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.type, []))
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        logger.debug("EventBus.publish: type=%s source=%s", event.type, event.source)
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.error("EventBus handler error: %s", exc)

    def get_history(self, event_type: str = "", limit: int = 50) -> List[Event]:
        if event_type:
            filtered = [e for e in self._history if e.type == event_type]
            return filtered[-limit:]
        return self._history[-limit:]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def count(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self._history:
            counts[e.type] = counts.get(e.type, 0) + 1
        return counts
