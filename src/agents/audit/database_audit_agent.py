"""DatabaseAuditAgent — Database query performance and security."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

SQL_ISSUE_PATTERNS = {
    "sql_injection": {"pattern": r"(?i)('.*\s+OR\s+.*'|UNION\s+SELECT|DROP\s+TABLE)", "severity": "critical"},
    "missing_index": {"pattern": r"(?i)(SELECT\s+\*\s+FROM.*WHERE.*NOT.*INDEX)", "severity": "medium"},
    "unparameterized_query": {"pattern": r"(?i)(execute\(['\"].*%s|execute\(['\"].*\+)", "severity": "high"},
    "n_plus_one": {"pattern": r"(?i)(for\s+.*\s+in\s+.*\.all\(\))", "severity": "medium"},
    "missing_limit": {"pattern": r"(?i)(SELECT\s+.*\s+FROM\s+.*\s+(?:WHERE|JOIN).*(?!LIMIT))", "severity": "low"},
    "full_table_scan": {"pattern": r"(?i)(SELECT\s+\*\s+FROM\s+\w+\s*$)", "severity": "medium"},
}


class DatabaseAuditAgent(BaseAgent):
    """Database query performance and security agent.

    Features
    --------
    * SQL injection pattern detection
    * Query performance analysis
    * Index usage verification
    * Connection pool auditing
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._queries_audited: int = 0

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "scan":
            return await self._scan(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "db_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "sql_injection_detection", "query_performance_audit", "index_analysis",
            "connection_pool_audit", "database_security",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        queries = task.payload.get("queries", [])
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        for query_info in queries:
            query = query_info.get("query", "")
            query_time = query_info.get("execution_time_ms", 0)
            self._queries_audited += 1

            for issue_name, config in SQL_ISSUE_PATTERNS.items():
                if re.search(config["pattern"], query):
                    findings.append({
                        "type": issue_name,
                        "severity": config["severity"],
                        "query": query[:100],
                        "execution_time_ms": query_time,
                        "target": target,
                    })

            if query_time > 1000:
                findings.append({
                    "type": "slow_query",
                    "severity": "medium",
                    "query": query[:100],
                    "execution_time_ms": query_time,
                    "target": target,
                })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "queries_audited": len(queries),
            "findings": findings,
        }

    async def _scan(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "total_queries_audited": self._queries_audited,
            "findings": self._findings[-20:],
        }
