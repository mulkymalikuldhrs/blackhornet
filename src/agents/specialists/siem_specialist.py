"""SIEM specialist — Security information and event management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class SiemSpecialist(BaseAgent):
    """Specialist agent for security information and event management.

    Handles log correlation, threat detection, incident management,
    compliance reporting, and security analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._events: List[Dict[str, Any]] = []
        self._correlation_rules: Dict[str, Dict[str, Any]] = {}
        self._incidents: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "ingest_event":
            return await self._ingest_event(task)
        elif action == "add_correlation_rule":
            return await self._add_correlation_rule(task)
        elif action == "correlate_events":
            return await self._correlate_events(task)
        elif action == "create_incident":
            return await self._create_incident(task)
        elif action == "generate_compliance_report":
            return await self._generate_compliance_report(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "security_event":
            event = message.get("payload", {})
            self._events.append({**event, "received_at": time.time()})
            return {"event_ingested": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "event_ingestion", "log_correlation", "threat_detection",
            "incident_management", "compliance_reporting", "security_analytics",
            "real_time_monitoring", "forensic_investigation",
        ]

    async def _ingest_event(self, task: Task) -> Dict[str, Any]:
        source = task.payload.get("source", "unknown")
        event_type = task.payload.get("event_type", "generic")
        severity = task.payload.get("severity", "info")
        data = task.payload.get("data", {})

        event = {
            "event_id": f"evt-{int(time.time() * 1000)}",
            "source": source,
            "event_type": event_type,
            "severity": severity,
            "data": data,
            "received_at": time.time(),
        }
        self._events.append(event)
        return {"success": True, "event_id": event["event_id"]}

    async def _add_correlation_rule(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_rule")
        conditions = task.payload.get("conditions", [])
        time_window_seconds = task.payload.get("time_window_seconds", 300)
        threshold = task.payload.get("threshold", 5)

        rule = {
            "name": name,
            "conditions": conditions,
            "time_window_seconds": time_window_seconds,
            "threshold": threshold,
            "enabled": True,
            "created_at": time.time(),
            "match_count": 0,
        }
        self._correlation_rules[name] = rule
        return {"success": True, "rule": name, "config": rule}

    async def _correlate_events(self, task: Task) -> Dict[str, Any]:
        time_window = task.payload.get("time_window_seconds", 300)
        start_time = time.time() - time_window

        recent = [e for e in self._events if e.get("received_at", 0) >= start_time]
        matches: List[Dict[str, Any]] = []

        for rule_name, rule in self._correlation_rules.items():
            if not rule["enabled"]:
                continue
            matching_events = []
            for event in recent:
                if any(event.get("event_type") == cond.get("event_type") for cond in rule["conditions"]):
                    matching_events.append(event)

            if len(matching_events) >= rule["threshold"]:
                rule["match_count"] += 1
                matches.append({
                    "rule": rule_name,
                    "matched_events": len(matching_events),
                    "events": matching_events[:10],
                })

        return {"success": True, "correlations": matches, "events_analyzed": len(recent)}

    async def _create_incident(self, task: Task) -> Dict[str, Any]:
        title = task.payload.get("title", "Security Incident")
        severity = task.payload.get("severity", "medium")
        description = task.payload.get("description", "")
        affected_assets = task.payload.get("affected_assets", [])

        incident_id = f"inc-{int(time.time())}"
        incident = {
            "incident_id": incident_id,
            "title": title,
            "severity": severity,
            "description": description,
            "affected_assets": affected_assets,
            "status": "open",
            "created_at": time.time(),
            "timeline": [{"event": "created", "timestamp": time.time()}],
        }
        self._incidents[incident_id] = incident
        return {"success": True, "incident_id": incident_id, "severity": severity}

    async def _generate_compliance_report(self, task: Task) -> Dict[str, Any]:
        framework = task.payload.get("framework", "soc2")
        time_range = task.payload.get("time_range_days", 30)
        start_time = time.time() - time_range * 86400

        recent_events = [e for e in self._events if e.get("received_at", 0) >= start_time]
        report = {
            "framework": framework,
            "time_range_days": time_range,
            "total_events_analyzed": len(recent_events),
            "security_events": sum(1 for e in recent_events if e.get("severity") in ("high", "critical")),
            "compliance_status": "compliant",
            "generated_at": time.time(),
        }
        return {"success": True, "report": report}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "total_events": len(self._events),
                "correlation_rules": len(self._correlation_rules),
                "open_incidents": sum(1 for i in self._incidents.values() if i.get("status") == "open"),
                "critical_events": sum(1 for e in self._events if e.get("severity") == "critical"),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "siem",
            "metrics": self._monitor()["metrics"],
        }
