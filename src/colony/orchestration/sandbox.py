"""Sandbox — temp directory isolation for agent execution."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional


class Sandbox:
    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.path: Optional[Path] = None

    def __enter__(self) -> Path:
        raw = tempfile.mkdtemp(prefix=f"sandbox_{self.agent_id}_")
        self.path = Path(raw)
        return self.path

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        if self.path is not None and self.path.exists():
            shutil.rmtree(str(self.path))
