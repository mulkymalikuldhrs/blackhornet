"""Change management specialist — Change management and control."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class ChangeManagementSpecialist(BaseAgent):
    """Specialist agent for change management and control.

    Handles change requests, approval workflows, impact analysis,
    rollback planning, and change tracking.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._change_requests: Dict[str, Dict[str, Any]] = {}
        self._approval_workflows: Dict[str, Dict[str, Any]] = {}
        self._change_log: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "submit_change":
            return await self._submit_change(task)
        elif action == "approve_change":
            return await self._approve_change(task)
        elif action == "reject_change":
            return await self._reject_change(task)
        elif action == "analyze_impact":
            return await self._analyze_impact(task)
        elif action == "plan_rollback":
            return await self._plan_rollback(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "change_event":
            event = message.get("payload", {})
            cr_id = event.get("change_id", "")
            if cr_id in self._change_requests:
                self._change_requests[cr_id].setdefault("events", []).append(event)
            return {"event_processed": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "change_request_management", "approval_workflow", "impact_analysis",
            "rollback_planning", "change_tracking", "risk_assessment",
            "scheduling", "communication",
        ]

    async def _submit_change(self, task: Task) -> Dict[str, Any]:
        title = task.payload.get("title", "Change Request")
        description = task.payload.get("description", "")
        change_type = task.payload.get("type", "normal")
        risk_level = task.payload.get("risk_level", "medium")
        requester = task.payload.get("requester", "system")

        cr_id = f"cr-{int(time.time())}"
        change_request = {
            "change_id": cr_id,
            "title": title,
            "description": description,
            "type": change_type,
            "risk_level": risk_level,
            "requester": requester,
            "status": "submitted",
            "submitted_at": time.time(),
            "approvals": [],
            "events": [],
        }
        self._change_requests[cr_id] = change_request
        self._change_log.append({"change_id": cr_id, "event": "submitted", "timestamp": time.time()})
        return {"success": True, "change_id": cr_id, "title": title}

    async def _approve_change(self, task: Task) -> Dict[str, Any]:
        change_id = task.payload.get("change_id", "")
        approver = task.payload.get("approver", "system")
        conditions = task.payload.get("conditions", [])

        if change_id not in self._change_requests:
            return {"success": False, "error": f"Change {change_id} not found"}

        cr = self._change_requests[change_id]
        cr["approvals"].append({"approver": approver, "timestamp": time.time(), "conditions": conditions})

        required_approvals = 2
        if len(cr["approvals"]) >= required_approvals:
            cr["status"] = "approved"
            cr["approved_at"] = time.time()

        self._change_log.append({"change_id": change_id, "event": "approved", "approver": approver, "timestamp": time.time()})
        return {"success": True, "change_id": change_id, "status": cr["status"]}

    async def _reject_change(self, task: Task) -> Dict[str, Any]:
        change_id = task.payload.get("change_id", "")
        reason = task.payload.get("reason", "Not specified")

        if change_id not in self._change_requests:
            return {"success": False, "error": f"Change {change_id} not found"}

        self._change_requests[change_id]["status"] = "rejected"
        self._change_requests[change_id]["rejection_reason"] = reason
        self._change_log.append({"change_id": change_id, "event": "rejected", "reason": reason, "timestamp": time.time()})
        return {"success": True, "change_id": change_id, "status": "rejected"}

    async def _analyze_impact(self, task: Task) -> Dict[str, Any]:
        change_id = task.payload.get("change_id", "")
        affected_systems = task.payload.get("affected_systems", [])

        impact = {
            "change_id": change_id,
            "affected_systems": affected_systems,
            "blast_radius": "low" if len(affected_systems) <= 2 else "medium" if len(affected_systems) <= 5 else "high",
            "downtime_estimate_minutes": len(affected_systems) * 5,
            "risk_assessment": "acceptable",
        }
        return {"success": True, "impact_analysis": impact}

    async def _plan_rollback(self, task: Task) -> Dict[str, Any]:
        change_id = task.payload.get("change_id", "")
        steps = task.payload.get("steps", [])
        trigger_conditions = task.payload.get("trigger_conditions", [])

        rollback_plan = {
            "change_id": change_id,
            "steps": steps,
            "trigger_conditions": trigger_conditions,
            "estimated_duration_minutes": len(steps) * 5,
            "created_at": time.time(),
        }
        if change_id in self._change_requests:
            self._change_requests[change_id]["rollback_plan"] = rollback_plan
        return {"success": True, "rollback_plan": rollback_plan}

    def _monitor(self) -> Dict[str, Any]:
        approved = sum(1 for c in self._change_requests.values() if c.get("status") == "approved")
        return {
            "success": True,
            "metrics": {
                "total_changes": len(self._change_requests),
                "approved_changes": approved,
                "pending_changes": sum(1 for c in self._change_requests.values() if c.get("status") == "submitted"),
                "change_log_entries": len(self._change_log),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "change_management",
            "metrics": self._monitor()["metrics"],
        }
