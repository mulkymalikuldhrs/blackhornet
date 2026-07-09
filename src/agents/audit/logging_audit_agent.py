"""LoggingAuditAgent — Logging completeness and security."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

LOGGING_ISSUES = {
    "sensitive_data_logged": {"pattern": r"(?i)(log.*password|log.*secret|log.*token|log.*key)", "severity": "critical"},
    "pii_logged": {"pattern": r"(?i)(log.*email|log.*ssn|log.*credit.?card|log.*phone)", "severity": "high"},
    "missing_auth_logging": {"pattern": r"(?i)(no.*auth.*log|no.*login.*log)", "severity": "medium"},
    "missing_error_logging": {"pattern": r"(?i)(no.*error.*log|silent.*fail)", "severity": "medium"},
    "verbose_debug_logs": {"pattern": r"(?i)(debug.*print|console\.log|print\(.*debug)", "severity": "low"},
    "no_log_rotation": {"pattern": r"(?i)(no.*rotation|unlimited.*log)", "severity": "medium"},
    "log_injection": {"pattern": r"(?i)(log.*\+.*input|log.*format.*user)", "severity": "high"},
}


class LoggingAuditAgent(BaseAgent):
    """Logging completeness and security agent.

    Features
    --------
    * Sensitive data exposure detection in logs
    * PII leakage identification
    * Logging coverage analysis
    * Log injection vulnerability detection
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "scan":
            return await self._scan(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "logging_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "logging_audit", "sensitive_data_detection", "pii_detection",
            "log_injection_detection", "logging_coverage_analysis",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        content = task.payload.get("content", "")
        findings: List[Dict[str, Any]] = []

        for issue_name, issue_config in LOGGING_ISSUES.items():
            if re.search(issue_config["pattern"], content):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Logging issue: {issue_name.replace('_', ' ')}",
                })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "findings": findings,
        }

    async def _scan(self, task: Task) -> Dict[str, Any]:
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
