"""
BlackHornet Evolution Module

Handles colony evolution, self-improvement, and adaptive learning.
"""

from . import auto_discovery
from . import orchestrator
from . import skill_learner
from . import self_modify

__all__ = ["auto_discovery", "orchestrator", "skill_learner", "self_modify"]
