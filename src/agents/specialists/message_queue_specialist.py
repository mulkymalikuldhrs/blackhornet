"""Message queue specialist — Message queue systems management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class MessageQueueSpecialist(BaseAgent):
    """Specialist agent for message queue systems management.

    Handles queue creation, message publishing, consumer management,
    dead letter queues, and queue monitoring.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._queues: Dict[str, Dict[str, Any]] = {}
        self._messages: Dict[str, List[Dict[str, Any]]] = {}
        self._consumers: Dict[str, List[Dict[str, Any]]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_queue":
            return await self._create_queue(task)
        elif action == "publish":
            return await self._publish_message(task)
        elif action == "consume":
            return await self._consume_message(task)
        elif action == "configure_dead_letter":
            return await self._configure_dead_letter(task)
        elif action == "get_queue_stats":
            return await self._get_queue_stats(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "queue_event":
            queue = message.get("payload", {}).get("queue", "")
            event = message.get("payload", {}).get("event", {})
            self._messages.setdefault(queue, []).append({**event, "received_at": time.time()})
            return {"event_received": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "queue_management", "message_publishing", "consumer_management",
            "dead_letter_handling", "queue_monitoring", "message_replay",
            "priority_queuing", "delayed_messages",
        ]

    async def _create_queue(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_queue")
        durable = task.payload.get("durable", True)
        max_length = task.payload.get("max_length", 10000)
        message_ttl_seconds = task.payload.get("message_ttl_seconds", 86400)

        queue = {
            "name": name,
            "durable": durable,
            "max_length": max_length,
            "message_ttl_seconds": message_ttl_seconds,
            "created_at": time.time(),
            "message_count": 0,
            "consumer_count": 0,
        }
        self._queues[name] = queue
        self._messages[name] = []
        return {"success": True, "queue": name, "config": queue}

    async def _publish_message(self, task: Task) -> Dict[str, Any]:
        queue = task.payload.get("queue", "default_queue")
        routing_key = task.payload.get("routing_key", "")
        body = task.payload.get("body", {})
        priority = task.payload.get("priority", 0)

        if queue not in self._messages:
            self._messages[queue] = []

        msg = {
            "message_id": f"msg-{int(time.time() * 1000)}",
            "routing_key": routing_key,
            "body": body,
            "priority": priority,
            "published_at": time.time(),
            "status": "published",
        }
        self._messages[queue].append(msg)
        if queue in self._queues:
            self._queues[queue]["message_count"] += 1

        return {"success": True, "message_id": msg["message_id"], "queue": queue}

    async def _consume_message(self, task: Task) -> Dict[str, Any]:
        queue = task.payload.get("queue", "default_queue")
        consumer_id = task.payload.get("consumer_id", "default_consumer")

        messages = self._messages.get(queue, [])
        pending = [m for m in messages if m.get("status") == "published"]

        if not pending:
            return {"success": True, "message": None, "queue": queue}

        msg = pending[0]
        msg["status"] = "consumed"
        msg["consumer_id"] = consumer_id
        msg["consumed_at"] = time.time()

        return {"success": True, "message": msg, "queue": queue}

    async def _configure_dead_letter(self, task: Task) -> Dict[str, Any]:
        queue = task.payload.get("queue", "default_queue")
        dlq_name = task.payload.get("dlq_name", f"{queue}-dlq")
        max_retries = task.payload.get("max_retries", 3)

        dlq_config = {
            "queue": queue,
            "dlq_name": dlq_name,
            "max_retries": max_retries,
            "requeue_on_success": False,
        }

        if queue in self._queues:
            self._queues[queue]["dead_letter_queue"] = dlq_config

        return {"success": True, "dlq_config": dlq_config}

    async def _get_queue_stats(self, task: Task) -> Dict[str, Any]:
        queue = task.payload.get("queue", "default_queue")
        messages = self._messages.get(queue, [])

        stats = {
            "queue": queue,
            "total_messages": len(messages),
            "published": sum(1 for m in messages if m.get("status") == "published"),
            "consumed": sum(1 for m in messages if m.get("status") == "consumed"),
            "failed": sum(1 for m in messages if m.get("status") == "failed"),
        }
        return {"success": True, "stats": stats}

    def _monitor(self) -> Dict[str, Any]:
        total_messages = sum(len(m) for m in self._messages.values())
        return {
            "success": True,
            "metrics": {
                "queues_count": len(self._queues),
                "total_messages": total_messages,
                "total_consumers": sum(c.get("consumer_count", 0) for c in self._queues.values()),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "message_queue",
            "metrics": self._monitor()["metrics"],
        }
