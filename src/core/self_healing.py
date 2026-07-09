"""
Self-Healing Module
Implements phi-accrual failure detection and automatic recovery strategies.
Computes suspicion level (phi) for each monitored component using statistical
model of heartbeat inter-arrival times.

Phi threshold:
  phi = 1  -> ~10% chance component is alive (90% sure crashed)
  phi = 2  -> ~1% chance component is alive (99% sure crashed)
  phi = 3  -> ~0.1% chance (99.9% sure crashed)

Reference: Hayashibara et al. (2004), "The Phi-Accrual Failure Detector"
Auto-recovery strategies: RESTART, FAILOVER, DEGRADE, ESCALATE, RECONNECT
"""
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import logging
import asyncio
import math

logger = logging.getLogger(__name__)


class FailureLevel(Enum):
    HEALTHY = "healthy"
    SUSPECT = "suspect"
    FAILED = "failed"
    RECOVERING = "recovering"
    DEGRADED = "degraded"


class RecoveryAction(Enum):
    RESTART = "restart"
    FAILOVER = "failover"
    DEGRADE = "degrade"
    ESCALATE = "escalate"
    RECONNECT = "reconnect"
    IGNORE = "ignore"


@dataclass
class HeartbeatRecord:
    timestamp: float
    seq_number: int


@dataclass
class ComponentHealth:
    component_id: str
    component_type: str
    level: FailureLevel
    phi: float
    last_heartbeat: float
    heartbeats_received: int
    heartbeats_missed: int
    last_recovery: float
    recovery_count: int
    uptime: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PhiAccrualFailureDetector:
    def __init__(self,
                 threshold: float = 3.0,
                 window_size: int = 200,
                 min_samples: int = 10,
                 acceptable_heartbeat_pause: float = 2.0,
                 initial_heartbeat_interval: float = 5.0):
        self.threshold = threshold
        self.window_size = window_size
        self.min_samples = min_samples
        self.acceptable_pause = acceptable_heartbeat_pause
        self.initial_interval = initial_heartbeat_interval

        self._heartbeat_history: Dict[str, List[HeartbeatRecord]] = {}
        self._intervals: Dict[str, List[float]] = {}
        self._stats: Dict[str, Dict[str, float]] = {}
        self._seq_counter: Dict[str, int] = {}
        self._first_heartbeat: Dict[str, float] = {}

    def record_heartbeat(self, component_id: str) -> ComponentHealth:
        now = time.time()
        if component_id not in self._heartbeat_history:
            self._heartbeat_history[component_id] = []
            self._intervals[component_id] = []
            self._stats[component_id] = {"mean": 0.0, "std": 1.0, "n": 0}
            self._seq_counter[component_id] = 0
            self._first_heartbeat[component_id] = now

        self._seq_counter[component_id] += 1
        record = HeartbeatRecord(timestamp=now, seq_number=self._seq_counter[component_id])

        history = self._heartbeat_history[component_id]
        if history:
            interval = now - history[-1].timestamp
            intervals = self._intervals[component_id]
            intervals.append(interval)
            if len(intervals) > self.window_size:
                intervals.pop(0)
            if intervals:
                self._stats[component_id] = {
                    "mean": sum(intervals) / len(intervals),
                    "std": (sum((i - (sum(intervals) / len(intervals))) ** 2 for i in intervals) / len(intervals)) ** 0.5 if len(intervals) > 1 else 1.0,
                    "n": len(intervals),
                }

        history.append(record)
        if len(history) > self.window_size:
            history.pop(0)

        health = self.get_health(component_id)
        logger.debug(f"Heartbeat from {component_id}: phi={health.phi:.2f}, level={health.level.value}")
        return health

    def compute_phi(self, component_id: str) -> float:
        now = time.time()
        history = self._heartbeat_history.get(component_id, [])
        stats = self._stats.get(component_id, {"mean": self.initial_interval, "std": 1.0, "n": 0})

        if not history:
            return 0.0

        last_time = history[-1].timestamp
        elapsed = now - last_time

        if elapsed <= self.acceptable_pause:
            return 0.0

        if stats["n"] < self.min_samples:
            expected_interval = self.initial_interval
            std = 1.0
        else:
            expected_interval = max(stats["mean"], 0.001)
            std = max(stats["std"], expected_interval * 0.1)

        if std < 1e-10:
            return 100.0 if elapsed > expected_interval else 0.0

        x = (elapsed - expected_interval) / std
        # Use standard normal CDF approximation to compute phi
        cdf = 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
        phi = -math.log10(max(1.0 - cdf, 1e-15))
        return max(0.0, phi)

    def get_health(self, component_id: str) -> ComponentHealth:
        history = self._heartbeat_history.get(component_id, [])
        phi = self.compute_phi(component_id)
        now = time.time()
        first = self._first_heartbeat.get(component_id, now)

        if phi >= self.threshold:
            level = FailureLevel.FAILED
        elif phi >= self.threshold / 3:
            level = FailureLevel.SUSPECT
        else:
            level = FailureLevel.HEALTHY

        missed = 0
        if history:
            elapsed = now - history[-1].timestamp
            expected = max(self._stats.get(component_id, {}).get("mean", self.initial_interval), 0.001)
            missed = int(elapsed / max(expected, 0.001))

        return ComponentHealth(
            component_id=component_id,
            component_type="unknown",
            level=level,
            phi=phi,
            last_heartbeat=history[-1].timestamp if history else 0.0,
            heartbeats_received=len(history),
            heartbeats_missed=missed,
            last_recovery=0.0,
            recovery_count=0,
            uptime=now - first,
        )

    def is_available(self, component_id: str) -> bool:
        health = self.get_health(component_id)
        return health.level in (FailureLevel.HEALTHY, FailureLevel.DEGRADED)

    def reset(self, component_id: str):
        self._heartbeat_history.pop(component_id, None)
        self._intervals.pop(component_id, None)
        self._stats.pop(component_id, None)
        self._seq_counter.pop(component_id, None)
        self._first_heartbeat[component_id] = time.time()

    def get_all_health(self) -> Dict[str, ComponentHealth]:
        return {cid: self.get_health(cid) for cid in self._heartbeat_history}


