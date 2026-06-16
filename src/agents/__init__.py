"""Agent framework for AI-MultiColony.

Exports all agent classes, the registry, event bus, circuit breaker,
graph orchestration, shared state, and Pydantic state models.
"""

from src.agents.base import BaseAgent, EventBus, CircuitBreaker, RetryPolicy
from src.agents.manus import ManusAgent
from src.agents.planner import PlannerAgent
from src.agents.executor import ExecutorAgent
from src.agents.coder import CoderAgent
from src.agents.browser import BrowserAgent
from src.agents.voice import VoiceAgent
from src.agents.security import SecurityAgent
from src.agents.researcher import ResearcherAgent
from src.agents.colony import ColonyAgent
from .graph import AgentGraph, GraphNode, GraphEdge, ConditionalEdge, ParallelBranch, GraphCheckpoint
from src.agents.registry import AgentRegistry, AGENT_TYPES
from src.agents.state import (
    SharedAgentState,
    AgentStateModel,
    AgentConfig,
    ColonyState,
    TaskStateModel,
    A2AMessageState,
    HealthReport,
)

# ── Re-exports from flat modules (backward compatibility) ─────────────────────
# These classes live in the flat .py files alongside the package directories.
# They may or may not be available depending on import order.
try:
    from src.agents.executor.executor import SandboxConfig, SandboxHandle  # type: ignore[no-redef]
except ImportError:
    SandboxConfig = None  # type: ignore[misc,assignment]
    SandboxHandle = None  # type: ignore[misc,assignment]

try:
    from src.agents.coder.coder import CodeArtifact  # type: ignore[no-redef]
except ImportError:
    CodeArtifact = None  # type: ignore[misc,assignment]

try:
    from src.agents.browser.browser import BrowserPage  # type: ignore[no-redef]
except ImportError:
    BrowserPage = None  # type: ignore[misc,assignment]

try:
    from src.agents.voice.voice import VoiceSession  # type: ignore[no-redef]
except ImportError:
    VoiceSession = None  # type: ignore[misc,assignment]

try:
    from src.agents.researcher.researcher import ResearchDocument, ResearchReport  # type: ignore[no-redef]
except ImportError:
    ResearchDocument = None  # type: ignore[misc,assignment]
    ResearchReport = None  # type: ignore[misc,assignment]

try:
    from src.agents.colony.colony import ColonyMetrics  # type: ignore[no-redef]
except ImportError:
    ColonyMetrics = None  # type: ignore[misc,assignment]

__all__ = [
    # Base
    "BaseAgent", "EventBus", "CircuitBreaker", "RetryPolicy",
    # Agents
    "ManusAgent", "PlannerAgent", "ExecutorAgent",
    "CoderAgent", "BrowserAgent", "VoiceAgent",
    "SecurityAgent", "ResearcherAgent", "ColonyAgent",
    # Executor helpers
    "SandboxConfig", "SandboxHandle",
    # Coder helpers
    "CodeArtifact",
    # Browser helpers
    "BrowserPage",
    # Voice helpers
    "VoiceSession",
    # Researcher helpers
    "ResearchDocument", "ResearchReport",
    # Colony helpers
    "ColonyMetrics",
    # Graph
    "AgentGraph", "GraphNode", "GraphEdge", "ConditionalEdge",
    "ParallelBranch", "GraphCheckpoint",
    # Registry
    "AgentRegistry", "AGENT_TYPES",
    # State
    "SharedAgentState", "AgentStateModel", "AgentConfig",
    "ColonyState", "TaskStateModel", "A2AMessageState", "HealthReport",
]
