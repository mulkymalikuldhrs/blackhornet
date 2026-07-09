"""Backward-compatible re-export of MCPTool base class.

The canonical definition now lives in ``tools.base``.  This module
keeps existing imports (``from .mcp import MCPToolBase``) working.
"""

from __future__ import annotations

from src.agent_tools.base import MCPTool as MCPToolBase  # noqa: F401 – backward compat alias
from src.agent_tools.base import MCPTool, RateLimitConfig, ToolHealth  # noqa: F401

__all__ = ["MCPToolBase", "MCPTool", "RateLimitConfig", "ToolHealth"]
