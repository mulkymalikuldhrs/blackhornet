"""Colony Radar Protocol — cross-instance discovery for Blackhornet colonies.

Layers:
  1. LAN Broadcast (UDP multicast) — zero-config discovery on local network
  2. Static Peers — manually configured remote colonies
  3. Rendezvous Server — optional central registry for WAN discovery
  4. DHT (planned) — fully decentralized peer discovery

Each colony emits ANNOUNCE / PING / PONG / ADVERTISE / BYE signals.
Peers are tracked with TTL-based expiration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import struct
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.config.logging_config import get_logger
from src.colony_types._pydantic_compat import model_dump, model_validate
from src.colony_types.colony_ecosystem import (
    ColonyIdentity,
    RadarDiscoveryMethod,
    RadarSignal,
    RadarSignalType,
)

logger = get_logger(__name__)

MULTICAST_GROUP = "239.255.43.21"
MULTICAST_PORT = 43210
DEFAULT_TTL = 300
CLEANUP_INTERVAL = 60


@dataclass
class RadarConfig:
    identity: ColonyIdentity
    discovery_methods: list[RadarDiscoveryMethod] = field(
        default_factory=lambda: [RadarDiscoveryMethod.LAN_BROADCAST]
    )
    multicast_group: str = MULTICAST_GROUP
    multicast_port: int = MULTICAST_PORT
    static_peers: list[str] = field(default_factory=list)
    rendezvous_url: Optional[str] = None
    announce_interval: int = 120
    ping_timeout: int = 10
    peer_ttl: int = DEFAULT_TTL
    cleanup_interval: int = CLEANUP_INTERVAL
    max_peers: int = 1000


class ColonyRadar:
    """Discovers and tracks remote Blackhornet colonies on the network."""

    def __init__(self, config: RadarConfig, health_monitor: Optional[ColonyHealthMonitor] = None) -> None:
        self._config = config
        self._peers: dict[str, ColonyIdentity] = {}
        self._peer_lock = asyncio.Lock()
        self._running = False
        self._sock: Optional[socket.socket] = None
        self._tasks: list[asyncio.Task] = []
        self._on_peer_join: Optional[Callable[[ColonyIdentity], None]] = None
        self._on_peer_leave: Optional[Callable[[ColonyIdentity], None]] = None
        self._health_monitor = health_monitor

    @property
    def peer_count(self) -> int:
        return len(self._peers)

    def on_peer_join(self, handler: Callable[[ColonyIdentity], None]) -> None:
        self._on_peer_join = handler

    def on_peer_leave(self, handler: Callable[[ColonyIdentity], None]) -> None:
        self._on_peer_leave = handler

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        methods = self._config.discovery_methods
        if RadarDiscoveryMethod.LAN_BROADCAST in methods:
            self._tasks.append(asyncio.create_task(self._lan_listener()))
            self._tasks.append(asyncio.create_task(self._lan_announcer()))

        if RadarDiscoveryMethod.RENDEZVOUS in methods and self._config.rendezvous_url:
            self._tasks.append(asyncio.create_task(self._rendezvous_loop()))

        if RadarDiscoveryMethod.STATIC_PEER in methods:
            await self._connect_static_peers()

        self._tasks.append(asyncio.create_task(self._cleanup_loop()))
        self._tasks.append(asyncio.create_task(self._peer_health_loop()))

        # Wire health monitor if provided
        if self._health_monitor:
            self._health_monitor.wire_radar(self)

        logger.info(
            "radar_started cid=%s methods=%s peers=%d",
            self._config.identity.colony_id,
            [m.value for m in methods],
            len(self._config.static_peers),
        )

    async def stop(self) -> None:
        self._running = False
        await self._send_bye()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        # Unregister from health monitor if provided
        if self._health_monitor:
            self._health_monitor.wire_radar(None)
        logger.info("radar_stopped cid=%s", self._config.identity.colony_id)

    def get_peers(self) -> list[ColonyIdentity]:
        return list(self._peers.values())

    async def get_peers_by_capability(self, capability: str) -> list[ColonyIdentity]:
        async with self._peer_lock:
            return [p for p in self._peers.values() if capability in p.capabilities]

    async def send_signal(self, signal: RadarSignal, target: Optional[str] = None) -> None:
        if self._sock and self._running:
            data = json.dumps(model_dump(signal)).encode()
            if target:
                addr = (target, self._config.multicast_port)
            else:
                addr = (self._config.multicast_group, self._config.multicast_port)
            try:
                self._sock.sendto(data, addr)
            except Exception as e:
                logger.warning("radar_send_error: %s", e)

    async def _setup_socket(self) -> None:
        if self._sock:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", 2))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                        struct.pack("4sl", socket.inet_aton(self._config.multicast_group),
                                    socket.INADDR_ANY))
        sock.setblocking(False)
        sock.bind(("0.0.0.0", self._config.multicast_port))
        self._sock = sock

    async def _lan_listener(self) -> None:
        await self._setup_socket()
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 65535)
                await self._handle_signal(data, addr)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.debug("radar_recv_error: %s", e)
                    await asyncio.sleep(0.1)

    async def _lan_announcer(self) -> None:
        await self._setup_socket()
        while self._running:
            await self._announce()
            await asyncio.sleep(self._config.announce_interval)

    async def _announce(self) -> None:
        signal = RadarSignal(
            signal_type=RadarSignalType.ANNOUNCE,
            sender=self._config.identity,
            payload={
                "methods": [m.value for m in self._config.discovery_methods],
                "peer_count": self.peer_count,
            },
        )
        await self.send_signal(signal)

    async def _send_bye(self) -> None:
        signal = RadarSignal(
            signal_type=RadarSignalType.BYE,
            sender=self._config.identity,
        )
        await self.send_signal(signal)

    async def _handle_signal(self, data: bytes, addr: tuple) -> None:
        try:
            signal = model_validate(RadarSignal, json.loads(data))
        except Exception:
            return

        peer_id = signal.sender.colony_id
        if peer_id == self._config.identity.colony_id:
            return

        signal.sender.last_seen = time.time()

        if signal.signal_type == RadarSignalType.BYE:
            async with self._peer_lock:
                removed = self._peers.pop(peer_id, None)
            if removed and self._on_peer_leave:
                self._on_peer_leave(removed)
            logger.info("peer_bye peer=%s name=%s", peer_id, signal.sender.name)
            return

        if signal.signal_type == RadarSignalType.PING:
            pong = RadarSignal(
                signal_type=RadarSignalType.PONG,
                sender=self._config.identity,
            )
            await self.send_signal(pong, target=addr[0])
            return

        is_new = peer_id not in self._peers
        async with self._peer_lock:
            self._peers[peer_id] = signal.sender

        if is_new:
            logger.info(
                "peer_discovered peer=%s name=%s method=%s addr=%s",
                peer_id,
                signal.sender.name,
                signal.signal_type.value,
                f"{addr[0]}:{addr[1]}",
            )
            if self._on_peer_join:
                self._on_peer_join(signal.sender)

    async def _cleanup_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._config.cleanup_interval)
            async with self._peer_lock:
                expired: list[str] = []
                for pid, peer in list(self._peers.items()):
                    if self._health_monitor:
                        health = self._health_monitor.get_peer_health(pid)
                        if health and health.level == "FAILED":
                            expired.append(pid)
                            del self._peers[pid]
                    else:
                        # Fallback to TTL if no health monitor
                        now = time.time()
                        if now - peer.last_seen > self._config.peer_ttl:
                            expired.append(pid)
                            del self._peers[pid]
                for pid in expired:
                    logger.info("peer_expired peer=%s", pid)

    async def _peer_health_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._config.ping_timeout)
            async with self._peer_lock:
                for peer_id in list(self._peers.keys()):
                    if self._health_monitor:
                        self._health_monitor.record_peer_heartbeat(peer_id)
                    else:
                        # Fallback to PING if no health monitor
                        ping = RadarSignal(
                            signal_type=RadarSignalType.PING,
                            sender=self._config.identity,
                        )
                        await self.send_signal(ping, target=peer_id)

    async def _rendezvous_loop(self) -> None:
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed; rendezvous disabled")
            return
        url = self._config.rendezvous_url.rstrip("/")
        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    payload = model_dump(self._config.identity)
                    async with session.post(f"{url}/colonies", json=payload, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for entry in data.get("colonies", []):
                                cid = entry.get("colony_id", "")
                                if cid and cid != self._config.identity.colony_id:
                                    peer = ColonyIdentity(**entry)
                                    peer.last_seen = time.time()
                                    is_new = cid not in self._peers
                                    async with self._peer_lock:
                                        self._peers[cid] = peer
                                    if is_new and self._on_peer_join:
                                        self._on_peer_join(peer)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("rendezvous_error: %s", e)
            await asyncio.sleep(self._config.announce_interval)

    async def _connect_static_peers(self) -> None:
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed; static peers disabled")
            return
        for peer_url in self._config.static_peers:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{peer_url}/api/v1/radar/identity", timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            peer = ColonyIdentity(**data)
                            peer.last_seen = time.time()
                            async with self._peer_lock:
                                self._peers[peer.colony_id] = peer
                            logger.info("static_peer_connected peer=%s url=%s", peer.colony_id, peer_url)
            except Exception as e:
                logger.warning("static_peer_error url=%s err=%s", peer_url, e)

    def get_stats(self) -> dict[str, Any]:
        stats = {
            "running": self._running,
            "peers": self.peer_count,
            "methods": [m.value for m in self._config.discovery_methods],
            "static_peers": len(self._config.static_peers),
            "rendezvous": bool(self._config.rendezvous_url),
            "announce_interval": self._config.announce_interval,
        }
        if self._health_monitor:
            health_stats = self._health_monitor.get_stats()
            stats["health"] = {
                "detector": health_stats["detector"],
                "orchestrator": health_stats["orchestrator"],
            }
        return stats
