"""Frontend UI specialist — Frontend development and UX optimization."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class FrontendUiSpecialist(BaseAgent):
    """Specialist agent for frontend development and UX optimization.

    Handles component architecture, responsive design, accessibility,
    state management, and performance optimization for web applications.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.CODER, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._components: Dict[str, Dict[str, Any]] = {}
        self._design_system: Dict[str, Any] = {"colors": {}, "typography": {}, "spacing": {}}
        self._accessibility_issues: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_component":
            return await self._create_component(task)
        elif action == "optimize_bundle":
            return await self._optimize_bundle(task)
        elif action == "audit_accessibility":
            return await self._audit_accessibility(task)
        elif action == "analyze_lighthouse":
            return await self._analyze_lighthouse(task)
        elif action == "manage_state":
            return await self._manage_state(task)
        elif action == "responsive_audit":
            return await self._responsive_audit(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "component_query":
            name = message.get("payload", {}).get("name", "")
            return self._components.get(name, {"found": False})
        elif msg_type == "ui_health_check":
            return {"status": "healthy", "components": len(self._components)}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "component_architecture", "responsive_design", "accessibility_auditing",
            "bundle_optimization", "state_management", "lighthouse_analysis",
            "design_system_management", "cross_browser_testing",
        ]

    async def _create_component(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "UnnamedComponent")
        component_type = task.payload.get("type", "functional")
        props = task.payload.get("props", [])
        styling = task.payload.get("styling", "css_modules")
        accessible = task.payload.get("accessible", True)

        component = {
            "name": name,
            "type": component_type,
            "props": props,
            "styling": styling,
            "accessible": accessible,
            "created_at": time.time(),
            "render_count": 0,
            "bundle_size_kb": 0.0,
        }

        if accessible:
            component["a11y_features"] = ["aria_labels", "keyboard_navigation", "focus_management"]

        self._components[name] = component
        logger.info(f"Created frontend component: {name}")
        return {"success": True, "component": name, "config": component}

    async def _optimize_bundle(self, task: Task) -> Dict[str, Any]:
        bundle_name = task.payload.get("bundle", "main")
        current_size = task.payload.get("size_kb", 500)

        optimizations: List[str] = []
        if current_size > 200:
            optimizations.append("code_splitting")
        if current_size > 100:
            optimizations.append("tree_shaking")
        optimizations.extend(["lazy_loading", "asset_compression"])

        optimized_size = current_size * 0.6
        return {
            "success": True,
            "bundle": bundle_name,
            "original_size_kb": current_size,
            "optimized_size_kb": round(optimized_size, 2),
            "reduction_percent": round((1 - optimized_size / current_size) * 100, 1),
            "optimizations_applied": optimizations,
        }

    async def _audit_accessibility(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "page")
        issues: List[Dict[str, Any]] = []

        checks = [
            {"rule": "missing_alt_text", "severity": "critical", "description": "Images without alt text"},
            {"rule": "low_contrast", "severity": "high", "description": "Insufficient color contrast"},
            {"rule": "missing_aria", "severity": "high", "description": "Missing ARIA attributes"},
            {"rule": "keyboard_trap", "severity": "critical", "description": "Keyboard focus trapped"},
            {"rule": "missing_label", "severity": "medium", "description": "Form inputs without labels"},
        ]

        for check in checks:
            if task.payload.get("include_all", True):
                issues.append(check)

        self._accessibility_issues.extend(issues)
        score = max(0, 100 - len(issues) * 10)
        return {"success": True, "target": target, "score": score, "issues": issues, "issue_count": len(issues)}

    async def _analyze_lighthouse(self, task: Task) -> Dict[str, Any]:
        url = task.payload.get("url", "localhost")
        scores = {
            "performance": task.payload.get("performance", 85),
            "accessibility": task.payload.get("accessibility", 90),
            "best_practices": task.payload.get("best_practices", 88),
            "seo": task.payload.get("seo", 92),
        }
        overall = sum(scores.values()) / len(scores)
        return {"success": True, "url": url, "scores": scores, "overall_score": round(overall, 1)}

    async def _manage_state(self, task: Task) -> Dict[str, Any]:
        operation = task.payload.get("operation", "get")
        store_name = task.payload.get("store", "default")
        key = task.payload.get("key", "")
        value = task.payload.get("value")

        if operation == "set":
            if not hasattr(self, "_state_stores"):
                self._state_stores: Dict[str, Dict[str, Any]] = {}
            if store_name not in self._state_stores:
                self._state_stores[store_name] = {}
            self._state_stores[store_name][key] = value
            return {"success": True, "operation": "set", "store": store_name, "key": key}
        elif operation == "get":
            stores = getattr(self, "_state_stores", {})
            val = stores.get(store_name, {}).get(key)
            return {"success": True, "operation": "get", "store": store_name, "key": key, "value": val}
        return {"success": False, "error": f"Unknown state operation: {operation}"}

    async def _responsive_audit(self, task: Task) -> Dict[str, Any]:
        breakpoints = {"mobile": 375, "tablet": 768, "desktop": 1024, "wide": 1440}
        issues: List[str] = []

        if task.payload.get("check_overflow", True):
            issues.append("horizontal_overflow_detected")
        if task.payload.get("check_images", True):
            issues.append("non_responsive_images")

        return {"success": True, "breakpoints": breakpoints, "issues": issues}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "components_count": len(self._components),
                "accessibility_issues": len(self._accessibility_issues),
                "design_system_tokens": sum(len(v) for v in self._design_system.values()),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "frontend_ui",
            "metrics": self._monitor()["metrics"],
        }
