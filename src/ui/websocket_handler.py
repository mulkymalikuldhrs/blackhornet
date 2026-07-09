"""WebSocketHandler — bridges EventBus events to WebSocket clients.

Provides real-time push updates from the colony ecosystem to browser/TUI clients.
Uses stdlib-compatible implementation (no external deps).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class WebSocketClient:
    """Represents a connected WebSocket client."""

    def __init__(self, client_id: str, send_fn: Callable[[str], None]):
        self.client_id = client_id
        self.send_fn = send_fn
        self.connected_at = time.time()
        self.last_heartbeat = time.time()
        self.subscriptions: Set[str] = set()

    def send(self, message: Dict[str, Any]) -> bool:
        try:
            self.send_fn(json.dumps(message))
            return True
        except Exception:
            return False

    def is_alive(self, timeout: float = 30.0) -> bool:
        return (time.time() - self.last_heartbeat) < timeout


class WebSocketHandler:
    """Manages WebSocket connections and bridges EventBus to real-time push.

    Usage:
        handler = WebSocketHandler(event_bus=event_bus)
        handler.start()

        # When a client connects (via upgrade or external WS library):
        handler.register_client(client_id, send_function)

        # Broadcast events are automatic via EventBus subscription
    """

    def __init__(self, event_bus: Any = None, broadcast_interval: float = 0.1):
        self._event_bus = event_bus
        self._broadcast_interval = broadcast_interval
        self._clients: Dict[str, WebSocketClient] = {}
        self._lock = threading.Lock()
        self._running = False
        self._broadcast_task: Optional[asyncio.Task] = None
        self._event_buffer: List[Dict[str, Any]] = []
        self._max_buffer = 1000

        # Auto-subscribe to event bus if provided
        if event_bus:
            event_bus.subscribe("*", self._on_event)

    def start(self) -> None:
        """Start the WebSocket handler."""
        self._running = True
        logger.info("WebSocketHandler started")

    def stop(self) -> None:
        """Stop the WebSocket handler."""
        self._running = False
        if self._event_bus:
            self._event_bus.unsubscribe("*", self._on_event)
        logger.info("WebSocketHandler stopped")

    def register_client(self, client_id: str, send_fn: Callable[[str], None]) -> WebSocketClient:
        """Register a new WebSocket client."""
        client = WebSocketClient(client_id, send_fn)
        with self._lock:
            self._clients[client_id] = client
        logger.info("WebSocket client connected: %s", client_id)
        return client

    def unregister_client(self, client_id: str) -> None:
        """Remove a WebSocket client."""
        with self._lock:
            self._clients.pop(client_id, None)
        logger.info("WebSocket client disconnected: %s", client_id)

    def get_client(self, client_id: str) -> Optional[WebSocketClient]:
        return self._clients.get(client_id)

    def get_client_count(self) -> int:
        return len(self._clients)

    def get_client_ids(self) -> List[str]:
        return list(self._clients.keys())

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> int:
        """Broadcast an event to all connected clients.

        Returns the number of clients that received the message.
        """
        message = {
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        }
        sent = 0
        dead_clients = []

        with self._lock:
            for client_id, client in self._clients.items():
                if client.send(message):
                    sent += 1
                else:
                    dead_clients.append(client_id)

        # Clean up dead connections
        for cid in dead_clients:
            self.unregister_client(cid)

        return sent

    def send_to(self, client_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Send an event to a specific client."""
        client = self.get_client(client_id)
        if client:
            return client.send({"type": event_type, "data": data, "timestamp": time.time()})
        return False

    def _on_event(self, event: Any) -> None:
        """Handle events from EventBus and broadcast to WebSocket clients."""
        if not self._running:
            return

        data = {
            "event_type": getattr(event, "type", "unknown"),
            "event_data": getattr(event, "data", {}),
            "source": getattr(event, "source", ""),
            "timestamp": getattr(event, "timestamp", time.time()),
        }
        self.broadcast("ecosystem.event", data)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "client_count": len(self._clients),
            "clients": list(self._clients.keys()),
        }
