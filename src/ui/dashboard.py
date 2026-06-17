from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Dashboard:
    def __init__(self, api_bridge=None, event_bus=None):
        self._api = api_bridge
        self._event_bus = event_bus
        self._snapshots: List[Dict[str, Any]] = []
        self._max_snapshots = 100

    def set_api(self, api_bridge) -> None:
        self._api = api_bridge

    def set_event_bus(self, event_bus) -> None:
        self._event_bus = event_bus

    def snapshot(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "graph": {},
            "events": {},
            "memory": {},
        }
        if self._api:
            g_resp = self._api.get_graph()
            if g_resp.success:
                gd = g_resp.data
                data["graph"] = {
                    "node_count": len(gd.get("nodes", [])),
                    "edge_count": len(gd.get("edges", [])),
                    "stats": gd.get("stats", {}),
                }
            s_resp = self._api.get_status()
            if s_resp.success:
                data["status"] = s_resp.data
        if self._event_bus:
            data["events"] = {"counts": self._event_bus.count()}
        self._snapshots.append(data)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        return data

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._snapshots[-limit:]

    def summary(self) -> str:
        data = self._snapshots[-1] if self._snapshots else self.snapshot()
        lines: List[str] = []
        lines.append(f"Time: {data.get('time_str', '—')}")
        graph = data.get("graph", {})
        lines.append(f"Graph: {graph.get('node_count', 0)} nodes, "
                     f"{graph.get('edge_count', 0)} edges")
        events = data.get("events", {}).get("counts", {})
        if events:
            lines.append("Events: " + ", ".join(
                f"{k}={v}" for k, v in events.items()
            ))
        status = data.get("status", {}).get("services", {})
        if status:
            ok_count = sum(1 for s in status.values()
                           if s.get("status") == "ok")
            lines.append(f"Services: {ok_count}/{len(status)} healthy")
        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self._snapshots[-1] if self._snapshots else {},
                          indent=indent)

    def clear(self) -> None:
        self._snapshots.clear()
