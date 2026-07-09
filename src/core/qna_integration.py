#!/usr/bin/env python3
"""
BLACKHORNET — QNA Integration Bridge
=====================================
Lazy-imports Quant Nanggroe AI modules and routes queries to the
appropriate engine subsystem.

Routing:
  - kelly/*   → _handle_kelly
  - regime/*  → _handle_regime
  - data/*    → _handle_data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("BlackHornet.QNA")


class QueryDomain(Enum):
    KELLY = "kelly"
    REGIME = "regime"
    DATA = "data"


@dataclass
class QNAQuery:
    domain: QueryDomain
    action: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QNAResponse:
    success: bool
    data: Any = None
    error: Optional[str] = None
    provider: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QNAIntegrationBridge:
    """Lazy-import bridge from BLACKHORNET into Quant Nanggroe AI engine."""

    def __init__(self):
        self._initialized = False
        self._modules: Dict[str, Any] = {}
        self._health = {"status": "uninitialized", "errors": []}

    def initialize(self) -> bool:
        """Lazy-import all QNA engine sub-modules."""
        if self._initialized:
            return True

        errors: List[str] = []
        targets = {
            "kelly": "quant_nanggroe.engine.kelly",
            "regime": "quant_nanggroe.engine.regime",
            "data": "quant_nanggroe.engine.data",
            "core": "quant_nanggroe.engine.core",
            "risk": "quant_nanggroe.engine.risk",
        }

        for name, module_path in targets.items():
            try:
                self._modules[name] = __import__(module_path, fromlist=["_trunk"])
                logger.info(f"Imported {module_path}")
            except ImportError as e:
                errors.append(f"{module_path}: {e}")
                logger.warning(f"Failed to import {module_path}: {e}")

        self._initialized = True
        self._health["status"] = "degraded" if errors else "healthy"
        self._health["errors"] = errors
        self._health["modules_loaded"] = len(self._modules)
        return len(errors) == 0

    def query(self, query: QNAQuery) -> QNAResponse:
        """Route a query to the correct handler based on domain."""
        if not self._initialized:
            self.initialize()

        handlers = {
            QueryDomain.KELLY: self._handle_kelly,
            QueryDomain.REGIME: self._handle_regime,
            QueryDomain.DATA: self._handle_data,
        }
        handler = handlers.get(query.domain)
        if handler is None:
            return QNAResponse(success=False, error=f"Unknown domain: {query.domain}")
        try:
            return handler(query)
        except Exception as e:
            logger.exception(f"Handler failed for {query.domain}.{query.action}: {e}")
            return QNAResponse(success=False, error=str(e))

    def _handle_kelly(self, query: QNAQuery) -> QNAResponse:
        """Route to Kelly Criterion engine."""
        kelly_mod = self._modules.get("kelly")
        if kelly_mod is None:
            return QNAResponse(success=False, error="Kelly module not loaded")

        action_map = {
            "fractional": getattr(kelly_mod, "fractional", None),
            "optimal_f": getattr(kelly_mod, "optimal_f", None),
            "adaptive": getattr(kelly_mod, "adaptive", None),
            "bayesian": getattr(kelly_mod, "bayesian", None),
            "multi_asset": getattr(kelly_mod, "multi_asset", None),
        }
        sub = action_map.get(query.action)
        if sub is None:
            return QNAResponse(success=False, error=f"Unknown kelly action: {query.action}")

        result = getattr(sub, "compute", None)
        if result is None:
            result = sub
        if callable(result):
            result = result(**query.params)
        return QNAResponse(success=True, data=result, provider="kelly")

    def _handle_regime(self, query: QNAQuery) -> QNAResponse:
        """Route to Market Regime detector."""
        regime_mod = self._modules.get("regime")
        if regime_mod is None:
            return QNAResponse(success=False, error="Regime module not loaded")

        detectors = {
            "hmm": getattr(regime_mod, "hmm_detector", None),
            "volatility": getattr(regime_mod, "volatility_clustering", None),
            "correlation": getattr(regime_mod, "correlation_regime", None),
            "macro": getattr(regime_mod, "macro_regime", None),
            "ensemble": getattr(regime_mod, "ensemble", None),
            "store": getattr(regime_mod, "regime_store", None),
            "strategy_selector": getattr(regime_mod, "strategy_selector", None),
        }
        detector = detectors.get(query.action)
        if detector is None:
            return QNAResponse(success=False, error=f"Unknown regime action: {query.action}")

        result = getattr(detector, "detect", None)
        if result is None:
            result = detector
        if callable(result):
            result = result(**query.params)
        return QNAResponse(success=True, data=result, provider="regime")

    def _handle_data(self, query: QNAQuery) -> QNAResponse:
        """Route to Data fallback chain / provider layer."""
        data_mod = self._modules.get("data")
        if data_mod is None:
            return QNAResponse(success=False, error="Data module not loaded")

        actions = {
            "fallback_chain": getattr(data_mod, "fallback_chain", None),
            "data_manager": getattr(data_mod, "data_manager", None),
            "provider_interface": getattr(data_mod, "provider_interface", None),
        }
        action_mod = actions.get(query.action)
        if action_mod is None:
            return QNAResponse(success=False, error=f"Unknown data action: {query.action}")

        create_default = getattr(action_mod, "create_default_chain", None)
        if create_default is not None and callable(create_default):
            result = create_default(**query.params)
            return QNAResponse(success=True, data=result, provider="data")

        return QNAResponse(success=True, data=action_mod, provider="data")

    def health_check(self) -> Dict[str, Any]:
        """Return bridge health status."""
        if not self._initialized:
            self.initialize()
        return dict(
            self._health,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


_SINGLETON: Optional[QNAIntegrationBridge] = None


def get_qna_bridge() -> QNAIntegrationBridge:
    """Return the singleton QNAIntegrationBridge instance."""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = QNAIntegrationBridge()
    return _SINGLETON
