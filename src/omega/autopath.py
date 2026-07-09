"""Auto-Path — dynamic path detection for the entire ecosystem.

Never hardcode. Always detect via env, git, cwd, or convention.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional


class AutoPath:
    """Detect all ecosystem paths dynamically."""

    @staticmethod
    def dhaherlabs() -> str:
        return os.environ.get("DHAHERLABS") or os.environ.get("DHAHER") or "/sdcard/dhaherlabs"

    @staticmethod
    def blackhornet() -> str:
        base = AutoPath.dhaherlabs()
        candidates = [
            os.path.join(base, "blackhornet-worktree"),
            os.path.join(base, "blackhornet"),
            os.path.join(os.getcwd()),
        ]
        for c in candidates:
            if os.path.isdir(os.path.join(c, "src")):
                return c
        return os.path.join(base, "blackhornet-worktree")

    @staticmethod
    def omega() -> str:
        return "/root/.config/opencode/skills/godmode/auto"

    @staticmethod
    def ecosystem_memory() -> str:
        return os.path.join(AutoPath.dhaherlabs(), "data", "ecosystem-memory")

    @staticmethod
    def hermes_nous() -> str:
        return os.path.join(AutoPath.dhaherlabs(), "data", "hermes-nous-research")

    @staticmethod
    def omega_data() -> str:
        return os.path.join(AutoPath.dhaherlabs(), "data", "omega")

    @staticmethod
    def detect_os() -> str:
        try:
            return subprocess.run(["uname", "-o"], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return "linux"

    @staticmethod
    def detect_shell() -> str:
        return os.environ.get("SHELL", "bash").split("/")[-1]

    @staticmethod
    def detect_project_root() -> str:
        for marker in [".git", "pyproject.toml", "src", "package.json"]:
            path = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
            if path.returncode == 0:
                return path.stdout.strip()
        return AutoPath.blackhornet()

    @staticmethod
    def all() -> dict:
        return {
            "DHAHERLABS": AutoPath.dhaherlabs(),
            "blackhornet": AutoPath.blackhornet(),
            "omega_skill": AutoPath.omega(),
            "ecosystem_memory": AutoPath.ecosystem_memory(),
            "hermes_nous": AutoPath.hermes_nous(),
            "omega_data": AutoPath.omega_data(),
            "os": AutoPath.detect_os(),
            "shell": AutoPath.detect_shell(),
            "project_root": AutoPath.detect_project_root(),
        }
