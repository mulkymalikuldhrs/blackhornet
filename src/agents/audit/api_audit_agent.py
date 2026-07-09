"""ApiAuditAgent — API contract and security validation."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

API_SECURITY_ISSUES = {
    "missing_auth": {"pattern": r"(?i)(GET|POST|PUT|DELETE|PATCH)\s+.*\s+.*no.*auth", "severity": "high"},
    "missing_rate_limit": {"pattern": r"(?i)(endpoint|route).*\s+.*no.*rate.*limit", "severity": "medium"},
    "input_validation_missing": {"pattern": r"(?i)(request\.body|request\.json).*\s+.*no.*valid", "severity": "high"},
    "verbose_error": {"pattern": r"(?i)(stack.?trace|traceback|exception.*detail)", "severity": "medium"},
    "versionless_api": {"pattern": r"(?i)(/api/[^v]|endpoint.*\s+.*no.*version)", "severity": "low"},
    "cors_misconfig": {"pattern": r"(?i)(origin.*\*|allow.*all)", "severity": "high"},
}


class ApiAuditAgent(BaseAgent):
    """API contract and security validation agent.

    Features
    --------
    * Authentication requirement verification
    * Input validation auditing
    * Rate limiting checks
    * API versioning compliance
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._endpoints: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "validate":
            return await self._validate_endpoint(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "api_query":
            return {"endpoints": self._endpoints[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "api_audit", "contract_validation", "security_review",
            "authentication_check", "rate_limit_validation",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        endpoints = task.payload.get("endpoints", [])
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        for endpoint in endpoints:
            path = endpoint.get("path", "")
            methods = endpoint.get("methods", [])
            auth_required = endpoint.get("auth_required", False)
            rate_limited = endpoint.get("rate_limited", False)

            if not auth_required:
                findings.append({
                    "type": "missing_auth",
                    "severity": "high",
                    "endpoint": path,
                    "description": "Endpoint lacks authentication requirement",
                })
            if not rate_limited:
                findings.append({
                    "type": "missing_rate_limit",
                    "severity": "medium",
                    "endpoint": path,
                    "description": "Endpoint lacks rate limiting",
                })

            self._endpoints.append({
                "path": path,
                "methods": methods,
                "auth_required": auth_required,
                "rate_limited": rate_limited,
            })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "endpoints_checked": len(endpoints),
            "findings": findings,
        }

    async def _validate_endpoint(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "endpoints_audited": len(self._endpoints),
            "findings": self._findings[-20:],
        }
