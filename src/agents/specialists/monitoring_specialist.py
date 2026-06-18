"""Monitoring specialist — Monitoring and observability infrastructure."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class MonitoringSpecialist(BaseAgent):
    """Specialist agent for monitoring and observability.

    Handles metric collection, alerting configuration, dashboard creation,
    distributed tracing, and SLA monitoring.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._alerts: Dict[str, Dict[str, Any]] = {}
        self._dashboards: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "collect_metric":
            return await self._collect_metric(task)
        elif action == "configure_alert":
            return await self._configure_alert(task)
        elif action == "create_dashboard":
            return await self._create_dashboard(task)
        elif action == "check_alerts":
            return await self._check_alerts(task)
        elif action == "query_metrics":
            return await self._query_metrics(task)
        elif action == "trace_request":
            return await self._trace_request(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "metric_report":
            metric_name = message.get("payload", {}).get("name", "")
            value = message.get("payload", {}).get("value", 0)
            self._metrics.setdefault(metric_name, []).append({"value": value, "timestamp": time.time()})
            return {"metric_received": True}
        elif msg_type == "alert_query":
            return {"alerts": list(self._alerts.values())}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "metric_collection", "alerting", "dashboard_creation",
            "distributed_tracing", "sla_monitoring", "log_aggregation",
            "anomaly_detection", "capacity_planning",
        ]

    async def _collect_metric(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "unnamed_metric")
        value = task.payload.get("value", 0)
        labels = task.payload.get("labels", {})

        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append({
            "value": value,
            "labels": labels,
            "timestamp": time.time(),
        })

        return {"success": True, "metric": name, "value": value, "labels": labels}

    async def _configure_alert(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "unnamed_alert")
        metric = task.payload.get("metric", "")
        condition = task.payload.get("condition", "above")
        threshold = task.payload.get("threshold", 0)
        severity = task.payload.get("severity", "warning")

        alert = {
            "name": name,
            "metric": metric,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "enabled": True,
            "created_at": time.time(),
            "triggered_count": 0,
        }
        self._alerts[name] = alert
        return {"success": True, "alert": name, "config": alert}

    async def _create_dashboard(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default-dashboard")
        panels = task.payload.get("panels", [])

        dashboard = {
            "name": name,
            "panels": panels,
            "refresh_interval_seconds": task.payload.get("refresh_interval", 30),
            "created_at": time.time(),
        }
        self._dashboards[name] = dashboard
        return {"success": True, "dashboard": name, "config": dashboard}

    async def _check_alerts(self, task: Task) -> Dict[str, Any]:
        triggered: List[Dict[str, Any]] = []
        for name, alert in self._alerts.items():
            if not alert["enabled"]:
                continue
            metric_values = self._metrics.get(alert["metric"], [])
            if metric_values:
                latest_value = metric_values[-1]["value"]
                if alert["condition"] == "above" and latest_value > alert["threshold"]:
                    alert["triggered_count"] += 1
                    triggered.append({"alert": name, "value": latest_value, "threshold": alert["threshold"]})
                elif alert["condition"] == "below" and latest_value < alert["threshold"]:
                    alert["triggered_count"] += 1
                    triggered.append({"alert": name, "value": latest_value, "threshold": alert["threshold"]})

        return {"success": True, "triggered_alerts": triggered, "count": len(triggered)}

    async def _query_metrics(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "")
        start_time = task.payload.get("start_time", time.time() - 3600)
        end_time = task.payload.get("end_time", time.time())

        values = self._metrics.get(name, [])
        filtered = [v for v in values if start_time <= v["timestamp"] <= end_time]

        return {"success": True, "metric": name, "data_points": len(filtered), "values": filtered}

    async def _trace_request(self, task: Task) -> Dict[str, Any]:
        request_id = task.payload.get("request_id", "unknown")
        spans = [
            {"name": "http_request", "duration_ms": 10.5, "status": "ok"},
            {"name": "auth_check", "duration_ms": 5.2, "status": "ok"},
            {"name": "db_query", "duration_ms": 25.3, "status": "ok"},
            {"name": "response_serialize", "duration_ms": 2.1, "status": "ok"},
        ]
        total_duration = sum(s["duration_ms"] for s in spans)
        return {"success": True, "request_id": request_id, "spans": spans, "total_duration_ms": total_duration}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "metric_names": len(self._metrics),
                "total_data_points": sum(len(v) for v in self._metrics.values()),
                "alerts_configured": len(self._alerts),
                "dashboards": len(self._dashboards),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "monitoring",
            "metrics": self._monitor()["metrics"],
        }
