"""AutoMerger — auto-merge sandbox changes if tests pass threshold.

Orchestrates the full self-modification pipeline:
1. Clone source to sandbox
2. Apply patch
3. Run tests
4. If test pass rate >= threshold (90%) → merge back to source
5. If fail → retry (max 3x), then log
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MergeReport:
    success: bool = False
    description: str = ""
    sandbox_id: str = ""
    test_pass_rate: float = 0.0
    files_modified: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    attempts: int = 0
    duration_ms: float = 0.0
    merged: bool = False


class AutoMerger:
    """Auto-merge sandbox changes if tests pass threshold."""

    def __init__(self, sandbox_manager: Any = None, self_modifier: Any = None,
                 test_runner: Any = None, pass_threshold: float = 0.9,
                 max_retries: int = 3):
        self._sandbox = sandbox_manager
        self._modifier = self_modifier
        self._test_runner = test_runner
        self._threshold = pass_threshold
        self._max_retries = max_retries

    def set_stores(self, sandbox_manager: Any = None, self_modifier: Any = None,
                   test_runner: Any = None) -> None:
        if sandbox_manager:
            self._sandbox = sandbox_manager
        if self_modifier:
            self._modifier = self_modifier
        if test_runner:
            self._test_runner = test_runner

    def merge(self, source_paths: List[str], old_text: str, new_text: str,
              test_command: str, description: str = "") -> MergeReport:
        start = time.time()
        report = MergeReport(description=description)

        for attempt in range(1, self._max_retries + 1):
            report.attempts = attempt
            logger.info("Merge attempt %d/%d: %s", attempt, self._max_retries, description)

            sandbox_id = self._clone_to_sandbox(source_paths)
            if not sandbox_id:
                report.errors.append("Failed to create sandbox")
                break

            report.sandbox_id = sandbox_id

            all_patched = self._apply_patches(sandbox_id, source_paths, old_text, new_text)
            if not all_patched:
                report.errors.append("Failed to apply patches")
                self._sandbox.destroy(sandbox_id)
                continue

            test_summary = self._run_tests(sandbox_id, test_command)
            report.test_pass_rate = test_summary.pass_rate

            if self._test_runner and self._test_runner.is_pass_rate_above_threshold(
                    test_summary, self._threshold):
                self._merge_back(sandbox_id, source_paths, report)
                report.success = True
                report.merged = True
                logger.info("Merge successful (pass rate: %.0f%%)", test_summary.pass_rate * 100)
                self._sandbox.destroy(sandbox_id)
                break
            else:
                msg = f"Attempt {attempt}: pass rate {test_summary.pass_rate:.0%} < threshold {self._threshold:.0%}"
                report.errors.append(msg)
                logger.warning(msg)
                self._sandbox.destroy(sandbox_id)

        report.duration_ms = (time.time() - start) * 1000
        return report

    def _clone_to_sandbox(self, source_paths: List[str]) -> Optional[str]:
        if not self._sandbox:
            return None
        sandbox = self._sandbox.create(f"merge_{int(time.time())}")
        for src in source_paths:
            if os.path.exists(src):
                rel = os.path.basename(src)
                self._sandbox.copy_to(sandbox.id, src, rel)
        return sandbox.id

    def _apply_patches(self, sandbox_id: str, source_paths: List[str],
                       old_text: str, new_text: str) -> bool:
        for src in source_paths:
            rel = os.path.basename(src)
            if not self._modifier.apply_patch(sandbox_id, rel, old_text, new_text):
                return False
        return True

    def _run_tests(self, sandbox_id: str, test_command: str) -> Any:
        if not self._test_runner:
            return None
        sandbox = self._sandbox.get(sandbox_id)
        if not sandbox:
            return None
        if os.path.isdir(test_command):
            return self._test_runner.run_unittest(test_command, cwd=sandbox.root)
        if test_command.endswith(".py"):
            return self._test_runner.run_single_file(
                os.path.join(sandbox.root, os.path.basename(test_command)),
                cwd=sandbox.root,
            )
        return self._test_runner.run_unittest(test_command, cwd=sandbox.root)

    def _merge_back(self, sandbox_id: str, source_paths: List[str],
                    report: MergeReport) -> None:
        sandbox = self._sandbox.get(sandbox_id)
        if not sandbox:
            return
        for src in source_paths:
            rel = os.path.basename(src)
            sandbox_path = os.path.join(sandbox.root, rel)
            if os.path.exists(sandbox_path):
                shutil.copy2(sandbox_path, src)
                report.files_modified.append(src)
                logger.info("Merged %s back to source", src)

    def stats(self) -> Dict[str, Any]:
        return {"pass_threshold": self._threshold, "max_retries": self._max_retries}
