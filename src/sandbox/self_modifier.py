"""SelfModifier — modify own source code in sandbox, then validate.

The core self-modification logic: copies source files to sandbox,
applies modifications, runs tests, and determines if changes are safe.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.sandbox.code_executor import ExecResult

logger = logging.getLogger(__name__)


@dataclass
class ModificationPlan:
    description: str = ""
    target_file: str = ""
    patch: str = ""
    expected_behavior: str = ""
    risk_level: str = "low"


@dataclass
class ModificationResult:
    success: bool = False
    sandbox_id: str = ""
    test_pass_rate: float = 0.0
    test_output: str = ""
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


class SelfModifier:
    """Modify own source code in sandbox with validation."""

    def __init__(self, sandbox_manager: Any = None, code_executor: Any = None):
        self._sandbox = sandbox_manager
        self._executor = code_executor
        self._max_retries = 3

    def set_sandbox(self, sandbox_manager: Any) -> None:
        self._sandbox = sandbox_manager

    def set_executor(self, code_executor: Any) -> None:
        self._executor = code_executor

    def clone_to_sandbox(self, source_paths: List[str], sandbox_id: str = "") -> Optional[str]:
        if not self._sandbox:
            return None
        sandbox = self._sandbox.create(sandbox_id)
        for src in source_paths:
            if os.path.exists(src):
                rel = os.path.basename(src)
                self._sandbox.copy_to(sandbox.id, src, rel)
        logger.info("Cloned %d files to sandbox %s", len(source_paths), sandbox.id)
        return sandbox.id

    def apply_patch(self, sandbox_id: str, file_rel: str, old_text: str, new_text: str) -> bool:
        try:
            content = self._sandbox.read_file(sandbox_id, file_rel)
            if old_text not in content:
                logger.warning("Patch target not found in %s", file_rel)
                return False
            modified = content.replace(old_text, new_text, 1)
            self._sandbox.write_file(sandbox_id, file_rel, modified)
            return True
        except Exception as e:
            logger.warning("Patch application failed: %s", e)
            return False

    def run_tests_in_sandbox(self, sandbox_id: str, test_command: str) -> ExecResult:
        if not self._executor:
            return ExecResult(success=False, stderr="No executor configured")
        sandbox = self._sandbox.get(sandbox_id)
        return self._executor.execute_code(test_command, cwd=sandbox.root)

    def modify_and_test(self, source_paths: List[str], old_text: str, new_text: str,
                         test_command: str, description: str = "") -> ModificationResult:
        start = time.time()
        result = ModificationResult()

        sandbox_id = self.clone_to_sandbox(source_paths)
        if not sandbox_id:
            result.errors.append("Failed to create sandbox")
            return result

        result.sandbox_id = sandbox_id
        source_files = [os.path.basename(p) for p in source_paths]

        for file_rel in source_files:
            if not self.apply_patch(sandbox_id, file_rel, old_text, new_text):
                result.errors.append(f"Failed to patch {file_rel}")

        if result.errors:
            self._sandbox.destroy(sandbox_id)
            result.duration_ms = (time.time() - start) * 1000
            return result

        exec_result = self.run_tests_in_sandbox(sandbox_id, test_command)
        result.test_output = exec_result.stdout or exec_result.stderr
        result.test_pass_rate = self._parse_test_rate(exec_result)

        result.success = exec_result.success
        result.duration_ms = (time.time() - start) * 1000
        return result

    def modify_with_retry(self, source_paths: List[str], old_text: str, new_text: str,
                           test_command: str, description: str = "") -> ModificationResult:
        last_result = ModificationResult()

        for attempt in range(1, self._max_retries + 1):
            logger.info("Modification attempt %d/%d: %s", attempt, self._max_retries, description)
            result = self.modify_and_test(source_paths, old_text, new_text, test_command, description)
            last_result = result

            if result.success:
                logger.info("Modification succeeded on attempt %d", attempt)
                return result

            if attempt < self._max_retries:
                if result.errors:
                    logger.warning("Attempt %d failed: %s", attempt, result.errors)
                else:
                    logger.warning("Attempt %d failed: tests %d%% passing", attempt, int(result.test_pass_rate * 100))

        return last_result

    @staticmethod
    def _parse_test_rate(exec_result: ExecResult) -> float:
        stdout = exec_result.stdout or ""
        if exec_result.success:
            for line in stdout.split("\n"):
                line = line.strip().lower()
                if "ok" in line and " " in line:
                    pass
                if line.startswith("ran "):
                    import re
                    m = re.search(r"ran\s+(\d+)\s+tests?\s+.*?\b(\d+)\s+fail", line)
                    if m:
                        total = int(m.group(1))
                        failures = int(m.group(2))
                        if total > 0:
                            return (total - failures) / total
        return 0.0 if not exec_result.success else 1.0



