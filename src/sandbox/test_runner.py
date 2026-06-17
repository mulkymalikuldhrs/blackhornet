"""TestRunner — run tests and measure pass rate.

Discovers and runs Python unittest/pytest tests, parses results,
and computes pass rate. Used by SelfModifier to validate changes.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TestSummary:
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    duration_ms: float = 0.0
    output: str = ""


class TestRunner:
    """Discover and run tests, compute pass rate."""

    def __init__(self, timeout: int = 60):
        self._timeout = timeout

    def run_unittest(self, test_path: str, cwd: str = "") -> TestSummary:
        start = __import__("time").time()
        summary = TestSummary()

        try:
            import subprocess
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", test_path, "-v"],
                capture_output=True, text=True, cwd=cwd or os.getcwd(),
                timeout=self._timeout,
            )
            summary.output = proc.stdout + proc.stderr
            summary = self._parse_unittest_output(summary.output)
            summary.pass_rate = self._compute_rate(summary)
        except subprocess.TimeoutExpired:
            summary.output = f"Tests timed out after {self._timeout}s"
            summary.errors = 1
        except Exception as e:
            summary.output = str(e)
            summary.errors = 1

        summary.duration_ms = (__import__("time").time() - start) * 1000
        return summary

    def run_single_file(self, file_path: str, cwd: str = "") -> TestSummary:
        start = __import__("time").time()
        summary = TestSummary()

        try:
            import subprocess
            proc = subprocess.run(
                [sys.executable, file_path],
                capture_output=True, text=True, cwd=cwd or os.getcwd(),
                timeout=self._timeout,
            )
            summary.output = proc.stdout + proc.stderr
            summary = self._parse_unittest_output(summary.output)
            summary.pass_rate = self._compute_rate(summary)
        except subprocess.TimeoutExpired:
            summary.output = f"Tests timed out after {self._timeout}s"
            summary.errors = 1
        except Exception as e:
            summary.output = str(e)
            summary.errors = 1

        summary.duration_ms = (__import__("time").time() - start) * 1000
        return summary

    def is_pass_rate_above_threshold(self, summary: TestSummary, threshold: float = 0.9) -> bool:
        return summary.total > 0 and summary.pass_rate >= threshold

    @staticmethod
    def _parse_unittest_output(output: str) -> TestSummary:
        summary = TestSummary()
        lines = output.split("\n")

        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("Ran "):
                m = re.search(r"Ran\s+(\d+)\s+tests?", line_stripped)
                if m:
                    summary.total = int(m.group(1))
            if line_stripped.startswith("FAILED"):
                m = re.search(r"failures=(\d+)", line_stripped)
                if m:
                    summary.failed = int(m.group(1))
                m = re.search(r"errors=(\d+)", line_stripped)
                if m:
                    summary.errors = int(m.group(1))
            if " ... ok" in line_stripped:
                summary.passed += 1
            if " ... FAIL" in line_stripped:
                summary.failed += 1
            if " ... ERROR" in line_stripped:
                summary.errors += 1

        if summary.total == 0:
            summary.total = summary.passed + summary.failed + summary.errors

        return summary

    @staticmethod
    def _compute_rate(summary: TestSummary) -> float:
        if summary.total == 0:
            return 0.0
        return max(0.0, (summary.total - summary.failed - summary.errors) / summary.total)
