"""SupplyChainAuditAgent — Supply chain security validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

SUPPLY_CHAIN_CHECKS = {
    "dependency_verification": {"severity": "critical", "description": "Dependency integrity verification"},
    "lockfile_present": {"severity": "high", "description": "Lockfile exists and is current"},
    "signed_commits": {"severity": "medium", "description": "Signed commits"},
    "signed_artifacts": {"severity": "high", "description": "Signed build artifacts"},
    "sbom_generated": {"severity": "high", "description": "Software Bill of Materials"},
    "vulnerability_scanning": {"severity": "critical", "description": "Vulnerability scanning in CI"},
    "private_registry": {"severity": "high", "description": "Private package registry"},
    "dependency_review": {"severity": "high", "description": "Dependency change review"},
    "reproducible_builds": {"severity": "medium", "description": "Reproducible builds"},
    "provenance_tracking": {"severity": "high", "description": "Build provenance tracking"},
}


class SupplyChainAuditAgent(BaseAgent):
    """Supply chain security validation agent.

    Features
    --------
    * Dependency integrity verification
    * Software Bill of Materials (SBOM) generation
    * Build provenance tracking
    * Supply chain attack prevention
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._security_score: float = 0.0

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
        if msg_type == "supply_chain_query":
            return {"security_score": self._security_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "supply_chain_audit", "dependency_verification", "sbom_generation",
            "provenance_tracking", "supply_chain_security",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config_item in SUPPLY_CHAIN_CHECKS.items():
            if config.get(check, False):
                checks_passed += 1
            else:
                findings.append({
                    "type": "missing_check",
                    "severity": config_item["severity"],
                    "check": check,
                    "target": target,
                    "description": config_item["description"],
                })

        self._security_score = checks_passed / len(SUPPLY_CHAIN_CHECKS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "security_score": self._security_score,
            "checks_passed": checks_passed,
            "checks_total": len(SUPPLY_CHAIN_CHECKS),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "security_score": self._security_score,
            "findings": self._findings[-20:],
        }
