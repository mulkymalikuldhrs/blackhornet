"""SMS specialist — SMS integration and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class SmsSpecialist(BaseAgent):
    """Specialist agent for SMS integration and management.

    Handles SMS sending, template management, delivery tracking,
    opt-out management, and two-way messaging.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._sms_log: List[Dict[str, Any]] = []
        self._opt_outs: Dict[str, float] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "send_sms":
            return await self._send_sms(task)
        elif action == "create_template":
            return await self._create_template(task)
        elif action == "track_delivery":
            return await self._track_delivery(task)
        elif action == "handle_opt_out":
            return await self._handle_opt_out(task)
        elif action == "handle_incoming":
            return await self._handle_incoming(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "sms_delivery":
            sms_id = message.get("payload", {}).get("sms_id", "")
            status = message.get("payload", {}).get("status", "unknown")
            for sms in self._sms_log:
                if sms.get("id") == sms_id:
                    sms["status"] = status
                    break
            return {"status_updated": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "sms_sending", "template_management", "delivery_tracking",
            "opt_out_management", "two_way_messaging", "bulk_sms",
            "scheduled_sms", "delivery_reporting",
        ]

    async def _send_sms(self, task: Task) -> Dict[str, Any]:
        to = task.payload.get("to", "")
        message = task.payload.get("message", "")
        from_number = task.payload.get("from", "+1234567890")
        template = task.payload.get("template")

        sms_id = f"sms-{int(time.time() * 1000)}"
        sms = {
            "id": sms_id,
            "to": to,
            "from": from_number,
            "message": message,
            "template": template,
            "status": "sent",
            "sent_at": time.time(),
            "char_count": len(message),
            "segments": (len(message) // 160) + 1,
        }
        self._sms_log.append(sms)
        return {"success": True, "sms_id": sms_id, "to": to, "segments": sms["segments"]}

    async def _create_template(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_template")
        body = task.payload.get("body", "")
        variables = task.payload.get("variables", [])

        template = {
            "name": name,
            "body": body,
            "variables": variables,
            "created_at": time.time(),
            "usage_count": 0,
        }
        self._templates[name] = template
        return {"success": True, "template": name, "variables": variables}

    async def _track_delivery(self, task: Task) -> Dict[str, Any]:
        sms_id = task.payload.get("sms_id", "")
        sms = next((s for s in self._sms_log if s.get("id") == sms_id), None)
        if not sms:
            return {"success": False, "error": f"SMS {sms_id} not found"}
        return {"success": True, "sms_id": sms_id, "status": sms.get("status", "unknown")}

    async def _handle_opt_out(self, task: Task) -> Dict[str, Any]:
        phone = task.payload.get("phone", "")
        action = task.payload.get("action", "opt_out")

        if action == "opt_out":
            self._opt_outs[phone] = time.time()
            return {"success": True, "phone": phone, "status": "opted_out"}
        elif action == "opt_in":
            self._opt_outs.pop(phone, None)
            return {"success": True, "phone": phone, "status": "opted_in"}
        elif action == "check":
            is_opted_out = phone in self._opt_outs
            return {"success": True, "phone": phone, "opted_out": is_opted_out}
        return {"success": False, "error": f"Unknown opt action: {action}"}

    async def _handle_incoming(self, task: Task) -> Dict[str, Any]:
        from_number = task.payload.get("from", "")
        message = task.payload.get("message", "")

        response = {"received": True, "from": from_number, "message": message}
        if message.lower() == "stop":
            self._opt_outs[from_number] = time.time()
            response["action"] = "opt_out"
        elif message.lower() == "start":
            self._opt_outs.pop(from_number, None)
            response["action"] = "opt_in"

        return {"success": True, "response": response}

    def _monitor(self) -> Dict[str, Any]:
        delivered = sum(1 for s in self._sms_log if s.get("status") == "delivered")
        return {
            "success": True,
            "metrics": {
                "templates_count": len(self._templates),
                "total_sms": len(self._sms_log),
                "delivered": delivered,
                "opted_out": len(self._opt_outs),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "sms",
            "metrics": self._monitor()["metrics"],
        }
