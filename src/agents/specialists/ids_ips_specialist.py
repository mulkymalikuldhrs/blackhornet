"""IDS/IPS specialist — Intrusion detection and prevention systems."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class IdsIpsSpecialist(BaseAgent):
    """Specialist agent for intrusion detection and prevention systems.

    Handles signature management, anomaly detection, alert management,
    traffic analysis, and threat response.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._signatures: Dict[str, Dict[str, Any]] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._blocked_ips: Dict[str, float] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "add_signature":
            return await self._add_signature(task)
        elif action == "analyze_traffic":
            return await self._analyze_traffic(task)
        elif action == "get_alerts":
            return await self._get_alerts(task)
        elif action == "block_threat":
            return await self._block_threat(task)
        elif action == "configure_anomaly_detection":
            return await self._configure_anomaly_detection(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "intrusion_event":
            event = message.get("payload", {})
            severity = event.get("severity", "low")
            alert = {
                "event_type": event.get("type", "unknown"),
                "severity": severity,
                "source_ip": event.get("source_ip", ""),
                "details": event.get("details", {}),
                "timestamp": time.time(),
            }
            self._alerts.append(alert)
            if severity == "critical":
                self._blocked_ips[alert["source_ip"]] = time.time() + 3600
            return {"alert_created": True, "severity": severity}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "signature_management", "anomaly_detection", "alert_management",
            "threat_blocking", "traffic_analysis", "forensic_analysis",
            "rule_tuning", "threat_intelligence",
        ]

    async def _add_signature(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_sig")
        pattern = task.payload.get("pattern", "")
        severity = task.payload.get("severity", "medium")
        category = task.payload.get("category", "generic")

        signature = {
            "name": name,
            "pattern": pattern,
            "severity": severity,
            "category": category,
            "enabled": True,
            "created_at": time.time(),
            "match_count": 0,
        }
        self._signatures[name] = signature
        return {"success": True, "signature": name, "severity": severity}

    async def _analyze_traffic(self, task: Task) -> Dict[str, Any]:
        payload = task.payload.get("payload", "")
        source_ip = task.payload.get("source_ip", "")

        matches: List[Dict[str, Any]] = []
        for name, sig in self._signatures.items():
            if sig["enabled"] and sig["pattern"] in str(payload):
                sig["match_count"] += 1
                matches.append({"signature": name, "severity": sig["severity"]})

        if matches:
            alert = {
                "event_type": "signature_match",
                "severity": max((m["severity"] for m in matches), key=lambda s: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s, 0)),
                "source_ip": source_ip,
                "matches": matches,
                "timestamp": time.time(),
            }
            self._alerts.append(alert)

        return {"success": True, "matches": len(matches), "details": matches}

    async def _get_alerts(self, task: Task) -> Dict[str, Any]:
        severity = task.payload.get("severity")
        time_range = task.payload.get("time_range", 3600)
        start_time = time.time() - time_range

        recent = [a for a in self._alerts if a.get("timestamp", 0) >= start_time]
        if severity:
            recent = [a for a in recent if a.get("severity") == severity]

        return {"success": True, "alerts": recent[-50:], "total": len(recent)}

    async def _block_threat(self, task: Task) -> Dict[str, Any]:
        ip = task.payload.get("ip", "")
        reason = task.payload.get("reason", "threat_detected")
        duration_seconds = task.payload.get("duration_seconds", 3600)

        self._blocked_ips[ip] = time.time() + duration_seconds
        return {"success": True, "blocked_ip": ip, "reason": reason, "expires_in_seconds": duration_seconds}

    async def _configure_anomaly_detection(self, task: Task) -> Dict[str, Any]:
        sensitivity = task.payload.get("sensitivity", "medium")
        baseline_window = task.payload.get("baseline_window_seconds", 3600)
        threshold = task.payload.get("threshold", 3.0)

        config = {
            "sensitivity": sensitivity,
            "baseline_window_seconds": baseline_window,
            "threshold": threshold,
            "enabled": True,
        }
        return {"success": True, "anomaly_config": config}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "signatures_count": len(self._signatures),
                "total_alerts": len(self._alerts),
                "critical_alerts": sum(1 for a in self._alerts if a.get("severity") == "critical"),
                "blocked_ips": len(self._blocked_ips),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "ids_ips",
            "metrics": self._monitor()["metrics"],
        }
