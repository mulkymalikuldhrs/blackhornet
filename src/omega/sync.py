"""Ecosystem sync pipeline — pages sync, hermes-nous-research auto-convert, Codeberg push."""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Optional

from src.config.logging_config import get_logger

logger = get_logger("omega.sync")


class EcosystemSync:
    """Sync pipeline: pages sync + hermes-nous auto-convert + Codeberg push."""

    HERMES_NOUS_REPO = "https://codeberg.org/mulkydhaher/hermes-nous-research.git"
    HERMES_NOUS_DIR = "data/hermes-nous-research"
    ECOSYSTEM_MEMORY = "data/ecosystem-memory"

    def __init__(self) -> None:
        self._base = os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs")
        self._last_sync: Optional[float] = None

    def run(self) -> dict:
        results = {"timestamp": time.time(), "actions": []}
        try:
            pages_result = self._sync_pages()
            results["actions"].append({"type": "pages_sync", **pages_result})
        except Exception as e:
            results["actions"].append({"type": "pages_sync", "error": str(e)})
        try:
            hermes_result = self._sync_hermes_nous()
            results["actions"].append({"type": "hermes_nous_sync", **hermes_result})
        except Exception as e:
            results["actions"].append({"type": "hermes_nous_sync", "error": str(e)})
        try:
            score_sync = self._sync_scores()
            results["actions"].append({"type": "score_sync", **score_sync})
        except Exception as e:
            results["actions"].append({"type": "score_sync", "error": str(e)})
        self._last_sync = time.time()
        return results

    def _sync_pages(self) -> dict:
        script = os.path.join(self._base, "data", "ecosystem-memory", "ecosystem-sync-pages.py")
        if os.path.isfile(script):
            result = subprocess.run(["python3", script], capture_output=True, text=True, timeout=60)
            return {"stdout": result.stdout[-200:], "stderr": result.stderr[-200:], "returncode": result.returncode}
        return {"info": "ecosystem-sync-pages.py not found", "script_path": script}

    def _sync_hermes_nous(self) -> dict:
        repo_dir = os.path.join(self._base, self.HERMES_NOUS_DIR)
        if os.path.isdir(repo_dir):
            result = subprocess.run(["git", "-C", repo_dir, "pull"], capture_output=True, text=True, timeout=30)
            return {"fetched": True, "stdout": result.stdout[:200], "stderr": result.stderr[:200]}
        clone_result = subprocess.run(
            ["git", "clone", self.HERMES_NOUS_REPO, repo_dir],
            capture_output=True, text=True, timeout=30,
        )
        if clone_result.returncode == 0:
            return {"cloned": True}
        return {"error": clone_result.stderr[:200]}

    def _sync_scores(self) -> dict:
        from src.omega.score import ProjectScorer
        scorer = ProjectScorer()
        scores = scorer.current()
        return {"project_count": scores["project_count"], "average": sum(p["total"] for p in scores["scores"].values()) / max(len(scores["scores"]), 1)}

    def status(self) -> dict:
        return {
            "last_sync": self._last_sync,
            "hermes_nous_dir_exists": os.path.isdir(os.path.join(self._base, self.HERMES_NOUS_DIR)),
            "ecosystem_memory_exists": os.path.isdir(os.path.join(self._base, self.ECOSYSTEM_MEMORY)),
        }
