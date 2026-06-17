"""Core module for the AI MultiColony Ecosystem."""

from src.core.base_agent import BaseAgent
from src.core.agent_loop import AgentLoop
from src.core.tool_registry import ToolRegistry, tool
from src.core.tool_base import BaseTool
from src.core.event_bus import EventBus
from src.core.llm_provider import LLMProvider, LLMResponse, LLMUsage
from src.core.memory_manager import MemoryManager
from src.core.channel import BaseChannel, TelegramChannel, DiscordChannel, SlackChannel, WhatsAppChannel, create_channel
from src.core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerMiddleware
from src.core.pii_redaction import redact_pii, pii_redaction_processor, PIIRedactionFilter

# Additional exports (12.3)
from src.core.edge_cases import GracefulDegrader, safe_execute, validate_input
from src.core.llm_router_bridge import LLMRouterBridge, RouterResponse
from src.core.observability import ObservabilityManager, StructuredLogger, NoOpMetrics, NoOpTracer, get_observability, reset_observability
from src.core.persistence import PersistenceBackend, FileBackend, MemoryBackend, get_persistence_backend
from src.core.qna_integration import QNAIntegrationBridge, QNAQuery, QNAResponse, QueryDomain
from src.core.self_healing import SelfHealingOrchestrator, RecoveryManager, PhiAccrualFailureDetector, ComponentHealth, FailureLevel

__all__ = [
    "BaseAgent", "AgentLoop", "ToolRegistry", "tool", "BaseTool",
    "EventBus", "LLMProvider", "LLMResponse", "LLMUsage",
    "MemoryManager", "BaseChannel", "TelegramChannel", "DiscordChannel",
    "SlackChannel", "WhatsAppChannel", "create_channel",
    "CircuitBreaker", "CircuitState", "CircuitBreakerMiddleware",
    "redact_pii", "pii_redaction_processor", "PIIRedactionFilter",
    # 12.3 additional exports
    "GracefulDegrader", "safe_execute", "validate_input",
    "LLMRouterBridge", "RouterResponse",
    "ObservabilityManager", "StructuredLogger", "NoOpMetrics", "NoOpTracer",
    "get_observability", "reset_observability",
    "PersistenceBackend", "FileBackend", "MemoryBackend", "get_persistence_backend",
    "QNAIntegrationBridge", "QNAQuery", "QNAResponse", "QueryDomain",
    "SelfHealingOrchestrator", "RecoveryManager", "PhiAccrualFailureDetector",
    "ComponentHealth", "FailureLevel",
]
