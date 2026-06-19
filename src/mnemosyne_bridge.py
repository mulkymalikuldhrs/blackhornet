#!/usr/bin/env python3
"""
MNEMOSYNE BRIDGE — Swarm Knowledge Memory
==========================================
Integrates Mnemosyne as the persistent knowledge layer for the entire agent swarm.

Mnemosyne provides:
  - Semantic memory with RAG (Retrieval Augmented Generation)
  - Knowledge graph connecting ideas automatically
  - 500+ free LLM models via Puter.js
  - MCP server for AI assistant integration
  - Multi-cloud storage with file ingestion
  - Full-text search + vector embeddings

This bridge:
  - Pushes agent learnings → Mnemosyne knowledge base
  - Queries Mnemosyne for relevant context before decisions
  - Syncs swarm memory to Mnemosyne's knowledge graph
  - Exposes Mnemosyne MCP to all agents
  - Agents "remember" across sessions and clones
"""

import os
import sys
import json
import time
import logging
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("MnemosyneBridge")

# ── Configuration ──────────────────────────────────────────────────────
MNEMOSYNE_DIR = Path(os.getenv("MNEMOSYNE_DIR",
    Path(__file__).parent.parent.parent / "mnemosyne"))
MNEMOSYNE_PORT = int(os.getenv("MNEMOSYNE_PORT", "3001"))
MNEMOSYNE_HOST = os.getenv("MNEMOSYNE_HOST", "localhost")
MNEMOSYNE_URL = os.getenv("MNEMOSYNE_URL",
    f"http://{MNEMOSYNE_HOST}:{MNEMOSYNE_PORT}")
MNEMOSYNE_MCP_PORT = int(os.getenv("MNEMOSYNE_MCP_PORT", "3002"))


