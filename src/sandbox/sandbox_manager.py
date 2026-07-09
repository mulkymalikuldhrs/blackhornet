"""SandboxManager — manage isolated sandbox environments.

Creates temporary directories with controlled permissions for safe
code execution and self-modification testing. Cleans up after use.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Sandbox:
    id: str = ""
    root: str = ""
    created_at: float = 0.0
    max_size: int = 10 * 1024 * 1024
    files: List[str] = field(default_factory=list)


class SandboxManager:
    """Manage isolated sandbox environments for safe execution."""

    def __init__(self, base_dir: str = "~/.bh/sandbox"):
        self._base_dir = os.path.expanduser(base_dir)
        os.makedirs(self._base_dir, exist_ok=True)
        self._sandboxes: Dict[str, Sandbox] = {}

    def create(self, sandbox_id: str = "") -> Sandbox:
        sid = sandbox_id or f"sandbox_{int(time.time())}_{len(self._sandboxes)}"
        root = tempfile.mkdtemp(dir=self._base_dir, prefix=f"{sid}_")
        sandbox = Sandbox(id=sid, root=root, created_at=time.time())
        self._sandboxes[sid] = sandbox
        logger.info("Created sandbox %s at %s", sid, root)
        return sandbox

    def get(self, sandbox_id: str) -> Optional[Sandbox]:
        return self._sandboxes.get(sandbox_id)

    def write_file(self, sandbox_id: str, path: str, content: str) -> str:
        sandbox = self._get_sandbox(sandbox_id)
        full_path = os.path.join(sandbox.root, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        rel_path = os.path.relpath(full_path, sandbox.root)
        if rel_path not in sandbox.files:
            sandbox.files.append(rel_path)
        return full_path

    def read_file(self, sandbox_id: str, path: str) -> str:
        sandbox = self._get_sandbox(sandbox_id)
        full_path = os.path.join(sandbox.root, path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        if not self._is_within_sandbox(full_path, sandbox.root):
            raise PermissionError(f"Path outside sandbox: {path}")
        with open(full_path) as f:
            return f.read()

    def list_files(self, sandbox_id: str) -> List[str]:
        sandbox = self._get_sandbox(sandbox_id)
        return list(sandbox.files)

    def copy_to(self, sandbox_id: str, source_path: str, dest_rel: str) -> str:
        sandbox = self._get_sandbox(sandbox_id)
        dest = os.path.join(sandbox.root, dest_rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(source_path, dest)
        if dest_rel not in sandbox.files:
            sandbox.files.append(dest_rel)
        return dest

    def destroy(self, sandbox_id: str) -> bool:
        sandbox = self._sandboxes.pop(sandbox_id, None)
        if sandbox and os.path.exists(sandbox.root):
            shutil.rmtree(sandbox.root, ignore_errors=True)
            logger.info("Destroyed sandbox %s", sandbox_id)
            return True
        return False

    def destroy_all(self) -> int:
        count = 0
        for sid in list(self._sandboxes.keys()):
            if self.destroy(sid):
                count += 1
        return count

    def get_size(self, sandbox_id: str) -> int:
        sandbox = self._get_sandbox(sandbox_id)
        total = 0
        for fname in sandbox.files:
            fpath = os.path.join(sandbox.root, fname)
            if os.path.exists(fpath):
                total += os.path.getsize(fpath)
        return total

    def stats(self) -> Dict[str, Any]:
        return {"active_sandboxes": len(self._sandboxes)}

    def _get_sandbox(self, sandbox_id: str) -> Sandbox:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox not found: {sandbox_id}")
        return sandbox

    @staticmethod
    def _is_within_sandbox(path: str, root: str) -> bool:
        return os.path.realpath(path).startswith(os.path.realpath(root))
