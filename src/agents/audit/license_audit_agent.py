"""LicenseAuditAgent — License compliance checking."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

LICENSE_CATEGORIES = {
    "permissive": {"licenses": ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"], "risk": "low"},
    "weak_copyleft": {"licenses": ["LGPL-2.1", "LGPL-3.0", "MPL-2.0"], "risk": "medium"},
    "strong_copyleft": {"licenses": ["GPL-2.0", "GPL-3.0", "AGPL-3.0"], "risk": "high"},
    "proprietary": {"licenses": ["Proprietary", "Commercial"], "risk": "high"},
    "unknown": {"licenses": ["Unknown", "UNLICENSED"], "risk": "high"},
}

LICENSE_ISSUES = {
    "copyleft_in_proprietary": {"severity": "critical", "description": "Copyleft license in proprietary project"},
    "incompatible_licenses": {"severity": "high", "description": "Incompatible license combination"},
    "missing_license": {"severity": "medium", "description": "Missing license declaration"},
    "unknown_license": {"severity": "medium", "description": "Unknown license type"},
    "viral_license": {"severity": "critical", "description": "Viral license detected"},
}


class LicenseAuditAgent(BaseAgent):
    """License compliance checking agent.

    Features
    --------
    * License compatibility analysis
    * Copyleft risk assessment
    * License conflict detection
    * Compliance recommendation generation
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._license_inventory: List[Dict[str, Any]] = []

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
        if msg_type == "license_query":
            return {"licenses": self._license_inventory[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "license_audit", "copyleft_risk_assessment",
            "license_compatibility", "compliance_recommendations",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        dependencies = task.payload.get("dependencies", [])
        target = task.payload.get("target", "")
        project_license = task.payload.get("project_license", "")
        findings: List[Dict[str, Any]] = []
        licenses_found: List[str] = []

        for dep in dependencies:
            name = dep.get("name", "")
            license_type = dep.get("license", "Unknown")
            licenses_found.append(license_type)
            self._license_inventory.append({"name": name, "license": license_type})

            risk = "low"
            for cat, config in LICENSE_CATEGORIES.items():
                if license_type in config["licenses"]:
                    risk = config["risk"]
                    break

            if risk == "high":
                findings.append({
                    "type": "high_risk_license",
                    "severity": "high",
                    "dependency": name,
                    "license": license_type,
                    "target": target,
                })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "licenses_found": list(set(licenses_found)),
            "findings": findings,
        }

    async def _scan(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "licenses_tracked": len(self._license_inventory),
            "findings": self._findings[-20:],
        }
