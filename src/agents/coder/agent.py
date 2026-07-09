"""Coder agent - from OpenHands CodeActAgent pattern.

Specializes in code generation, debugging, review, refactoring,
and test generation with execution-in-the-loop feedback.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from src.config.logging_config import get_logger
from src.core.base_agent import BaseAgent
from src.colony_types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from src.colony_types.memory import MemoryType
from src.colony_types.messages import Message, MessageRole
from src.agents.coder.prompts import (
    CODER_SYSTEM_PROMPT,
    CODER_DEBUG_PROMPT,
    CODER_REVIEW_PROMPT,
    CODER_TEST_GENERATION_PROMPT,
    CODER_REFACTOR_PROMPT,
)
from src.colony_types import Task
from src.core.reflexion import ReflexionLoop, Memory

logger = get_logger(__name__)


class CoderAgent(BaseAgent):
    """Coder agent following the OpenHands CodeActAgent pattern.

    Combines code understanding with execution capabilities.
    Can write, read, debug, and execute code with iterative
    fix-verify loops.

    State-specific behavior:
    - IDLE: Ready for coding tasks
    - RUNNING: Actively writing, editing, or executing code
    - THINKING: Analyzing code structure or debugging
    - PAUSED: Execution paused, possibly waiting for user input
    - ERROR: Code execution error, attempts debug-retry cycle
    """

    # Track code changes
    _code_changes: list[dict[str, Any]]
    _debug_attempts: int = 0
    _max_debug_attempts: int = 3

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.CODER,
                name="coder-agent",
                description="Code generation, debugging, and review specialist",
                tools=["code", "file", "shell", "search", "memory"],
                system_prompt=CODER_SYSTEM_PROMPT,
                temperature=0.1,
                max_iterations=15,  # More iterations for code-debug cycles
                capabilities=AgentCapabilities(
                    code_generation=True,
                    code_execution=True,
                    file_operations=True,
                    shell_execution=True,
                    web_search=True,
                    memory_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = CODER_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["code", "file", "shell", "search", "memory"]

        super().__init__(config=config, **kwargs)
        self._code_changes = []
        self._debug_attempts = 0
        self._reflexion_memory = Memory()
        self._reflexion = ReflexionLoop(max_attempts=3, memory=self._reflexion_memory)

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names CoderAgent requires.

        Returns:
            Tools needed for code operations.
        """
        return ["code", "file", "shell", "search", "memory"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Coder agent."""
        return self.config.system_prompt or CODER_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "coder_agent_running",
            agent_id=self.agent_id,
            changes=len(self._code_changes),
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state — attempt debug cycle."""
        self._debug_attempts += 1
        logger.warning(
            "coder_agent_error",
            agent_id=self.agent_id,
            debug_attempts=self._debug_attempts,
        )
        # Store error in code changes for tracking
        self._code_changes.append({
            "type": "error",
            "debug_attempt": self._debug_attempts,
            "iteration": self.iteration_count,
        })

    def _on_enter_thinking(self) -> None:
        """Hook called when entering THINKING state."""
        logger.debug("coder_agent_thinking", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # Code operations
    # ------------------------------------------------------------------

    async def write_code(self, task: str, language: str = "python") -> str:
        """Write code for a specific task.

        Args:
            task: Description of what the code should do.
            language: Programming language.

        Returns:
            The generated code or execution result.
        """
        prompt = f"Write {language} code for: {task}\n\nExecute the code and verify it works."
        result = await self.run(prompt)

        self._code_changes.append({
            "type": "write",
            "language": language,
            "task": task[:100],
            "result_preview": result[:200],
        })

        return result

    async def debug_code(self, code: str, error: str) -> str:
        """Debug code that has an error.

        Uses an iterative debug-verify cycle: attempt to fix, execute,
        and check if the fix resolved the issue.

        Args:
            code: The code with the error.
            error: The error message.

        Returns:
            The fixed code or debug result.
        """
        self._debug_attempts = 0
        prompt = CODER_DEBUG_PROMPT.format(code=code, error=error)
        prompt += "\n\nFix the code and execute it to verify the fix works."
        result = await self.run(prompt)

        self._code_changes.append({
            "type": "debug",
            "error_preview": error[:100],
            "debug_attempts": self._debug_attempts,
            "result_preview": result[:200],
        })

        return result

    async def review_code(self, code: str, language: str = "python") -> str:
        """Review code for issues.

        Args:
            code: The code to review.
            language: Programming language.

        Returns:
            Review findings and suggestions.
        """
        prompt = CODER_REVIEW_PROMPT.format(code=code, language=language)
        result = await self.run(prompt)

        self._code_changes.append({
            "type": "review",
            "language": language,
            "code_length": len(code),
        })

        return result

    async def refactor_code(self, code: str, language: str = "python") -> str:
        """Refactor code for better quality.

        Args:
            code: The code to refactor.
            language: Programming language.

        Returns:
            Refactored code with explanation.
        """
        prompt = CODER_REFACTOR_PROMPT.format(code=code, language=language)
        result = await self.run(prompt)

        self._code_changes.append({
            "type": "refactor",
            "language": language,
            "original_length": len(code),
        })

        return result

    async def generate_tests(self, code: str, language: str = "python") -> str:
        """Generate tests for code.

        Args:
            code: The code to generate tests for.
            language: Programming language.

        Returns:
            Generated test code.
        """
        prompt = CODER_TEST_GENERATION_PROMPT.format(code=code, language=language)
        result = await self.run(prompt)

        self._code_changes.append({
            "type": "test_generation",
            "language": language,
            "code_length": len(code),
        })

        return result

    # ------------------------------------------------------------------
    # Execution loop override for debug-retry cycle
    # ------------------------------------------------------------------

    async def _execute_loop(self) -> str:
        """Execute the coder loop with debug-retry on code errors.

        Extends the base loop with:
        - Automatic debug cycle when code execution fails
        - Code change tracking
        - State hooks for THINKING/RUNNING transitions
        """
        max_iter = self.config.max_iterations
        last_response = ""

        while self.iteration_count < max_iter:
            if self.state == AgentState.PAUSED:
                await asyncio.sleep(0.1)
                continue

            if self.state == AgentState.TERMINATED:
                break

            if self.state == AgentState.ERROR:
                if self._debug_attempts < self._max_debug_attempts:
                    logger.info("coder_retry_after_error", agent_id=self.agent_id)
                    try:
                        self._transition_to(AgentState.RUNNING)
                    except Exception:
                        break
                else:
                    return f"Code debugging failed after {self._debug_attempts} attempts: {last_response}"

            self.iteration_count += 1

            try:
                self._transition_to(AgentState.THINKING)
                self._on_enter_thinking()
                response = await self._call_llm()
                self._transition_to(AgentState.RUNNING)
                self._on_enter_running()

                if response.tool_calls:
                    last_response = await self._process_tool_calls(response)
                else:
                    last_response = response.content
                    if self._is_done(response.content):
                        break

                self.tokens_used += response.usage.total_tokens
                self.cost_incurred += response.cost

            except Exception as e:
                self.error_count += 1
                self._on_enter_error()
                if self.error_count >= 5:
                    return f"Coder agent failed after {self.error_count} errors: {e}"
                last_response = f"Error in iteration {self.iteration_count}: {e}"

        if self.iteration_count >= max_iter:
            return last_response or "Max iterations reached"

        return last_response

    # ------------------------------------------------------------------
    # Code change history
    # ------------------------------------------------------------------

    def get_code_changes(self) -> list[dict[str, Any]]:
        """Get the history of code changes made by this agent.

        Returns:
            List of code change entries.
        """
        return list(self._code_changes)

    def clear_code_changes(self) -> None:
        """Clear the code change history."""
        self._code_changes.clear()
        self._debug_attempts = 0

    # ------------------------------------------------------------------
    # Reflexion self-improvement
    # ------------------------------------------------------------------

    async def reflexive_generate(self, spec: str, language: str = "python") -> Dict[str, Any]:
        """Generate code using Reflexion loop for self-improvement."""

        async def actor(task: str) -> str:
            prompt = f"Write {language} code for: {task}\n\nExecute the code and verify it works."
            return await self.run(prompt)

        def evaluator(task: str, output: str) -> tuple:
            issues = []
            if "from __future__ import annotations" not in output:
                issues.append("Missing future annotations import")
            if "def " not in output and "function " not in output:
                issues.append("No function definitions found")
            if "pass" in output and output.count("pass") > 2:
                issues.append("Too many pass statements - implement the logic")
            if issues:
                return (False, "; ".join(issues))
            return (True, "Code quality check passed")

        result = await self._reflexion.arun(spec, actor, evaluator)
        return {
            "action": "reflexive_generate",
            "spec": spec,
            "language": language,
            "code": result.get("output", ""),
            "attempts": result.get("attempts", 0),
            "success": result.get("success", False),
            "feedback": result.get("feedback", ""),
            "reflexion_history": self._reflexion_memory.feedback_history,
        }

    async def reflexive_review(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Review code with Reflexion - retry review if quality check fails."""

        async def actor(task: str) -> str:
            prompt = f"REVIEW:\n```{language}\n{task}\n```"
            return await self.run(prompt)

        def evaluator(task: str, output: str) -> tuple:
            patterns_found = sum(
                1 for p in ["password", "secret", "eval(", "exec(", "shell=True"]
                if p in task
            )
            if patterns_found > 0 and all(p not in output for p in ["issue", "warning", "security"]):
                return (False, "Review did not flag known security patterns")
            return (True, "Review quality check passed")

        review_task = f"REVIEW:\n```{language}\n{code}\n```"
        result = await self._reflexion.arun(review_task, actor, evaluator)

        return {
            "action": "reflexive_review",
            "code_length": len(code),
            "language": language,
            "attempts": result.get("attempts", 0),
            "success": result.get("success", False),
        }

    async def _generate_with_reflexion(self, task: Task) -> Dict[str, Any]:
        """Generate code using Reflexion loop via task payload."""
        language = task.payload.get("language", "python")
        spec = task.payload.get("spec", task.description)
        max_attempts = task.payload.get("max_attempts", 3)

        reflexion_memory = Memory()
        reflexion_loop = ReflexionLoop(max_attempts=max_attempts, memory=reflexion_memory)

        async def actor(task_spec: str) -> str:
            prompt = f"Write {language} code for: {task_spec}"
            return await self.run(prompt)

        def evaluator(task_spec: str, output: str) -> tuple:
            issues = []
            if "def " not in output and "function " not in output:
                issues.append("No function definitions found")
            if "pass" in output and output.count("pass") > 2:
                issues.append("Too many pass statements")
            if issues:
                return (False, "; ".join(issues))
            return (True, "Code quality check passed")

        result = await reflexion_loop.arun(spec, actor, evaluator)

        return {
            "action": "generate_with_reflexion",
            "language": language,
            "code": result.get("output", ""),
            "attempts": result.get("attempts", 0),
            "success": result.get("success", False),
            "feedback": result.get("feedback", ""),
            "reflexion_history": reflexion_memory.feedback_history,
        }
