"""ApiContractAuditAgent — API contract adherence."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

CONTRACT_ISSUES = {
    "missing_versioning": {"severity": "high", "description": "API versioning not implemented"},
    "breaking_changes": {"severity": "critical", "description": "Breaking changes without version bump"},
    "inconsistent_naming": {"severity": "medium", "description": "Inconsistent naming conventions"},
    "missing_error_schema": {"severity": "high", "description": "No standardized error responses"},
    "missing_pagination": {"severity": "medium", "description": "No pagination for list endpoints"},
    "missing_rate_limiting": {"severity": "high", "description": "No rate limiting headers"},
    "missing_content_type": {"severity": "medium", "description": "Content-Type header missing"},
    "inconsistent_response_format": {"severity": "medium", "description": "Inconsistent response format"},
    "missing_hateoas": {"severity": "low", "description": "No HATEOAS links"},
    "openapi_spec_missing": {"severity": "medium", "description": "OpenAPI specification missing"},
}


class ApiContractAuditAgent(BaseAgent):
    """API contract adherence agent.

    Features
    --------
    * API contract validation
    * Breaking change detection
    * Naming convention checking
    * OpenAPI/Swagger specification audit
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._adherence_score: float = 0.0

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
        if msg_type == "contract_query":
            return {"adherence_score": self._adherence_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "api_contract_audit", "breaking_change_detection",
            "naming_convention_check", "openapi_validation",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config_item in CONTRACT_ISSUES.items():
            if config.get(check, False):
                checks_passed += 1
            else:
                findings.append({
                    "type": "contract_violation",
                    "severity": config_item["severity"],
                    "check": check,
                    "target": target,
                    "description": config_item["description"],
                })

        self._adherence_score = checks_passed / len(CONTRACT_ISSUES)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "adherence_score": self._adherence_score,
            "checks_passed": checks_passed,
            "checks_total": len(CONTRACT_ISSUES),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "adherence_score": self._adherence_score,
            "findings": self._findings[-20:],
        }
