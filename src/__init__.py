"""BLACKHORNET — Source Package.

Unified API for all BH modules:
- Types: types
- Core: core
- Modules: auto_discovery, memory, thinking, graph, sandbox, ui, integration
- Agents: agents
- Swarm: swarm
- Config: config

Usage:
    from src import get_unified_launcher
    launcher = get_unified_launcher()
    launcher.start_all()
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def get_unified_launcher() -> Any:
    """Get the UnifiedLauncher instance for starting all BH modules."""
    from src.integration.unified_launcher import UnifiedLauncher
    return UnifiedLauncher()


def get_keeper_extension() -> Any:
    """Get KeeperExtension for health checks on new modules."""
    from src.integration.keeper_extension import KeeperExtension
    return KeeperExtension


def check_all_modules() -> Dict[str, Any]:
    """Check health of all new BH modules."""
    from src.integration.keeper_extension import KeeperExtension
    return KeeperExtension.check_all()


def get_amc_bridge() -> Any:
    """Get AMCBridge for connecting BH modules to AMC ecosystem."""
    from src.integration.amc_bridge import AMCBridge
    return AMCBridge()


def get_amc_tool_registrar() -> Any:
    """Get AMCToolRegistrar for registering BH modules as AMC tools."""
    from src.integration.amc_tools import AMCToolRegistrar
    return AMCToolRegistrar()
