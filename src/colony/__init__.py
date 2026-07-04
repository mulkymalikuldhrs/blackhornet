"""Colony management for AI-MultiColony.

Provides colony lifecycle, hand-based agent grouping, task scheduling,
agent-to-agent communication, cross-instance radar, mesh messaging,
and self-nest bootstrap.
"""

from .manager import Colony, ColonyManager, SCALE_PRESETS
from .hands import (
    Hand,
    HandManager,
    SecurityHand,
    CodeHand,
    ResearchHand,
    BrowserHand,
    VoiceHand,
    ComputeHand,
    IntegrationHand,
    HAND_DESCRIPTIONS,
    HAND_DEFAULTS,
)
from .scheduler import TaskScheduler
from .a2a import A2ACoordinator
from .radar import ColonyRadar, RadarConfig
from .mesh_bus import MeshBus
from .nest import SelfNest, NestConfig
from .orchestrator import EcosystemOrchestrator, OrchestratorConfig
from .lifecycle import LifecycleRecorder, LifecycleEventType
from .graph_sync import GraphifySyncBridge
from .session_export import SessionExporter
from .queen import QueenAgent
from .voice_service import VoiceService
from .consciousness import ColonyConsciousness
from .intelligence import IntelligenceBridge
from .health_monitor import ColonyHealthMonitor

# Swarm skills — multi-agent coordination engineering (arXiv:2605.10052)
from src.swarm.swarm_skills import SwarmSkillsManager, SwarmSkill, AgentRole, WorkflowStep

__all__ = [
    # Manager
    "Colony",
    "ColonyManager",
    "SCALE_PRESETS",
    # Hands
    "Hand",
    "HandManager",
    "SecurityHand",
    "CodeHand",
    "ResearchHand",
    "BrowserHand",
    "VoiceHand",
    "ComputeHand",
    "IntegrationHand",
    "HAND_DESCRIPTIONS",
    "HAND_DEFAULTS",
    # Scheduler
    "TaskScheduler",
    # A2A
    "A2ACoordinator",
    # Ecosystem
    "ColonyRadar",
    "RadarConfig",
    "MeshBus",
    "SelfNest",
    "NestConfig",
    # Control Center
    "EcosystemOrchestrator",
    "OrchestratorConfig",
    # Lifecycle
    "LifecycleRecorder",
    "LifecycleEventType",
    # Graph sync
    "GraphifySyncBridge",
    # Session export
    "SessionExporter",
    # Queen
    "QueenAgent",
    # Voice
    "VoiceService",
    # Consciousness
    "ColonyConsciousness",
    # Intelligence
    "IntelligenceBridge",
    # Health Monitor
    "ColonyHealthMonitor",
    # Swarm Skills (v2.0)
    "SwarmSkillsManager",
    "SwarmSkill",
    "AgentRole",
    "WorkflowStep",
]
