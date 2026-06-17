"""BlackHornet Auto-Discovery Engine.

FASE 1 — 10 sub-agents:
  1.1 LLM Scanner      — discovers free LLM providers
  1.2 Data Scanner     — discovers free data providers
  1.3 Router Engine    — routes requests to best provider by complexity
  1.4 Fallback Chain   — multi-provider fallback with timeout
  1.5 Health Check     — periodic provider health monitoring
  1.6 Config Manager   — user-configurable provider preferences
  1.7 Cost Tracker     — token usage and cost tracking
  1.8 CLI              — command-line interface
  1.10 Integration     — wires all components as a service
"""

from __future__ import annotations

from src.auto_discovery.llm_scanner import LLMScanner, ProviderInfo
from src.auto_discovery.data_scanner import DataScanner, DataSource
from src.auto_discovery.router import ComplexityLevel, LLMRouter, RouteResult, RouterConfig
from src.auto_discovery.fallback import FallbackChain, FallbackResult
from src.auto_discovery.health import HealthChecker, HealthStatus
from src.auto_discovery.config_manager import ConfigManager, AutoDiscoveryConfig, ProviderConfig, RoutingConfig
from src.auto_discovery.cost_tracker import CostTracker, UsageRecord, ProviderStats

__all__ = [
    "LLMScanner", "ProviderInfo",
    "DataScanner", "DataSource",
    "ComplexityLevel", "LLMRouter", "RouteResult", "RouterConfig",
    "FallbackChain", "FallbackResult",
    "HealthChecker", "HealthStatus",
    "ConfigManager", "AutoDiscoveryConfig", "ProviderConfig", "RoutingConfig",
    "CostTracker", "UsageRecord", "ProviderStats",
]
