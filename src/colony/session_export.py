"""SessionExporter — always-on session and memory export.

Exports everything the colony does:
  - Session log (markdown): lifecycle events, agent state, milestones
  - Graph state (JSON): all nodes + edges from Graphify
  - Memory state (JSON): memory system contents
  - Ecosystem status (JSON): comprehensive status snapshot
  - Auto-todo (markdown): derived from milestones, errors, open tasks
  - Cleanup: keeps last N exports, rotates old ones

Wired into EcosystemOrchestrator for always-on operation.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)

MAX_EXPORTS = 50
EXPORT_INTERVAL = 120


class SessionExporter:
    """Comprehensive session + memory exporter.

    Usage:
        exporter = SessionExporter(export_dir="data/session-export")
        await exporter.export_full(
            status={...},
            lifecycle_events=[...],
            graph_store=graph,
            memory_system=memory,
        )
        exporter.export_final(status={...})
    """

    def __init__(
        self,
        export_dir: str = "data/session-export",
        max_exports: int = MAX_EXPORTS,
        auto_rotate: bool = True,
    ) -> None:
        self._export_dir = export_dir
        self._max_exports = max_exports
        self._auto_rotate = auto_rotate
        self._export_count = 0
        self._session_start: Optional[float] = None
        os.makedirs(self._export_dir, exist_ok=True)

    @property
    def export_count(self) -> int:
        return self._export_count

    def set_session_start(self, timestamp: float) -> None:
        self._session_start = timestamp

    def _timestamp_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def _rotate(self) -> None:
        if not self._auto_rotate:
            return
        try:
            all_files = sorted(
                f for f in os.listdir(self._export_dir)
                if f.endswith(".json") or f.endswith(".md")
            )
            while len(all_files) > self._max_exports:
                oldest = all_files.pop(0)
                os.remove(os.path.join(self._export_dir, oldest))
        except Exception as e:
            logger.debug("export_rotate_error err=%s", e)

    def _write_json(self, filename: str, data: Any) -> str:
        filepath = os.path.join(self._export_dir, filename)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return filepath

    def _write_md(self, filename: str, content: str) -> str:
        filepath = os.path.join(self._export_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    async def export_full(
        self,
        status: Optional[dict[str, Any]] = None,
        lifecycle_events: Optional[list[dict[str, Any]]] = None,
        graph_store: Any = None,
        memory_system: Any = None,
        colony_id: str = "unknown",
    ) -> dict[str, str]:
        """Export everything: status, lifecycle, graph, memory, session log.

        Returns dict of {export_type: filepath}.
        """
        ts = self._timestamp_str()
        exported: dict[str, str] = {}

        status = status or {}

        ecosystem_path = self._write_json(
            f"ecosystem_status_{ts}.json", status
        )
        exported["ecosystem"] = ecosystem_path

        if graph_store:
            try:
                if hasattr(graph_store, "export_json"):
                    graph_data = graph_store.export_json()
                elif hasattr(graph_store, "get_graph"):
                    graph_data = graph_store.get_graph()
                else:
                    graph_data = {}
                graph_path = self._write_json(f"graph_{ts}.json", graph_data)
                exported["graph"] = graph_path
            except Exception as e:
                logger.debug("graph_export_error err=%s", e)

        if memory_system:
            try:
                memory_data: dict[str, Any] = {}
                if hasattr(memory_system, "get_stats"):
                    memory_data["stats"] = memory_system.get_stats()
                if hasattr(memory_system, "get_all"):
                    mem_all = memory_system.get_all() if not hasattr(memory_system, "get_all") or not callable(memory_system.get_all) else {}
                    memory_data["data"] = mem_all
                memory_path = self._write_json(f"memory_{ts}.json", memory_data)
                exported["memory"] = memory_path
            except Exception as e:
                logger.debug("memory_export_error err=%s", e)

        session_log = self._generate_session_log(
            status=status,
            lifecycle_events=lifecycle_events or [],
            colony_id=colony_id,
            start_time=self._session_start,
        )
        log_path = self._write_md(f"session_{ts}.md", session_log)
        exported["session_log"] = log_path

        todo = self._generate_auto_todo(
            lifecycle_events=lifecycle_events or [],
            status=status,
        )
        todo_path = self._write_md(f"auto_todo_{ts}.md", todo)
        exported["auto_todo"] = todo_path

        self._export_count += 1
        self._rotate()

        logger.info(
            "session_exported #%d files=%s",
            self._export_count,
            ", ".join(exported.values()),
        )

        return exported

    async def export_final(
        self,
        status: Optional[dict[str, Any]] = None,
        lifecycle_events: Optional[list[dict[str, Any]]] = None,
        colony_id: str = "unknown",
    ) -> dict[str, str]:
        """Export final session summary on shutdown."""
        ts = self._timestamp_str()
        summary = self._generate_session_summary(
            status=status or {},
            lifecycle_events=lifecycle_events or [],
            colony_id=colony_id,
        )
        path = self._write_md(f"session_final_{ts}.md", summary)
        logger.info("session_final_exported file=%s", path)
        return {"session_final": path}

    def _generate_session_log(
        self,
        status: dict[str, Any],
        lifecycle_events: list[dict[str, Any]],
        colony_id: str,
        start_time: Optional[float] = None,
    ) -> str:
        lines: list[str] = [
            f"# Session Log — {colony_id}",
            f"**Exported**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        ]
        if start_time:
            uptime = time.time() - start_time
            lines.append(f"**Session Uptime**: {uptime:.0f}s")
        lines.append("")

        orch = status.get("orchestrator", {})
        lines.append(f"## Ecosystem Status")
        lines.append(f"- Colony: {orch.get('colony_name', '?')} v{orch.get('version', '?')}")
        lines.append(f"- Running: {orch.get('running', False)}")
        lines.append(f"- Agents: {status.get('agents', {}).get('total', 0)}")
        lines.append(f"- Peers: {status.get('radar', {}).get('peer_count', 0)}")
        lines.append(f"- Colonies: {status.get('colonies', {}).get('total', 0)}")
        lines.append("")

        errors = [e for e in lifecycle_events if e.get("event_type") == "error"]
        if errors:
            lines.append(f"## Errors ({len(errors)})")
            for e in errors[-10:]:
                msg = e.get("data", {}).get("message", str(e.get("data", {})))
                lines.append(f"- {e.get('source', '?')}: {msg}")
            lines.append("")

        milestones = [e for e in lifecycle_events if e.get("event_type") == "milestone"]
        if milestones:
            lines.append(f"## Milestones ({len(milestones)})")
            for m in milestones:
                md = m.get("data", {})
                lines.append(f"- {md.get('milestone', '?')}: {md.get('description', '')}")
            lines.append("")

        tasks_done = len([e for e in lifecycle_events if e.get("event_type") == "task_completed"])
        tasks_failed = len([e for e in lifecycle_events if e.get("event_type") == "task_failed"])
        lines.append(f"## Tasks")
        lines.append(f"- Completed: {tasks_done}")
        lines.append(f"- Failed: {tasks_failed}")
        if tasks_done + tasks_failed > 0:
            rate = tasks_done / (tasks_done + tasks_failed) * 100
            lines.append(f"- Success Rate: {rate:.1f}%")
        lines.append("")

        return "\n".join(lines)

    def _generate_auto_todo(
        self,
        lifecycle_events: list[dict[str, Any]],
        status: dict[str, Any],
    ) -> str:
        lines: list[str] = [
            f"# Auto-Todo ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})",
            "",
        ]

        errors = [e for e in lifecycle_events if e.get("event_type") == "error"]
        if errors:
            lines.append("## ⚠ Errors to Resolve")
            for e in errors[-5:]:
                msg = e.get("data", {}).get("message", str(e.get("data", {})))
                lines.append(f"- [ ] Fix: {msg}")
            lines.append("")

        tasks_failed = [e for e in lifecycle_events if e.get("event_type") == "task_failed"]
        if tasks_failed:
            lines.append("## Failed Tasks (needs retry)")
            for t in tasks_failed[-5:]:
                td = t.get("data", {})
                desc = td.get("task_type", td.get("task_id", "unknown"))
                lines.append(f"- [ ] Retry: {desc}")
            lines.append("")

        nest = status.get("nest", {})
        unhealthy: list[str] = []
        if nest:
            comps = nest.get("components", {})
            unhealthy = [k for k, v in comps.items() if v != "running"]
            if unhealthy:
                lines.append("## Unhealthy Nest Components")
                for c in unhealthy:
                    lines.append(f"- [ ] Restart: {c}")
                lines.append("")

        if not errors and not tasks_failed and not unhealthy:
            lines.append("*No pending issues detected.*")
            lines.append("")

        lines.append("---")
        lines.append(f"*Auto-generated by SessionExporter*")
        return "\n".join(lines)

    def _generate_session_summary(
        self,
        status: dict[str, Any],
        lifecycle_events: list[dict[str, Any]],
        colony_id: str,
    ) -> str:
        lines: list[str] = [
            f"# Session Summary — {colony_id}",
            f"**Ended**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        orch = status.get("orchestrator", {})
        if orch.get("uptime"):
            lines.append(f"**Total Uptime**: {orch['uptime']:.0f}s")
        lines.append("")

        total = len(lifecycle_events)
        errors = sum(1 for e in lifecycle_events if e.get("event_type") == "error")
        milestones = sum(1 for e in lifecycle_events if e.get("event_type") == "milestone")
        tasks_done = sum(1 for e in lifecycle_events if e.get("event_type") == "task_completed")

        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Events | {total} |")
        lines.append(f"| Milestones | {milestones} |")
        lines.append(f"| Errors | {errors} |")
        lines.append(f"| Tasks Completed | {tasks_done} |")
        lines.append("")

        if milestones:
            lines.append("## Milestones Achieved")
            for e in lifecycle_events:
                if e.get("event_type") == "milestone":
                    md = e.get("data", {})
                    lines.append(f"- {md.get('milestone', '?')}")
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        return {
            "export_count": self._export_count,
            "export_dir": self._export_dir,
        }
