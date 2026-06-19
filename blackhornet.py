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
  ProxyGateLLM/         ← LLM gateway (10 providers, 468 models)
  mnemosyne/            ← Knowledge memory (RAG + graph)
  agent/                ← Swarm shared state registry
  Quant-Nanggroe-AI/    ← Research engine
  AI-MultiColony-Ecosystem/ ← Multi-agent colony
  Vibe-Trading/         ← Alpha factors (450+)

Sovereign: Mulky Malikul Dhaher
Status: PRODUCTION READY — Immortal Autonomous Empire
"""

import os
import sys
import json
import time
import signal
import logging

# ── BRIDGE INTEGRATION: HyperGate & Mnemosyne ────────────────────
from src.hypergate import HyperGate
from src.mnemosyne_bridge import MnemosyneBridge
# ── END BRIDGE INTEGRATION ───────────────────────────────────────

# ── GRAPHIFY + HERMES + AUDIT ───────────────────────────────────
from src.graph.graphify_pipeline import GraphifyPipeline
from src.graphify_api import GraphifyAPIServer
from src.memory.hermes_bridge import HermesMemoryBridge
from src.memory.session import SessionMemory
from src.agents.audit_orchestrator import AuditOrchestrator
# ── END GRAPHIFY ────────────────────────────────────────────────

import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

# ── BLACKHORNET Identity ──────────────────────────────────────────────
VERSION = "1.0.0"
SOVEREIGN = "Mulky Malikul Dhaher"
ECOSYSTEM_NAME = "BLACKHORNET"
NEST_DIR = Path(os.getenv("BLACKHORNET_NEST", Path.home() / "blackhornet-nest"))

CODEBERG_USER = "Dhaher-Labs"
GITLAB_USER = "mulkymalikuldhr"

ECOSYSTEM_REPOS = {
    "blackhornet":       {"type": "orchestrator", "urls": [
        f"https://codeberg.org/{CODEBERG_USER}/blackhornet.git",
        f"https://gitlab.com/{GITLAB_USER}/blackhornet.git",
        f"https://github.com/{CODEBERG_USER}/blackhornet.git",
    ]},
    "ProxyGateLLM":      {"type": "llm-gateway",  "urls": [
        f"https://codeberg.org/{CODEBERG_USER}/ProxyGateLLM.git",
        f"https://gitlab.com/{GITLAB_USER}/ProxyGateLLM.git",
        f"https://github.com/{CODEBERG_USER}/ProxyGateLLM.git",
    ]},
    "mnemosyne":         {"type": "memory",       "urls": [
        f"https://codeberg.org/{CODEBERG_USER}/mnemosyne.git",
        f"https://gitlab.com/{GITLAB_USER}/mnemosyne.git",
        f"https://github.com/{CODEBERG_USER}/mnemosyne.git",
    ]},
    "agent":             {"type": "swarm-registry","urls": [
        f"https://codeberg.org/{CODEBERG_USER}/agent.git",
        f"https://gitlab.com/{GITLAB_USER}/agent.git",
        f"https://github.com/{CODEBERG_USER}/agent.git",
    ]},
    "Quant-Nanggroe-AI": {"type": "research",     "urls": [
        f"https://codeberg.org/{CODEBERG_USER}/Quant-Nanggroe-AI.git",
        f"https://gitlab.com/{GITLAB_USER}/Quant-Nanggroe-AI.git",
        f"https://github.com/{CODEBERG_USER}/Quant-Nanggroe-AI.git",
    ]},
    "AI-MultiColony-Ecosystem": {"type": "colony", "urls": [
        f"https://codeberg.org/{CODEBERG_USER}/AI-MultiColony-Ecosystem.git",
        f"https://gitlab.com/{GITLAB_USER}/AI-MultiColony-Ecosystem.git",
        f"https://github.com/{CODEBERG_USER}/AI-MultiColony-Ecosystem.git",
    ]},
    "Vibe-Trading":      {"type": "alpha",        "urls": [
        f"https://codeberg.org/{CODEBERG_USER}/Vibe-Trading.git",
        f"https://gitlab.com/{GITLAB_USER}/Vibe-Trading.git",
        f"https://github.com/{CODEBERG_USER}/Vibe-Trading.git",
    ]},
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

        # Graphify + Hermes systems
        self.graphify_pipeline = GraphifyPipeline()
        self.graphify_api = GraphifyAPIServer(pipeline=self.graphify_pipeline)
        self.session_memory = SessionMemory()
        self.hermes_bridge = HermesMemoryBridge(
            session_memory=self.session_memory,
            pipeline=self.graphify_pipeline,
        )
        self.audit_orchestrator = AuditOrchestrator(pipeline=self.graphify_pipeline)

    def _shutdown(self, signum, frame):
        logger.info("Nest shutting down...")
        self.running = False
        self.nest_status = "SHUTDOWN"

    def roar(self):
        """Display the BLACKHORNET banner."""
        print(f"\033[1;30;47m{HORNET_ART}\033[0m")
        print(f"\033[1;30;47m  {ECOSYSTEM_NAME} v{VERSION} — Sovereign: {SOVEREIGN}  \033[0m")
        print()

    def _clone_with_fallback(self, name: str, urls: list, dest: str) -> bool:
        """Try cloning from multiple URLs (Codeberg → GitLab → GitHub)."""
        for url in urls:
            try:
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", url, dest],
                    capture_output=True, timeout=60
                )
                if result.returncode == 0:
                    logger.info(f"  🐝 {name}: cloned from {url.split('/')[2]}")
                    return True
            except Exception:
                continue
        return False

    def _pull_repo(self, repo_dir: str) -> bool:
        """Pull latest changes for an existing repo."""
        try:
            result = subprocess.run(
                ["git", "-C", repo_dir, "pull", "--rebase"],
                capture_output=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    def deploy_nest(self) -> bool:
        """Clone all ecosystem repos into the nest. Pull if already cloned."""
        NEST_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Building nest at {NEST_DIR}...")

        for name, info in ECOSYSTEM_REPOS.items():
            repo_dir = NEST_DIR / name
            urls = info.get("urls", [])

            if (repo_dir / ".git").exists():
                updated = self._pull_repo(str(repo_dir))
                status = "UPDATED" if updated else "IN_NEST"
                logger.info(f"  🐝 {name}: {status}")
                self.hornets[name] = {"status": status, "dir": str(repo_dir)}
                continue

            logger.info(f"  🐝 {name}: cloning...")
            if urls and self._clone_with_fallback(name, urls, str(repo_dir)):
                self.hornets[name] = {"status": "CLONED", "dir": str(repo_dir)}
            else:
                logger.warning(f"  ⚠ {name}: clone failed on all mirrors")
                self.hornets[name] = {"status": "FAILED", "error": "all mirrors failed"}

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

        # 3. BH Doctor (replaces immortal_daemon + memory_bridge)
        hq_dir = NEST_DIR / "blackhornet"
        if hq_dir.exists():
            subprocess.Popen(
                [sys.executable, "bh-doctor", "start"],
                cwd=str(hq_dir),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info("  ⚕️ BH Doctor started")

        # 4. Unified Launcher (core services)
        if hq_dir.exists():
            subprocess.Popen(
                [sys.executable, "-m", "src.integration.unified_launcher"],
                cwd=str(hq_dir),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info("  🧬 Unified Launcher started")

        # 5. HyperGate (LLM bridge — routes through ProxyGateLLM)
        try:
            sys.path.insert(0, str(Path(__file__).parent / "src"))
            from hypergate import HyperGate
            hg = HyperGate()
            hg.start()
            logger.info("  🔗 HyperGate started (LLM bridge)")
        except Exception as e:
            logger.warning(f"  ⚠ HyperGate: {e}")

        # 6. Mnemosyne Bridge (knowledge memory)
        try:
            sys.path.insert(0, str(Path(__file__).parent / "src"))
            from mnemosyne_bridge import MnemosyneBridge
            mb = MnemosyneBridge()
            mb.start()
            logger.info("  🧠 Mnemosyne Bridge started (knowledge memory)")
        except Exception as e:
            logger.warning(f"  ⚠ Mnemosyne Bridge: {e}")

        # 7. MultiColony — wire engine patterns
        # 8. Graphify API — expose graph data externally
        try:
            self.graphify_api.start()
            logger.info("  🕸️ GraphifyAPI started on port 9090")
        except Exception as e:
            logger.warning(f"  ⚠ GraphifyAPI: {e}")

        # 9. Hermes Memory Bridge — unified memory
        try:
            logger.info("  🧠 HermesMemoryBridge ready (%d records)", len(self.hermes_bridge._records))
        except Exception as e:
            logger.warning(f"  ⚠ HermesMemoryBridge: {e}")

        # 10. Audit Orchestrator — 100 agents ready
        try:
            logger.info("  🔍 AuditOrchestrator ready (%d agents)", len(self.audit_orchestrator.agents))
        except Exception as e:
            logger.warning(f"  ⚠ AuditOrchestrator: {e}")
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
            "hypergate": False,
            "mnemosyne": False,
            "graphify": False,
            "hermes_bridge": False,
            "trading_pipeline": False,
            "daemon_running": False,
        }

        # Check ProxyGateLLM
        try:
            r = urllib.request.urlopen("http://localhost:3333/health", timeout=3)
            health["proxygate"] = r.status == 200
        except Exception:
            pass

        # Check GraphifyAPI
        try:
            health["graphify"] = self.graphify_api.is_running()
        except Exception:
            pass

        # Check HermesBridge
        try:
            stats = self.hermes_bridge.stats()
            health["hermes_bridge"] = stats["total_records"] >= 0
        except Exception:
            pass

        # Check HyperGate (uses ProxyGateLLM)
        try:
            sys.path.insert(0, str(Path(__file__).parent / "src"))
            from hypergate import HyperGate
            hg = HyperGate()
            health["hypergate"] = hg.is_available()
        except Exception:
            pass

        # Check Mnemosyne
        try:
            r = urllib.request.urlopen("http://localhost:3001", timeout=3)
            health["mnemosyne"] = r.status == 200
        except Exception:
            pass

        # Check Daemon (unified launcher)
        result = subprocess.run(
            ["pgrep", "-f", "unified_launcher"],
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

    def self_push(self, message: str = "auto: BH self-upgrade") -> bool:
        """Auto-commit and push all changes to Codeberg + GitLab.
        This enables the immortal self-push capability.
        """
        bh_dir = NEST_DIR / "blackhornet"
        if not (bh_dir / ".git").exists():
            logger.warning("Self-push: not a git repo")
            return False

        try:
            subprocess.run(
                ["git", "-C", str(bh_dir), "add", "-A"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["git", "-C", str(bh_dir), "commit", "-m", message, "--allow-empty"],
                capture_output=True, timeout=10
            )
            result = subprocess.run(
                ["git", "-C", str(bh_dir), "push", "codeberg", "main", "--force"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info("Self-push: pushed to Codeberg ✅")
            else:
                logger.warning(f"Self-push: Codeberg failed — {result.stderr[:100]}")

            result_gl = subprocess.run(
                ["git", "-C", str(bh_dir), "push", "gitlab", "main"],
                capture_output=True, text=True, timeout=30
            )
            if result_gl.returncode == 0:
                logger.info("Self-push: pushed to GitLab ✅")

            return True
        except Exception as e:
            logger.error(f"Self-push failed: {e}")
            return False

    def immortal_daemon(self, interval: int = 300):
        """Immortal self-healing daemon loop.
        Every `interval` seconds:
        - Check health of all services
        - Auto-restart failed services
        - Auto-pull latest code from repos
        - Auto-push any self-modifications
        """
        logger.info(f"🖤 Immortal daemon started (interval={interval}s)")
        cycle = 0
        while self.running:
            try:
                cycle += 1

                # Health check every cycle
                health = self.health_check()
                failed = [k for k, v in health.items() if not v]

                if failed:
                    logger.warning(f"Health issues: {failed}")
                    self._auto_heal(failed)

                # Auto-pull repos every 10 cycles
                if cycle % 10 == 0:
                    for name in ECOSYSTEM_REPOS:
                        repo_dir = NEST_DIR / name
                        if (repo_dir / ".git").exists():
                            self._pull_repo(str(repo_dir))

                # Auto-push self-modifications every 20 cycles
                if cycle % 20 == 0:
                    self.self_push(f"auto: immortal cycle {cycle}")

                time.sleep(interval)
            except Exception as e:
                logger.error(f"Immortal daemon error: {e}")
                time.sleep(30)

    def _auto_heal(self, failed_components: List[str]):
        """Auto-heal failed components."""
        for component in failed_components:
            if component == "proxygate":
                pg_dir = NEST_DIR / "ProxyGateLLM"
                if pg_dir.exists():
                    subprocess.Popen(
                        ["node", "index.js"],
                        cwd=str(pg_dir),
                        env={**os.environ, "PORT": "3333"},
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    logger.info("  🔧 Auto-healed: ProxyGateLLM restarted")
            elif component == "mnemosyne":
                mn_dir = NEST_DIR / "mnemosyne"
                if mn_dir.exists():
                    subprocess.Popen(
                        ["npm", "start"],
                        cwd=str(mn_dir),
                        env={**os.environ, "PORT": "3001"},
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    logger.info("  🔧 Auto-healed: Mnemosyne restarted")
            elif component == "daemon_running":
                hq_dir = NEST_DIR / "blackhornet"
                if hq_dir.exists():
                    subprocess.Popen(
                        [sys.executable, "-m", "src.integration.unified_launcher"],
                        cwd=str(hq_dir),
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    logger.info("  🔧 Auto-healed: Unified Launcher restarted")

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
    # Initialize Bridge Infrastructure
    print('🖤 HyperGate: Initializing LLM Gateway...')
    hypergate = HyperGate()
    hypergate.start()
    print(f'   ✅ HyperGate active on port {hypergate.port}')

    print('🧠 Mnemosyne Bridge: Initializing Swarm Memory...')
    mnemosyne = MnemosyneBridge()
    mnemosyne.start()
    print(f'   ✅ Mnemosyne Bridge active on port {mnemosyne.port}')

    import argparse
    parser = argparse.ArgumentParser(description="🖤 BLACKHORNET — Sovereign Autonomous Ecosystem")
    parser.add_argument("--deploy", action="store_true", help="Deploy nest (clone all repos)")
    parser.add_argument("--start", action="store_true", help="Start all hornets")
    parser.add_argument("--status", action="store_true", help="Show nest status")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--sovereign", action="store_true", help="Display sovereign panel")
    parser.add_argument("--immortal", action="store_true", help="Start immortal self-healing daemon")
    parser.add_argument("--self-push", action="store_true", help="Auto-commit and push changes")
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
    elif args.immortal:
        nest.deploy_nest()
        nest.start_hornets()
        nest.immortal_daemon()
    elif args.self_push:
        nest.deploy_nest()
        nest.self_push()
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
        print("    python3 blackhornet.py --deploy       Clone all repos")
        print("    python3 blackhornet.py --start        Start the full nest")
        print("    python3 blackhornet.py --immortal     Immortal self-healing daemon")
        print("    python3 blackhornet.py --self-push    Auto-commit + push changes")
        print("    python3 blackhornet.py --status       Nest status")
        print("    python3 blackhornet.py --health       Health check")
        print("    python3 blackhornet.py --sovereign    Sovereign panel")
        print()


if __name__ == "__main__":
    # Console colors
    B = '\033[1m'; N = '\033[0m'
    main()
