"""Thinking module — semantic reasoning, learning, and self-improvement.

FASE 3 (complete):
  3.1 ConceptMap — semantic concept graph
  3.2 CoTRetrieval — chain-of-thought reasoning retrieval
  3.3 FeedbackCollector — collect and store interaction feedback
  3.4 SkillExtractor — extract reusable skills from successes
  3.5 AvoidanceLearner — learn what to avoid from failures

FASE 4 (complete):
  4.1 UserProfile — store and manage user profiles
  4.2 PreferenceLearner — learn user preferences from interactions
  4.3 SelfPromptGenerator — generate adaptive self-prompts
  4.4 ContextAdapter — adapt responses based on user context

FASE 5 (complete):
  5.1 GoalManager — manage and track goals
  5.2 TaskScheduler — schedule and prioritize tasks
  5.3 PriorityEngine — compute priority scores
  5.4 ProactiveBehavior — initiate actions without prompt
  5.5 IntentDetector — detect user intent from messages
  5.6 CuriosityDrive — generate exploration goals
  5.7 SelfTaskGenerator — generate self-assigned tasks
"""

from .concept_map import ConceptMap, ConceptNode, ConceptEdge
from .cot_retrieval import CoTRetrieval, CoTPath
from .feedback_collector import FeedbackCollector, Feedback
from .skill_extractor import SkillExtractor, Skill
from .avoidance_learner import AvoidanceLearner, AvoidanceRule
from .user_profile import UserProfileStore, UserProfile
from .preference_learner import PreferenceLearner, Preference, PreferenceModel
from .self_prompt import SelfPromptGenerator, PromptContext
from .context_adapter import ContextAdapter, AdaptationResult
from .goal_manager import GoalManager, Goal
from .task_scheduler import TaskScheduler, Task
from .priority_engine import PriorityEngine, PriorityFactors, ScoredItem
from .proactive_behavior import ProactiveBehavior, ProactiveAction
from .intent_detector import IntentDetector, Intent, IntentPattern
from .curiosity_drive import CuriosityDrive, ExplorationGoal
from .self_task_generator import SelfTaskGenerator, TaskProposal

__all__ = [
    "ConceptMap", "ConceptNode", "ConceptEdge",
    "CoTRetrieval", "CoTPath",
    "FeedbackCollector", "Feedback",
    "SkillExtractor", "Skill",
    "AvoidanceLearner", "AvoidanceRule",
    "UserProfileStore", "UserProfile",
    "PreferenceLearner", "Preference", "PreferenceModel",
    "SelfPromptGenerator", "PromptContext",
    "ContextAdapter", "AdaptationResult",
    "GoalManager", "Goal",
    "TaskScheduler", "Task",
    "PriorityEngine", "PriorityFactors", "ScoredItem",
    "ProactiveBehavior", "ProactiveAction",
    "IntentDetector", "Intent", "IntentPattern",
    "CuriosityDrive", "ExplorationGoal",
    "SelfTaskGenerator", "TaskProposal",
]
