#!/usr/bin/env python3
"""
BLACKHORNET — Agent Swarm Memory Bridge
============================================
Real-time shared memory sync between blackhornet agents
and the dhaher-labs/agent swarm repository.

Architecture:
  blackhornet tools → SharedState (SQLite) → MemoryBridge → agent repo (Git)
                                                                    ↕
  Hermes Agent (Nous) ← hermes memory ← agent repo ← other bot clones

Features:
  - Auto-sync agent state to Git repo
  - Bidirectional: pull external agent updates
  - Immortal: auto-retry on failure, never stops
  - State files per bot (devbot, traderbot, researchbot, etc.)
  - Conflict resolution: Git merge with timestamp arbitration
"""

import os
import sys
import json
import time
import sqlite3
import logging
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("MemoryBridge")

# ── Configuration ──────────────────────────────────────────────────────
AGENT_REPO_URL = os.getenv(
    "AGENT_REPO_URL",
    "https://github.com/dhaher-labs/agent.git"
)
SYNC_INTERVAL = int(os.getenv("MEMORY_SYNC_INTERVAL", "60"))  # seconds
BOT_NAME = os.getenv("BOT_NAME", "traderbot")
HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))

# ── State schema ───────────────────────────────────────────────────────
STATE_SCHEMA = {
    "bot_id": BOT_NAME,
    "agent": "blackhornet",
    "version": "4.0.0",
    "status": "RUNNING",  # RUNNING | IDLE | ERROR | SHUTDOWN
    "uptime_seconds": 0,
    "last_sync": None,
    "decisions_today": 0,
    "trades_today": 0,
    "pnl_daily_pct": 0.0,
    "risk_limit_status": "OK",
    "active_strategies": [],
    "market_regime": "UNKNOWN",
    "current_positions": [],
    "errors_24h": 0,
    "restarts_24h": 0,
    "memory_notes": [],
    "connected_agents": [],
    "timestamp": None,
}


