"""Dashboard specialist — Dashboard development and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class DashboardSpecialist(BaseAgent):
    """Specialist agent for dashboard development and management.

    Handles widget creation, layout management, real-time updates,
    user personalization, and dashboard performance optimization.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.CODER, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._dashboards: Dict[str, Dict[str, Any]] = {}
        self._widgets: Dict[str, Dict[str, Any]] = {}
        self._user_preferences: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_dashboard":
            return await self._create_dashboard(task)
        elif action == "add_widget":
            return await self._add_widget(task)
        elif action == "update_layout":
            return await self._update_layout(task)
        elif action == "configure_refresh":
            return await self._configure_refresh(task)
        elif action == "personalize":
            return await self._personalize(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "dashboard_data":
            dashboard_id = message.get("payload", {}).get("dashboard_id", "")
            return self._dashboards.get(dashboard_id, {"found": False})
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "dashboard_creation", "widget_management", "layout_management",
            "real_time_updates", "user_personalization", "performance_optimization",
            "responsive_design", "theme_management",
        ]

    async def _create_dashboard(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_dashboard")
        description = task.payload.get("description", "")
        layout = task.payload.get("layout", "grid")
        theme = task.payload.get("theme", "light")

        dashboard_id = f"dash-{int(time.time())}"
        dashboard = {
            "dashboard_id": dashboard_id,
            "name": name,
            "description": description,
            "layout": layout,
            "theme": theme,
            "widgets": [],
            "created_at": time.time(),
            "refresh_interval_seconds": task.payload.get("refresh_interval", 30),
        }
        self._dashboards[dashboard_id] = dashboard
        return {"success": True, "dashboard_id": dashboard_id, "name": name}

    async def _add_widget(self, task: Task) -> Dict[str, Any]:
        dashboard_id = task.payload.get("dashboard_id", "")
        widget_type = task.payload.get("type", "chart")
        title = task.payload.get("title", "Widget")
        data_source = task.payload.get("data_source", "default")
        position = task.payload.get("position", {"x": 0, "y": 0, "w": 6, "h": 4})

        if dashboard_id not in self._dashboards:
            return {"success": False, "error": f"Dashboard {dashboard_id} not found"}

        widget_id = f"widget-{int(time.time())}"
        widget = {
            "widget_id": widget_id,
            "type": widget_type,
            "title": title,
            "data_source": data_source,
            "position": position,
            "created_at": time.time(),
        }
        self._widgets[widget_id] = widget
        self._dashboards[dashboard_id]["widgets"].append(widget_id)
        return {"success": True, "widget_id": widget_id, "type": widget_type}

    async def _update_layout(self, task: Task) -> Dict[str, Any]:
        dashboard_id = task.payload.get("dashboard_id", "")
        layout = task.payload.get("layout", "grid")
        positions = task.payload.get("positions", {})

        if dashboard_id not in self._dashboards:
            return {"success": False, "error": f"Dashboard {dashboard_id} not found"}

        self._dashboards[dashboard_id]["layout"] = layout
        for widget_id, pos in positions.items():
            if widget_id in self._widgets:
                self._widgets[widget_id]["position"] = pos

        return {"success": True, "dashboard_id": dashboard_id, "layout": layout}

    async def _configure_refresh(self, task: Task) -> Dict[str, Any]:
        dashboard_id = task.payload.get("dashboard_id", "")
        interval = task.payload.get("interval_seconds", 30)
        auto_refresh = task.payload.get("auto_refresh", True)

        if dashboard_id in self._dashboards:
            self._dashboards[dashboard_id]["refresh_interval_seconds"] = interval
            self._dashboards[dashboard_id]["auto_refresh"] = auto_refresh

        return {"success": True, "dashboard_id": dashboard_id, "interval": interval}

    async def _personalize(self, task: Task) -> Dict[str, Any]:
        user_id = task.payload.get("user_id", "default")
        preferences = task.payload.get("preferences", {})

        self._user_preferences[user_id] = {
            "user_id": user_id,
            "preferences": preferences,
            "updated_at": time.time(),
        }
        return {"success": True, "user_id": user_id, "preferences": preferences}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "dashboards_count": len(self._dashboards),
                "widgets_count": len(self._widgets),
                "personalized_users": len(self._user_preferences),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "dashboard",
            "metrics": self._monitor()["metrics"],
        }
