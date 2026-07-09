"""Cross-Colony Mesh EventBus — extends EventBus for inter-colony messaging.

Bridges the local EventBus to remote colonies discovered by ColonyRadar.
Messages are delivered via:
1. Direct HTTP (for known peers with public endpoints)
2. Relay through rendezvous server
3. LAN multicast (for local network peers)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Optional

from src.config.logging_config import get_logger
from src.core.event_bus import EventBus
from src.colony_types._pydantic_compat import model_dump
from src.colony_types.colony_ecosystem import ColonyIdentity, MeshMessage

logger = get_logger(__name__)


class MeshBus:  # noqa: D101
    """Extends EventBus for cross-colony messaging."""

    def __init__(
        self,
        local_bus: EventBus,
        identity: ColonyIdentity,
        http_port: int = 0,
        health_monitor: Optional[ColonyHealthMonitor] = None,
    ) -> None:
        self._local_bus = local_bus
        self._identity = identity
        self._http_port = http_port
        self._running = False
        self._health_monitor = health_monitor

        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._peers: dict[str, ColonyIdentity] = {}
        self._outbox: list[MeshMessage] = []
        self._tasks: list[asyncio.Task] = []

        self._delivered: set[str] = set()
        self._pending_responses: dict[str, asyncio.Future] = {}

        self._message_count = 0
        self._relay_count = 0

    @property
    def peer_count(self) -> int:
        return len(self._peers)

    def on_peer_join(self, handler: Callable[[ColonyIdentity], None]) -> None:
        """Register a handler for when a peer joins."""
        self._on_peer_join = handler

    def on_peer_leave(self, handler: Callable[[ColonyIdentity], None]) -> None:
        """Register a handler for when a peer leaves."""
        self._on_peer_leave = handler

    async def start(self) -> None:
        """Start the mesh bus."""
        await super().start()  # Call parent start
        if self._running:
            return
        self._running = True
        self._tasks.append(asyncio.create_task(self._outbox_flusher()))
        # Wire health monitor if provided
        if self._health_monitor:
            self._health_monitor.wire_mesh(self)
        logger.info("mesh_started cid=%s", self._identity.colony_id)

    async def stop(self) -> None:
        """Stop the mesh bus."""
        await super().stop()  # Call parent stop
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        # Unregister from health monitor if provided
        if self._health_monitor:
            self._health_monitor.wire_mesh(None)
        logger.info("mesh_stopped cid=%s", self._identity.colony_id)

    def get_peers(self) -> list[ColonyIdentity]:
        return list(self._peers.values())

    async def get_peers_by_capability(self, capability: str) -> list[ColonyIdentity]:
        async with self._peer_lock:
            return [p for p in self._peers.values() if capability in p.capabilities]

    async def send_signal(self, signal: MeshMessage, target: Optional[str] = None) -> None:
        if self._running:
            data = json.dumps(model_dump(signal)).encode()
            if target:
                addr = (target, self._http_port)
            else:
                addr = ("239.255.43.21", 43210)
            try:
                # Use asyncio to send UDP multicast
                loop = asyncio.get_event_loop()
                if not hasattr(self, "_sock"):
                    self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", 2))
                self._sock.sendto(data, addr)
            except Exception as e:
                logger.warning("mesh_send_error: %s", e)

    async def _outbox_flusher(self) -> None:
        while self._running:
            if self._outbox:
                batch = self._outbox[:50]
                self._outbox = self._outbox[50:]
                await asyncio.gather(
                    *[self._send_http(msg) for msg in batch],
                    return_exceptions=True,
                )
            await asyncio.sleep(0.5)

    async def _send_http(self, message: MeshMessage) -> None:
        target = message.target_colony
        if not target or target not in self._peers:
            return

        peer = self._peers[target]
        endpoint = peer.public_endpoint or f"http://{peer.host}:{peer.port}"

        if self._health_monitor:
            success = await self._health_monitor.monitored_deliver(message, endpoint)
            if not success:
                logger.debug("mesh_delivery_failed target=%s circuit_breaker_open", target)
            return

        # Fallback to direct HTTP if no health monitor
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"{endpoint}/api/v1/mesh/message"
                async with session.post(
                    url,
                    json=model_dump(message),
                    timeout=10,
                ) as resp:
                    if resp.status != 200:
                        logger.debug("mesh_delivery_failed target=%s status=%d", target, resp.status)
        except ImportError:
            logger.debug("aiohttp not available for mesh HTTP")
        except Exception as e:
            logger.debug("mesh_send_error target=%s err=%s", target, e)

    async def receive_message(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            from src.colony_types._pydantic_compat import model_validate
            message = model_validate(MeshMessage, data)
        except Exception as e:
            return {"status": "error", "error": str(e)}

        if message.message_id in self._delivered:
            return {"status": "duplicate", "message_id": message.message_id}

        self._delivered.add(message.message_id)
        self._message_count += 1

        await self._dispatch_local(message)

        if message.hop_count < message.max_hops and not message.target_colony:
            await self._dispatch_remote(message)

        if message.correlation_id and message.correlation_id in self._pending_responses:
            future = self._pending_responses[message.correlation_id]
            if not future.done():
                future.set_result(message.payload)

        return {"status": "delivered", "message_id": message.message_id}

    async def _http_listener(self) -> None:
        try:
            import aiohttp
            from aiohttp import web
        except ImportError:
            logger.warning("aiohttp not installed; mesh HTTP listener disabled")
            return

        app = web.Application()

        async def handle_mesh(request: web.Request) -> web.Response:
            data = await request.json()
            result = await self.receive_message(data)
            return web.json_response(result)

        async def handle_identity(request: web.Request) -> web.Response:
            return web.json_response(model_dump(self._identity))

        app.router.add_post("/api/v1/mesh/message", handle_mesh)
        app.router.add_get("/api/v1/mesh/identity", handle_identity)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self._http_port)
        await site.start()
        logger.info("mesh_http_listener_started port=%d", self._http_port)

        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            await runner.cleanup()

    def get_stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "peers": self.peer_count,
            "messages_sent": self._message_count,
            "relays": self._relay_count,
            "outbox_pending": len(self._outbox),
            "subscribers": {t: len(h) for t, h in self._subscribers.items()},
        }
