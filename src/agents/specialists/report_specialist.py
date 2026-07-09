"""Report specialist — Report generation and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class ReportSpecialist(BaseAgent):
    """Specialist agent for report generation and management.

    Handles report templates, data aggregation, formatting,
    scheduling, and multi-format export.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._generated_reports: List[Dict[str, Any]] = {}
        self._schedules: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_template":
            return await self._create_template(task)
        elif action == "generate_report":
            return await self._generate_report(task)
        elif action == "schedule_report":
            return await self._schedule_report(task)
        elif action == "export_report":
            return await self._export_report(task)
        elif action == "list_reports":
            return await self._list_reports(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "report_request":
            template = message.get("payload", {}).get("template", "")
            return self._templates.get(template, {"found": False})
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "template_management", "report_generation", "report_scheduling",
            "multi_format_export", "data_aggregation", "report_formatting",
            "distribution_management", "report_archiving",
        ]

    async def _create_template(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_template")
        sections = task.payload.get("sections", [])
        format_type = task.payload.get("format", "pdf")

        template = {
            "name": name,
            "sections": sections,
            "format": format_type,
            "created_at": time.time(),
            "usage_count": 0,
        }
        self._templates[name] = template
        return {"success": True, "template": name, "sections": len(sections)}

    async def _generate_report(self, task: Task) -> Dict[str, Any]:
        template_name = task.payload.get("template", "default")
        data = task.payload.get("data", {})
        parameters = task.payload.get("parameters", {})

        report_id = f"rpt-{int(time.time())}"
        report = {
            "report_id": report_id,
            "template": template_name,
            "data": data,
            "parameters": parameters,
            "generated_at": time.time(),
            "status": "completed",
            "size_kb": 250.0,
        }
        self._generated_reports[report_id] = report

        if template_name in self._templates:
            self._templates[template_name]["usage_count"] += 1

        return {"success": True, "report_id": report_id, "template": template_name}

    async def _schedule_report(self, task: Task) -> Dict[str, Any]:
        report_name = task.payload.get("report", "default")
        cron = task.payload.get("cron", "0 9 * * *")
        recipients = task.payload.get("recipients", [])

        schedule = {
            "report": report_name,
            "cron": cron,
            "recipients": recipients,
            "enabled": True,
            "created_at": time.time(),
            "last_run": None,
            "next_run": time.time() + 86400,
        }
        self._schedules[report_name] = schedule
        return {"success": True, "schedule": report_name, "cron": cron}

    async def _export_report(self, task: Task) -> Dict[str, Any]:
        report_id = task.payload.get("report_id", "")
        format_type = task.payload.get("format", "pdf")

        if report_id not in self._generated_reports:
            return {"success": False, "error": f"Report {report_id} not found"}

        export = {
            "report_id": report_id,
            "format": format_type,
            "exported_at": time.time(),
            "file_path": f"/reports/{report_id}.{format_type}",
        }
        return {"success": True, "export": export}

    async def _list_reports(self, task: Task) -> Dict[str, Any]:
        return {
            "success": True,
            "reports": list(self._generated_reports.keys()),
            "templates": list(self._templates.keys()),
            "schedules": list(self._schedules.keys()),
        }

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "templates_count": len(self._templates),
                "generated_reports": len(self._generated_reports),
                "active_schedules": sum(1 for s in self._schedules.values() if s.get("enabled")),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "report",
            "metrics": self._monitor()["metrics"],
        }
