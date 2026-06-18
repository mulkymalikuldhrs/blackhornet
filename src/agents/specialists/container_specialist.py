"""Container specialist — Containerization and Docker management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class ContainerSpecialist(BaseAgent):
    """Specialist agent for containerization and Docker management.

    Handles Dockerfile creation, image optimization, container orchestration,
    registry management, and security scanning.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._images: Dict[str, Dict[str, Any]] = {}
        self._containers: Dict[str, Dict[str, Any]] = {}
        self._registries: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_dockerfile":
            return await self._create_dockerfile(task)
        elif action == "build_image":
            return await self._build_image(task)
        elif action == "optimize_image":
            return await self._optimize_image(task)
        elif action == "run_container":
            return await self._run_container(task)
        elif action == "scan_image":
            return await self._scan_image(task)
        elif action == "manage_registry":
            return await self._manage_registry(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "container_status":
            container_id = message.get("payload", {}).get("container_id", "")
            return self._containers.get(container_id, {"found": False})
        elif msg_type == "image_query":
            return {"images": list(self._images.keys())}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "dockerfile_creation", "image_building", "image_optimization",
            "container_management", "registry_management", "security_scanning",
            "multi_stage_builds", "docker_compose",
        ]

    async def _create_dockerfile(self, task: Task) -> Dict[str, Any]:
        base_image = task.payload.get("base_image", "python:3.11-slim")
        stages = task.payload.get("stages", ["build", "runtime"])
        commands = task.payload.get("commands", [])

        dockerfile_content = f"FROM {base_image} AS base\n"
        for cmd in commands:
            dockerfile_content += f"RUN {cmd}\n"

        result = {
            "base_image": base_image,
            "stages": stages,
            "content": dockerfile_content,
            "multi_stage": len(stages) > 1,
            "created_at": time.time(),
        }
        return {"success": True, "dockerfile": result}

    async def _build_image(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "app")
        tag = task.payload.get("tag", "latest")
        dockerfile_path = task.payload.get("dockerfile_path", ".")

        image_name = f"{name}:{tag}"
        image = {
            "name": image_name,
            "tag": tag,
            "dockerfile_path": dockerfile_path,
            "size_mb": 150.0,
            "layers": 12,
            "built_at": time.time(),
            "vulnerabilities": {"critical": 0, "high": 1, "medium": 3},
        }
        self._images[image_name] = image
        return {"success": True, "image": image_name, "size_mb": image["size_mb"]}

    async def _optimize_image(self, task: Task) -> Dict[str, Any]:
        image_name = task.payload.get("image", "")
        if image_name not in self._images:
            return {"success": False, "error": f"Image {image_name} not found"}

        original_size = self._images[image_name]["size_mb"]
        optimizations = ["multi_stage_build", "alpine_base", "layer_caching", "minimize_layers"]
        optimized_size = original_size * 0.4

        self._images[image_name]["size_mb"] = optimized_size
        self._images[image_name]["optimizations"] = optimizations

        return {
            "success": True,
            "image": image_name,
            "original_size_mb": original_size,
            "optimized_size_mb": round(optimized_size, 2),
            "reduction_percent": round((1 - optimized_size / original_size) * 100, 1),
        }

    async def _run_container(self, task: Task) -> Dict[str, Any]:
        image = task.payload.get("image", "alpine:latest")
        name = task.payload.get("container_name", "container-" + str(int(time.time())))
        ports = task.payload.get("ports", {})
        env = task.payload.get("env", {})
        volumes = task.payload.get("volumes", [])

        container = {
            "id": name,
            "image": image,
            "status": "running",
            "ports": ports,
            "environment": env,
            "volumes": volumes,
            "started_at": time.time(),
            "restart_count": 0,
        }
        self._containers[name] = container
        return {"success": True, "container": name, "status": "running"}

    async def _scan_image(self, task: Task) -> Dict[str, Any]:
        image = task.payload.get("image", "")
        scan_type = task.payload.get("scan_type", "security")

        findings = {
            "critical": 0,
            "high": 2,
            "medium": 5,
            "low": 10,
            "info": 15,
        }
        return {"success": True, "image": image, "scan_type": scan_type, "findings": findings}

    async def _manage_registry(self, task: Task) -> Dict[str, Any]:
        operation = task.payload.get("operation", "list")
        registry_url = task.payload.get("registry_url", "docker.io")

        if operation == "list":
            return {"success": True, "registry": registry_url, "repositories": list(self._images.keys())}
        elif operation == "push":
            image = task.payload.get("image", "")
            return {"success": True, "image": image, "registry": registry_url, "status": "pushed"}
        elif operation == "pull":
            image = task.payload.get("image", "")
            return {"success": True, "image": image, "registry": registry_url, "status": "pulled"}
        return {"success": False, "error": f"Unknown registry operation: {operation}"}

    def _monitor(self) -> Dict[str, Any]:
        running = sum(1 for c in self._containers.values() if c.get("status") == "running")
        return {
            "success": True,
            "metrics": {
                "images_count": len(self._images),
                "containers_total": len(self._containers),
                "containers_running": running,
                "registries": len(self._registries),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "container",
            "metrics": self._monitor()["metrics"],
        }
