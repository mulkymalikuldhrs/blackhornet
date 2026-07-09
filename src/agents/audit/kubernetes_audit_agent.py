"""KubernetesAuditAgent — Kubernetes security and best practices."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

K8S_CHECKS = {
    "rbac_enabled": {"severity": "critical", "description": "RBAC enabled"},
    "network_policies": {"severity": "high", "description": "Network policies configured"},
    "pod_security_policies": {"severity": "high", "description": "Pod security policies"},
    "resource_quotas": {"severity": "medium", "description": "Resource quotas set"},
    "limit_ranges": {"severity": "medium", "description": "Limit ranges configured"},
    "secrets_encryption": {"severity": "critical", "description": "Secrets encrypted at rest"},
    "audit_logging": {"severity": "high", "description": "Audit logging enabled"},
    "image_pull_policy": {"severity": "medium", "description": "Image pull policy"},
    "readiness_probes": {"severity": "high", "description": "Readiness probes configured"},
    "liveness_probes": {"severity": "high", "description": "Liveness probes configured"},
    "security_context": {"severity": "high", "description": "Security context set"},
    "service_account_tokens": {"severity": "high", "description": "SA token automounting"},
}


class KubernetesAuditAgent(BaseAgent):
    """Kubernetes security and best practices agent.

    Features
    --------
    * RBAC configuration validation
    * Pod security policy auditing
    * Network policy verification
    * Kubernetes security best practices
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
        if msg_type == "k8s_query":
            return {"security_score": self._security_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "kubernetes_audit", "rbac_validation", "pod_security_audit",
            "network_policy_audit", "k8s_best_practices",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        k8s_config = task.payload.get("k8s_config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config in K8S_CHECKS.items():
            if k8s_config.get(check, False):
                checks_passed += 1
            else:
                findings.append({
                    "type": "missing_check",
                    "severity": config["severity"],
                    "check": check,
                    "target": target,
                    "description": config["description"],
                })

        self._security_score = checks_passed / len(K8S_CHECKS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "security_score": self._security_score,
            "checks_passed": checks_passed,
            "checks_total": len(K8S_CHECKS),
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
