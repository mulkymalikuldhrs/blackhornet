"""AccessControlAgent — Access control mechanism validation."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

ACCESS_ISSUES = {
    "missing_auth_check": {"pattern": r"(?i)(no.*auth.*check|endpoint.*no.*permission)", "severity": "critical"},
    "overprivileged_user": {"pattern": r"(?i)(user.*admin|role.*all.*permission)", "severity": "high"},
    "missing_least_privilege": {"pattern": r"(?i)(wildcard.*permission|role.*\*)", "severity": "high"},
    "no_access_logging": {"pattern": r"(?i)(no.*access.*log|no.*audit.*trail)", "severity": "medium"},
    "session_fixation": {"pattern": r"(?i)(session.*fix|session.*not.*rotat)", "severity": "high"},
    "missing_timeout": {"pattern": r"(?i)(no.*session.*timeout|no.*idle.*timeout)", "severity": "medium"},
    "default_permissions": {"pattern": r"(?i)(default.*permission|default.*access|default.*role)", "severity": "high"},
}


class AccessControlAgent(BaseAgent):
    """Access control mechanism validation agent.

    Features
    --------
    * Least privilege principle verification
    * Session management auditing
    * Access logging completeness
    * Permission boundary validation
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
        if msg_type == "access_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "access_control_audit", "least_privilege_validation",
            "session_management_audit", "permission_boundary_check",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        config_str = str(config)

        for issue_name, issue_config in ACCESS_ISSUES.items():
            if re.search(issue_config["pattern"], config_str):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Access control issue: {issue_name.replace('_', ' ')}",
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
