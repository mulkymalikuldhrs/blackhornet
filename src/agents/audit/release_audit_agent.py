"""ReleaseAuditAgent — Release readiness validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

RELEASE_CHECKS = {
    "tests_passing": {"required": True, "severity": "critical"},
    "code_review_complete": {"required": True, "severity": "critical"},
    "security_scan_passed": {"required": True, "severity": "critical"},
    "performance_benchmark_met": {"required": True, "severity": "high"},
    "documentation_updated": {"required": True, "severity": "medium"},
    "changelog_updated": {"required": True, "severity": "medium"},
    "version_number_bumped": {"required": True, "severity": "high"},
    "rollback_plan_ready": {"required": True, "severity": "high"},
    "monitoring_configured": {"required": True, "severity": "medium"},
    "stakeholder_notification": {"required": False, "severity": "low"},
}


class ReleaseAuditAgent(BaseAgent):
    """Release readiness validation agent.

    Features
    --------
    * Pre-release checklist validation
    * Test coverage verification
    * Security scan confirmation
    * Release gate enforcement
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
        if msg_type == "release_query":
            return {"readiness_score": self._readiness_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "release_readiness_validation", "pre_release_checklist",
            "release_gate_enforcement", "release_audit",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        release_info = task.payload.get("release_info", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config in RELEASE_CHECKS.items():
            if release_info.get(check, False):
                checks_passed += 1
            elif config["required"]:
                findings.append({
                    "type": "check_failed",
                    "severity": config["severity"],
                    "check": check,
                    "target": target,
                    "description": f"Release check failed: {check.replace('_', ' ')}",
                })

        self._readiness_score = checks_passed / len(RELEASE_CHECKS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "readiness_score": self._readiness_score,
            "checks_passed": checks_passed,
            "checks_total": len(RELEASE_CHECKS),
            "findings": findings,
            "release_ready": self._readiness_score >= 0.9,
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
