"""Sandbox module — safe self-modification with sandbox isolation.

7.1 SandboxManager — manage isolated sandbox environments
7.2 CodeExecutor — execute code in sandbox with safety
7.3 SelfModifier — modify own source code in sandbox
7.4 TestRunner — run tests and measure pass rate
7.5 AutoMerger — auto-merge if >90% tests pass
"""

from .sandbox_manager import SandboxManager, Sandbox
from .code_executor import CodeExecutor, ExecResult
from .self_modifier import SelfModifier, ModificationPlan, ModificationResult
from .test_runner import TestRunner, TestSummary
from .auto_merger import AutoMerger, MergeReport

__all__ = [
    "SandboxManager", "Sandbox",
    "CodeExecutor", "ExecResult",
    "SelfModifier", "ModificationPlan", "ModificationResult",
    "TestRunner", "TestSummary",
    "AutoMerger", "MergeReport",
]
