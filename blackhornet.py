#!/usr/bin/env python3
"""
🖤 BLACKHORNET — Sovereign Autonomous Ecosystem
=================================================
Umbrella orchestrator for the entire autonomous agent empire.

Philosophy:
  Like hornets — autonomous, relentless, swarm-intelligent, territorial.
  Each agent is a hornet. Together they form the BLACKHORNET nest.
  The Sovereign commands. The nest expands. The swarm never dies.

Ecosystem:
  blackhornet/          ← YOU ARE HERE (umbrella + orchestrator)
  blackhornet/        ← Trading agents (21 specialized)
  ProxyGateLLM/         ← LLM gateway (10 providers, 468 models)
  mnemosyne/            ← Knowledge memory (RAG + graph)
  agent/                ← Swarm shared state registry
  Quant-Nanggroe-AI/    ← Research engine
  AI-MultiColony/       ← Multi-agent colony
  Vibe-Trading/         ← Alpha factors (450+)
  AutoHedge/            ← Execution engine

Sovereign: Mulky Malikul Dhaher
Status: PRODUCTION READY — Immortal Autonomous Empire
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

# ── BLACKHORNET Identity ──────────────────────────────────────────────
VERSION = "1.0.0"
SOVEREIGN = "Mulky Malikul Dhaher"
ECOSYSTEM_NAME = "BLACKHORNET"
NEST_DIR = Path(os.getenv("BLACKHORNET_NEST", Path.home() / "blackhornet-nest"))

ECOSYSTEM_REPOS = {
    "blackhornet":       {"type": "orchestrator", "url": "https://github.com/dhaher-labs/blackhornet"},
    "ProxyGateLLM":        {"type": "llm-gateway",  "url": "https://github.com/dhaher-labs/ProxyGateLLM"},
    "mnemosyne":           {"type": "memory",       "url": "https://github.com/dhaher-labs/mnemosyne"},
    "agent":               {"type": "swarm-registry","url": "https://github.com/dhaher-labs/agent"},
    "Quant-Nanggroe-AI":   {"type": "research",     "url": "https://github.com/dhaher-labs/Quant-Nanggroe-AI"},
    "AI-MultiColony-Ecosystem": {"type": "colony",  "url": "https://github.com/dhaher-labs/AI-MultiColony-Ecosystem"},
    "Vibe-Trading":        {"type": "alpha",        "url": "https://github.com/dhaher-labs/Vibe-Trading"},
    "AutoHedge":           {"type": "execution",    "url": "https://github.com/dhaher-labs/AutoHedge"},
}

HORNET_ART = r"""
      \    /\
       )  ( ')
      (  /  )
       \(__)|
        /  \
       /    \
      /      \
     /        \
    /          \
   /   BLACK    \
  /   HORNET     \
 /________________\
        |
      NEST
"""

logger = logging.getLogger("BLACKHORNET")


class BlackHornetNest:
    """
    The central nest of the BLACKHORNET ecosystem.
    Orchestrates all hornet agents across all repos.
    """

    def __init__(self):
        self.running = True
        self.start_time = time.time()
        self.hornets: Dict[str, Dict] = {}
        self.nest_status = "INITIALIZING"
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        logger.info("Nest shutting down...")
        self.running = False
        self.nest_status = "SHUTDOWN"

    def roar(self):
        """Display the BLACKHORNET banner."""
        print(f"\033[1;30;47m{HORNET_ART}\033[0m")
        print(f"\033[1;30;47m  {ECOSYSTEM_NAME} v{VERSION} — Sovereign: {SOVEREIGN}  \033[0m")
        print()

    def deploy_nest(self) -> bool:
        """Clone all ecosystem repos into the nest."""
        NEST_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Building nest at {NEST_DIR}...")

        for name, info in ECOSYSTEM_REPOS.items():
            repo_dir = NEST_DIR / name
            if (repo_dir / ".git").exists():
                logger.info(f"  🐝 {name}: already in nest")
                self.hornets[name] = {"status": "IN_NEST", "dir": str(repo_dir)}
                continue

            logger.info(f"  🐝 {name}: cloning...")
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", info["url"], str(repo_dir)],
                    capture_output=True, timeout=60
                )
                self.hornets[name] = {"status": "CLONED", "dir": str(repo_dir)}
            except Exception as e:
                logger.warning(f"  ⚠ {name}: clone failed — {e}")
                self.hornets[name] = {"status": "FAILED", "error": str(e)}

        return True

    def start_hornets(self):
        """Start all hornet services in the nest."""
        logger.info("Starting hornet swarm...")

        # 1. ProxyGateLLM (LLM gateway — must start first)
        pg_dir = NEST_DIR / "ProxyGateLLM"
        if pg_dir.exists():
            subprocess.Popen(
                ["node", "index.js"],
                cwd=str(pg_dir),
                env={**os.environ, "PORT": "3333"},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info("  🔗 ProxyGateLLM started")
            time.sleep(2)

        # 2. Mnemosyne (optional — needs build)
        mn_dir = NEST_DIR / "mnemosyne"
        if (mn_dir / ".next").exists():
            subprocess.Popen(
                ["npm", "start"],
                cwd=str(mn_dir),
                env={**os.environ, "PORT": "3001"},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info("  🧠 Mnemosyne started")

        # 3. Immortal Daemon from blackhornet
        hq_dir = NEST_DIR / "blackhornet"
        if hq_dir.exists():
            subprocess.Popen(
                [sys.executable, "src/immortal_daemon.py"],
                cwd=str(hq_dir),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info("  🛡️ Immortal Daemon started")

        # 4. Memory Bridge
        if hq_dir.exists():
            subprocess.Popen(
                [sys.executable, "src/memory_bridge.py", "--bot", "blackhornet-orchestrator"],
                cwd=str(hq_dir),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info("  🧬 Memory Bridge started")

        # 5. MultiColony — wire engine patterns
        mc_dir = NEST_DIR / "AI-MultiColony-Ecosystem"
        if mc_dir.exists():
            hornet_src = Path(__file__).parent / "src"
            sys.path.insert(0, str(hornet_src))
            try:
                from colony_bridge import ColonyBridge
                cb = ColonyBridge()
                results = cb.integrate_to_hornet()
                wired = sum(1 for v in results.values() if v)
                logger.info(f"  🏛️  MultiColony wired: {wired}/{len(results)} patterns")
            except Exception as e:
                logger.warning(f"  ⚠ MultiColony bridge: {e}")

        self.nest_status = "OPERATIONAL"

    def status(self) -> Dict:
        """Get full nest status."""
        return {
            "ecosystem": ECOSYSTEM_NAME,
            "version": VERSION,
            "sovereign": SOVEREIGN,
            "nest_status": self.nest_status,
            "uptime_seconds": int(time.time() - self.start_time),
            "hornets": {
                name: {
                    **info,
                    "in_nest": (NEST_DIR / name).exists(),
                }
                for name, info in ECOSYSTEM_REPOS.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def health_check(self) -> Dict:
        """Quick health check of critical services."""
        import urllib.request
        health = {
            "proxygate": False,
            "trading_pipeline": False,
            "daemon_running": False,
        }

        # Check ProxyGateLLM
        try:
            r = urllib.request.urlopen("http://localhost:3333/health", timeout=3)
            health["proxygate"] = r.status == 200
        except:
            pass

        # Check Daemon
        result = subprocess.run(
            ["pgrep", "-f", "immortal_daemon"],
            capture_output=True, text=True
        )
        health["daemon_running"] = bool(result.stdout.strip())

        # Check Trading Pipeline
        hq_src = NEST_DIR / "blackhornet" / "src"
        if hq_src.exists():
            try:
                sys.path.insert(0, str(hq_src))
                from tools.market_data_tool import MarketDataTool
                md = MarketDataTool()
                data = json.loads(md.get_ohlcv('XAUUSD', '1d', 1))
                health["trading_pipeline"] = len(data.get("data", [])) > 0
            except:
                pass

        return health

    def run(self):
        """Main nest loop — keeps everything alive."""
        self.roar()
        self.deploy_nest()
        self.start_hornets()

        logger.info(f"🖤 {ECOSYSTEM_NAME} NEST OPERATIONAL")
        logger.info(f"   Sovereign: {SOVEREIGN}")
        logger.info(f"   Hornets: {len(self.hornets)} repos")
        logger.info(f"   Nest: {NEST_DIR}")

        cycle = 0
        while self.running:
            try:
                cycle += 1
                if cycle % 60 == 0:  # Every 60s
                    health = self.health_check()
                    all_ok = all(health.values())
                    if not all_ok:
                        logger.warning(f"Health: {health}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Nest cycle error: {e}")
                time.sleep(5)

        logger.info("Nest closed. Hornets continue autonomously.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="🖤 BLACKHORNET — Sovereign Autonomous Ecosystem")
    parser.add_argument("--deploy", action="store_true", help="Deploy nest (clone all repos)")
    parser.add_argument("--start", action="store_true", help="Start all hornets")
    parser.add_argument("--status", action="store_true", help="Show nest status")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--sovereign", action="store_true", help="Display sovereign panel")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    nest = BlackHornetNest()

    if args.deploy:
        nest.deploy_nest()
        print(json.dumps(nest.status(), indent=2, default=str))
    elif args.start:
        nest.deploy_nest()
        nest.run()
    elif args.status:
        nest.deploy_nest()
        print(json.dumps(nest.status(), indent=2, default=str))
    elif args.health:
        nest.deploy_nest()
        print(json.dumps(nest.health_check(), indent=2))
    elif args.sovereign:
        nest.roar()
        nest.deploy_nest()
        s = nest.status()
        print(f"  {B}{'Ecosystem:':<20}{N} {s['ecosystem']}")
        print(f"  {B}{'Version:':<20}{N} {s['version']}")
        print(f"  {B}{'Sovereign:':<20}{N} {s['sovereign']}")
        print(f"  {B}{'Status:':<20}{N} {s['nest_status']}")
        print(f"  {B}{'Uptime:':<20}{N} {s['uptime_seconds']}s")
        print(f"\n  {B}HORNETS:{N}")
        for name, info in s['hornets'].items():
            icon = "🟢" if info.get('in_nest') else "🔴"
            print(f"    {icon} {name:<30} [{info['type']}]")
        print()
    else:
        nest.roar()
        print("  Commands:")
        print("    python3 blackhornet.py --deploy     Clone all repos")
        print("    python3 blackhornet.py --start      Start the full nest")
        print("    python3 blackhornet.py --status     Nest status")
        print("    python3 blackhornet.py --health     Health check")
        print("    python3 blackhornet.py --sovereign  Sovereign panel")
        print()


if __name__ == "__main__":
    # Console colors
    B = '\033[1m'; N = '\033[0m'
    main()
