"""Notification specialist — Notification systems management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class NotificationSpecialist(BaseAgent):
    """Specialist agent for notification systems management.

    Handles multi-channel notification delivery, template management,
    preference management, and notification analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._notification_log: List[Dict[str, Any]] = []
        self._preferences: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "send":
            return await self._send_notification(task)
        elif action == "create_template":
            return await self._create_template(task)
        elif action == "set_preferences":
            return await self._set_preferences(task)
        elif action == "batch_send":
            return await self._batch_send(task)
        elif action == "get_analytics":
            return await self._get_analytics(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "notification_delivery":
            notif_id = message.get("payload", {}).get("notification_id", "")
            return next((n for n in self._notification_log if n.get("id") == notif_id), {"found": False})
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "multi_channel_delivery", "template_management", "preference_management",
            "batch_notifications", "notification_analytics", "scheduling",
            "priority_management", "rate_limiting",
        ]

    async def _send_notification(self, task: Task) -> Dict[str, Any]:
        channel = task.payload.get("channel", "email")
        recipient = task.payload.get("recipient", "")
        template = task.payload.get("template", "default")
        data = task.payload.get("data", {})
        priority = task.payload.get("priority", "normal")

        notif_id = f"notif-{int(time.time() * 1000)}"
        notification = {
            "id": notif_id,
            "channel": channel,
            "recipient": recipient,
            "template": template,
            "data": data,
            "priority": priority,
            "status": "sent",
            "sent_at": time.time(),
        }
        self._notification_log.append(notification)
        return {"success": True, "notification_id": notif_id, "channel": channel}

    async def _create_template(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_template")
        subject = task.payload.get("subject", "")
        body = task.payload.get("body", "")
        channels = task.payload.get("channels", ["email"])

        template = {
            "name": name,
            "subject": subject,
            "body": body,
            "channels": channels,
            "created_at": time.time(),
            "usage_count": 0,
        }
        self._templates[name] = template
        return {"success": True, "template": name, "channels": channels}

    async def _set_preferences(self, task: Task) -> Dict[str, Any]:
        user_id = task.payload.get("user_id", "default")
        preferences = task.payload.get("preferences", {})

        self._preferences[user_id] = {
            "user_id": user_id,
            "channels_enabled": preferences.get("channels_enabled", ["email"]),
            "quiet_hours": preferences.get("quiet_hours", {"start": "22:00", "end": "07:00"}),
            "frequency": preferences.get("frequency", "realtime"),
        }
        return {"success": True, "user_id": user_id, "preferences": self._preferences[user_id]}

    async def _batch_send(self, task: Task) -> Dict[str, Any]:
        recipients = task.payload.get("recipients", [])
        template = task.payload.get("template", "default")
        channel = task.payload.get("channel", "email")

        sent = 0
        for recipient in recipients:
            notif_id = f"notif-{int(time.time() * 1000)}-{sent}"
            self._notification_log.append({
                "id": notif_id,
                "channel": channel,
                "recipient": recipient,
                "template": template,
                "status": "sent",
                "sent_at": time.time(),
            })
            sent += 1

        return {"success": True, "sent_count": sent, "channel": channel}

    async def _get_analytics(self, task: Task) -> Dict[str, Any]:
        time_range = task.payload.get("time_range", 86400)
        start_time = time.time() - time_range

        recent = [n for n in self._notification_log if n.get("sent_at", 0) >= start_time]
        channels: Dict[str, int] = {}
        for n in recent:
            ch = n.get("channel", "unknown")
            channels[ch] = channels.get(ch, 0) + 1

        return {"success": True, "total_sent": len(recent), "by_channel": channels}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "templates_count": len(self._templates),
                "total_notifications": len(self._notification_log),
                "user_preferences": len(self._preferences),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "notification",
            "metrics": self._monitor()["metrics"],
        }
