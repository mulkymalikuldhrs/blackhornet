"""GraphifyAPI — REST API server exposing GraphStore & GraphifyPipeline externally.

Usage:
    from src.graphify_api import GraphifyAPIServer
    server = GraphifyAPIServer(port=9090)
    server.start()
"""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

from src.graph.graph_store import GraphStore
from src.graph.graphify_pipeline import GraphifyPipeline

logger = logging.getLogger(__name__)


class GraphifyAPIHandler(BaseHTTPRequestHandler):

    pipeline: Optional[GraphifyPipeline] = None

    def log_message(self, fmt, *args):
        logger.debug("GraphifyAPI: %s", fmt % args)

    def _send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, msg: str, status: int = 400):
        self._send_json({"error": msg}, status)

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        pipe = self.pipeline
        if not pipe:
            return self._send_error("Pipeline not initialized", 500)

        path = self.path.rstrip("/")

        if path == "/graph/stats":
            self._send_json(pipe.stats())

        elif path == "/graph/export":
            self._send_json(pipe.export_json())

        elif path.startswith("/graph/search/"):
            query = self.path.split("/graph/search/", 1)[-1]
            results = pipe.search(query)
            self._send_json({"query": query, "results": results, "count": len(results)})

        elif path.startswith("/graph/node/"):
            node_id = self.path.split("/graph/node/", 1)[-1]
            try:
                nid = int(node_id)
            except ValueError:
                return self._send_error("Invalid node ID", 400)
            node = pipe.graph.get_node(nid)
            if not node:
                return self._send_error("Node not found", 404)
            neighbors = pipe.graph.get_neighbors(nid)
            self._send_json({"node": node, "neighbors": neighbors})

        elif path == "/graph/nodes":
            node_type = self.headers.get("X-Node-Type", "")
            nodes = pipe.graph.get_nodes(node_type=node_type)
            self._send_json({"nodes": [{**n.__dict__} for n in nodes[:500]], "total": len(nodes)})

        elif path == "/graph/edges":
            relation = self.headers.get("X-Relation", "")
            edges = pipe.graph.list_edges(relation=relation)
            self._send_json({"edges": [{**r.__dict__} for r in edges[:500]], "total": len(edges)})

        elif path == "/graph/events":
            event_type = self.headers.get("X-Event-Type", "")
            events = pipe.get_events(event_type=event_type or None)
            self._send_json({"events": events, "count": len(events)})

        elif path == "/health":
            self._send_json({"status": "ok", "service": "graphify"})

        else:
            self._send_error(f"Unknown path: {path}", 404)

    def do_POST(self):
        pipe = self.pipeline
        if not pipe:
            return self._send_error("Pipeline not initialized", 500)

        path = self.path.rstrip("/")

        if path == "/graph/emit":
            body = self._read_body()
            event_type = body.get("event_type", "")
            source = body.get("source", "api")
            data = body.get("data", {})
            if not event_type:
                return self._send_error("event_type required", 400)
            pipe.emit(event_type, source=source, data=data)
            self._send_json({"status": "emitted", "event_type": event_type})

        elif path == "/graph/sync":
            body = self._read_body()
            pipe.emit("agent_state", source=body.get("agent", "api"), data=body)
            self._send_json({"status": "synced"})

        elif path == "/graph/query":
            body = self._read_body()
            query = body.get("query", "")
            if not query:
                return self._send_error("query required", 400)
            results = pipe.search(query, limit=body.get("limit", 50))
            self._send_json({"query": query, "results": results, "count": len(results)})

        elif path == "/graph/node":
            body = self._read_body()
            label = body.get("label", "")
            node_type = body.get("node_type", "external")
            if not label:
                return self._send_error("label required", 400)
            node_id = pipe.graph.find_or_create(label=label, node_type=node_type)
            self._send_json({"node_id": node_id, "label": label})

        elif path == "/graph/edge":
            body = self._read_body()
            source = body.get("source", "")
            target = body.get("target", "")
            relation = body.get("relation", "related_to")
            if not source or not target:
                return self._send_error("source and target required", 400)
            s_id = pipe.graph.find_or_create(label=source, node_type=body.get("source_type", "external"))
            t_id = pipe.graph.find_or_create(label=target, node_type=body.get("target_type", "external"))
            pipe.graph.add_edge(s_id, t_id, relation=relation)
            self._send_json({"status": "edge_created", "source_id": s_id, "target_id": t_id})

        else:
            self._send_error(f"Unknown path: {path}", 404)


class GraphifyAPIServer:
    """HTTP server exposing GraphStore & GraphifyPipeline via REST API."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9090,
        pipeline: Optional[GraphifyPipeline] = None,
    ):
        self.host = host
        self.port = port
        self.pipeline = pipeline or GraphifyPipeline()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, block: bool = False):
        GraphifyAPIHandler.pipeline = self.pipeline
        self._server = HTTPServer((self.host, self.port), GraphifyAPIHandler)
        logger.info("GraphifyAPI running on http://%s:%s", self.host, self.port)

        if block:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            logger.info("GraphifyAPI stopped")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
