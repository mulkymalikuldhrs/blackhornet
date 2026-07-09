"""Tool type definitions for the AI MultiColony Ecosystem.

Merges AI-Manus tool_type pattern, Nanobot ToolRegistry tags, and
OpenManus BaseTool/ToolResult Pydantic models.

ToolCall and ToolResult are defined in models.py (unified superset).
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .models import ToolCall, ToolResult


class ToolType(str, Enum):
    """Types of tools available in the system."""

    SHELL = "shell"
    FILE = "file"
    BROWSER = "browser"
    SEARCH = "search"
    CODE = "code"
    MCP = "mcp"
    DOCKER = "docker"
    VOICE = "voice"
    MEMORY = "memory"
    CHANNEL = "channel"


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[list[str]] = None
    examples: Optional[list[Any]] = None

    model_config = {"arbitrary_types_allowed": True}


class ToolDefinition(BaseModel):
    """Complete definition of a tool for registration and LLM function calling."""

    name: str
    description: str
    tool_type: ToolType
    parameters: list[ToolParameter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    requires_permission: Optional[str] = None
    timeout: int = 60
    examples: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.examples:
                prop["examples"] = param.examples
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
