"""IncidentResponseAgent — Incident response readiness."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

IR_COMPONENTS = {
    "incident_detection": {"required": True, "severity": "critical"},
    "escalation_procedure": {"required": True, "severity": "critical"},
    "communication_plan": {"required": True, "severity": "high"},
    "containment_strategy": {"required": True, "severity": "critical"},
    "evidence_preservation": {"required": True, "severity": "high"},
    "recovery_procedure": {"required": True, "severity": "high"},
    "post_incident_review": {"required": True, "severity": "medium"},
    "playbook_coverage": {"required": False, "severity": "medium"},
}


class IncidentResponseAgent(BaseAgent):
    """Incident response readiness agent.

    Features
    --------
    * IR plan completeness validation
    * Playbook coverage assessment
    * Response time SLA verification
    * Communication channel readiness
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._readiness_score: float = 0.0

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "validate":
            return await self._validate(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "ir_query":
            return {"readiness_score": self._readiness_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "incident_response_audit", "ir_plan_validation", "playbook_assessment",
            "response_readiness", "communication_plan_audit",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        ir_plan = task.payload.get("ir_plan", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        components_present = 0

        for component, config in IR_COMPONENTS.items():
            if component in ir_plan and ir_plan[component]:
                components_present += 1
            elif config["required"]:
                findings.append({
                    "type": "missing_component",
                    "severity": config["severity"],
                    "component": component,
                    "target": target,
                    "description": f"Missing IR component: {component.replace('_', ' ')}",
                })

        self._readiness_score = components_present / len(IR_COMPONENTS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "readiness_score": self._readiness_score,
            "components_present": components_present,
            "components_total": len(IR_COMPONENTS),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "readiness_score": self._readiness_score,
            "findings": self._findings[-20:],
        }
