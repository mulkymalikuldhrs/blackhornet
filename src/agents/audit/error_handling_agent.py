"""ErrorHandlingAgent — Error handling completeness."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

ERROR_HANDLING_ISSUES = {
    "bare_except": {"pattern": r"except\s*:", "severity": "high"},
    "exception_silenced": {"pattern": r"except.*:\s*pass", "severity": "high"},
    "generic_exception": {"pattern": r"except\s+Exception\s+as", "severity": "medium"},
    "missing_finally": {"pattern": r"(?i)(open\(.*\).*(?!finally))", "severity": "medium"},
    "unhandled_error": {"pattern": r"(?i)(no.*error.*handler|unhandled.*exception)", "severity": "high"},
    "swallowed_error": {"pattern": r"(?i)(catch.*\{?\s*\}|except.*\{\s*\})", "severity": "high"},
    "missing_error_logging": {"pattern": r"(?i)(except.*:(?!\s*log|print|raise))", "severity": "medium"},
}


class ErrorHandlingAgent(BaseAgent):
    """Error handling completeness agent.

    Features
    --------
    * Exception handling pattern detection
    * Error logging completeness validation
    * Resource cleanup verification
    * Error propagation analysis
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
        if msg_type == "error_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "error_handling_audit", "exception_pattern_detection",
            "error_logging_validation", "resource_cleanup_verification",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        content = task.payload.get("content", "")
        findings: List[Dict[str, Any]] = []

        for issue_name, issue_config in ERROR_HANDLING_ISSUES.items():
            matches = re.findall(issue_config["pattern"], content)
            if matches:
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "count": len(matches),
                    "target": target,
                    "description": f"Error handling issue: {issue_name.replace('_', ' ')}",
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
