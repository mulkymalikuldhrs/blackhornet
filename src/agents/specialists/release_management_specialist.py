"""Release management specialist — Release planning and coordination."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class ReleaseManagementSpecialist(BaseAgent):
    """Specialist agent for release planning and coordination.

    Handles release planning, version management, deployment coordination,
    rollback management, and release analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._releases: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, Dict[str, Any]] = {}
        self._release_history: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "plan_release":
            return await self._plan_release(task)
        elif action == "create_version":
            return await self._create_version(task)
        elif action == "approve_release":
            return await self._approve_release(task)
        elif action == "deploy_release":
            return await self._deploy_release(task)
        elif action == "rollback_release":
            return await self._rollback_release(task)
        elif action == "get_release_status":
            return await self._get_release_status(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "release_event":
            release_id = message.get("payload", {}).get("release_id", "")
            if release_id in self._releases:
                self._releases[release_id].setdefault("events", []).append(message.get("payload", {}))
            return {"event_processed": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "release_planning", "version_management", "approval_workflow",
            "deployment_coordination", "rollback_management", "release_analytics",
            "change_freeze_management", "release_calendar",
        ]

    async def _plan_release(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "Release 1.0")
        version = task.payload.get("version", "1.0.0")
        components = task.payload.get("components", [])
        target_date = task.payload.get("target_date", "")

        release_id = f"rel-{int(time.time())}"
        release = {
            "release_id": release_id,
            "name": name,
            "version": version,
            "components": components,
            "target_date": target_date,
            "status": "planned",
            "planned_at": time.time(),
            "approvals": [],
            "events": [],
        }
        self._releases[release_id] = release
        return {"success": True, "release_id": release_id, "name": name}

    async def _create_version(self, task: Task) -> Dict[str, Any]:
        component = task.payload.get("component", "app")
        version = task.payload.get("version", "1.0.0")
        changelog = task.payload.get("changelog", "")

        version_info = {
            "component": component,
            "version": version,
            "changelog": changelog,
            "created_at": time.time(),
            "status": "created",
        }
        self._versions[f"{component}:{version}"] = version_info
        return {"success": True, "component": component, "version": version}

    async def _approve_release(self, task: Task) -> Dict[str, Any]:
        release_id = task.payload.get("release_id", "")
        approver = task.payload.get("approver", "system")

        if release_id not in self._releases:
            return {"success": False, "error": f"Release {release_id} not found"}

        release = self._releases[release_id]
        release["approvals"].append({"approver": approver, "timestamp": time.time()})

        if len(release["approvals"]) >= 2:
            release["status"] = "approved"

        return {"success": True, "release_id": release_id, "status": release["status"]}

    async def _deploy_release(self, task: Task) -> Dict[str, Any]:
        release_id = task.payload.get("release_id", "")
        environment = task.payload.get("environment", "production")

        if release_id not in self._releases:
            return {"success": False, "error": f"Release {release_id} not found"}

        release = self._releases[release_id]
        release["status"] = "deployed"
        release["deployed_at"] = time.time()
        release["environment"] = environment

        self._release_history.append({
            "release_id": release_id,
            "version": release.get("version"),
            "environment": environment,
            "deployed_at": time.time(),
            "status": "success",
        })
        return {"success": True, "release_id": release_id, "environment": environment}

    async def _rollback_release(self, task: Task) -> Dict[str, Any]:
        release_id = task.payload.get("release_id", "")
        target_version = task.payload.get("target_version", "")

        rollback = {
            "release_id": release_id,
            "target_version": target_version,
            "status": "rolled_back",
            "rolled_back_at": time.time(),
        }
        self._release_history.append(rollback)
        return {"success": True, "rollback": rollback}

    async def _get_release_status(self, task: Task) -> Dict[str, Any]:
        release_id = task.payload.get("release_id", "")
        release = self._releases.get(release_id, {})
        return {"success": True, "release": release}

    def _monitor(self) -> Dict[str, Any]:
        deployed = sum(1 for r in self._releases.values() if r.get("status") == "deployed")
        return {
            "success": True,
            "metrics": {
                "releases_count": len(self._releases),
                "deployed_releases": deployed,
                "versions_count": len(self._versions),
                "total_deploys": len(self._release_history),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "release_management",
            "metrics": self._monitor()["metrics"],
        }
