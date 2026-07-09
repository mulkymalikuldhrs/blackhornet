from __future__ import annotations

import io
import json
import logging
import mimetypes
import os
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")


class _RequestHandler(BaseHTTPRequestHandler):
    api_bridge: Any = None
    static_dir: str = STATIC_DIR

    def _send_json(self, data: Dict, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str) -> None:
        try:
            with open(path, "rb") as f:
                content = f.read()
            mime, _ = mimetypes.guess_type(path)
            self.send_response(200)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._send_json({"error": "File not found"}, 404)

    def _read_body(self) -> Optional[Dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            raw = self.rfile.read(length)
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
        return None

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            body = self._read_body()
            if self.api_bridge:
                resp = self.api_bridge.handle_request("GET", path, body)
                self._send_json(resp.to_dict(), resp.status_code)
            else:
                self._send_json({"error": "API not available"}, 503)
        elif path == "/" or path == "/index.html":
            self._send_file(os.path.join(self.static_dir, "index.html"))
        else:
            file_path = os.path.normpath(os.path.join(self.static_dir, path.lstrip("/")))
            if file_path.startswith(self.static_dir) and os.path.isfile(file_path):
                self._send_file(file_path)
            else:
                self._send_file(os.path.join(self.static_dir, "index.html"))

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            body = self._read_body()
            if self.api_bridge:
                resp = self.api_bridge.handle_request("POST", path, body)
                self._send_json(resp.to_dict(), resp.status_code)
            else:
                self._send_json({"error": "API not available"}, 503)
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug("HTTP: " + fmt, *args)


class WebServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 api_bridge=None, static_dir: str = ""):
        self._host = host
        self._port = port
        self._api = api_bridge
        self._static_dir = static_dir or STATIC_DIR
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def set_api(self, api_bridge) -> None:
        self._api = api_bridge

    def start(self) -> bool:
        try:
            _RequestHandler.api_bridge = self._api
            _RequestHandler.static_dir = self._static_dir
            self._server = HTTPServer((self._host, self._port), _RequestHandler)
            self._thread = threading.Thread(target=self._server.serve_forever,
                                            daemon=True)
            self._thread.start()
            logger.info("WebServer started on %s:%s", self._host, self._port)
            return True
        except (OSError, socket.error) as exc:
            logger.error("WebServer failed to start: %s", exc)
            return False

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
            logger.info("WebServer stopped")

    @property
    def is_running(self) -> bool:
        return self._server is not None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    @staticmethod
    def find_free_port(start: int = 8080, end: int = 8100) -> int:
        for port in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                    return port
                except OSError:
                    continue
        return 0
