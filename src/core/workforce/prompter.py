"""Dynamic Prompter — SamanAI §3.3 WORKFORCE layer."""

from __future__ import annotations

import logging
from typing import Optional

from src.core.workforce.agent_factory import AgentFactory, AgentSpec

logger = logging.getLogger(__name__)


class DynamicPrompter:
    """Generates inception prompts for OWL agents."""

    def __init__(self, factory: Optional[AgentFactory] = None) -> None:
        self.factory = factory

    def generate_inception_prompt(
        self,
        role: str,
        task_description: str,
        allowed_tools: list[str] | None = None,
        constraints: list[str] | None = None,
        memory_bindings: list[str] | None = None,
    ) -> str:
        spec = AgentSpec(
            role=role,
            goal=task_description,
            tools=allowed_tools or [],
            constraints=constraints or [],
            memory_bindings=memory_bindings or [],
        )
        if self.factory:
            agent = self.factory.register(spec)
            return agent.system_prompt
        return self._default_prompt(spec)

    def _default_prompt(self, spec: AgentSpec) -> str:
        return f"[ROLE]: {spec.role}\n[TASK]: {spec.goal}\n[TOOLS]: {', '.join(spec.tools)}\n[MEMORY]: {', '.join(spec.memory_bindings)}"


__all__ = ["DynamicPrompter"]
