"""EvolutionOrchestrator — wires SkillLearner + AutoDiscoveryEnhancer + SelfModifyEngine."""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .skill_learner import SkillLearner, SkillRecord
from .auto_discovery import AutoDiscoveryEnhancer
from .self_modify import SelfModifyEngine, ChangeProposal


@dataclass
class EvolutionConfig:
    skill_persist_path: Optional[str] = None
    discovery_persist_path: Optional[str] = None
    scan_paths: Optional[list[str]] = None
    codebase_root: str = "."
    sync_interval: int = 120
    auto_discover: bool = True
    auto_learn: bool = True
    auto_propose: bool = False
    min_skill_confidence: int = 2
    require_approval: bool = True


class EvolutionOrchestrator:
    def __init__(self, config: Optional[EvolutionConfig] = None):
        self._config = config or EvolutionConfig()
        self._skill_learner = SkillLearner(
            persist_path=self._config.skill_persist_path,
            min_success_threshold=self._config.min_skill_confidence,
        )
        self._discovery = AutoDiscoveryEnhancer(
            scan_paths=self._config.scan_paths,
            persist_path=self._config.discovery_persist_path,
        )
        self._self_modify = SelfModifyEngine(
            codebase_root=self._config.codebase_root,
            require_approval=self._config.require_approval,
        )
        self._lifecycle: Any = None
        self._orchestrator: Any = None
        self._radar: Any = None
        self._running = False
        self._start_time: float = 0.0

    @property
    def skill_learner(self) -> SkillLearner:
        return self._skill_learner

    @property
    def discovery(self) -> AutoDiscoveryEnhancer:
        return self._discovery

    @property
    def self_modify(self) -> SelfModifyEngine:
        return self._self_modify

    def wire(
        self,
        lifecycle: Any = None,
        orchestrator: Any = None,
        radar: Any = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._orchestrator = orchestrator
        self._radar = radar
        if radar:
            self._discovery.wire_radar(radar)

    async def start(self) -> None:
        self._running = True
        self._start_time = time.time()

    async def stop(self) -> None:
        self._running = False

    def record_command(
        self,
        command: str,
        success: bool,
        result: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        latency_ms: float = 0.0,
    ) -> None:
        if not self._config.auto_learn:
            return
        self._skill_learner.record(
            command=command,
            success=success,
            result=result,
            context=context,
            tags=tags,
            latency_ms=latency_ms,
        )

    async def run_discovery_scan(self) -> dict[str, Any]:
        if not self._config.auto_discover:
            return {"success": False, "reason": "auto_discover disabled"}
        result = await self._discovery.scan_modules()
        dir_result = None
        for path in (self._config.scan_paths or []):
            dir_result = await self._discovery.scan_directory(path)
        return {
            "success": result.success,
            "module_capabilities": len(result.capabilities),
            "directory_capabilities": len(dir_result.capabilities) if dir_result else 0,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }

    def get_learned_skills(self) -> list[SkillRecord]:
        return self._skill_learner.learned_skills()

    def get_all_skills(self) -> list[SkillRecord]:
        return self._skill_learner.all_skills()

    def get_discovered_capabilities(
        self, capability_type: Optional[str] = None, source: Optional[str] = None
    ) -> list[Any]:
        return self._discovery.get_capabilities(capability_type, source)

    def get_proposals(
        self, status: Optional[str] = None, limit: int = 50
    ) -> list[ChangeProposal]:
        return self._self_modify.get_proposals(status=status, limit=limit)

    def get_stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "skill_learner": self._skill_learner.get_stats(),
            "discovery": self._discovery.get_stats(),
            "self_modify": self._self_modify.get_stats(),
            "config": {
                "sync_interval": self._config.sync_interval,
                "auto_discover": self._config.auto_discover,
                "auto_learn": self._config.auto_learn,
                "auto_propose": self._config.auto_propose,
            },
        }