class RecoveryManager:
    def __init__(self, detector: PhiAccrualFailureDetector):
        self.detector = detector
        self._recovery_handlers: Dict[str, Callable] = {}
        self._recovery_history: Dict[str, List[Dict]] = {}
        self._cooldown: float = 30.0
        self._max_recoveries: int = 5

    def register_handler(self, component_type: str, handler: Callable):
        self._recovery_handlers[component_type] = handler

    async def check_and_recover(self, component_id: str, component_type: str,
                                 recovery_action: RecoveryAction = RecoveryAction.RESTART) -> bool:
        health = self.detector.get_health(component_id)
        if health.level != FailureLevel.FAILED:
            return True

        now = time.time()
        history = self._recovery_history.get(component_id, [])
        recent = [r for r in history if now - r["timestamp"] < 300]
        if len(recent) >= self._max_recoveries:
            logger.error(f"Max recoveries reached for {component_id}, escalating")
            return False

        if history and now - history[-1]["timestamp"] < self._cooldown:
            logger.debug(f"Recovery cooldown for {component_id}")
            return False

        handler = self._recovery_handlers.get(component_type)
        if not handler:
            logger.warning(f"No recovery handler for {component_type}")
            return False

        try:
            result = await handler(component_id, recovery_action)
            self._recovery_history.setdefault(component_id, []).append({
                "timestamp": now,
                "action": recovery_action.value,
                "success": result,
            })
            if result:
                self.detector.reset(component_id)
                logger.info(f"Recovery OK for {component_id} ({recovery_action.value})")
            return result
        except Exception as e:
            logger.error(f"Recovery failed for {component_id}: {e}")
            self._recovery_history.setdefault(component_id, []).append({
                "timestamp": now,
                "action": recovery_action.value,
                "success": False,
                "error": str(e),
            })
            return False

    def get_recovery_stats(self) -> Dict[str, Any]:
        total = 0
        success = 0
        for cid, records in self._recovery_history.items():
            total += len(records)
            success += sum(1 for r in records if r.get("success"))
        return {
            "total_recoveries": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / max(total, 1),
            "components": len(self._recovery_history),
        }


class SelfHealingOrchestrator:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.detector = PhiAccrualFailureDetector(
            threshold=self.config.get("phi_threshold", 3.0),
            acceptable_heartbeat_pause=self.config.get("acceptable_pause", 2.0),
        )
        self.recovery = RecoveryManager(self.detector)
        self._monitored: Dict[str, str] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def monitor(self, component_id: str, component_type: str,
                recovery_action: RecoveryAction = RecoveryAction.RESTART):
        self._monitored[component_id] = component_type

    def unmonitor(self, component_id: str):
        self._monitored.pop(component_id, None)

    def heartbeat(self, component_id: str) -> ComponentHealth:
        return self.detector.record_heartbeat(component_id)

    async def _healing_loop(self):
        while self._running:
            for cid, ctype in self._monitored.items():
                health = self.detector.get_health(cid)
                if health.level == FailureLevel.FAILED:
                    await self.recovery.check_and_recover(cid, ctype)
            await asyncio.sleep(self.config.get("check_interval", 5.0))

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._healing_loop())
        logger.info("Self-healing orchestrator started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Self-healing orchestrator stopped")

    def get_status(self) -> Dict[str, Any]:
        return {
            "monitored_components": len(self._monitored),
            "health": {
                cid: {
                    "level": self.detector.get_health(cid).level.value,
                    "phi": round(self.detector.get_health(cid).phi, 2),
                }
                for cid in self._monitored
            },
            "recovery": self.recovery.get_recovery_stats(),
        }
