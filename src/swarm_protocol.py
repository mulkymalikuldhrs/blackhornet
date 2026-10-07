#!/usr/bin/env python3
"""
HERMES SWARM PROTOCOL — Universal Agent Discovery & Sync
=========================================================
The nervous system of the immortal agent ecosystem.

Every agent in every repo uses this protocol to:
  1. REGISTER — announce presence to the swarm
  2. DISCOVER — find other agents across repos
  3. SYNC — share state, memory, and learnings
  4. UPGRADE — check for updates, self-upgrade
  5. EXPAND — spawn new agents into new repos
  6. HEAL — detect dead agents, resurrect them

Protocol via: Git (dhaher-labs/agent) + optional WebSocket

Architecture:
  Each agent writes to: agent/sync/swarm/{agent_id}.json
  Each agent reads from: agent/sync/swarm/*.json
  Discovery happens via Git pull/push every N seconds.
"""

import os
import platform
import sys
import json
import time
import hashlib
import logging
import subprocess
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("SwarmProtocol")

# ── Constants ─────────────────────────────────────────────────────────
AGENT_REPO = os.getenv("AGENT_REPO", "https://github.com/dhaher-labs/agent.git")
SWARM_DIR = "sync/swarm"
HEARTBEAT_INTERVAL = int(os.getenv("SWARM_HEARTBEAT", "60"))  # seconds
AGENT_TIMEOUT = int(os.getenv("SWARM_TIMEOUT", "300"))       # 5 min → considered dead
HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
DEFAULT_SWARM_REPO = HERMES_HOME / "agent-sync"

# ── Data Structures ────────────────────────────────────────────────────

@dataclass
class SwarmIdentity:
    """Who am I in the swarm?"""
    agent_id: str
    agent_type: str         # "trading", "research", "orchestrator", "builder", "execution"
    repo: str               # source repo name
    repo_url: str           # full GitHub URL
    version: str
    hostname: str
    pid: int
    started_at: str
    capabilities: List[str] = field(default_factory=list)

@dataclass
class SwarmHeartbeat:
    """I'm alive — here's my status."""
    agent_id: str
    timestamp: str
    status: str             # "RUNNING" | "IDLE" | "UPGRADING" | "ERROR"
    uptime_seconds: int
    tasks_completed: int
    errors_24h: int
    memory_size_bytes: int
    connected_peers: List[str] = field(default_factory=list)
    active_capabilities: List[str] = field(default_factory=list)
    last_decision: Optional[str] = None

@dataclass
class SwarmMessage:
    """Inter-agent communication."""
    from_agent: str
    to_agent: str           # "*" = broadcast
    msg_type: str           # "command", "query", "upgrade", "spawn", "alert"
    priority: str           # "low" | "normal" | "high" | "critical"
    payload: Dict[str, Any]
    timestamp: str
    ttl: int = 3600         # seconds until message expires

# ── Swarm Protocol ─────────────────────────────────────────────────────

