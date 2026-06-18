"""SSE (Server-Sent Events) transport for MCP servers.

Implements the MCP SSE transport specification:
- GET /mcp/sse → SSE stream for server-to-client messages
- POST /mcp/messages → Client-to-server JSON-RPC messages
- Heartbeat via SSE comment events (every 30s)
"""

import asyncio
import json
import time
import uuid
from typing import Any, Callable, Optional

from src.config.logging_config import get_logger
from src.mcp.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    parse_request,
    parse_message,
)

logger = get_logger(__name__)

# SSE event types
EVENT_MESSAGE = "message"
EVENT_HEARTBEAT = "heartbeat"
EVENT_ERROR = "error"


class SSETransport:
    """SSE transport for MCP servers.

    Manages SSE connections and routes messages between
    HTTP transport and the MCP server.
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
        max_connections: int = 100,
    ):
        self._heartbeat_interval = heartbeat_interval
        self._max_connections = max_connections

        # Connection tracking
        self._connections: dict[str, asyncio.Queue] = {}
        self._connection_times: dict[str, float] = {}

        # Message handlers
        self._message_handler: Optional[Callable] = None

        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        # Stats
        self._total_messages = 0
        self._total_connections = 0

    def set_message_handler(self, handler: Callable) -> None:
        """Set the handler for incoming messages."""
        self._message_handler = handler

    async def start(self) -> None:
        """Start the SSE transport."""
        if self._running:
            return
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("sse_transport_started")

    async def stop(self) -> None:
        """Stop the SSE transport."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        # Close all connections
        for conn_id in list(self._connections.keys()):
            await self._close_connection(conn_id)
        logger.info("sse_transport_stopped")

    async def handle_sse_request(self, request: Any) -> Any:
        """Handle an SSE GET request.

        Returns an ASGI application for SSE streaming.
        """
        connection_id = str(uuid.uuid4())

        if len(self._connections) >= self._max_connections:
            return {"status": "error", "message": "Max connections reached"}

        # Create a queue for this connection
        queue: asyncio.Queue = asyncio.Queue()
        self._connections[connection_id] = queue
        self._connection_times[connection_id] = time.time()
        self._total_connections += 1

        logger.info("sse_connection_opened conn=%s total=%d", connection_id, len(self._connections))

        return {
            "status": "ok",
            "connection_id": connection_id,
            "queue": queue,
        }

    async def handle_message_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle a POST request to /mcp/messages."""
        try:
            message = parse_message(data)
            if message is None:
                return {"status": "error", "message": "Invalid JSON-RPC message"}

            # Route to handler
            if self._message_handler:
                response = await self._message_handler(message)
                if response:
                    return {"status": "ok", "response": response.model_dump()}
                return {"status": "ok"}
            else:
                return {"status": "error", "message": "No message handler set"}
        except Exception as e:
            logger.error("sse_message_error: %s", e)
            return {"status": "error", "message": str(e)}

    async def send_to_client(self, connection_id: str, message: Any) -> bool:
        """Send a message to a specific client."""
        if connection_id not in self._connections:
            return False

        queue = self._connections[connection_id]
        try:
            await asyncio.wait_for(queue.put(message), timeout=5.0)
            self._total_messages += 1
            return True
        except asyncio.TimeoutError:
            logger.warning("sse_send_timeout conn=%s", connection_id)
            return False

    async def broadcast(self, message: Any) -> int:
        """Broadcast a message to all connected clients."""
        sent = 0
        for conn_id in list(self._connections.keys()):
            if await self.send_to_client(conn_id, message):
                sent += 1
        return sent

    async def _close_connection(self, connection_id: str) -> None:
        """Close a specific connection."""
        if connection_id in self._connections:
            queue = self._connections.pop(connection_id)
            self._connection_times.pop(connection_id, None)
            # Send a sentinel value to signal the SSE stream to close
            try:
                await queue.put(None)
            except Exception:
                pass
            logger.info("sse_connection_closed conn=%s", connection_id)

    async def _heartbeat_loop(self) -> None:
        """Send heartbeat events to all connections."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                heartbeat = {"event": EVENT_HEARTBEAT, "data": "ping"}
                for conn_id in list(self._connections.keys()):
                    await self.send_to_client(conn_id, heartbeat)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("sse_heartbeat_error: %s", e)

    def get_stats(self) -> dict[str, Any]:
        """Get transport statistics."""
        return {
            "running": self._running,
            "active_connections": len(self._connections),
            "total_connections": self._total_connections,
            "total_messages": self._total_messages,
            "heartbeat_interval": self._heartbeat_interval,
        }