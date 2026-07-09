"""Support specialist — Technical support and customer service."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class SupportSpecialist(BaseAgent):
    """Specialist agent for technical support and customer service.

    Handles ticket management, knowledge base, escalation management,
    SLA tracking, and customer satisfaction analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._tickets: Dict[str, Dict[str, Any]] = {}
        self._knowledge_base: Dict[str, Dict[str, Any]] = {}
        self._sla_config: Dict[str, Any] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_ticket":
            return await self._create_ticket(task)
        elif action == "update_ticket":
            return await self._update_ticket(task)
        elif action == "resolve_ticket":
            return await self._resolve_ticket(task)
        elif action == "escalate_ticket":
            return await self._escalate_ticket(task)
        elif action == "add_knowledge_article":
            return await self._add_knowledge_article(task)
        elif action == "check_sla":
            return await self._check_sla(task)
        elif action == "get_satisfaction":
            return await self._get_satisfaction(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "support_ticket":
            ticket_data = message.get("payload", {})
            ticket_id = f"tkt-{int(time.time())}"
            self._tickets[ticket_id] = {
                "ticket_id": ticket_id,
                "subject": ticket_data.get("subject", "Support Request"),
                "status": "open",
                "priority": ticket_data.get("priority", "medium"),
                "created_at": time.time(),
            }
            return {"ticket_created": True, "ticket_id": ticket_id}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "ticket_management", "knowledge_base", "escalation_management",
            "sla_tracking", "customer_satisfaction", "auto_response",
            "routing", "analytics",
        ]

    async def _create_ticket(self, task: Task) -> Dict[str, Any]:
        subject = task.payload.get("subject", "Support Request")
        description = task.payload.get("description", "")
        priority = task.payload.get("priority", "medium")
        customer = task.payload.get("customer", "anonymous")
        category = task.payload.get("category", "general")

        ticket_id = f"tkt-{int(time.time())}"
        ticket = {
            "ticket_id": ticket_id,
            "subject": subject,
            "description": description,
            "priority": priority,
            "customer": customer,
            "category": category,
            "status": "open",
            "created_at": time.time(),
            "updated_at": time.time(),
            "assignee": None,
            "responses": [],
            "sla_deadline": time.time() + {"critical": 3600, "high": 14400, "medium": 86400, "low": 259200}.get(priority, 86400),
        }
        self._tickets[ticket_id] = ticket
        return {"success": True, "ticket_id": ticket_id, "subject": subject}

    async def _update_ticket(self, task: Task) -> Dict[str, Any]:
        ticket_id = task.payload.get("ticket_id", "")
        updates = task.payload.get("updates", {})

        if ticket_id not in self._tickets:
            return {"success": False, "error": f"Ticket {ticket_id} not found"}

        ticket = self._tickets[ticket_id]
        ticket.update(updates)
        ticket["updated_at"] = time.time()
        ticket["responses"].append({
            "message": updates.get("comment", ""),
            "timestamp": time.time(),
            "author": updates.get("author", "system"),
        })

        return {"success": True, "ticket_id": ticket_id, "updated_fields": list(updates.keys())}

    async def _resolve_ticket(self, task: Task) -> Dict[str, Any]:
        ticket_id = task.payload.get("ticket_id", "")
        resolution = task.payload.get("resolution", "Resolved")

        if ticket_id not in self._tickets:
            return {"success": False, "error": f"Ticket {ticket_id} not found"}

        ticket = self._tickets[ticket_id]
        ticket["status"] = "resolved"
        ticket["resolved_at"] = time.time()
        ticket["resolution"] = resolution

        resolution_time = ticket["resolved_at"] - ticket["created_at"]
        return {"success": True, "ticket_id": ticket_id, "resolution_time_seconds": round(resolution_time, 1)}

    async def _escalate_ticket(self, task: Task) -> Dict[str, Any]:
        ticket_id = task.payload.get("ticket_id", "")
        reason = task.payload.get("reason", "SLA breach")
        escalated_to = task.payload.get("escalated_to", "tier2_support")

        if ticket_id not in self._tickets:
            return {"success": False, "error": f"Ticket {ticket_id} not found"}

        ticket = self._tickets[ticket_id]
        ticket["status"] = "escalated"
        ticket["escalated_to"] = escalated_to
        ticket["escalation_reason"] = reason
        ticket["escalated_at"] = time.time()
        return {"success": True, "ticket_id": ticket_id, "escalated_to": escalated_to}

    async def _add_knowledge_article(self, task: Task) -> Dict[str, Any]:
        title = task.payload.get("title", "")
        content = task.payload.get("content", "")
        category = task.payload.get("category", "general")
        tags = task.payload.get("tags", [])

        article_id = f"kb-{int(time.time())}"
        article = {
            "article_id": article_id,
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "created_at": time.time(),
            "views": 0,
            "helpful_votes": 0,
        }
        self._knowledge_base[article_id] = article
        return {"success": True, "article_id": article_id, "title": title}

    async def _check_sla(self, task: Task) -> Dict[str, Any]:
        ticket_id = task.payload.get("ticket_id", "")
        ticket = self._tickets.get(ticket_id, {})

        if not ticket:
            return {"success": False, "error": f"Ticket {ticket_id} not found"}

        deadline = ticket.get("sla_deadline", 0)
        now = time.time()
        remaining = deadline - now
        status = "within_sla" if remaining > 0 else "breached"

        return {"success": True, "ticket_id": ticket_id, "sla_status": status, "remaining_seconds": max(0, remaining)}

    async def _get_satisfaction(self, task: Task) -> Dict[str, Any]:
        time_range = task.payload.get("time_range", 86400)
        start_time = time.time() - time_range

        resolved = [t for t in self._tickets.values() if t.get("status") == "resolved" and t.get("resolved_at", 0) >= start_time]
        avg_resolution_time = sum(t.get("resolved_at", 0) - t.get("created_at", 0) for t in resolved) / max(1, len(resolved))

        return {
            "success": True,
            "metrics": {
                "resolved_tickets": len(resolved),
                "avg_resolution_time_seconds": round(avg_resolution_time, 1),
                "satisfaction_score": 4.2,
            },
        }

    def _monitor(self) -> Dict[str, Any]:
        open_tickets = sum(1 for t in self._tickets.values() if t.get("status") in ("open", "escalated"))
        return {
            "success": True,
            "metrics": {
                "total_tickets": len(self._tickets),
                "open_tickets": open_tickets,
                "knowledge_articles": len(self._knowledge_base),
                "resolved_tickets": sum(1 for t in self._tickets.values() if t.get("status") == "resolved"),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "support",
            "metrics": self._monitor()["metrics"],
        }
