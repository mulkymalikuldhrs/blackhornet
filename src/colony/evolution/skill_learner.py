"""SkillLearner — records successful command patterns and replays as learned skills."""

import json
import os
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class SkillRecord:
    id: str
    skill_name: str
    command: str
    context: dict[str, Any]
    tags: list[str]
    success_count: int
    fail_count: int
    first_seen: float
    last_seen: float
    avg_latency_ms: float
    source: str


@dataclass
class SkillResult:
    success: bool
    skill_name: str
    result: dict[str, Any]
    error: Optional[str] = None
    latency_ms: float = 0.0


class SkillLearner:
    def __init__(
        self,
        persist_path: Optional[str] = None,
        min_success_threshold: int = 2,
        max_skills: int = 200,
        auto_persist: bool = True,
    ):
        self._skills: dict[str, SkillRecord] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history = 10000
        self._persist_path = persist_path
        self._min_success_threshold = min_success_threshold
        self._max_skills = max_skills
        self._auto_persist = auto_persist
        self._total_recorded = 0
        self._total_replayed = 0
        self._total_learned = 0
        self._load()

    def _load(self) -> None:
        if not self._persist_path or not os.path.exists(self._persist_path):
            return
        try:
            with open(self._persist_path) as f:
                data = json.load(f)
            for item in data.get("skills", []):
                sr = SkillRecord(**item)
                self._skills[sr.id] = sr
            self._total_learned = len(self._skills)
            self._total_recorded = data.get("total_recorded", 0)
        except Exception:
            pass

    def _save(self) -> None:
        if not self._persist_path or not self._auto_persist:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, "w") as f:
                json.dump(
                    {
                        "skills": [asdict(s) for s in self._skills.values()],
                        "total_recorded": self._total_recorded,
                        "total_learned": self._total_learned,
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def record(
        self,
        command: str,
        success: bool,
        result: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        source: str = "queen",
        latency_ms: float = 0.0,
    ) -> None:
        entry = {
            "id": str(uuid.uuid4()),
            "command": command,
            "success": success,
            "result": result,
            "context": context or {},
            "tags": tags or [],
            "source": source,
            "latency_ms": latency_ms,
            "timestamp": time.time(),
        }
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        self._total_recorded += 1

        if not success:
            return

        base = command.split()[0] if command.split() else command
        similar = [
            s
            for s in self._skills.values()
            if s.skill_name == base and s.command == command
        ]
        if similar:
            sk = similar[0]
            sk.success_count += 1
            sk.last_seen = time.time()
            sk.avg_latency_ms = (
                sk.avg_latency_ms * (sk.success_count - 1) + latency_ms
            ) / sk.success_count
            if sk.success_count >= self._min_success_threshold and sk.id not in {
                s.id for s in self._skills.values() if s.success_count >= self._min_success_threshold
            }:
                self._total_learned += 1
        else:
            sk = SkillRecord(
                id=str(uuid.uuid4()),
                skill_name=base,
                command=command,
                context=context or {},
                tags=tags or [],
                success_count=1,
                fail_count=0,
                first_seen=time.time(),
                last_seen=time.time(),
                avg_latency_ms=latency_ms,
                source=source,
            )
            if base not in {s.skill_name for s in self._skills.values()}:
                pass
            self._skills[sk.id] = sk
            if len(self._skills) > self._max_skills:
                oldest = min(self._skills.keys(), key=lambda k: self._skills[k].last_seen)
                del self._skills[oldest]

        if self._auto_persist:
            self._save()

    def learn(self, skill_name: str) -> Optional[SkillRecord]:
        for sk in self._skills.values():
            if sk.skill_name == skill_name and sk.success_count >= self._min_success_threshold:
                return sk
        return None

    def learned_skills(self) -> list[SkillRecord]:
        return [
            s for s in self._skills.values()
            if s.success_count >= self._min_success_threshold
        ]

    def all_skills(self) -> list[SkillRecord]:
        return list(self._skills.values())

    def get_history(
        self, limit: int = 100, success_only: bool = False
    ) -> list[dict[str, Any]]:
        entries = self._history
        if success_only:
            entries = [e for e in entries if e["success"]]
        return entries[-limit:]

    def get_stats(self) -> dict[str, Any]:
        learned = self.learned_skills()
        return {
            "total_recorded": self._total_recorded,
            "total_replayed": self._total_replayed,
            "total_learned": self._total_learned,
            "skills_count": len(self._skills),
            "learned_skills_count": len(learned),
            "learned_skills": [s.skill_name for s in learned],
            "history_size": len(self._history),
            "persist_path": self._persist_path,
        }

    def forget(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            del self._skills[skill_id]
            self._save()
            return True
        return False

    def clear_history(self) -> None:
        self._history = []

    def replay(self, skill_name: str, **overrides) -> SkillResult:
        sk = self.learn(skill_name)
        if not sk:
            return SkillResult(
                success=False,
                skill_name=skill_name,
                result={},
                error=f"Skill '{skill_name}' not learned yet",
            )
        self._total_replayed += 1
        return SkillResult(
            success=True,
            skill_name=skill_name,
            result={
                "command": sk.command,
                "context": {**sk.context, **overrides},
                "skill_id": sk.id,
            },
        )
