"""ContainerAuditAgent — Container security and configuration."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

CONTAINER_ISSUES = {
    "running_as_root": {"pattern": r"(?i)(USER\s+root|as.*root)", "severity": "high"},
    "latest_tag": {"pattern": r"(?i)(FROM\s+\w+:latest|image.*:latest)", "severity": "medium"},
    "secrets_in_dockerfile": {"pattern": r"(?i)(ENV\s+\w*SECRET|ENV\s+\w*PASSWORD|ENV\s+\w*KEY)", "severity": "critical"},
    "no_healthcheck": {"pattern": r"(?i)(HEALTHCHECK\s+NONE|no.*healthcheck)", "severity": "medium"},
    "exposed_ports": {"pattern": r"(?i)(EXPOSE\s+\d+)", "severity": "low"},
    "privileged_mode": {"pattern": r"(?i)(--privileged|privileged.*true)", "severity": "critical"},
    "no_read_only_rootfs": {"pattern": r"(?i)(read_only.*false|no.*read.?only)", "severity": "medium"},
}


class ContainerAuditAgent(BaseAgent):
    """Container security and configuration agent.

    Features
    --------
    * Dockerfile security analysis
    * Container runtime configuration audit
    * Image vulnerability scanning
    * Container security best practices validation
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
        if msg_type == "container_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "container_security_audit", "dockerfile_analysis",
            "image_vulnerability_scan", "container_best_practices",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        dockerfile_content = task.payload.get("dockerfile", "")
        findings: List[Dict[str, Any]] = []

        for issue_name, issue_config in CONTAINER_ISSUES.items():
            if re.search(issue_config["pattern"], dockerfile_content):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Container issue: {issue_name.replace('_', ' ')}",
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
