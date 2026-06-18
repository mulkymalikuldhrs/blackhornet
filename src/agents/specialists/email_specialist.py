"""Email specialist — Email infrastructure and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class EmailSpecialist(BaseAgent):
    """Specialist agent for email infrastructure and management.

    Handles email template management, delivery tracking, bounce handling,
    deliverability optimization, and email analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._email_log: List[Dict[str, Any]] = {}
        self._delivery_stats: Dict[str, int] = {"sent": 0, "delivered": 0, "bounced": 0, "opened": 0}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "send_email":
            return await self._send_email(task)
        elif action == "create_template":
            return await self._create_template(task)
        elif action == "track_delivery":
            return await self._track_delivery(task)
        elif action == "handle_bounce":
            return await self._handle_bounce(task)
        elif action == "get_analytics":
            return await self._get_analytics(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "email_event":
            event = message.get("payload", {})
            email_id = event.get("email_id", "")
            event_type = event.get("event", "")
            if email_id in self._email_log:
                self._email_log[email_id]["events"].append({**event, "timestamp": time.time()})
                if event_type == "delivered":
                    self._delivery_stats["delivered"] += 1
                elif event_type == "bounced":
                    self._delivery_stats["bounced"] += 1
                elif event_type == "opened":
                    self._delivery_stats["opened"] += 1
            return {"event_processed": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "email_sending", "template_management", "delivery_tracking",
            "bounce_handling", "deliverability_optimization", "email_analytics",
            "ab_testing", "scheduling",
        ]

    async def _send_email(self, task: Task) -> Dict[str, Any]:
        to = task.payload.get("to", "")
        subject = task.payload.get("subject", "")
        template = task.payload.get("template")
        body = task.payload.get("body", "")
        from_address = task.payload.get("from", "noreply@example.com")

        email_id = f"email-{int(time.time() * 1000)}"
        email = {
            "id": email_id,
            "to": to,
            "from": from_address,
            "subject": subject,
            "body": body,
            "template": template,
            "status": "sent",
            "sent_at": time.time(),
            "events": [],
        }
        self._email_log[email_id] = email
        self._delivery_stats["sent"] += 1
        return {"success": True, "email_id": email_id, "to": to}

    async def _create_template(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_template")
        subject = task.payload.get("subject", "")
        html_body = task.payload.get("html_body", "")
        text_body = task.payload.get("text_body", "")

        template = {
            "name": name,
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "created_at": time.time(),
            "usage_count": 0,
        }
        self._templates[name] = template
        return {"success": True, "template": name}

    async def _track_delivery(self, task: Task) -> Dict[str, Any]:
        email_id = task.payload.get("email_id", "")
        email = self._email_log.get(email_id, {})
        return {"success": True, "email_id": email_id, "status": email.get("status", "unknown"), "events": email.get("events", [])}

    async def _handle_bounce(self, task: Task) -> Dict[str, Any]:
        email_id = task.payload.get("email_id", "")
        bounce_type = task.payload.get("bounce_type", "hard")
        reason = task.payload.get("reason", "unknown")

        if email_id in self._email_log:
            self._email_log[email_id]["status"] = "bounced"
            self._email_log[email_id]["bounce_type"] = bounce_type
            self._email_log[email_id]["bounce_reason"] = reason

        return {"success": True, "email_id": email_id, "bounce_type": bounce_type, "action": "suppress" if bounce_type == "hard" else "retry"}

    async def _get_analytics(self, task: Task) -> Dict[str, Any]:
        time_range = task.payload.get("time_range", 86400)
        start_time = time.time() - time_range

        recent = {k: v for k, v in self._email_log.items() if v.get("sent_at", 0) >= start_time}
        delivery_rate = (self._delivery_stats["delivered"] / max(1, self._delivery_stats["sent"])) * 100
        open_rate = (self._delivery_stats["opened"] / max(1, self._delivery_stats["delivered"])) * 100

        return {
            "success": True,
            "stats": {
                **self._delivery_stats,
                "delivery_rate": round(delivery_rate, 1),
                "open_rate": round(open_rate, 1),
                "total_emails": len(recent),
            },
        }

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "templates_count": len(self._templates),
                "total_emails": len(self._email_log),
                **self._delivery_stats,
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "email",
            "metrics": self._monitor()["metrics"],
        }
