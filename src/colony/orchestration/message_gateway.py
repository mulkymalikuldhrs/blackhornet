"""DeerFlow-inspired message gateway for inter-agent communication."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MessageType(Enum):
    TASK = "task"
    RESULT = "result"
    QUERY = "query"
    BROADCAST = "broadcast"
    ERROR = "error"


@dataclass
class Message:
    msg_id: str
    msg_type: MessageType
    source: str
    target: Optional[str]
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.msg_id:
            self.msg_id = f"msg-{uuid.uuid4().hex[:8]}"


class MessageGateway:
    """Pub/sub message gateway for agent-to-agent communication."""

    def __init__(self) -> None:
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_log: List[Message] = []
        self.pending: List[Message] = []

    def subscribe(self, channel: str, handler: Callable) -> None:
        self.subscribers.setdefault(channel, []).append(handler)

    def unsubscribe(self, channel: str, handler: Callable) -> None:
        handlers = self.subscribers.get(channel, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, message: Message) -> None:
        self.message_log.append(message)
        channel = message.target or message.msg_type.value
        handlers = self.subscribers.get(channel, []) + self.subscribers.get("*", [])

        for handler in handlers:
            try:
                handler(message)
            except Exception:
                self.pending.append(message)

    def send_to_agent(
        self,
        target: str,
        payload: Dict[str, Any],
        msg_type: MessageType = MessageType.TASK,
    ) -> str:
        msg = Message(
            msg_id=f"msg-{uuid.uuid4().hex[:8]}",
            msg_type=msg_type,
            source="gateway",
            target=target,
            payload=payload,
        )
        self.publish(msg)
        return msg.msg_id

    def broadcast(
        self,
        payload: Dict[str, Any],
        msg_type: MessageType = MessageType.BROADCAST,
    ) -> str:
        msg = Message(
            msg_id=f"msg-{uuid.uuid4().hex[:8]}",
            msg_type=msg_type,
            source="gateway",
            target=None,
            payload=payload,
        )
        self.publish(msg)
        return msg.msg_id

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self.message_log),
            "pending": len(self.pending),
            "subscribers": len(self.subscribers),
            "channels": list(self.subscribers.keys()),
        }
