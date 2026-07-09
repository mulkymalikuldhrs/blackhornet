"""DataIntegrityAgent — Data integrity and consistency validation."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class DataIntegrityAgent(BaseAgent):
    """Data integrity and consistency validation agent.

    Features
    --------
    * Checksum verification
    * Data consistency checking
    * Tamper detection
    * Replication integrity validation
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._checksums: Dict[str, str] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "verify":
            return await self._verify(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "integrity_query":
            return {"checksums": self._checksums}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "data_integrity_verification", "checksum_validation",
            "tamper_detection", "consistency_checking",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        data_records = task.payload.get("records", [])
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        for record in data_records:
            record_id = record.get("id", "")
            content = record.get("content", "")
            expected_hash = record.get("expected_hash", "")
            current_hash = hashlib.sha256(content.encode()).hexdigest()

            if expected_hash and current_hash != expected_hash:
                findings.append({
                    "type": "checksum_mismatch",
                    "severity": "critical",
                    "record_id": record_id,
                    "target": target,
                    "expected": expected_hash,
                    "actual": current_hash,
                })

            self._checksums[record_id] = current_hash

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "records_checked": len(data_records),
            "findings": findings,
        }

    async def _verify(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "checksums_tracked": len(self._checksums),
            "findings": self._findings[-20:],
        }
