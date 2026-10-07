"""Backward-compat shim — FileTool lives in file_tool.py.

Historical importers (`from src.agent_tools.file import FileTool`)
must keep working after the module rename.
"""

from __future__ import annotations

from .file_tool import FileTool

__all__ = ["FileTool"]
