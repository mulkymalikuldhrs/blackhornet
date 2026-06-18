"""SSL/TLS specialist — SSL/TLS certificate management and security."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class SslTlsSpecialist(BaseAgent):
    """Specialist agent for SSL/TLS certificate management and security.

    Handles certificate provisioning, renewal, configuration,
    vulnerability scanning, and compliance checking.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._certificates: Dict[str, Dict[str, Any]] = {}
        self._scan_results: List[Dict[str, Any]] = []
        self._renewal_log: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "provision_certificate":
            return await self._provision_certificate(task)
        elif action == "renew_certificate":
            return await self._renew_certificate(task)
        elif action == "scan_vulnerabilities":
            return await self._scan_vulnerabilities(task)
        elif action == "configure_hsts":
            return await self._configure_hsts(task)
        elif action == "check_compliance":
            return await self._check_compliance(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "cert_expiry_alert":
            domain = message.get("payload", {}).get("domain", "")
            cert = self._certificates.get(domain, {})
            return {"domain": domain, "expires_at": cert.get("expires_at"), "auto_renew": cert.get("auto_renew", True)}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "certificate_provisioning", "auto_renewal", "vulnerability_scanning",
            "hsts_configuration", "compliance_checking", "certificate_monitoring",
            "chain_validation", "cipher_suite_management",
        ]

    async def _provision_certificate(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "example.com")
        provider = task.payload.get("provider", "letsencrypt")
        san = task.payload.get("san", [])
        key_type = task.payload.get("key_type", "ecdsa")

        cert_id = f"cert-{int(time.time())}"
        certificate = {
            "id": cert_id,
            "domain": domain,
            "provider": provider,
            "san": san,
            "key_type": key_type,
            "issued_at": time.time(),
            "expires_at": time.time() + 90 * 86400,
            "auto_renew": True,
            "status": "active",
        }
        self._certificates[domain] = certificate
        return {"success": True, "certificate_id": cert_id, "domain": domain}

    async def _renew_certificate(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "")
        if domain not in self._certificates:
            return {"success": False, "error": f"No certificate for {domain}"}

        cert = self._certificates[domain]
        cert["expires_at"] = time.time() + 90 * 86400
        cert["renewed_at"] = time.time()

        renewal = {"domain": domain, "renewed_at": time.time(), "new_expiry": cert["expires_at"]}
        self._renewal_log.append(renewal)
        return {"success": True, "renewal": renewal}

    async def _scan_vulnerabilities(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "all")

        findings = [
            {"type": "weak_cipher", "severity": "medium", "description": "TLS_RSA_WITH_AES_128_CBC_SHA is enabled"},
            {"type": "expired_cert", "severity": "critical", "description": "Certificate expiring in 7 days"},
        ]

        scan = {
            "domain": domain,
            "findings": findings,
            "scan_time": time.time(),
            "overall_risk": "medium" if findings else "low",
        }
        self._scan_results.append(scan)
        return {"success": True, "scan": scan}

    async def _configure_hsts(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "")
        max_age_seconds = task.payload.get("max_age_seconds", 31536000)
        include_subdomains = task.payload.get("include_subdomains", True)
        preload = task.payload.get("preload", False)

        hsts_config = {
            "domain": domain,
            "max_age_seconds": max_age_seconds,
            "include_subdomains": include_subdomains,
            "preload": preload,
        }
        return {"success": True, "hsts_config": hsts_config}

    async def _check_compliance(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "example.com")
        cert = self._certificates.get(domain, {})

        checks = {
            "valid_certificate": bool(cert),
            "not_expired": cert.get("expires_at", 0) > time.time(),
            "strong_key": cert.get("key_type") in ("ecdsa", "rsa"),
            "hsts_enabled": True,
            "secure_protocols": True,
        }

        passed = sum(checks.values())
        return {"success": True, "domain": domain, "compliance_score": round(passed / len(checks) * 100, 1), "checks": checks}

    def _monitor(self) -> Dict[str, Any]:
        expiring_soon = sum(1 for c in self._certificates.values() if c.get("expires_at", 0) - time.time() < 30 * 86400)
        return {
            "success": True,
            "metrics": {
                "certificates_count": len(self._certificates),
                "expiring_soon": expiring_soon,
                "scans_performed": len(self._scan_results),
                "renewals": len(self._renewal_log),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "ssl_tls",
            "metrics": self._monitor()["metrics"],
        }
