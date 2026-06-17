from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KeeperExtension:
    """Extend BH scripts/keeper.py with new module health checks.

    Provides health check methods for all new modules (auto_discovery,
    memory, thinking, graph, sandbox, ui) so the keeper can monitor them.
    """

    @staticmethod
    def check_module(module_name: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "module": module_name,
            "status": "unknown",
            "error": "",
        }
        try:
            if module_name == "auto_discovery":
                from src.auto_discovery.integration import AutoDiscoveryEngine
                engine = AutoDiscoveryEngine()
                result["status"] = "ok"
            elif module_name == "memory":
                from src.memory.system import MemorySystem, MemorySystemConfig
                cfg = MemorySystemConfig(data_dir="/tmp/bh_test_memory")
                ms = MemorySystem(cfg)
                result["status"] = "ok"
            elif module_name == "graph":
                from src.graph.graph_store import GraphStore
                gs = GraphStore(":memory:")
                result["status"] = "ok"
            elif module_name == "sandbox":
                from src.sandbox.sandbox_manager import SandboxManager
                sm = SandboxManager()
                result["status"] = "ok"
            elif module_name == "ui":
                from src.ui.web_server import WebServer
                ws = WebServer()
                result["status"] = "ok"
            else:
                result["status"] = "unknown_module"
        except ImportError as exc:
            result["status"] = "not_installed"
            result["error"] = str(exc)
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
        return result

    @staticmethod
    def check_all() -> Dict[str, Any]:
        modules = ["auto_discovery", "memory", "graph", "sandbox", "ui"]
        results: Dict[str, Any] = {}
        all_ok = True
        for mod in modules:
            r = KeeperExtension.check_module(mod)
            results[mod] = r
            if r["status"] != "ok":
                all_ok = False
        return {
            "all_ok": all_ok,
            "modules": results,
            "timestamp": time.time(),
        }

    @staticmethod
    def summary() -> str:
        status = KeeperExtension.check_all()
        parts: List[str] = []
        for mod, info in status["modules"].items():
            icon = "OK" if info["status"] == "ok" else "ERR"
            parts.append(f"[{icon}] {mod}")
        return " | ".join(parts)
