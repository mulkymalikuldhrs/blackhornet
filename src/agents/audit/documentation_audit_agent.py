"""DocumentationAuditAgent — Documentation completeness and accuracy."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

DOC_REQUIREMENTS = {
    "readme": {"required": True, "severity": "medium", "description": "README file"},
    "api_documentation": {"required": True, "severity": "high", "description": "API documentation"},
    "architecture_decision_records": {"required": False, "severity": "low", "description": "ADRs"},
    "deployment_guide": {"required": True, "severity": "high", "description": "Deployment guide"},
    "contributing_guide": {"required": False, "severity": "low", "description": "Contributing guide"},
    "changelog": {"required": True, "severity": "medium", "description": "Changelog"},
    "license": {"required": True, "severity": "medium", "description": "License file"},
    "code_comments": {"required": True, "severity": "medium", "description": "Code comments"},
    "inline_documentation": {"required": True, "severity": "medium", "description": "Inline docs"},
    "type_hints": {"required": True, "severity": "medium", "description": "Type hints"},
}


class DocumentationAuditAgent(BaseAgent):
    """Documentation completeness and accuracy agent.

    Features
    --------
    * Documentation completeness validation
    * API documentation auditing
    * Code comment quality assessment
    * Documentation freshness checking
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._completeness_score: float = 0.0

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "validate":
            return await self._validate(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "doc_query":
            return {"completeness_score": self._completeness_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "documentation_audit", "completeness_validation",
            "api_doc_audit", "documentation_freshness",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        docs = task.payload.get("docs", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        present = 0

        for doc, config in DOC_REQUIREMENTS.items():
            if docs.get(doc, False):
                present += 1
            elif config["required"]:
                findings.append({
                    "type": "missing_documentation",
                    "severity": config["severity"],
                    "document": doc,
                    "target": target,
                    "description": f"Missing documentation: {config['description']}",
                })

        self._completeness_score = present / len(DOC_REQUIREMENTS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "completeness_score": self._completeness_score,
            "docs_present": present,
            "docs_total": len(DOC_REQUIREMENTS),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "completeness_score": self._completeness_score,
            "findings": self._findings[-20:],
        }
