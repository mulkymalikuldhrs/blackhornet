"""Documentation specialist — Technical documentation management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class DocumentationSpecialist(BaseAgent):
    """Specialist agent for technical documentation management.

    Handles documentation generation, API docs, architecture docs,
    runbooks, and documentation quality assessment.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.CODER, autonomy_level=1)
        super().__init__(spec=spec, **kwargs)
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._api_docs: Dict[str, Dict[str, Any]] = {}
        self._templates: Dict[str, str] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "generate_api_docs":
            return await self._generate_api_docs(task)
        elif action == "create_runbook":
            return await self._create_runbook(task)
        elif action == "generate_readme":
            return await self._generate_readme(task)
        elif action == "validate_docs":
            return await self._validate_docs(task)
        elif action == "generate_architecture":
            return await self._generate_architecture(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "doc_query":
            doc_id = message.get("payload", {}).get("doc_id", "")
            return self._documents.get(doc_id, {"found": False})
        elif msg_type == "doc_health_check":
            return {"status": "healthy", "documents": len(self._documents)}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "api_documentation", "runbook_creation", "readme_generation",
            "architecture_documentation", "documentation_validation",
            "code_commenting", "changelog_generation", "doc_quality_assessment",
        ]

    async def _generate_api_docs(self, task: Task) -> Dict[str, Any]:
        api_spec = task.payload.get("api_spec", {})
        format_type = task.payload.get("format", "openapi")

        doc_id = f"api-doc-{int(time.time())}"
        endpoints = api_spec.get("paths", {})
        doc = {
            "id": doc_id,
            "format": format_type,
            "title": api_spec.get("info", {}).get("title", "API Documentation"),
            "version": api_spec.get("info", {}).get("version", "1.0.0"),
            "endpoints_count": len(endpoints),
            "sections": ["overview", "authentication", "endpoints", "errors", "examples"],
            "generated_at": time.time(),
        }
        self._api_docs[doc_id] = doc
        self._documents[doc_id] = doc
        return {"success": True, "doc_id": doc_id, "doc": doc}

    async def _create_runbook(self, task: Task) -> Dict[str, Any]:
        title = task.payload.get("title", "Default Runbook")
        procedures = task.payload.get("procedures", [])

        doc_id = f"runbook-{int(time.time())}"
        doc = {
            "id": doc_id,
            "title": title,
            "type": "runbook",
            "procedures": procedures,
            "sections": ["overview", "prerequisites", "procedures", "troubleshooting", "escalation"],
            "created_at": time.time(),
            "review_status": "draft",
        }
        self._documents[doc_id] = doc
        return {"success": True, "doc_id": doc_id, "doc": doc}

    async def _generate_readme(self, task: Task) -> Dict[str, Any]:
        project_name = task.payload.get("project_name", "Project")
        description = task.payload.get("description", "")
        features = task.payload.get("features", [])

        doc_id = f"readme-{int(time.time())}"
        sections = ["# " + project_name, "## Description", "## Features", "## Installation", "## Usage", "## Contributing"]
        doc = {
            "id": doc_id,
            "type": "readme",
            "project_name": project_name,
            "description": description,
            "features": features,
            "sections": sections,
            "created_at": time.time(),
        }
        self._documents[doc_id] = doc
        return {"success": True, "doc_id": doc_id, "sections": sections}

    async def _validate_docs(self, task: Task) -> Dict[str, Any]:
        doc_id = task.payload.get("doc_id", "")
        doc = self._documents.get(doc_id, {})

        issues: List[str] = []
        if not doc.get("sections"):
            issues.append("missing_sections")
        if not doc.get("title"):
            issues.append("missing_title")

        return {"success": True, "doc_id": doc_id, "valid": len(issues) == 0, "issues": issues}

    async def _generate_architecture(self, task: Task) -> Dict[str, Any]:
        project = task.payload.get("project", "default")
        components = task.payload.get("components", [])

        doc_id = f"arch-{int(time.time())}"
        doc = {
            "id": doc_id,
            "type": "architecture",
            "project": project,
            "components": components,
            "diagrams": ["system_overview", "data_flow", "deployment"],
            "created_at": time.time(),
        }
        self._documents[doc_id] = doc
        return {"success": True, "doc_id": doc_id, "doc": doc}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "documents_count": len(self._documents),
                "api_docs_count": len(self._api_docs),
                "doc_types": list(set(d.get("type", "unknown") for d in self._documents.values())),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "documentation",
            "metrics": self._monitor()["metrics"],
        }
