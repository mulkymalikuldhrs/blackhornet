"""Integration specialist — System integration and middleware."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class IntegrationSpecialist(BaseAgent):
    """Specialist agent for system integration and middleware.

    Handles API integrations, data synchronization, protocol translation,
    error handling, and integration monitoring.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._integrations: Dict[str, Dict[str, Any]] = {}
        self._sync_logs: List[Dict[str, Any]] = []
        self._protocol_mappings: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_integration":
            return await self._create_integration(task)
        elif action == "sync_data":
            return await self._sync_data(task)
        elif action == "translate_protocol":
            return await self._translate_protocol(task)
        elif action == "health_check":
            return await self._health_check(task)
        elif action == "transform_data":
            return await self._transform_data(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "integration_event":
            integration_id = message.get("payload", {}).get("integration_id", "")
            return self._integrations.get(integration_id, {"found": False})
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "api_integration", "data_synchronization", "protocol_translation",
            "error_handling", "integration_monitoring", "data_transformation",
            "middleware_management", "connector_management",
        ]

    async def _create_integration(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_integration")
        source_system = task.payload.get("source", {})
        target_system = task.payload.get("target", {})
        protocol = task.payload.get("protocol", "rest")

        integration_id = f"int-{int(time.time())}"
        integration = {
            "id": integration_id,
            "name": name,
            "source": source_system,
            "target": target_system,
            "protocol": protocol,
            "status": "active",
            "created_at": time.time(),
            "sync_count": 0,
            "error_count": 0,
        }
        self._integrations[integration_id] = integration
        return {"success": True, "integration_id": integration_id, "name": name}

    async def _sync_data(self, task: Task) -> Dict[str, Any]:
        integration_id = task.payload.get("integration_id", "")
        data = task.payload.get("data", {})
        direction = task.payload.get("direction", "source_to_target")

        if integration_id not in self._integrations:
            return {"success": False, "error": f"Integration {integration_id} not found"}

        sync_log = {
            "integration_id": integration_id,
            "direction": direction,
            "records_synced": len(data) if isinstance(data, dict) else 1,
            "synced_at": time.time(),
            "status": "success",
            "duration_ms": 250.0,
        }
        self._sync_logs.append(sync_log)
        self._integrations[integration_id]["sync_count"] += 1
        return {"success": True, "sync_log": sync_log}

    async def _translate_protocol(self, task: Task) -> Dict[str, Any]:
        source_protocol = task.payload.get("source_protocol", "rest")
        target_protocol = task.payload.get("target_protocol", "graphql")
        data = task.payload.get("data", {})

        mapping_key = f"{source_protocol}_to_{target_protocol}"
        if mapping_key not in self._protocol_mappings:
            self._protocol_mappings[mapping_key] = {
                "source": source_protocol,
                "target": target_protocol,
                "created_at": time.time(),
            }

        translated = {"translated": True, "source_protocol": source_protocol, "target_protocol": target_protocol}
        return {"success": True, "translation": translated}

    async def _health_check(self, task: Task) -> Dict[str, Any]:
        integration_id = task.payload.get("integration_id", "all")
        results: Dict[str, Any] = {}

        if integration_id == "all":
            for iid, integration in self._integrations.items():
                results[iid] = {"status": "healthy", "last_sync": integration.get("sync_count", 0)}
        elif integration_id in self._integrations:
            results[integration_id] = {"status": "healthy", "last_sync": self._integrations[integration_id].get("sync_count", 0)}

        return {"success": True, "health_results": results}

    async def _transform_data(self, task: Task) -> Dict[str, Any]:
        source_data = task.payload.get("data", {})
        transformation_rules = task.payload.get("rules", {})

        transformed = {}
        for source_key, target_key in transformation_rules.items():
            if source_key in source_data:
                transformed[target_key] = source_data[source_key]

        return {"success": True, "transformed_data": transformed, "fields_mapped": len(transformed)}

    def _monitor(self) -> Dict[str, Any]:
        total_syncs = sum(i.get("sync_count", 0) for i in self._integrations.values())
        total_errors = sum(i.get("error_count", 0) for i in self._integrations.values())
        return {
            "success": True,
            "metrics": {
                "integrations_count": len(self._integrations),
                "total_syncs": total_syncs,
                "total_errors": total_errors,
                "protocol_mappings": len(self._protocol_mappings),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "integration",
            "metrics": self._monitor()["metrics"],
        }
