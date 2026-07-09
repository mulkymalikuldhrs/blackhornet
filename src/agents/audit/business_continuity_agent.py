"""BusinessContinuityAgent — Business continuity planning."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

BCP_COMPONENTS = {
    "business_impact_analysis": {"required": True, "severity": "critical"},
    "recovery_time_objectives": {"required": True, "severity": "critical"},
    "recovery_point_objectives": {"required": True, "severity": "critical"},
    "critical_process_identification": {"required": True, "severity": "critical"},
    "alternative_site_planning": {"required": True, "severity": "high"},
    "communication_plan": {"required": True, "severity": "high"},
    "testing_schedule": {"required": True, "severity": "medium"},
    "vendor_contingency": {"required": False, "severity": "medium"},
}


class BusinessContinuityAgent(BaseAgent):
    """Business continuity planning agent.

    Features
    --------
    * BCP completeness validation
    * RTO/RPO compliance checking
    * Critical process identification
    * Alternative site readiness assessment
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
        if msg_type == "bcp_query":
            return {"readiness_score": self._readiness_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "business_continuity_audit", "bcp_validation", "rto_rpo_checking",
            "critical_process_identification", "alternative_site_assessment",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        bcp_plan = task.payload.get("bcp_plan", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        components_present = 0

        for component, config in BCP_COMPONENTS.items():
            if component in bcp_plan and bcp_plan[component]:
                components_present += 1
            elif config["required"]:
                findings.append({
                    "type": "missing_component",
                    "severity": config["severity"],
                    "component": component,
                    "target": target,
                    "description": f"Missing BCP component: {component.replace('_', ' ')}",
                })

        self._readiness_score = components_present / len(BCP_COMPONENTS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "readiness_score": self._readiness_score,
            "components_present": components_present,
            "components_total": len(BCP_COMPONENTS),
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
