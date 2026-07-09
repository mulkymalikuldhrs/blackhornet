"""TypeScript Bridge — compatibility layer for Autonomous Organism TS colony.

Allows BH Python agents to communicate with AO TypeScript agents
via standardized bridge messages and event bus integration.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional


class BridgeDirection(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class BridgeMessage:
    id: str
    bridge_id: str
    direction: BridgeDirection
    content: str
    message_type: str = "text"
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = ""
    target: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if isinstance(self.direction, str):
            self.direction = BridgeDirection(self.direction)


class TypeScriptBridge:
    """Bridge for TS colony compatibility — mirrors AO's BaseBridge pattern."""

    def __init__(self, bridge_id: str, bridge_type: str, name: str, enabled: bool = True) -> None:
        self.id = bridge_id
        self.type = bridge_type
        self.name = name
        self.enabled = enabled
        self._handlers: dict[str, list[Callable]] = {}
        self._messages: list[BridgeMessage] = []
        self._connected = False

    def connect(self) -> bool:
        if self.enabled:
            self._connected = True
            self._emit("bridge.connected", {"bridgeId": self.id, "type": self.type})
            return True
        return False

    def disconnect(self) -> None:
        self._connected = False
        self._emit("bridge.disconnected", {"bridgeId": self.id})

    def send(self, target: str, content: str, message_type: str = "text", metadata: Optional[dict] = None) -> BridgeMessage:
        msg = BridgeMessage(
            id=str(uuid.uuid4()),
            bridge_id=self.id,
            direction=BridgeDirection.OUTBOUND,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            timestamp=time.time(),
            source=self.id,
            target=target,
        )
        self._messages.append(msg)
        self._emit("bridge.message", asdict(msg))
        return msg

    def receive(self, source: str, content: str, message_type: str = "text") -> BridgeMessage:
        msg = BridgeMessage(
            id=str(uuid.uuid4()),
            bridge_id=self.id,
            direction=BridgeDirection.INBOUND,
            content=content,
            message_type=message_type,
            timestamp=time.time(),
            source=source,
            target=self.id,
        )
        self._messages.append(msg)
        self._emit("bridge.message", asdict(msg))
        return msg

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def _emit(self, event: str, payload: Any) -> None:
        if event in self._handlers:
            for handler in self._handlers[event]:
                try:
                    result = handler(payload)
                    if hasattr(result, "__await__"):
                        pass
                except Exception:
                    pass

    def get_messages(self, limit: int = 50) -> list[BridgeMessage]:
        return self._messages[-limit:]

    def status(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "enabled": self.enabled,
            "connected": self._connected,
            "message_count": len(self._messages),
        }