class MnemosyneBridge:
    """
    Swarm-wide knowledge memory.
    Every agent reads from and writes to Mnemosyne.
    """

    def __init__(self):
        self.available = False
        self.mnemosyne_process = None
        self.knowledge_graph: Dict[str, List] = {}
        self.stats = {
            "notes_stored": 0,
            "queries_made": 0,
            "knowledge_edges": 0,
        }
        self._ensure_mnemosyne()

    # ── Mnemosyne Management ──────────────────────────────────────────

    def _ensure_mnemosyne(self) -> bool:
        """Start Mnemosyne if available, or discover remote instance."""
        if self._check_health():
            self.available = True
            logger.info(f"Mnemosyne found at {MNEMOSYNE_URL}")
            return True

        if MNEMOSYNE_DIR.exists():
            logger.info("Starting Mnemosyne locally...")
            try:
                # Check for Node.js/bun
                runtime = "node"
                if subprocess.run(["which", "bun"], capture_output=True).returncode == 0:
                    runtime = "bun"

                # Check if already built
                if not (MNEMOSYNE_DIR / ".next").exists():
                    logger.info("Building Mnemosyne...")
                    subprocess.run(
                        ["npm", "install"],
                        cwd=str(MNEMOSYNE_DIR),
                        capture_output=True, timeout=120
                    )
                    subprocess.run(
                        ["npm", "run", "build"],
                        cwd=str(MNEMOSYNE_DIR),
                        capture_output=True, timeout=120
                    )

                self.mnemosyne_process = subprocess.Popen(
                    ["npm", "run", "start"],
                    cwd=str(MNEMOSYNE_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env={**os.environ, "PORT": str(MNEMOSYNE_PORT)}
                )

                for _ in range(15):
                    time.sleep(1)
                    if self._check_health():
                        self.available = True
                        logger.info(f"Mnemosyne started on port {MNEMOSYNE_PORT}")
                        return True

            except Exception as e:
                logger.warning(f"Could not start Mnemosyne: {e}")

        logger.info("Mnemosyne unavailable — using file-based memory fallback")
        return False

    def _check_health(self) -> bool:
        try:
            req = Request(f"{MNEMOSYNE_URL}/api/health", 
                         headers={"User-Agent": "HermesQuantOS/4.0"})
            resp = urlopen(req, timeout=3)
            return resp.status == 200
        except Exception:
            return False

    def _api_call(self, method: str, path: str, body: Dict = None) -> Optional[Dict]:
        """Call Mnemosyne API."""
        if not self.available:
            return None
        try:
            url = f"{MNEMOSYNE_URL}{path}"
            data = json.dumps(body).encode() if body else None
            req = Request(url, data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "HermesQuantOS/4.0"
                },
                method=method
            )
            resp = urlopen(req, timeout=30)
            return json.loads(resp.read())
        except Exception as e:
            logger.debug(f"Mnemosyne API {method} {path} failed: {e}")
            return None

    # ── Knowledge Operations ──────────────────────────────────────────

    def store_knowledge(self, title: str, content: str, 
                        tags: List[str] = None,
                        source: str = "hermes_quant_os",
                        agent_id: str = None) -> Optional[str]:
        """
        Store knowledge in Mnemosyne.
        This becomes part of the swarm's permanent memory.
        """
        self.stats["notes_stored"] += 1

        note = {
            "title": title,
            "content": content,
            "tags": tags or [],
            "source": source,
            "agent_id": agent_id or "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Try Mnemosyne API
        result = self._api_call("POST", "/api/notes", note)
        if result:
            note_id = result.get("id") or hashlib.md5(
                f"{title}{content}".encode()
            ).hexdigest()[:12]
            logger.debug(f"Knowledge stored: {note_id}")
            return note_id

        # Fallback: store locally
        return self._store_local(note)

    def _store_local(self, note: Dict) -> str:
        """Local fallback storage."""
        memory_dir = Path(os.getenv("HERMES_HOME", 
            Path.home() / ".hermes")) / "knowledge"
        memory_dir.mkdir(parents=True, exist_ok=True)

        note_id = hashlib.md5(
            f"{note['title']}{note['timestamp']}".encode()
        ).hexdigest()[:12]

        (memory_dir / f"{note_id}.json").write_text(
            json.dumps(note, indent=2))
        return note_id

    # ── Knowledge Retrieval ────────────────────────────────────────────

    def query_knowledge(self, query: str, 
                        limit: int = 5) -> List[Dict]:
        """
        Search swarm knowledge for relevant context.
        Uses Mnemosyne's RAG if available.
        """
        self.stats["queries_made"] += 1

        # Try Mnemosyne search
        result = self._api_call("GET", 
            f"/api/search?q={query}&limit={limit}")
        if result:
            return result.get("results", [])

        # Fallback: local search
        return self._search_local(query, limit)

    def _search_local(self, query: str, limit: int) -> List[Dict]:
        """Local keyword search fallback."""
        memory_dir = Path(os.getenv("HERMES_HOME",
            Path.home() / ".hermes")) / "knowledge"
        if not memory_dir.exists():
            return []

        results = []
        query_lower = query.lower()
        for f in memory_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                content = data.get("content", "") + data.get("title", "")
                if query_lower in content.lower():
                    results.append({
                        "id": f.stem,
                        "title": data["title"],
                        "snippet": data["content"][:200],
                        "source": data.get("source", "local"),
                        "timestamp": data.get("timestamp", ""),
                    })
            except Exception:
                pass

        return sorted(results, 
            key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    # ── Swarm Knowledge Sync ──────────────────────────────────────────

    def sync_swarm_to_mnemosyne(self, swarm_state: Dict):
        """Push swarm state into Mnemosyne knowledge graph."""
        # Store agent discoveries
        agents = swarm_state.get("agents", [])
        for agent in agents:
            self.store_knowledge(
                title=f"Agent: {agent.get('agent_id', '?')}",
                content=json.dumps(agent, default=str),
                tags=["swarm", "agent", agent.get("agent_type", "unknown")],
                source="swarm_protocol"
            )

        # Store ecosystem health
        health = swarm_state.get("health", {})
        if health:
            self.store_knowledge(
                title=f"Ecosystem Health {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                content=json.dumps(health, default=str),
                tags=["swarm", "health", "ecosystem"],
                source="immortal_daemon"
            )

    def store_trade_knowledge(self, symbol: str, decision: str,
                               reasoning: str, outcome: str = None):
        """Store trading knowledge for future learning."""
        tags = ["trading", "decision", symbol]
        if outcome:
            tags.append(f"outcome_{outcome}")

        self.store_knowledge(
            title=f"Trade: {symbol} — {decision}",
            content=f"## Decision\n{decision}\n\n## Reasoning\n{reasoning}\n\n"
                    f"## Outcome\n{outcome or 'pending'}",
            tags=tags,
            source="hermes_quant_os"
        )

    def get_trade_context(self, symbol: str) -> List[Dict]:
        """Retrieve past trading knowledge for a symbol."""
        return self.query_knowledge(f"{symbol} trade", limit=10)

    def store_learning(self, topic: str, insight: str, confidence: float = 0.5):
        """Store a learned insight into the knowledge graph."""
        self.store_knowledge(
            title=f"Learning: {topic}",
            content=f"## Insight\n{insight}\n\n## Confidence\n{confidence:.0%}",
            tags=["learning", "insight", topic.replace(" ", "_").lower()],
            source="agent_learning"
        )

    # ── MCP Bridge ─────────────────────────────────────────────────────

    def get_mcp_tools(self) -> List[Dict]:
        """Get available Mnemosyne MCP tools for agents."""
        if not self.available:
            return []

        result = self._api_call("GET", "/api/mcp/tools")
        return result.get("tools", []) if result else []

    def call_mcp_tool(self, tool_name: str, args: Dict) -> Optional[Dict]:
        """Call a Mnemosyne MCP tool."""
        return self._api_call("POST", "/api/mcp/call", {
            "tool": tool_name,
            "arguments": args,
        })

    # ── Status ─────────────────────────────────────────────────────────

    def status(self) -> Dict:
        return {
            "available": self.available,
            "url": MNEMOSYNE_URL if self.available else None,
            "mcp_url": f"http://{MNEMOSYNE_HOST}:{MNEMOSYNE_MCP_PORT}" if self.available else None,
            "stats": self.stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def stop(self):
        if self.mnemosyne_process:
            self.mnemosyne_process.terminate()
            logger.info("Mnemosyne stopped")


# ── Standalone ────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mnemosyne Bridge — Swarm Knowledge Memory")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--store", nargs=2, metavar=("TITLE", "CONTENT"), help="Store knowledge")
    parser.add_argument("--search", help="Search knowledge")
    parser.add_argument("--sync-swarm", action="store_true", help="Sync swarm state to Mnemosyne")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    bridge = MnemosyneBridge()

    if args.status:
        print(json.dumps(bridge.status(), indent=2, default=str))
    elif args.store:
        note_id = bridge.store_knowledge(args.store[0], args.store[1])
        print(f"Stored: {note_id}")
    elif args.search:
        results = bridge.query_knowledge(args.search)
        print(json.dumps(results, indent=2))
    elif args.sync_swarm:
        from swarm_protocol import SwarmProtocol
        s = SwarmProtocol()
        bridge.sync_swarm_to_mnemosyne({
            "agents": s.discover_agents(),
            "health": {"timestamp": datetime.now(timezone.utc).isoformat()}
        })
        print("Swarm synced to Mnemosyne")

    bridge.stop()


if __name__ == "__main__":
    main()
