"""ColonyHealthMonitor — unified health monitoring for colony ecosystem."""

import asyncio
import logging
import time
from typing import Any, Optional

from src.core.self_healing import PhiAccrualFailureDetector, SelfHealingOrchestrator, RecoveryAction, ComponentHealth, FailureLevel
from src.core.circuit_breaker import CircuitBreaker
from src.colony.radar import ColonyRadar
from src.colony.mesh_bus import MeshBus
from src.colony.nest import SelfNest
from src.colony.orchestrator import EcosystemOrchestrator

logger = logging.getLogger(__name__)


class ColonyHealthMonitor:
    """Unified health monitor for colony ecosystem components.

    Integrates PhiAccrual failure detection, circuit breakers, and recovery
    orchestration to provide self-healing for Radar, MeshBus, and SelfNest.
    """

    def __init__(
        self,
        detector: Optional[PhiAccrualFailureDetector] = None,
        orchestrator: Optional[SelfHealingOrchestrator] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self._detector = detector or PhiAccrualFailureDetector()
        self._orchestrator = orchestrator or SelfHealingOrchestrator()
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            name="mesh_delivery",
            failure_threshold=5,
            timeout_seconds=60.0,
        )
        self._radar: Optional[ColonyRadar] = None
        self._mesh_bus: Optional[MeshBus] = None
        self._nest: Optional[SelfNest] = None
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def wire_radar(self, radar: ColonyRadar) -> None:
        """Wire Radar to health monitor."""
        self._radar = radar
        # Register all peer IDs for monitoring
        if radar._peers:
            for peer_id in radar._peers.keys():
                self._detector.reset(peer_id)

    def wire_mesh(self, mesh_bus: MeshBus) -> None:
        """Wire MeshBus to health monitor."""
        self._mesh_bus = mesh_bus
        # Register mesh delivery circuit breaker
        self._circuit_breaker = CircuitBreaker(
            name="mesh_delivery",
            failure_threshold=5,
            timeout_seconds=60.0,
        )

    def wire_nest(self, nest: SelfNest) -> None:
        """Wire SelfNest to health monitor."""
        self._nest = nest
        # Register nest components for recovery
        if nest.components:
            for component_id in nest.components.keys():
                self._orchestrator.recovery.register_handler(
                    component_id, self._recover_component
                )

    async def start(self) -> None:
        """Start health monitoring loops."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        # Start recovery loop
        asyncio.create_task(self._recovery_loop())

    async def stop(self) -> None:
        """Stop health monitoring loops."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self._monitor_task = None

    async def _monitor_loop(self) -> None:
        """Main monitoring loop: record heartbeats and check health."""
        while self._running:
            try:
                # Record heartbeat from Radar peers
                if self._radar and self._radar.peers:
                    for peer_id in self._radar.peers.keys():
                        self.record_peer_heartbeat(peer_id)

                # Record heartbeat from Nest components
                if self._nest and self._nest.components:
                    for component_id in self._nest.components.keys():
                        self._detector.record_heartbeat(component_id)

                # Check health of all monitored components
                if self._nest:
                    for component_id in self._nest.components.keys():
                        health = self._detector.get_health(component_id)
                        if health.level == FailureLevel.FAILED:
                            await self._orchestrator.recovery.check_and_recover(
                                component_id, "nest_component", RecoveryAction.RESTART
                            )

                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor loop error: {e}")
                await asyncio.sleep(1)

    async def _recovery_loop(self) -> None:
        """Recovery loop: handle pending recoveries."""
        while self._running:
            try:
                # Check for any pending recoveries
                if self._nest:
                    status = self._orchestrator.get_status()
                    if status.get("pending_recoveries", 0) > 0:
                        logger.info(f"Pending recoveries: {status['pending_recoveries']}")
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Recovery loop error: {e}")
                await asyncio.sleep(1)

    def record_peer_heartbeat(self, peer_id: str) -> None:
        """Record a heartbeat from a peer."""
        if self._radar and peer_id in self._radar.peers:
            self._detector.record_heartbeat(peer_id)

    async def _recover_component(self, component_id: str) -> bool:
        """Recovery handler for failed nest components."""
        logger.info("recovering_component component=%s", component_id)
        if self._nest:
            try:
                await self._nest.restart_component(component_id)
                return True
            except Exception as e:
                logger.error("recovery_failed component=%s err=%s", component_id, e)
        return False

    def get_peer_health(self, peer_id: str) -> Optional[ComponentHealth]:
        """Get the health status of a peer."""
        return self._detector.get_health(peer_id)

    async def monitored_deliver(self, message: Any, target_url: str) -> bool:
        """Deliver a message via MeshBus with circuit breaker protection."""
        if not self._mesh_bus:
            return False

        try:
            if not self._circuit_breaker.can_execute():
                logger.debug("circuit_breaker_open target=%s", target_url)
                return False

            # Use the mesh bus's HTTP delivery method
            success = await self._mesh_bus._send_http(message)
            if success:
                self._circuit_breaker.record_success()
            else:
                self._circuit_breaker.record_failure()
            return success
        except Exception:
            self._circuit_breaker.record_failure()
            return False

    def get_stats(self) -> dict:
        """Get health monitor statistics."""
        all_health = self._detector.get_all_health()
        return {
            "detector": {
                "monitored_count": len(all_health),
                "component_ids": list(all_health.keys()),
            },
            "circuit_breaker": self._circuit_breaker.to_dict(),
            "orchestrator": self._orchestrator.get_status(),
            "radar_wired": self._radar is not None,
            "mesh_wired": self._mesh_bus is not None,
            "nest_wired": self._nest is not None,
        }