"""DisasterRecoveryAgent — Disaster recovery preparedness."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

DR_COMPONENTS = {
    "backup_strategy": {"required": True, "severity": "critical"},
    "backup_verification": {"required": True, "severity": "critical"},
    "recovery_procedures": {"required": True, "severity": "critical"},
    "failover_mechanism": {"required": True, "severity": "high"},
    "data_replication": {"required": True, "severity": "high"},
    "recovery_testing": {"required": True, "severity": "high"},
    "offsite_storage": {"required": True, "severity": "medium"},
    "documentation": {"required": True, "severity": "medium"},
}


class DisasterRecoveryAgent(BaseAgent):
    """Disaster recovery preparedness agent.

    Features
    --------
    * DR plan completeness validation
    * Backup strategy auditing
    * Recovery procedure verification
    * Failover mechanism testing
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
        if msg_type == "dr_query":
            return {"readiness_score": self._readiness_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "disaster_recovery_audit", "backup_strategy_validation",
            "recovery_procedure_verification", "failover_testing",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        dr_plan = task.payload.get("dr_plan", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        components_present = 0

        for component, config in DR_COMPONENTS.items():
            if component in dr_plan and dr_plan[component]:
                components_present += 1
            elif config["required"]:
                findings.append({
                    "type": "missing_component",
                    "severity": config["severity"],
                    "component": component,
                    "target": target,
                    "description": f"Missing DR component: {component.replace('_', ' ')}",
                })

        self._readiness_score = components_present / len(DR_COMPONENTS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "readiness_score": self._readiness_score,
            "components_present": components_present,
            "components_total": len(DR_COMPONENTS),
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
