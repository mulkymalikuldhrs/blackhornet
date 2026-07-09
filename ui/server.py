"""BlackHornet Living World — zero-dep HTTP + WebSocket server.
No external dependencies needed — uses built-in http.server + asyncio."""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import time
from pathlib import Path

HERE = Path(__file__).parent
WS_CLIENTS: set = set()

try:
    import subprocess
    import sys
    has_uvicorn = False
except Exception:
    has_uvicorn = False


async def handle_http(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        data = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
    except asyncio.TimeoutError:
        writer.close()
        return

    request_line = data.split(b"\r\n")[0].decode("utf-8", errors="replace")
    method, path, *_ = request_line.split() + ["", ""]
    path = path.rstrip("/") or "/index.html"

    resp_headers = b"HTTP/1.1 200 OK\r\nServer: BH-Omega/5.0\r\n"

    if path == "/api/status":
        body = json.dumps({
            "name": "BlackHornet Living World",
            "version": "5.0.0",
            "status": "alive",
            "time": time.time(),
            "players": len(WS_CLIENTS),
        }).encode()
        resp_headers += b"Content-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n"

    elif path == "/api/projects":
        try:
            p = os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs")
            with open(os.path.join(p, "data/ecosystem-memory/project-scores.json")) as f:
                body = json.dumps(json.load(f)).encode()
        except Exception:
            body = b'{"error":"no scores"}'
        resp_headers += b"Content-Type: application/json\r\n"

    else:
        fp = HERE / path.lstrip("/")
        if not fp.exists() or not fp.is_file():
            fp = HERE / "index.html"
        body = fp.read_bytes()
        mime, _ = mimetypes.guess_type(str(fp))
        if mime:
            resp_headers += f"Content-Type: {mime}\r\n".encode()

    resp_headers += f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
    writer.write(resp_headers + body)
    await writer.drain()
    writer.close()


async def main():
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = await asyncio.start_server(handle_http, host, port)
    print(f"BH Ω Living World: http://{host}:{port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
