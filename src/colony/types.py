"""Colony type definitions."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable


class AgentRole:
    """Agent role definition."""
    def __init__(self, role_id: str, role_type: str, capabilities: List[str] = None):
        self.id = role_id
        self.role_type = role_type
        self.capabilities = capabilities or []


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
