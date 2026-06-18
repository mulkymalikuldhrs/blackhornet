"""AuthenticationAuditAgent — Authentication mechanism validation."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

AUTH_ISSUES = {
    "weak_password_policy": {"pattern": r"(?i)(password.*min.*[0-6]|no.*password.*policy)", "severity": "high"},
    "missing_mfa": {"pattern": r"(?i)(no.*multi.*factor|no.*mfa|no.*2fa)", "severity": "high"},
    "hardcoded_credentials": {"pattern": r"(?i)(password\s*[:=]\s*['\"][^'\"]+)", "severity": "critical"},
    "insecure_session": {"pattern": r"(?i)(session.*http|cookie.*secure.*false)", "severity": "high"},
    "brute_force_no_protection": {"pattern": r"(?i)(no.*rate.*limit.*login|no.*lockout)", "severity": "medium"},
    "jwt_weak_secret": {"pattern": r"(?i)(jwt.*secret.*[:=]\s*['\"][^'\"]{1,16})", "severity": "critical"},
}


class AuthenticationAuditAgent(BaseAgent):
    """Authentication mechanism validation agent.

    Features
    --------
    * Password policy compliance checking
    * Multi-factor authentication verification
    * Session security validation
    * JWT configuration auditing
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
        if msg_type == "auth_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "authentication_audit", "password_policy_check", "mfa_verification",
            "session_security", "jwt_audit",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        config_str = str(config)

        for issue_name, issue_config in AUTH_ISSUES.items():
            if re.search(issue_config["pattern"], config_str):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Auth issue: {issue_name.replace('_', ' ')}",
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
