"""SelfPromptGenerator — generate self-prompts based on context and user model.

Produces dynamic system prompt blocks that incorporate user profile,
preferences, learned topics, recent context, and active goals to
create adaptive self-prompting for the BlackHornet agent.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptContext:
    user_id: str = ""
    user_name: str = ""
    topics: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    expertise: Dict[str, float] = field(default_factory=dict)
    recent_interactions: int = 0
    active_goals: List[str] = field(default_factory=list)
    communication_style: str = ""


class SelfPromptGenerator:
    """Generate adaptive self-prompts from user model context."""

    def __init__(self, user_store: Any = None, preference_learner: Any = None):
        self._user_store = user_store
        self._pref_learner = preference_learner

    def set_stores(self, user_store: Any, preference_learner: Any) -> None:
        self._user_store = user_store
        self._pref_learner = preference_learner

    def build_context(self, user_id: str) -> PromptContext:
        ctx = PromptContext(user_id=user_id)
        if self._user_store:
            profile = self._user_store.get_by_user_id(user_id)
            if profile:
                ctx.user_name = profile.name
                ctx.topics = profile.topics_of_interest
                ctx.preferences = profile.preferences
                ctx.expertise = profile.skill_levels
                ctx.recent_interactions = profile.interaction_count

        if self._pref_learner:
            model = self._pref_learner.get_model(user_id)
            if model.learned_topics:
                for t in model.learned_topics:
                    if t not in ctx.topics:
                        ctx.topics.append(t)
            ctx.communication_style = model.communication_style
            for domain, level in model.expertise_level.items():
                if domain not in ctx.expertise or level > ctx.expertise[domain]:
                    ctx.expertise[domain] = level

        return ctx

    def generate_system_prompt_block(self, user_id: str) -> str:
        ctx = self.build_context(user_id)
        lines: List[str] = ["<user-context>"]
        if ctx.user_name:
            lines.append(f"  User: {ctx.user_name}")

        if ctx.topics:
            top = ctx.topics[:5]
            lines.append(f"  Topics of interest: {', '.join(top)}")

        if ctx.expertise:
            domains = sorted(ctx.expertise.items(), key=lambda x: x[1], reverse=True)[:3]
            lines.append(f"  Expertise: {', '.join(f'{d}({v:.1f})' for d, v in domains)}")

        if ctx.communication_style:
            lines.append(f"  Prefers {ctx.communication_style} communication")

        prefs = {k: v for k, v in ctx.preferences.items()
                 if isinstance(v, (str, int, float)) and not k.startswith("_")}
        if prefs:
            lines.append(f"  Preferences: {json.dumps(prefs)}")

        lines.append("</user-context>")
        return "\n".join(lines)

    def generate_instruction_block(self, user_id: str, task: str = "") -> str:
        ctx = self.build_context(user_id)
        lines: List[str] = ["<user-instructions>"]
        if ctx.communication_style:
            lines.append(f"  Communicate in a {ctx.communication_style} style.")

        lines.append(f"  The user has engaged in {ctx.recent_interactions} previous interactions.")
        lines.append(f"  Respond appropriately to their expertise level across domains.")

        if task:
            lines.append(f"  Task context: {task}")

        lines.append("</user-instructions>")
        return "\n".join(lines)

    def generate_full_prompt(self, user_id: str, task: str = "") -> str:
        return f"{self.generate_system_prompt_block(user_id)}\n\n{self.generate_instruction_block(user_id, task)}"
