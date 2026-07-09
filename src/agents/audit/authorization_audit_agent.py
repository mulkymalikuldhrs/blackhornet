"""AuthorizationAuditAgent — Authorization and RBAC validation."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

AUTHZ_ISSUES = {
    "missing_authorization": {"pattern": r"(?i)(no.*auth.*check|endpoint.*no.*permission)", "severity": "critical"},
    "privilege_escalation": {"pattern": r"(?i)(role.*admin.*assign|privilege.*escalat)", "severity": "critical"},
    "overprivileged_role": {"pattern": r"(?i)(role.*all.*permission|role.*wildcard)", "severity": "high"},
    "idor_vulnerability": {"pattern": r"(?i)(user.*id.*param.*no.*check|object.*id.*direct)", "severity": "high"},
    "missing_role_check": {"pattern": r"(?i)(action.*no.*role.*verify|operation.*no.*check)", "severity": "high"},
    "default_role_permission": {"pattern": r"(?i)(default.*role.*admin|anonymous.*write)", "severity": "critical"},
}


class AuthorizationAuditAgent(BaseAgent):
    """Authorization and RBAC validation agent.

    Features
    --------
    * Role-based access control validation
    * Privilege escalation detection
    * IDOR vulnerability identification
    * Permission boundary verification
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []

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
        if msg_type == "authz_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "authorization_audit", "rbac_validation", "privilege_escalation_detection",
            "idor_detection", "permission_boundary_check",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        config_str = str(config)

        for issue_name, issue_config in AUTHZ_ISSUES.items():
            if re.search(issue_config["pattern"], config_str):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Authorization issue: {issue_name.replace('_', ' ')}",
                })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        severity_counts: Dict[str, int] = {}
        for f in self._findings:
            sev = f.get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        return {
            "success": True,
            "total_findings": len(self._findings),
            "severity_breakdown": severity_counts,
            "findings": self._findings[-20:],
        }
