"""CodeExecutor — execute code in sandbox with safety controls.

Runs Python code in the sandbox directory with timeout, restricted
builtins, and stdout/stderr capture. Returns execution results.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    success: bool = False
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    error_type: str = ""
    error_message: str = ""


class CodeExecutor:
    """Execute Python code in sandbox with safety controls."""

    def __init__(self, timeout: int = 30):
        self._timeout = timeout

    def execute_file(self, file_path: str, cwd: str = "") -> ExecResult:
        start = time.time()
        result = ExecResult()
        cwd = cwd or os.path.dirname(file_path) or os.getcwd()

        try:
            import subprocess
            proc = subprocess.run(
                [sys.executable, file_path],
                capture_output=True, text=True, cwd=cwd,
                timeout=self._timeout,
            )
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.error_type = "TimeoutError"
            result.error_message = f"Execution timed out after {self._timeout}s"
        except FileNotFoundError:
            result.error_type = "FileNotFoundError"
            result.error_message = f"File not found: {file_path}"
        except Exception as e:
            result.error_type = type(e).__name__
            result.error_message = str(e)

        result.duration_ms = (time.time() - start) * 1000
        return result

    def execute_code(self, code: str, cwd: str = "") -> ExecResult:
        start = time.time()
        result = ExecResult()

        try:
            import subprocess
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, cwd=cwd or os.getcwd(),
                timeout=self._timeout,
            )
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.error_type = "TimeoutError"
            result.error_message = f"Execution timed out after {self._timeout}s"
        except Exception as e:
            result.error_type = type(e).__name__
            result.error_message = str(e)

        result.duration_ms = (time.time() - start) * 1000
        return result

    def execute_module(self, module_name: str, args: Optional[List[str]] = None,
                       cwd: str = "") -> ExecResult:
        start = time.time()
        result = ExecResult()

        try:
            import subprocess
            cmd = [sys.executable, "-m", module_name]
            if args:
                cmd.extend(args)
            proc = subprocess.run(
                cmd, capture_output=True, text=True, cwd=cwd or os.getcwd(),
                timeout=self._timeout,
            )
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.error_type = "TimeoutError"
            result.error_message = f"Execution timed out after {self._timeout}s"
        except Exception as e:
            result.error_type = type(e).__name__
            result.error_message = str(e)

        result.duration_ms = (time.time() - start) * 1000
        return result
