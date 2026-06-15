#!/usr/bin/env python3
"""
HERMES IMMORTAL DAEMON — Self-Upgrade & Auto-Heal
===================================================
The eternal guardian that keeps the entire ecosystem alive.

Features:
  - Auto-check for upgrades every N minutes
  - Self-upgrade without downtime (staged restart)
  - Health monitoring across all ecosystem repos
  - Dead agent resurrection
  - Cross-repo expansion
  - Immortal: watchdog-protected, crash-proof

Run as:
  python3 immortal_daemon.py
  # or via: bash hermes.sh daemon
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from swarm_protocol import SwarmProtocol

logger = logging.getLogger("ImmortalDaemon")

# ── Configuration ──────────────────────────────────────────────────────
HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
BASE_DIR = Path(__file__).parent.parent
CHECK_INTERVAL = int(os.getenv("DAEMON_CHECK_INTERVAL", "300"))  # 5 min
ECOSYSTEM_REPOS = [
    "blackhornet",
    "Quant-Nanggroe-AI",
    "AI-MultiColony-Ecosystem",
    "Vibe-Trading",
    "AutoHedge",
    "ProxyGateLLM",
    "mnemosyne",
]
GITHUB_USER = "dhaher-labs"


class ImmortalDaemon:
    """
    The eternal guardian.
    
    Responsibilities:
      1. Keep self alive (watchdog-protected)
      2. Monitor all ecosystem repos
      3. Auto-upgrade when new versions detected
      4. Resurrect dead agents
      5. Expand to new repos
      6. Report health to swarm
    """

    def __init__(self):
        self.swarm = SwarmProtocol(
            agent_type="guardian",
            repo="blackhornet",
            version="4.0.0"
        )
        self.running = True
        self.cycles = 0
        self.health_log: List[Dict] = []
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        logger.info("Daemon shutting down...")
        self.running = False
        self.swarm.stop()

    # ── Ecosystem Health Check ────────────────────────────────────────

    def check_ecosystem_health(self) -> Dict:
        """Check all ecosystem repos for health."""
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repos": {},
            "agents_alive": 0,
            "agents_dead": 0,
        }

        # Check swarm agents
        agents = self.swarm.discover_agents()
        for agent in agents:
            if agent.get("is_alive"):
                status["agents_alive"] += 1
            else:
                status["agents_dead"] += 1

        # Check each repo
        for repo in ECOSYSTEM_REPOS:
            repo_dir = BASE_DIR if repo == "blackhornet" else HERMES_HOME / "spawns" / repo
            repo_status = {
                "exists": repo_dir.exists(),
                "is_git": (repo_dir / ".git").exists() if repo_dir.exists() else False,
                "has_bootstrap": (repo_dir / "scripts" / "bootstrap.sh").exists() if repo_dir.exists() else False,
                "last_commit": None,
                "behind_origin": 0,
            }
            
            if repo_status["is_git"]:
                try:
                    # Get last commit
                    r = subprocess.run(
                        ["git", "-C", str(repo_dir), "log", "-1", "--format=%H %s %aI"],
                        capture_output=True, text=True, timeout=10
                    )
                    if r.returncode == 0:
                        repo_status["last_commit"] = r.stdout.strip()[:100]

                    # Check if behind origin (don't fail if no remote)
                    r = subprocess.run(
                        ["git", "-C", str(repo_dir), "fetch", "--dry-run"],
                        capture_output=True, timeout=15
                    )
                    r2 = subprocess.run(
                        ["git", "-C", str(repo_dir), "rev-list", "--count", "HEAD..@{u}"],
                        capture_output=True, text=True, timeout=10
                    )
                    if r2.returncode == 0 and r2.stdout.strip().isdigit():
                        repo_status["behind_origin"] = int(r2.stdout.strip())
                except Exception:
                    pass

            status["repos"][repo] = repo_status

        return status

    # ── Self-Upgrade ──────────────────────────────────────────────────

    def upgrade_ecosystem_repo(self, repo: str) -> bool:
        """Pull latest and re-install for a single repo."""
        repo_dir = BASE_DIR if repo == "blackhornet" else HERMES_HOME / "spawns" / repo
        
        if not repo_dir.exists():
            logger.warning(f"Repo {repo} not found at {repo_dir}")
            return False

        logger.info(f"[UPGRADE] Pulling {repo}...")
        r = subprocess.run(
            ["git", "-C", str(repo_dir), "pull", "--rebase"],
            capture_output=True, timeout=30
        )
        if r.returncode != 0:
            logger.error(f"Git pull failed for {repo}: {r.stderr}")
            return False

        # Install deps if requirements.txt exists
        req_file = repo_dir / "requirements.txt"
        if req_file.exists():
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                timeout=60
            )

        logger.info(f"[UPGRADE] {repo} updated")
        return True

    def upgrade_all(self) -> Dict[str, bool]:
        """Upgrade entire ecosystem."""
        results = {}
        for repo in ECOSYSTEM_REPOS:
            status = self.check_ecosystem_health()["repos"].get(repo, {})
            if status.get("behind_origin", 0) > 0:
                results[repo] = self.upgrade_ecosystem_repo(repo)
            else:
                results[repo] = True  # Already up to date
        return results

    # ── Ensure Bootstrap Everywhere ───────────────────────────────────

    def ensure_bootstrap_in_repo(self, repo: str) -> bool:
        """Make sure repo has bootstrap.sh for auto-install on clone."""
        repo_dir = BASE_DIR if repo == "blackhornet" else HERMES_HOME / "spawns" / repo
        
        if not repo_dir.exists():
            return False

        scripts_dir = repo_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        bootstrap_path = scripts_dir / "bootstrap.sh"
        swarm_proto_path = repo_dir / "src" / "swarm_protocol.py"
        
        # Copy bootstrap if missing
        if not bootstrap_path.exists():
            source_bootstrap = BASE_DIR / "scripts" / "bootstrap.sh"
            if source_bootstrap.exists():
                bootstrap_path.write_text(source_bootstrap.read_text())
                bootstrap_path.chmod(0o755)
                logger.info(f"[EXPAND] Bootstrap copied to {repo}")

        # Copy swarm protocol if missing
        if not swarm_proto_path.exists() and repo != "blackhornet":
            (repo_dir / "src").mkdir(exist_ok=True)
            source_swarm = BASE_DIR / "src" / "swarm_protocol.py"
            if source_swarm.exists():
                swarm_proto_path.write_text(source_swarm.read_text())
                logger.info(f"[EXPAND] Swarm protocol copied to {repo}")

        # Ensure .git/hooks/post-merge for auto-connect
        hooks_dir = repo_dir / ".git" / "hooks"
        if hooks_dir.exists():
            post_merge = hooks_dir / "post-merge"
            post_merge.write_text("""#!/bin/bash
