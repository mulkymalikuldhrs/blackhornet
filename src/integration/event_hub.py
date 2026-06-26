from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class EventHub:
    """Bridge between new EventBus (src/ui/event_bus.py) and BH's existing event bus.

    Forwards events in both directions so the UI and dashboard
    can see BH events, and BH modules can react to UI events.
    """

    def __init__(self, new_event_bus=None, bh_event_bus=None):
        self._new_bus = new_event_bus
        self._bh_bus = bh_event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def set_buses(self, new_event_bus=None, bh_event_bus=None):
        if new_event_bus:
            self._new_bus = new_event_bus
        if bh_event_bus:
            self._bh_bus = bh_event_bus

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._new_bus:
            self._new_bus.subscribe("bridge.in", self._forward_to_bh)
        if self._bh_bus and hasattr(self._bh_bus, "subscribe"):
            try:
                self._bh_bus.subscribe("bridge.in", self._forward_to_new)
            except Exception:
                logger.warning("BH event bus has no subscribe; skipping forward")
        logger.info("EventHub: bridging started")

    def stop(self) -> None:
        self._running = False
        if self._new_bus:
            self._new_bus.unsubscribe("bridge.in", self._forward_to_bh)
        logger.info("EventHub: bridging stopped")

    def _forward_to_bh(self, event: Any) -> None:
        if not self._bh_bus or not self._running:
            return
        try:
            if hasattr(self._bh_bus, "publish_event"):
                self._bh_bus.publish_event(
                    event_type=event.type,
                    data=event.data,
                )
            elif hasattr(self._bh_bus, "publish"):
                self._bh_bus.publish(event.type, event.data)
        except Exception as exc:
            logger.debug("EventHub forward to BH: %s", exc)

    def _forward_to_new(self, event_type: str, data: Dict[str, Any]) -> None:
        if not self._new_bus or not self._running:
            return
        try:
            from src.ui.event_bus import Event
            self._new_bus.publish(
                Event(type=event_type, data=data, source="blackhornet")
            )
        except Exception as exc:
            logger.debug("EventHub forward to new: %s", exc)

    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        if self._new_bus:
            from src.ui.event_bus import Event
            self._new_bus.publish(
                Event(type=event_type, data=data, source="event_hub")
            )
        if self._bh_bus:
            try:
                if hasattr(self._bh_bus, "publish_event"):
                    self._bh_bus.publish_event(event_type=event_type, data=data)
            except Exception:
                pass

    def status(self) -> Dict[str, bool]:
        return {
            "new_event_bus": self._new_bus is not None,
            "bh_event_bus": self._bh_bus is not None,
            "running": self._running,
        }
