"""Zero-trust AST + command sanitizer.

Inspects code payloads and shell commands before execution.
Raises SecurityViolationException on policy breach.

Implements SamanAI's AGENT TRUST guardrail concept:
- Regex + AST parsing for forbidden operations
- Shell command interception
- Payload validation against system policies
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class SecurityViolationException(Exception):
    """Raised when a payload violates sanitizer policy."""

    def __init__(self, reason: str, payload: str = "") -> None:
        self.reason = reason
        self.payload_preview = payload[:200] if payload else ""
        super().__init__(f"SecurityViolation: {reason}")


@dataclass(slots=True)
class SanitizeResult:
    """Outcome of a sanitizer pass."""

    allowed: bool
    reason: str
    violations: list[str]


# ── Regex guardrails (always checked first) ──────────────────────────

_FORBIDDEN_COMMANDS = [
    (re.compile(r"rm\s+-rf\s+/"), "Destructive recursive delete of root filesystem"),
    (re.compile(r"rm\s+-rf\s+~"), "Destructive recursive delete of home directory"),
    (re.compile(r":\s*\(\s*\|\s*:\s*\)"), "Fork bomb pattern detected"),
    (re.compile(r"\$\{.*\}"), "Arbitrary shell expansion detected"),
    (re.compile(r"`[^`]+`"), "Backtick command substitution detected"),
    (re.compile(r"\beval\s*\("), "Dynamic eval() usage detected"),
    (re.compile(r"\bexec\s*\("), "Dynamic exec() usage detected"),
    (re.compile(r"\bcompile\s*\("), "Dynamic compile() usage detected"),
    (re.compile(r"__import__\s*\("), "Dynamic __import__() usage detected"),
    (re.compile(r"\bos\s*\."), "OS module access detected"),
    (re.compile(r"\bsubprocess\s*\."), "Subprocess module access detected"),
    (re.compile(r"\bsocket\s*\."), "Socket module access detected"),
    (re.compile(r"\bctypes\b"), "ctypes module (native code) detected"),
    (re.compile(r"import\s+os"), "OS module import detected"),
    (re.compile(r"import\s+subprocess"), "Subprocess module import detected"),
    (re.compile(r"import\s+socket"), "Socket module import detected"),
    (re.compile(r"from\s+os\s+import"), "OS module from-import detected"),
    (re.compile(r"from\s+subprocess\s+import"), "Subprocess module from-import detected"),
    (re.compile(r"from\s+socket\s+import"), "Socket module from-import detected"),
    (re.compile(r"\bchmod\s*\("), "chmod() call detected"),
    (re.compile(r"\bchown\s*\("), "chown() call detected"),
    (re.compile(r"\bkill\s*\("), "kill() call detected"),
    (re.compile(r"\bsystem\s*\("), "system() call detected"),
    (re.compile(r"\bpopen\s*\("), "popen() call detected"),
    (re.compile(r"\bexecve\s*\("), "execve() call detected"),
]

# AST-only forbidden nodes (checked after parse)
_AST_FORBIDDEN = {
    ast.Expr: "Top-level expression statement (potential code injection)",
}


def _check_regex(payload: str) -> list[str]:
    """Return list of violation descriptions from regex guardrails."""
    violations = []
    for pattern, reason in _FORBIDDEN_COMMANDS:
        if pattern.search(payload):
            violations.append(reason)
    return violations


def _check_ast(tree: ast.AST) -> list[str]:
    """Walk AST and return violation descriptions."""
    violations = []
    for node in ast.walk(tree):
        # Forbidden imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"os", "subprocess", "socket", "ctypes", "shutil", "sys", "signal"}:
                    violations.append(f"Import of restricted module: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module in {"os", "subprocess", "socket", "ctypes", "shutil", "sys", "signal"}:
                violations.append(f"From-import of restricted module: {node.module}")
        # Forbidden calls
        elif isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in {"eval", "exec", "compile", "__import__", "system", "popen", "execve", "chmod", "chown", "kill"}:
                violations.append(f"Forbidden function call: {name}()")
    return violations


def sanitize(payload: str, *, language: str = "python") -> SanitizeResult:
    """Sanitize a code or command payload.

    Args:
        payload: Raw source code or shell command to inspect.
        language: Payload language hint (only "python" and "shell" supported).

    Returns:
        SanitizeResult with allowed flag and reason.

    Raises:
        SecurityViolationException: If payload violates policy and fail_closed is True.
    """
    if not payload or not payload.strip():
        return SanitizeResult(True, "Empty payload", [])

    violations: list[str] = []

    # Phase 1: Regex guardrails (fast, catch obvious issues)
    violations.extend(_check_regex(payload))

    # Phase 2: AST parse (Python only)
    if language.lower() == "python" not in violations:
        try:
            tree = ast.parse(payload)
            violations.extend(_check_ast(tree))
        except SyntaxError:
            # Syntax error alone is not a security violation; let the executor handle it
            pass

    if violations:
        reason = "; ".join(violations)
        logger.warning("Sanitizer blocked payload: %s", reason)
        raise SecurityViolationException(reason, payload)

    return SanitizeResult(True, "Payload passed all guardrails", [])


def is_allowed(payload: str, *, language: str = "python") -> bool:
    """Quick boolean check without raising."""
    try:
        sanitize(payload, language=language)
        return True
    except SecurityViolationException:
        return False
