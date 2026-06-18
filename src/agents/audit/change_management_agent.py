"""ChangeManagementAgent — Change management process audit."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

CHANGE_COMPONENTS = {
    "change_request_process": {"required": True, "severity": "high"},
    "approval_workflow": {"required": True, "severity": "critical"},
    "impact_assessment": {"required": True, "severity": "high"},
    "rollback_plan": {"required": True, "severity": "high"},
    "change_window": {"required": True, "severity": "medium"},
    "communication_plan": {"required": True, "severity": "medium"},
    "post_change_verification": {"required": True, "severity": "high"},
    "changeDocumentation": {"required": True, "severity": "medium"},
}


class ChangeManagementAgent(BaseAgent):
    """Change management process audit agent.

    Features
    --------
    * Change process completeness validation
    * Approval workflow auditing
    * Rollback plan verification
    * Post-change testing validation
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._process_score: float = 0.0

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
        if msg_type == "change_query":
            return {"process_score": self._process_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "change_management_audit", "approval_workflow_validation",
            "rollback_plan_verification", "post_change_validation",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        change_process = task.payload.get("change_process", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        components_present = 0

        for component, config in CHANGE_COMPONENTS.items():
            if component in change_process and change_process[component]:
                components_present += 1
            elif config["required"]:
                findings.append({
                    "type": "missing_component",
                    "severity": config["severity"],
                    "component": component,
                    "target": target,
                    "description": f"Missing change management component: {component.replace('_', ' ')}",
                })

        self._process_score = components_present / len(CHANGE_COMPONENTS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "process_score": self._process_score,
            "components_present": components_present,
            "components_total": len(CHANGE_COMPONENTS),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "process_score": self._process_score,
            "findings": self._findings[-20:],
        }
