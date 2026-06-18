"""Incident management specialist — Incident response and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class IncidentManagementSpecialist(BaseAgent):
    """Specialist agent for incident response and management.

    Handles incident detection, triage, response coordination,
    post-mortem analysis, and incident tracking.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._incidents: Dict[str, Dict[str, Any]] = {}
        self._runbooks: Dict[str, Dict[str, Any]] = {}
        self._post_mortems: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_incident":
            return await self._create_incident(task)
        elif action == "triage":
            return await self._triage(task)
        elif action == "respond":
            return await self._respond(task)
        elif action == "resolve":
            return await self._resolve(task)
        elif action == "create_runbook":
            return await self._create_runbook(task)
        elif action == "post_mortem":
            return await self._post_mortem(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "incident_alert":
            alert = message.get("payload", {})
            incident_id = f"inc-{int(time.time())}"
            self._incidents[incident_id] = {
                "incident_id": incident_id,
                "title": alert.get("title", "Auto-detected incident"),
                "severity": alert.get("severity", "medium"),
                "status": "detected",
                "detected_at": time.time(),
                "timeline": [{"event": "detected", "timestamp": time.time()}],
            }
            return {"incident_created": True, "incident_id": incident_id}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "incident_detection", "triage", "response_coordination",
            "resolution_tracking", "post_mortem_analysis", "runbook_management",
            "escalation_management", "incident_reporting",
        ]

    async def _create_incident(self, task: Task) -> Dict[str, Any]:
        title = task.payload.get("title", "New Incident")
        severity = task.payload.get("severity", "medium")
        description = task.payload.get("description", "")
        affected_services = task.payload.get("affected_services", [])

        incident_id = f"inc-{int(time.time())}"
        incident = {
            "incident_id": incident_id,
            "title": title,
            "severity": severity,
            "description": description,
            "affected_services": affected_services,
            "status": "detected",
            "detected_at": time.time(),
            "timeline": [{"event": "created", "timestamp": time.time(), "details": description}],
            "responders": [],
        }
        self._incidents[incident_id] = incident
        return {"success": True, "incident_id": incident_id, "severity": severity}

    async def _triage(self, task: Task) -> Dict[str, Any]:
        incident_id = task.payload.get("incident_id", "")
        if incident_id not in self._incidents:
            return {"success": False, "error": f"Incident {incident_id} not found"}

        incident = self._incidents[incident_id]
        incident["status"] = "triaged"
        incident["triaged_at"] = time.time()
        incident["priority"] = task.payload.get("priority", "high")
        incident["assigned_to"] = task.payload.get("assigned_to", "oncall_team")
        incident["timeline"].append({"event": "triaged", "timestamp": time.time()})

        return {"success": True, "incident_id": incident_id, "status": "triaged"}

    async def _respond(self, task: Task) -> Dict[str, Any]:
        incident_id = task.payload.get("incident_id", "")
        action = task.payload.get("action", "investigate")
        responder = task.payload.get("responder", "system")

        if incident_id not in self._incidents:
            return {"success": False, "error": f"Incident {incident_id} not found"}

        incident = self._incidents[incident_id]
        incident["status"] = "responding"
        incident["responders"].append(responder)
        incident["timeline"].append({
            "event": "response_action",
            "action": action,
            "responder": responder,
            "timestamp": time.time(),
        })

        return {"success": True, "incident_id": incident_id, "action": action}

    async def _resolve(self, task: Task) -> Dict[str, Any]:
        incident_id = task.payload.get("incident_id", "")
        resolution = task.payload.get("resolution", "resolved")
        root_cause = task.payload.get("root_cause", "unknown")

        if incident_id not in self._incidents:
            return {"success": False, "error": f"Incident {incident_id} not found"}

        incident = self._incidents[incident_id]
        incident["status"] = "resolved"
        incident["resolved_at"] = time.time()
        incident["resolution"] = resolution
        incident["root_cause"] = root_cause
        incident["timeline"].append({"event": "resolved", "timestamp": time.time()})

        duration = incident["resolved_at"] - incident["detected_at"]
        return {"success": True, "incident_id": incident_id, "duration_seconds": round(duration, 1)}

    async def _create_runbook(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_runbook")
        scenario = task.payload.get("scenario", "generic")
        steps = task.payload.get("steps", [])

        runbook = {
            "name": name,
            "scenario": scenario,
            "steps": steps,
            "created_at": time.time(),
            "usage_count": 0,
        }
        self._runbooks[name] = runbook
        return {"success": True, "runbook": name, "steps": len(steps)}

    async def _post_mortem(self, task: Task) -> Dict[str, Any]:
        incident_id = task.payload.get("incident_id", "")
        findings = task.payload.get("findings", [])
        action_items = task.payload.get("action_items", [])

        pm = {
            "incident_id": incident_id,
            "findings": findings,
            "action_items": action_items,
            "generated_at": time.time(),
            "status": "draft",
        }
        self._post_mortems[incident_id] = pm
        return {"success": True, "incident_id": incident_id, "findings_count": len(findings)}

    def _monitor(self) -> Dict[str, Any]:
        open_incidents = sum(1 for i in self._incidents.values() if i.get("status") not in ("resolved", "closed"))
        return {
            "success": True,
            "metrics": {
                "total_incidents": len(self._incidents),
                "open_incidents": open_incidents,
                "runbooks_count": len(self._runbooks),
                "post_mortems_count": len(self._post_mortems),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "incident_management",
            "metrics": self._monitor()["metrics"],
        }