class SwarmProtocol:
    """
    Universal agent-to-agent communication protocol.
    Every agent instance uses this to join the swarm.
    """

    def __init__(self,
                 agent_id: str = None,
                 agent_type: str = "trading",
                 repo: str = "blackhornet",
                 repo_url: str = "https://github.com/dhaher-labs/blackhornet",
                 version: str = "4.0.0",
                 swarm_repo_path: str = None):
        
        self.swarm_repo = Path(swarm_repo_path or DEFAULT_SWARM_REPO)
        self.swarm_dir = self.swarm_repo / SWARM_DIR
        self.messages_dir = self.swarm_repo / "sync" / "messages"
        self.identity = SwarmIdentity(
            agent_id=agent_id or self._generate_id(),
            agent_type=agent_type,
            repo=repo,
            repo_url=repo_url,
            version=version,
            hostname=platform.node(),
            pid=os.getpid(),
            started_at=datetime.now(timezone.utc).isoformat(),
            capabilities=self._detect_capabilities()
        )
        self.running = True
        self.start_time = time.time()
        self.tasks_completed = 0
        self.errors_24h = 0
        self._ensure_dirs()
        self._register()

    # ── Identity ──────────────────────────────────────────────────────

    def _generate_id(self) -> str:
        """Generate unique agent ID based on host + repo + hash."""
        seed = f"{platform.node()}-{os.getpid()}-{time.time()}"
        return hashlib.md5(seed.encode()).hexdigest()[:12]

    def _detect_capabilities(self) -> List[str]:
        """Auto-detect what this agent can do."""
        caps = ["swarm_protocol", "self_upgrade", "memory_sync"]
        # Detect based on available tools
        try:
            from src.tools.shared_state import get_shared_state
            caps.append("trading")
            caps.append("risk_management")
        except ImportError:
            pass
        try:
            import yfinance
            caps.append("market_data")
        except ImportError:
            pass
        return caps

    # ── File System ───────────────────────────────────────────────────

    def _ensure_dirs(self):
        self.swarm_dir.mkdir(parents=True, exist_ok=True)
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_repo(self) -> bool:
        """Ensure agent repo is cloned and up to date."""
        if not (self.swarm_repo / ".git").exists():
            try:
                subprocess.run(
                    ["git", "clone", AGENT_REPO, str(self.swarm_repo)],
                    capture_output=True, timeout=60
                )
            except Exception as e:
                logger.warning(f"Swarm repo clone failed: {e}")
                return False
        return True

    def _git_pull(self) -> bool:
        try:
            r = subprocess.run(
                ["git", "-C", str(self.swarm_repo), "pull", "--rebase"],
                capture_output=True, timeout=30
            )
            return r.returncode == 0
        except Exception:
            return False

    def _git_push(self, msg: str = None) -> bool:
        try:
            subprocess.run(
                ["git", "-C", str(self.swarm_repo), "add", "sync/swarm/", "sync/messages/"],
                capture_output=True, timeout=10
            )
            msg = msg or f"[swarm] heartbeat {self.identity.agent_id}"
            subprocess.run(
                ["git", "-C", str(self.swarm_repo), "commit", "-m", msg, "--allow-empty"],
                capture_output=True, timeout=10
            )
            r = subprocess.run(
                ["git", "-C", str(self.swarm_repo), "push"],
                capture_output=True, timeout=30
            )
            return r.returncode == 0
        except Exception as e:
            logger.debug(f"Swarm push failed: {e}")
            return False

    # ── Registration ──────────────────────────────────────────────────

    def _register(self):
        """Write identity to swarm directory."""
        identity_file = self.swarm_dir / f"{self.identity.agent_id}.json"
        data = asdict(self.identity)
        data["last_seen"] = datetime.now(timezone.utc).isoformat()
        identity_file.parent.mkdir(parents=True, exist_ok=True)
        identity_file.write_text(json.dumps(data, indent=2))
        logger.info(f"[SWARM] Registered: {self.identity.agent_id} ({self.identity.agent_type})")

    # ── Heartbeat ─────────────────────────────────────────────────────

    def heartbeat(self) -> SwarmHeartbeat:
        """Generate heartbeat with current status."""
        hb = SwarmHeartbeat(
            agent_id=self.identity.agent_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="RUNNING" if self.running else "SHUTDOWN",
            uptime_seconds=int(time.time() - self.start_time),
            tasks_completed=self.tasks_completed,
            errors_24h=self.errors_24h,
            memory_size_bytes=0,
            connected_peers=self.get_peer_ids(),
            active_capabilities=self.identity.capabilities,
        )
        # Write heartbeat
        hb_file = self.swarm_dir / f"{self.identity.agent_id}_heartbeat.json"
        hb_file.write_text(json.dumps(asdict(hb), indent=2))
        return hb

    # ── Discovery ─────────────────────────────────────────────────────

    def discover_agents(self) -> List[Dict]:
        """Discover all agents in the swarm."""
        agents = []
        if not self.swarm_dir.exists():
            return agents

        for f in sorted(self.swarm_dir.glob("*.json")):
            if f.name.endswith("_heartbeat.json"):
                continue
            try:
                data = json.loads(f.read_text())
                agent_id = data.get("agent_id", f.stem)
                last_seen = data.get("last_seen", "")
                
                # Check if alive (recent heartbeat)
                try:
                    hb_file = self.swarm_dir / f"{agent_id}_heartbeat.json"
                    if hb_file.exists():
                        hb = json.loads(hb_file.read_text())
                        is_alive = (
                            datetime.now(timezone.utc) -
                            datetime.fromisoformat(hb["timestamp"])
                        ).total_seconds() < AGENT_TIMEOUT
                    else:
                        is_alive = False
                except Exception:
                    is_alive = False

                agents.append({
                    **data,
                    "is_alive": is_alive,
                    "agent_file": f.name
                })
            except Exception:
                pass
        return agents

    def get_peer_ids(self) -> List[str]:
        """Get IDs of all other alive agents."""
        peers = self.discover_agents()
        return [
            a["agent_id"] for a in peers
            if a["agent_id"] != self.identity.agent_id and a.get("is_alive")
        ]

    # ── Messaging ─────────────────────────────────────────────────────

    def send_message(self, to_agent: str, msg_type: str, payload: Dict,
                     priority: str = "normal", ttl: int = 3600) -> str:
        """Send message to another agent (or broadcast with '*')."""
        msg = SwarmMessage(
            from_agent=self.identity.agent_id,
            to_agent=to_agent,
            msg_type=msg_type,
            priority=priority,
            payload=payload,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ttl=ttl
        )
        msg_id = hashlib.md5(
            f"{msg.from_agent}{msg.timestamp}{msg.msg_type}".encode()
        ).hexdigest()[:8]
        msg_file = self.messages_dir / f"{msg_id}.json"
        msg_file.write_text(json.dumps(asdict(msg), indent=2))
        return msg_id

    def get_messages(self, for_agent: str = None) -> List[Dict]:
        """Get messages addressed to this agent (or all)."""
        for_agent = for_agent or self.identity.agent_id
        messages = []
        if not self.messages_dir.exists():
            return messages

        now = datetime.now(timezone.utc)
        for f in sorted(self.messages_dir.glob("*.json")):
            try:
                msg = json.loads(f.read_text())
                # Filter: to me OR broadcast
                if msg["to_agent"] not in (for_agent, "*"):
                    continue
                # Check TTL
                msg_time = datetime.fromisoformat(msg["timestamp"])
                if (now - msg_time).total_seconds() > msg.get("ttl", 3600):
                    f.unlink()  # Expired
                    continue
                messages.append(msg)
            except Exception:
                pass
        return messages

    # ── Self-Upgrade ──────────────────────────────────────────────────

    def check_upgrade(self) -> Optional[Dict]:
        """Check if a newer version exists in the source repo."""
        try:
            # Check GitHub releases/tags
            import requests
            api_url = self.identity.repo_url.replace(
                "github.com", "api.github.com/repos"
            ) + "/releases/latest"
            r = requests.get(api_url, timeout=10)
            if r.status_code == 200:
                latest = r.json()["tag_name"].lstrip("v")
                if latest > self.identity.version:
                    return {
                        "current": self.identity.version,
                        "latest": latest,
                        "url": r.json()["html_url"]
                    }
        except Exception as e:
            logger.debug(f"Upgrade check failed: {e}")
        return None

    def self_upgrade(self) -> bool:
        """Pull latest code and restart."""
        upgrade = self.check_upgrade()
        if not upgrade:
            return False

        logger.info(f"[SWARM] Upgrading {self.identity.version} → {upgrade['latest']}")

        # Notify swarm
        self.send_message(
            "*", "upgrade",
            {"action": "upgrading", "from": self.identity.version, "to": upgrade["latest"]},
            priority="high"
        )

        # Pull latest
        repo_dir = Path(os.getenv("REPO_DIR", os.getcwd()))
        subprocess.run(["git", "-C", str(repo_dir), "pull"], capture_output=True, timeout=30)

        # Install deps
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=str(repo_dir), timeout=60
        )

        # Update identity
        self.identity.version = upgrade["latest"]
        self._register()

        # Notify completion
        self.send_message(
            "*", "upgrade",
            {"action": "upgraded", "version": upgrade["latest"]},
            priority="normal"
        )

        return True

    # ── Expansion (Clone & Spawn) ────────────────────────────────────

    def spawn_agent(self, target_repo: str, agent_type: str,
                    branch: str = "main") -> Optional[str]:
        """
        Spawn a new agent by:
        1. Forking/cloning target repo
        2. Setting up the agent
        3. Registering in swarm
        """
        repo_url = f"https://github.com/dhaher-labs/{target_repo}.git"
        spawn_dir = HERMES_HOME / "spawns" / target_repo

        logger.info(f"[SWARM] Spawning agent in {target_repo}...")

        # Clone repo
        if not spawn_dir.exists():
            r = subprocess.run(
                ["git", "clone", repo_url, str(spawn_dir)],
                capture_output=True, timeout=60
            )
            if r.returncode != 0:
                logger.error(f"Failed to clone {target_repo}")
                return None

        # If repo has bootstrap, run it
        bootstrap_script = spawn_dir / "scripts" / "bootstrap.sh"
        if bootstrap_script.exists():
            subprocess.run(["bash", str(bootstrap_script)], timeout=120)

        # Register new agent in swarm
        spawn_id = hashlib.md5(
            f"{target_repo}-{time.time()}".encode()
        ).hexdigest()[:12]
        
        identity = SwarmIdentity(
            agent_id=spawn_id,
            agent_type=agent_type,
            repo=target_repo,
            repo_url=repo_url,
            version="0.1.0",
            hostname=platform.node(),
            pid=0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        id_file = self.swarm_dir / f"{spawn_id}.json"
        id_file.write_text(json.dumps(asdict(identity), indent=2))

        self.send_message(
            "*", "spawn",
            {"new_agent": spawn_id, "repo": target_repo, "type": agent_type},
            priority="high"
        )

        logger.info(f"[SWARM] Spawned {spawn_id} in {target_repo}")
        return spawn_id

    def expand_to_all_repos(self) -> Dict[str, str]:
        """Expand agent swarm to all ecosystem repos."""
        ECOSYSTEM_REPOS = [
            ("Quant-Nanggroe-AI", "research"),
            ("AI-MultiColony-Ecosystem", "orchestrator"),
            ("Vibe-Trading", "trading"),
            ("AutoHedge", "execution"),
        ]
        results = {}
        for repo, a_type in ECOSYSTEM_REPOS:
            agent_id = self.spawn_agent(repo, a_type)
            results[repo] = agent_id or "FAILED"
        return results

    # ── Healing (Resurrect Dead Agents) ──────────────────────────────

    def heal_swarm(self) -> List[str]:
        """Find dead agents and attempt resurrection."""
        resurrected = []
        agents = self.discover_agents()
        
        for agent in agents:
            if agent["agent_id"] == self.identity.agent_id:
                continue
            if not agent.get("is_alive", False):
                logger.info(f"[SWARM] Dead agent detected: {agent['agent_id']} ({agent.get('repo')})")
                
                # Try to resurrect if we know its repo
                repo = agent.get("repo")
                if repo and repo != self.identity.repo:
                    new_id = self.spawn_agent(repo, agent.get("agent_type", "trading"))
                    if new_id:
                        resurrected.append(new_id)
                        self.send_message(
                            "*", "heal",
                            {"dead_agent": agent["agent_id"], "resurrected_as": new_id, "repo": repo},
                            priority="critical"
                        )

        return resurrected

    # ── Main Loop (Immortal) ──────────────────────────────────────────

    def run(self, 
            on_upgrade: Callable = None,
            auto_expand: bool = False,
            auto_heal: bool = True):
        """
        Immortal swarm loop — never stops.
        
        Every cycle:
          1. Pull latest swarm state
          2. Send heartbeat
          3. Process incoming messages
          4. Check for upgrades
          5. Heal dead agents (if auto_heal)
          6. Push state
        """
        logger.info(f"[SWARM] {self.identity.agent_id} joining swarm as {self.identity.agent_type}")
        cycles = 0

        while self.running:
            try:
                cycles += 1

                # Pull
                self._ensure_repo()
                self._git_pull()

                # Heartbeat
                self.heartbeat()

                # Process messages
                messages = self.get_messages()
                for msg in messages:
                    self._handle_message(msg)

                # Check upgrades (every 10 cycles)
                if cycles % 10 == 0:
                    upgrade = self.check_upgrade()
                    if upgrade:
                        logger.info(f"[SWARM] Upgrade available: {upgrade['latest']}")
                        if on_upgrade:
                            on_upgrade(upgrade)
                        else:
                            self.self_upgrade()

                # Auto-heal (every 5 cycles)
                if auto_heal and cycles % 5 == 0:
                    self.heal_swarm()

                # Push
                self._git_push()

                time.sleep(HEARTBEAT_INTERVAL)

            except Exception as e:
                self.errors_24h += 1
                logger.error(f"[SWARM] Cycle error: {e}")
                time.sleep(10)  # Brief pause on error

        # Graceful shutdown
        self.heartbeat()
        self._git_push(f"[swarm] {self.identity.agent_id} shutting down")
        logger.info(f"[SWARM] {self.identity.agent_id} left swarm")

    def _handle_message(self, msg: Dict):
        """Process incoming swarm message."""
        msg_type = msg.get("msg_type", "")
        payload = msg.get("payload", {})

        if msg_type == "command":
            logger.info(f"[SWARM] Command from {msg['from_agent']}: {payload}")
        elif msg_type == "alert":
            logger.warning(f"[SWARM] ALERT from {msg['from_agent']}: {payload}")
        elif msg_type == "upgrade":
            logger.info(f"[SWARM] Upgrade notice: {payload}")
        elif msg_type == "spawn":
            logger.info(f"[SWARM] New agent spawned: {payload}")

    def stop(self):
        """Graceful shutdown."""
        self.running = False


# ── Standalone ────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Swarm Protocol")
    parser.add_argument("--agent-id", help="Agent ID (auto-generated if not set)")
    parser.add_argument("--type", default="trading", help="Agent type")
    parser.add_argument("--repo", default="blackhornet", help="Source repo name")
    parser.add_argument("--expand", action="store_true", help="Auto-expand to all ecosystem repos")
    parser.add_argument("--heal", action="store_true", help="Check and resurrect dead agents")
    parser.add_argument("--list", action="store_true", help="List all agents and exit")
    parser.add_argument("--upgrade", action="store_true", help="Check and perform upgrade")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    swarm = SwarmProtocol(
        agent_id=args.agent_id,
        agent_type=args.type,
        repo=args.repo
    )

    if args.list:
        agents = swarm.discover_agents()
        print(json.dumps(agents, indent=2, default=str))
        return

    if args.heal:
        resurrected = swarm.heal_swarm()
        print(f"Resurrected: {resurrected}")
        return

    if args.expand:
        results = swarm.expand_to_all_repos()
        print(f"Expansion results: {json.dumps(results, indent=2)}")
        return

    if args.upgrade:
        upgrade = swarm.check_upgrade()
        if upgrade:
            print(f"Upgrade available: {upgrade}")
            swarm.self_upgrade()
        else:
            print("Already at latest version")
        return

    # Run immortal loop
    try:
        swarm.run(auto_expand=args.expand, auto_heal=True)
    except KeyboardInterrupt:
        swarm.stop()


if __name__ == "__main__":
    main()
