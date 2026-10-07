"""OWL Agent Creator — SamanAI §3.3 WORKFORCE layer."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.core.ast_sanitizer import is_allowed

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentSpec:
    role: str
    goal: str
    tools: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    memory_bindings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CreatedAgent:
    spec: AgentSpec
    system_prompt: str
    tool_manifest: list[str]
    created: bool = True


class AgentFactory:
    """Creates and configures agents for the workforce."""

    DEFAULTS = {
        "researcher": "You are a thorough researcher. Cite sources. Never fabricate.",
        "coder": "You are an expert coder. Write clean, tested, secure code.",
        "critic": "You are a critical reviewer. Find gaps, risks, and improvements.",
        "orchestrator": "You coordinate agents. Decompose tasks, assign, synthesize.",
        "security": "You enforce security policy. Block unsafe operations.",
    }

    def __init__(self) -> None:
        self._registry: dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> CreatedAgent:
        if not is_allowed(spec.goal):
            raise ValueError(f"Agent goal failed sanitizer: {spec.goal[:100]}")
        self._registry[spec.role] = spec
        prompt = self._build_prompt(spec)
        return CreatedAgent(spec=spec, system_prompt=prompt, tool_manifest=spec.tools)

    def get(self, role: str) -> Optional[CreatedAgent]:
        spec = self._registry.get(role)
        if not spec:
            return None
        return CreatedAgent(spec=spec, system_prompt=self._build_prompt(spec), tool_manifest=spec.tools)

    def list_roles(self) -> list[str]:
        return list(self._registry.keys())

    def _build_prompt(self, spec: AgentSpec) -> str:
        base = self.DEFAULTS.get(spec.role.lower(), f"You are {spec.role}.")
        lines = [base, f"Goal: {spec.goal}"]
        if spec.tools:
            lines.append(f"Tools: {', '.join(spec.tools)}")
        if spec.constraints:
            lines.append("Constraints:")
            for c in spec.constraints:
                lines.append(f"  - {c}")
        if spec.memory_bindings:
            lines.append(f"Memory: {', '.join(spec.memory_bindings)}")
        return "\n".join(lines)


__all__ = ["AgentFactory", "AgentSpec", "CreatedAgent"]
