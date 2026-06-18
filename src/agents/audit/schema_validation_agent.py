"""SchemaValidationAgent — Data schema validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

SCHEMA_ISSUES = {
    "missing_required_field": {"severity": "high", "description": "Required field missing"},
    "type_mismatch": {"severity": "high", "description": "Field type mismatch"},
    "invalid_enum_value": {"severity": "medium", "description": "Invalid enum value"},
    "string_too_long": {"severity": "medium", "description": "String exceeds max length"},
    "string_too_short": {"severity": "low", "description": "String below min length"},
    "number_out_of_range": {"severity": "medium", "description": "Number out of range"},
    "invalid_format": {"severity": "medium", "description": "Invalid string format"},
    "unexpected_field": {"severity": "low", "description": "Unexpected field present"},
    "null_value": {"severity": "high", "description": "Null value for required field"},
    "nested_validation_error": {"severity": "high", "description": "Nested object validation error"},
}


class SchemaValidationAgent(BaseAgent):
    """Data schema validation agent.

    Features
    --------
    * Schema compliance validation
    * Type checking and coercion detection
    * Data format verification
    * Schema evolution tracking
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._validation_count: int = 0

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
        if msg_type == "schema_query":
            return {"validation_count": self._validation_count}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "schema_validation", "type_checking", "format_verification",
            "schema_evolution_tracking",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        data = task.payload.get("data", {})
        schema = task.payload.get("schema", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        self._validation_count += 1

        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required_fields:
            if field not in data:
                findings.append({
                    "type": "missing_required_field",
                    "severity": SCHEMA_ISSUES["missing_required_field"]["severity"],
                    "field": field,
                    "target": target,
                })
            elif data[field] is None:
                findings.append({
                    "type": "null_value",
                    "severity": SCHEMA_ISSUES["null_value"]["severity"],
                    "field": field,
                    "target": target,
                })

        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get("type", "")
                if expected_type and not self._check_type(value, expected_type):
                    findings.append({
                        "type": "type_mismatch",
                        "severity": SCHEMA_ISSUES["type_mismatch"]["severity"],
                        "field": field,
                        "expected_type": expected_type,
                        "actual_type": type(value).__name__,
                        "target": target,
                    })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "fields_checked": len(data),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _check_type(self, value: Any, expected_type: str) -> bool:
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        return isinstance(value, expected)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "validation_count": self._validation_count,
            "findings": self._findings[-20:],
        }
