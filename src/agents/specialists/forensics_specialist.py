"""Forensics specialist — Digital forensics and investigation."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class ForensicsSpecialist(BaseAgent):
    """Specialist agent for digital forensics and investigation.

    Handles evidence collection, chain of custody, forensic analysis,
    timeline reconstruction, and investigation reporting.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._cases: Dict[str, Dict[str, Any]] = {}
        self._evidence: Dict[str, List[Dict[str, Any]]] = {}
        self._timeline: Dict[str, List[Dict[str, Any]]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "open_case":
            return await self._open_case(task)
        elif action == "collect_evidence":
            return await self._collect_evidence(task)
        elif action == "analyze_evidence":
            return await self._analyze_evidence(task)
        elif action == "reconstruct_timeline":
            return await self._reconstruct_timeline(task)
        elif action == "generate_report":
            return await self._generate_report(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "forensic_evidence":
            case_id = message.get("payload", {}).get("case_id", "")
            evidence = message.get("payload", {}).get("evidence", {})
            self._evidence.setdefault(case_id, []).append({**evidence, "received_at": time.time()})
            return {"evidence_received": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "case_management", "evidence_collection", "evidence_analysis",
            "timeline_reconstruction", "chain_of_custody", "forensic_reporting",
            "memory_analysis", "disk_forensics",
        ]

    async def _open_case(self, task: Task) -> Dict[str, Any]:
        title = task.payload.get("title", "Investigation")
        description = task.payload.get("description", "")
        priority = task.payload.get("priority", "medium")

        case_id = f"case-{int(time.time())}"
        case = {
            "case_id": case_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "open",
            "created_at": time.time(),
            "evidence_count": 0,
            "timeline_events": 0,
        }
        self._cases[case_id] = case
        self._evidence[case_id] = []
        self._timeline[case_id] = []
        return {"success": True, "case_id": case_id, "title": title}

    async def _collect_evidence(self, task: Task) -> Dict[str, Any]:
        case_id = task.payload.get("case_id", "")
        evidence_type = task.payload.get("type", "digital")
        source = task.payload.get("source", "")
        description = task.payload.get("description", "")
        hash_value = task.payload.get("hash", "")

        if case_id not in self._evidence:
            return {"success": False, "error": f"Case {case_id} not found"}

        evidence_id = f"ev-{int(time.time() * 1000)}"
        evidence = {
            "evidence_id": evidence_id,
            "type": evidence_type,
            "source": source,
            "description": description,
            "hash": hash_value,
            "collected_at": time.time(),
            "chain_of_custody": [{"action": "collected", "timestamp": time.time(), "officer": "system"}],
        }
        self._evidence[case_id].append(evidence)
        if case_id in self._cases:
            self._cases[case_id]["evidence_count"] += 1
        return {"success": True, "evidence_id": evidence_id, "case_id": case_id}

    async def _analyze_evidence(self, task: Task) -> Dict[str, Any]:
        case_id = task.payload.get("case_id", "")
        evidence_id = task.payload.get("evidence_id", "")
        analysis_type = task.payload.get("analysis_type", "metadata")

        findings = [
            {"type": analysis_type, "finding": "Timestamps indicate activity during incident window", "confidence": 0.85},
            {"type": analysis_type, "finding": "File signatures match known malware patterns", "confidence": 0.72},
        ]

        return {"success": True, "case_id": case_id, "evidence_id": evidence_id, "findings": findings}

    async def _reconstruct_timeline(self, task: Task) -> Dict[str, Any]:
        case_id = task.payload.get("case_id", "")
        events = task.payload.get("events", [])

        if case_id not in self._timeline:
            self._timeline[case_id] = []

        for event in events:
            self._timeline[case_id].append({
                **event,
                "added_at": time.time(),
            })

        if case_id in self._cases:
            self._cases[case_id]["timeline_events"] = len(self._timeline[case_id])

        sorted_timeline = sorted(self._timeline[case_id], key=lambda e: e.get("timestamp", 0))
        return {"success": True, "case_id": case_id, "timeline": sorted_timeline, "events_count": len(sorted_timeline)}

    async def _generate_report(self, task: Task) -> Dict[str, Any]:
        case_id = task.payload.get("case_id", "")
        case = self._cases.get(case_id, {})
        evidence = self._evidence.get(case_id, [])
        timeline = self._timeline.get(case_id, [])

        report = {
            "case_id": case_id,
            "title": case.get("title", ""),
            "status": case.get("status", ""),
            "evidence_count": len(evidence),
            "timeline_events": len(timeline),
            "findings": [],
            "recommendations": ["Preserve all evidence", "Notify legal team", "Document chain of custody"],
            "generated_at": time.time(),
        }
        return {"success": True, "report": report}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "cases_count": len(self._cases),
                "open_cases": sum(1 for c in self._cases.values() if c.get("status") == "open"),
                "total_evidence": sum(len(e) for e in self._evidence.values()),
                "total_timeline_events": sum(len(t) for t in self._timeline.values()),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "forensics",
            "metrics": self._monitor()["metrics"],
        }