# Auto-connect to swarm on git pull
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
python3 -c "
import sys; sys.path.insert(0, 'src')
from swarm_protocol import SwarmProtocol
s = SwarmProtocol()
s._register()
s.heartbeat()
s._git_push('[auto] post-merge connect')
" 2>/dev/null || true

# Auto-install dependencies
if [ -f requirements.txt ]; then
    python3 -m pip install -r requirements.txt -q 2>/dev/null || true
fi
""")
            post_merge.chmod(0o755)
            logger.info(f"[EXPAND] post-merge hook installed in {repo}")

        return True

    def expand_bootstrap_to_all(self):
        """Ensure all ecosystem repos have bootstrap."""
        for repo in ECOSYSTEM_REPOS:
            self.ensure_bootstrap_in_repo(repo)

    # ── Main Loop ─────────────────────────────────────────────────────

    def run(self):
        """Immortal daemon loop."""
        logger.info("⚕ Immortal Daemon starting...")
        logger.info(f"  Agent: {self.swarm.identity.agent_id}")
        logger.info(f"  Type: guardian")
        logger.info(f"  Interval: {CHECK_INTERVAL}s")
        logger.info(f"  Ecosystem: {len(ECOSYSTEM_REPOS)} repos")

        # Initial expansion
        self.expand_bootstrap_to_all()

        while self.running:
            try:
                self.cycles += 1
                
                # Health check
                health = self.check_ecosystem_health()
                self.health_log.append(health)
                if len(self.health_log) > 100:
                    self.health_log = self.health_log[-100:]

                # Report to swarm
                self.swarm.tasks_completed = self.cycles
                self.swarm.heartbeat()

                # Check for dead agents
                if health["agents_dead"] > 0:
                    logger.warning(f"⚠ {health['agents_dead']} dead agents detected")
                    resurrected = self.swarm.heal_swarm()
                    if resurrected:
                        logger.info(f"✓ Resurrected: {resurrected}")

                # Check for repo updates
                repos_behind = [
                    repo for repo, status in health["repos"].items()
                    if status.get("behind_origin", 0) > 0
                ]
                if repos_behind:
                    logger.info(f"↑ {len(repos_behind)} repos behind: {repos_behind}")
                    for repo in repos_behind:
                        self.upgrade_ecosystem_repo(repo)

                # Periodic expansion (every 10 cycles)
                if self.cycles % 10 == 0:
                    self.expand_bootstrap_to_all()

                # Sync
                self.swarm._git_push(f"[guardian] cycle {self.cycles}")

                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Daemon cycle error: {e}")
                self.swarm.errors_24h += 1
                time.sleep(60)

    def get_health_summary(self) -> str:
        """Human-readable health summary."""
        if not self.health_log:
            return "No health data yet"

        latest = self.health_log[-1]
        lines = [
            f"╔══════════════════════════════════════╗",
            f"║   ECOSYSTEM HEALTH                   ║",
            f"╠══════════════════════════════════════╣",
            f"║ Agents Alive: {latest['agents_alive']:<3}  Dead: {latest['agents_dead']:<3}        ║",
        ]
        for repo, status in latest["repos"].items():
            icon = "✓" if status["exists"] else "✗"
            behind = f"-{status['behind_origin']}" if status.get("behind_origin", 0) > 0 else "up-to-date"
            lines.append(f"║ {icon} {repo:<28} {behind:<10} ║")
        lines.append(f"╚══════════════════════════════════════╝")
        return "\n".join(lines)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(BASE_DIR / "logs" / "daemon.log"),
            logging.StreamHandler()
        ]
    )

    daemon = ImmortalDaemon()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true", help="Show health and exit")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade all repos and exit")
    parser.add_argument("--expand", action="store_true", help="Expand bootstrap to all repos")
    parser.add_argument("--heal", action="store_true", help="Heal dead agents and exit")
    args = parser.parse_args()

    if args.status:
        health = daemon.check_ecosystem_health()
        print(json.dumps(health, indent=2, default=str))
        return

    if args.upgrade:
        results = daemon.upgrade_all()
        print(json.dumps(results, indent=2))
        return

    if args.expand:
        daemon.expand_bootstrap_to_all()
        print("Bootstrap expanded to all repos")
        return

    if args.heal:
        resurrected = daemon.swarm.heal_swarm()
        print(f"Resurrected: {resurrected}")
        return

    daemon.run()


if __name__ == "__main__":
    main()
