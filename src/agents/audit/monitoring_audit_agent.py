"""MonitoringAuditAgent — Monitoring coverage and alerting."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

MONITORING_ISSUES = {
    "missing_health_check": {"pattern": r"(?i)(no.*health.*check|no.*readiness|no.*liveness)", "severity": "high"},
    "missing_metrics": {"pattern": r"(?i)(no.*metrics|no.*prometheus|no.*telemetry)", "severity": "medium"},
    "missing_alerting": {"pattern": r"(?i)(no.*alert|no.*notification|no.*pager)", "severity": "high"},
    "missing_logging": {"pattern": r"(?i)(no.*structured.*log|no.*log.*aggregation)", "severity": "medium"},
    "missing_tracing": {"pattern": r"(?i)(no.*trace|no.*distributed.*trace|no.*span)", "severity": "medium"},
    "no_slo_monitoring": {"pattern": r"(?i)(no.*slo|no.*sla|no.*error.*budget)", "severity": "medium"},
}


class MonitoringAuditAgent(BaseAgent):
    """Monitoring coverage and alerting agent.

    Features
    --------
    * Health check configuration validation
    * Metrics collection coverage audit
    * Alerting rule completeness check
    * Distributed tracing verification
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
        if msg_type == "monitoring_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "monitoring_audit", "health_check_validation", "metrics_coverage",
            "alerting_completeness", "tracing_verification",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        config_str = str(config)

        for issue_name, issue_config in MONITORING_ISSUES.items():
            if re.search(issue_config["pattern"], config_str):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Monitoring gap: {issue_name.replace('_', ' ')}",
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
        return {
            "success": True,
            "total_findings": len(self._findings),
            "findings": self._findings[-20:],
        }
