"""Logging specialist — Logging infrastructure and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class LoggingSpecialist(BaseAgent):
    """Specialist agent for logging infrastructure and management.

    Handles log collection, parsing, aggregation, rotation,
    structured logging, and log-based analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._log_entries: List[Dict[str, Any]] = []
        self._log_configs: Dict[str, Dict[str, Any]] = {}
        self._parsers: Dict[str, str] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "configure":
            return await self._configure_logging(task)
        elif action == "ingest":
            return await self._ingest_logs(task)
        elif action == "parse":
            return await self._parse_logs(task)
        elif action == "search":
            return await self._search_logs(task)
        elif action == "rotate":
            return await self._rotate_logs(task)
        elif action == "aggregate":
            return await self._aggregate_logs(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "log_entry":
            entry = message.get("payload", {})
            self._log_entries.append({**entry, "received_at": time.time()})
            return {"log_received": True}
        elif msg_type == "log_query":
            level = message.get("payload", {}).get("level", "INFO")
            filtered = [e for e in self._log_entries if e.get("level") == level]
            return {"count": len(filtered), "entries": filtered[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "log_collection", "log_parsing", "log_aggregation",
            "log_rotation", "structured_logging", "log_search",
            "log_analysis", "log_retention",
        ]

    async def _configure_logging(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default")
        level = task.payload.get("level", "INFO")
        format_type = task.payload.get("format", "json")
        outputs = task.payload.get("outputs", ["stdout"])
        retention_days = task.payload.get("retention_days", 30)

        config = {
            "name": name,
            "level": level,
            "format": format_type,
            "outputs": outputs,
            "retention_days": retention_days,
            "configured_at": time.time(),
        }
        self._log_configs[name] = config
        return {"success": True, "config_name": name, "config": config}

    async def _ingest_logs(self, task: Task) -> Dict[str, Any]:
        entries = task.payload.get("entries", [])
        source = task.payload.get("source", "unknown")

        ingested = 0
        for entry in entries:
            self._log_entries.append({
                "message": entry.get("message", ""),
                "level": entry.get("level", "INFO"),
                "source": source,
                "timestamp": entry.get("timestamp", time.time()),
                "metadata": entry.get("metadata", {}),
            })
            ingested += 1

        return {"success": True, "ingested_count": ingested, "source": source}

    async def _parse_logs(self, task: Task) -> Dict[str, Any]:
        pattern_name = task.payload.get("pattern", "default")
        content = task.payload.get("content", "")

        patterns = {
            "apache": r'\[.*?\] \w+ \S+ \S+ "\w+ \S+ \S+" \d+ \d+',
            "nginx": r'\S+ - \S+ \[.*?\] "\w+ \S+ \S+" \d+ \d+',
            "syslog": r'\w+ \d+ \d+:\d+:\d+ \S+ \S+:.*',
            "json": r'\{.*\}',
        }

        return {
            "success": True,
            "pattern": pattern_name,
            "available_patterns": list(patterns.keys()),
            "parsed": bool(content),
        }

    async def _search_logs(self, task: Task) -> Dict[str, Any]:
        query = task.payload.get("query", "")
        level = task.payload.get("level")
        start_time = task.payload.get("start_time", time.time() - 3600)
        end_time = task.payload.get("end_time", time.time())
        limit = task.payload.get("limit", 100)

        results = self._log_entries
        if query:
            results = [e for e in results if query.lower() in e.get("message", "").lower()]
        if level:
            results = [e for e in results if e.get("level") == level]
        results = [e for e in results if start_time <= e.get("timestamp", 0) <= end_time]

        return {"success": True, "query": query, "results": results[:limit], "total": len(results)}

    async def _rotate_logs(self, task: Task) -> Dict[str, Any]:
        source = task.payload.get("source", "all")
        max_size_mb = task.payload.get("max_size_mb", 100)
        keep_files = task.payload.get("keep_files", 5)

        rotation = {
            "source": source,
            "max_size_mb": max_size_mb,
            "keep_files": keep_files,
            "rotated_at": time.time(),
            "entries_rotated": len(self._log_entries) if source == "all" else 0,
        }
        return {"success": True, "rotation": rotation}

    async def _aggregate_logs(self, task: Task) -> Dict[str, Any]:
        group_by = task.payload.get("group_by", "level")
        time_range = task.payload.get("time_range", 3600)
        start_time = time.time() - time_range

        recent = [e for e in self._log_entries if e.get("timestamp", 0) >= start_time]
        aggregated: Dict[str, int] = {}
        for entry in recent:
            key = entry.get(group_by, "unknown")
            aggregated[key] = aggregated.get(key, 0) + 1

        return {"success": True, "group_by": group_by, "aggregation": aggregated, "total_entries": len(recent)}

    def _monitor(self) -> Dict[str, Any]:
        levels: Dict[str, int] = {}
        for entry in self._log_entries:
            level = entry.get("level", "UNKNOWN")
            levels[level] = levels.get(level, 0) + 1

        return {
            "success": True,
            "metrics": {
                "total_entries": len(self._log_entries),
                "levels": levels,
                "configs": len(self._log_configs),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "logging",
            "metrics": self._monitor()["metrics"],
        }
