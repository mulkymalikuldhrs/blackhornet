"""OctoGent-inspired tentacle context isolation for subagents."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Tentacle:
    """Isolated context directory for a subagent."""

    name: str
    scope: str  # "agent", "task", "session"
    path: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def initialize(self) -> None:
        self.path = tempfile.mkdtemp(prefix=f"tentacle_{self.name}_")
        os.makedirs(f"{self.path}/context", exist_ok=True)
        os.makedirs(f"{self.path}/artifacts", exist_ok=True)

    def store(self, key: str, value: Any) -> None:
        self.context[key] = value

    def retrieve(self, key: str) -> Optional[Any]:
        return self.context.get(key)

    def cleanup(self) -> None:
        if self.path and os.path.exists(self.path):
            shutil.rmtree(self.path, ignore_errors=True)


class TentaclePool:
    """Manages multiple tentacles for subagent isolation."""

    def __init__(self) -> None:
        self.tentacles: Dict[str, Tentacle] = {}

    def create_tentacle(self, name: str, scope: str = "task") -> Tentacle:
        t = Tentacle(name=name, scope=scope)
        t.initialize()
        self.tentacles[name] = t
        return t

    def get_tentacle(self, name: str) -> Optional[Tentacle]:
        return self.tentacles.get(name)

    def release_tentacle(self, name: str) -> None:
        t = self.tentacles.pop(name, None)
        if t:
            t.cleanup()