class MemoryBridge:
    """Shared memory bridge: blackhornet ↔ Agent Swarm Repo"""

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path or HERMES_HOME / "agent-sync")
        self.state_file = self.repo_path / "sync" / "logs" / f"{BOT_NAME}_state.json"
        self.running = True
        self.state = dict(STATE_SCHEMA)
        self._load_state()
        self._ensure_repo()

    # ── Repository management ──────────────────────────────────────────

    def _ensure_repo(self) -> None:
        """Clone agent repo if not present, otherwise pull latest."""
        try:
            if not (self.repo_path / ".git").exists():
                logger.info(f"Cloning agent repo: {AGENT_REPO_URL}")
                subprocess.run(
                    ["git", "clone", AGENT_REPO_URL, str(self.repo_path)],
                    capture_output=True, timeout=60
                )
            self._git_pull()
        except Exception as e:
            logger.warning(f"Repo init failed (will retry): {e}")

    def _git_pull(self) -> bool:
        """Pull latest from agent repo. Returns True on success."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "pull", "--rebase"],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    def _git_push(self) -> bool:
        """Commit and push state to agent repo."""
        try:
            # Stage
            subprocess.run(
                ["git", "-C", str(self.repo_path), "add", "."],
                capture_output=True, timeout=10
            )
            # Commit (allow empty — no error if no changes)
            timestamp = datetime.now(timezone.utc).isoformat()
            subprocess.run(
                ["git", "-C", str(self.repo_path), "commit",
                 "-m", f"[{BOT_NAME}] sync {timestamp}", "--allow-empty"],
                capture_output=True, timeout=10
            )
            # Push
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "push"],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Git push failed: {e}")
            return False

    # ── State management ───────────────────────────────────────────────

    def _load_state(self) -> None:
        """Load existing state from agent repo or local file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if self.state_file.exists():
            try:
                loaded = json.loads(self.state_file.read_text())
                self.state.update(loaded)
            except json.JSONDecodeError:
                logger.warning("Corrupt state file, starting fresh")

    def _save_state(self) -> None:
        """Persist state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.state_file.write_text(json.dumps(self.state, indent=2, default=str))

    def update(self, **kwargs) -> None:
        """Update state fields."""
        self.state.update(kwargs)
        self.state["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

    def log_memory(self, note: str) -> None:
        """Add a memory note to shared state."""
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "bot": BOT_NAME,
            "note": note
        }
        self.state.setdefault("memory_notes", []).append(entry)
        # Keep last 100 notes
        self.state["memory_notes"] = self.state["memory_notes"][-100:]
        self._save_state()

    def report_error(self, error: str) -> None:
        """Log an error to shared state."""
        self.state["errors_24h"] = self.state.get("errors_24h", 0) + 1
        self.log_memory(f"ERROR: {error}")
        self._save_state()

    def connect_shared_state(self, db_path: str) -> None:
        """
        Connect to blackhornet SharedState (SQLite) and mirror
        trading data into the memory bridge.
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Pull PnL data
            cursor.execute("SELECT SUM(pnl) FROM trades WHERE date = date('now')")
            row = cursor.fetchone()
            if row and row[0]:
                self.state["pnl_daily_pct"] = round(row[0], 4)

            # Pull trade count
            cursor.execute("SELECT COUNT(*) FROM trades WHERE date = date('now')")
            row = cursor.fetchone()
            if row and row[0]:
                self.state["trades_today"] = row[0]

            # Pull positions
            cursor.execute("SELECT symbol, direction, lot_size FROM positions WHERE status='open'")
            self.state["current_positions"] = [
                {"symbol": r[0], "direction": r[1], "size": r[2]}
                for r in cursor.fetchall()
            ]

            conn.close()
            self._save_state()
        except Exception as e:
            logger.warning(f"SharedState sync failed: {e}")

    # ── Peer discovery ─────────────────────────────────────────────────

    def discover_agents(self) -> List[Dict]:
        """Read other agent state files from the repo."""
        agents = []
        log_dir = self.repo_path / "sync" / "logs"
        if log_dir.exists():
            for f in log_dir.glob("*_state.json"):
                try:
                    data = json.loads(f.read_text())
                    agents.append({
                        "bot_id": data.get("bot_id", f.stem.replace("_state", "")),
                        "status": data.get("status", "UNKNOWN"),
                        "last_sync": data.get("timestamp"),
                    })
                except Exception:
                    pass
        self.state["connected_agents"] = [a["bot_id"] for a in agents]
        return agents

    # ── Sync loop (immortal) ───────────────────────────────────────────

    def sync_once(self) -> bool:
        """Single sync cycle: pull → update → push. Returns True if pushed."""
        pulled = self._git_pull()
        if pulled:
            self._load_state()  # Reload in case external agents updated
        self._save_state()
        pushed = self._git_push()
        return pushed

    def run_sync_loop(self) -> None:
        """Immortal sync loop — never stops, auto-retry."""
        logger.info(f"[{BOT_NAME}] Memory bridge started (interval={SYNC_INTERVAL}s)")
        start_time = time.time()
        failures = 0

        while self.running:
            try:
                uptime = int(time.time() - start_time)
                self.state["uptime_seconds"] = uptime
                self.state["restarts_24h"] = failures

                self.discover_agents()
                success = self.sync_once()

                if success:
                    failures = 0
                    logger.debug(f"[{BOT_NAME}] Sync OK (uptime={uptime}s)")
                else:
                    failures += 1
                    logger.warning(f"[{BOT_NAME}] Sync failed #{failures}")

                time.sleep(SYNC_INTERVAL)

            except Exception as e:
                failures += 1
                logger.error(f"[{BOT_NAME}] Sync error: {e}")
                time.sleep(min(SYNC_INTERVAL * failures, 300))

        logger.info(f"[{BOT_NAME}] Memory bridge stopped")

    def stop(self) -> None:
        """Graceful shutdown."""
        self.running = False
        self.state["status"] = "SHUTDOWN"
        self._save_state()
        self.sync_once()


# ── Standalone entrypoint ──────────────────────────────────────────────

def main():
    """Run memory bridge as standalone daemon."""
    import argparse
    parser = argparse.ArgumentParser(description="blackhornet Memory Bridge")
    parser.add_argument("--bot", default=None, help="Bot name for state file")
    parser.add_argument("--interval", type=int, default=None, help="Sync interval in seconds")
    parser.add_argument("--once", action="store_true", help="Sync once and exit")
    parser.add_argument("--db", help="Path to blackhornet SQLite DB for state mirroring")
    args = parser.parse_args()

    if args.bot is not None:
        BOT_NAME = args.bot
    if args.interval is not None:
        SYNC_INTERVAL = args.interval

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    bridge = MemoryBridge()

    if args.db:
        bridge.connect_shared_state(args.db)

    if args.once:
        bridge.sync_once()
    else:
        try:
            bridge.run_sync_loop()
        except KeyboardInterrupt:
            bridge.stop()


if __name__ == "__main__":
    main()
