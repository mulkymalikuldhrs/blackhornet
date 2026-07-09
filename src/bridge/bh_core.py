"""BlackHornet Core — Node.js bridge module.
Absorbed from bh-core/index.js."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BHCoreEntry:
    stored: bool
    id: str


class BlackHornetCore:
    """Core BH engine — init, remember, status."""

    def __init__(self, name: str = "BlackHornet") -> None:
        self.name = name
        self._memory: dict[str, str] = {}

    def init(self) -> dict:
        return {"status": "ok", "name": self.name}

    def remember(self, content: str, id: Optional[str] = None, tags: Optional[list[str]] = None, importance: float = 0.5) -> BHCoreEntry:
        key = id or str(hash(content))
        self._memory[key] = content
        return BHCoreEntry(stored=True, id=key)

    def recall(self, id: str) -> Optional[str]:
        return self._memory.get(id)

    def status(self) -> dict:
        return {"name": self.name, "entries": len(self._memory), "online": True}
