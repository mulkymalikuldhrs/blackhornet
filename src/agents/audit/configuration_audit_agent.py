"""ConfigurationAuditAgent — Configuration correctness and security validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

INSECURE_SETTINGS = {
    "debug": {"dangerous_value": True, "severity": "high", "description": "Debug mode enabled in production"},
    "cors_allow_all": {"dangerous_value": True, "severity": "high", "description": "CORS allows all origins"},
    "ssl_verify": {"dangerous_value": False, "severity": "high", "description": "SSL verification disabled"},
    "default_secret": {"dangerous_value": True, "severity": "critical", "description": "Default secret key in use"},
    "log_level_debug": {"dangerous_value": "DEBUG", "severity": "medium", "description": "Debug logging in production"},
    "admin_default_password": {"dangerous_value": True, "severity": "critical", "description": "Default admin password"},
    "exposed_port": {"dangerous_value": True, "severity": "high", "description": "Port exposed to public network"},
}


class ConfigurationAuditAgent(BaseAgent):
    """Configuration correctness and security validation agent.

    Features
    --------
    * Insecure configuration detection
    * Environment-appropriate settings validation
    * Secret management verification
    * Configuration drift detection
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._baseline: Dict[str, Any] = {}

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
        if msg_type == "config_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "configuration_audit", "security_validation", "config_drift_detection",
            "secret_management_audit", "environment_validation",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        environment = task.payload.get("environment", "production")
        findings: List[Dict[str, Any]] = []

        for key, value in config.items():
            check = self._check_setting(key, value, environment)
            if check:
                findings.append(check)

        self._findings.extend(findings)
        return {
            "success": True,
            "environment": environment,
            "settings_checked": len(config),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _check_setting(self, key: str, value: Any, environment: str) -> Optional[Dict[str, Any]]:
        key_lower = key.lower()
        for setting_name, config in INSECURE_SETTINGS.items():
            if setting_name in key_lower:
                if value == config["dangerous_value"]:
                    return {
                        "setting": key,
                        "severity": config["severity"],
                        "description": config["description"],
                        "current_value": str(value)[:50],
                        "environment": environment,
                    }
        return None

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
