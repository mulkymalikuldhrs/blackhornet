from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderHub:
    """Combine AutoDiscovery engine with HyperGate LLM gateway.

    AutoDiscovery finds available LLM providers.
    HyperGate provides the routing/fallback layer.
    Together they give BH a unified, self-healing LLM provider pool.
    """

    def __init__(self, discovery_engine=None, hypergate=None):
        self._discovery = discovery_engine
        self._hypergate = hypergate
        self._providers: Dict[str, Any] = {}

    def set_services(self, discovery_engine=None, hypergate=None):
        if discovery_engine:
            self._discovery = discovery_engine
        if hypergate:
            self._hypergate = hypergate

    def scan_and_register(self) -> Dict[str, Any]:
        providers: Dict[str, Any] = {}
        if self._discovery:
            try:
                result = self._discovery.scan_providers()
                for prov in result:
                    name = prov.get("name", "unknown")
                    providers[name] = {
                        "status": prov.get("status", "unknown"),
                        "models": prov.get("models", []),
                    }
            except Exception as exc:
                logger.warning("Discovery scan failed: %s", exc)
        self._providers = providers
        return providers

    def get_best_provider(self, task_type: str = "general") -> str:
        if self._discovery:
            try:
                route = self._discovery.route(task_type)
                return route.get("provider", "")
            except Exception:
                pass
        return ""

    def complete(self, messages: List[Dict[str, str]],
                 **kwargs: Any) -> Optional[str]:
        if self._hypergate:
            try:
                return self._hypergate.complete(messages, **kwargs)
            except Exception as exc:
                logger.warning("HyperGate.complete failed: %s", exc)
        return None

    def list_providers(self) -> Dict[str, Any]:
        return {
            "discovered": self._providers,
            "hypergate_available": self._hypergate is not None,
        }
