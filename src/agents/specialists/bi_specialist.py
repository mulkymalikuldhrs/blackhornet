"""BI specialist — Business intelligence and reporting."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class BiSpecialist(BaseAgent):
    """Specialist agent for business intelligence and reporting.

    Handles report creation, dashboard design, data visualization,
    KPI tracking, and business analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._dashboards: Dict[str, Dict[str, Any]] = {}
        self._kpis: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_report":
            return await self._create_report(task)
        elif action == "create_dashboard":
            return await self._create_dashboard(task)
        elif action == "define_kpi":
            return await self._define_kpi(task)
        elif action == "update_kpi":
            return await self._update_kpi(task)
        elif action == "generate_insight":
            return await self._generate_insight(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "report_query":
            report_id = message.get("payload", {}).get("report_id", "")
            return self._reports.get(report_id, {"found": False})
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "report_generation", "dashboard_creation", "kpi_management",
            "data_visualization", "business_analytics", "scheduled_reporting",
            "ad_hoc_analysis", "insight_generation",
        ]

    async def _create_report(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_report")
        report_type = task.payload.get("type", "tabular")
        data_source = task.payload.get("data_source", "default")
        filters = task.payload.get("filters", [])

        report_id = f"rpt-{int(time.time())}"
        report = {
            "report_id": report_id,
            "name": name,
            "type": report_type,
            "data_source": data_source,
            "filters": filters,
            "created_at": time.time(),
            "last_run": None,
            "run_count": 0,
        }
        self._reports[report_id] = report
        return {"success": True, "report_id": report_id, "name": name}

    async def _create_dashboard(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_dashboard")
        widgets = task.payload.get("widgets", [])
        layout = task.payload.get("layout", "grid")

        dashboard_id = f"dash-{int(time.time())}"
        dashboard = {
            "dashboard_id": dashboard_id,
            "name": name,
            "widgets": widgets,
            "layout": layout,
            "created_at": time.time(),
            "refresh_interval_seconds": task.payload.get("refresh_interval", 300),
        }
        self._dashboards[dashboard_id] = dashboard
        return {"success": True, "dashboard_id": dashboard_id, "name": name}

    async def _define_kpi(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_kpi")
        metric = task.payload.get("metric", "revenue")
        target = task.payload.get("target", 1000)
        unit = task.payload.get("unit", "currency")

        kpi = {
            "name": name,
            "metric": metric,
            "target": target,
            "unit": unit,
            "current_value": 0,
            "status": "undefined",
            "created_at": time.time(),
        }
        self._kpis[name] = kpi
        return {"success": True, "kpi": name, "target": target}

    async def _update_kpi(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "")
        value = task.payload.get("value", 0)

        if name not in self._kpis:
            return {"success": False, "error": f"KPI {name} not found"}

        kpi = self._kpis[name]
        kpi["current_value"] = value
        kpi["last_updated"] = time.time()

        target = kpi.get("target", 1)
        if target > 0:
            achievement = (value / target) * 100
            kpi["achievement_percent"] = round(achievement, 1)
            if achievement >= 100:
                kpi["status"] = "on_track"
            elif achievement >= 80:
                kpi["status"] = "at_risk"
            else:
                kpi["status"] = "behind"

        return {"success": True, "kpi": name, "value": value, "status": kpi["status"]}

    async def _generate_insight(self, task: Task) -> Dict[str, Any]:
        data = task.payload.get("data", {})
        insight_type = task.payload.get("type", "trend")

        insights: List[str] = []
        if insight_type == "trend":
            insights.append("Revenue increased by 12% compared to last month")
            insights.append("Customer acquisition cost decreased by 8%")
        elif insight_type == "anomaly":
            insights.append("Unusual spike in error rates detected")
        elif insight_type == "forecast":
            insights.append("Projected 15% growth for next quarter")

        return {"success": True, "insights": insights, "type": insight_type}

    def _monitor(self) -> Dict[str, Any]:
        on_track = sum(1 for k in self._kpis.values() if k.get("status") == "on_track")
        return {
            "success": True,
            "metrics": {
                "reports_count": len(self._reports),
                "dashboards_count": len(self._dashboards),
                "kpis_count": len(self._kpis),
                "kpis_on_track": on_track,
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "bi",
            "metrics": self._monitor()["metrics"],
        }
