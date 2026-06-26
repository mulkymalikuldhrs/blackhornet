#!/usr/bin/env python3
"""
BLACKHORNET AGI DAEMON — Persistent Runtime with TRUE AGI features
===================================================================
- Continuous agent loop with cross-agent messaging
- Vector memory consolidation every 5 cycles
- Self-modification (scans agent files for improvements)
- Error recovery with safe mode after 3 consecutive crashes
- Real autonomy layer integration (no simulated results)
"""

import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from threading import Lock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.memory import VectorMemory
from scripts.message_bus import MessageBus
from scripts.autonomy import AutonomyLayer
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
PID_FILE = DATA_DIR / "blackhornet.pid"
LOG_FILE = BASE_DIR / "logs" / "blackhornet-daemon.log"
HEALTH_FILE = DATA_DIR / "blackhornet-health.json"
HEARTBEAT_FILE = DATA_DIR / "blackhornet-heartbeat.json"

os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("BH-Daemon")


def load_heartbeat() -> dict:
    if HEARTBEAT_FILE.exists():
        return json.loads(HEARTBEAT_FILE.read_text())
    return {"last_beat": None, "status": "dead", "uptime": 0, "agents_active": 0, "cycles": 0}


def save_heartbeat(data: dict):
    HEARTBEAT_FILE.write_text(json.dumps(data, indent=2))


class AGIDaemon:
    """
    The heart of BlackHornet AGI with TRUE autonomous capabilities:
    - Cross-agent message processing
    - Memory consolidation
    - Self-modification scanning
    - Graceful error recovery with safe mode
    """

    def __init__(self):
        self.running = False
        self.cycle_count = 0
        self.start_time: float | None = None
        self.agents: dict[str, dict] = {}
        self.error_counts: dict[str, int] = {}
        self.safe_mode_agents: set[str] = set()
        self.memory = VectorMemory()
        self.bus = MessageBus()
        self.autonomy = AutonomyLayer()
        self._discover_agents()

    def _discover_agents(self):
        agents_dir = SRC_DIR / "agents"
        if agents_dir.exists():
            for d in agents_dir.iterdir():
                if d.is_dir() and (d / "agent.py").exists():
                    self.agents[d.name] = {
                        "path": str(d / "agent.py"),
                        "status": "idle",
                        "last_run": None,
                        "cycles": 0,
                        "has_loop": False,
                    }
        for name, info in self.agents.items():
            agent_file = Path(info["path"])
            if agent_file.exists():
                content = agent_file.read_text()
                info["has_loop"] = any(
                    kw in content for kw in ["def run", "def start", "while True", "async def"]
                )
        log.info(f"Discovered {len(self.agents)} agents: {', '.join(self.agents.keys())}")

    def start(self):
        if self.running:
            log.warning("Daemon already running")
            return
        self.running = True
        self.start_time = time.time()
        log.info("BLACKHORNET AGI DAEMON STARTED")
        self._save_pid()
        self._main_loop()

    def stop(self):
        log.info("BLACKHORNET AGI DAEMON STOPPING...")
        self.running = False

    def _save_pid(self):
        PID_FILE.write_text(str(os.getpid()))

    def _main_loop(self):
        while self.running:
            try:
                self.cycle_count += 1
                cycle_start = time.time()
                log.info(f"--- Cycle {self.cycle_count} ---")

                self._heartbeat()

                # 1. Process cross-agent messages
                self._process_messages()

                # 2. Run agent cycle (runs each agent as subprocess)
                self._run_agent_cycle()

                # 3. Run autonomy layer (REAL execution, not simulated)
                self._run_autonomy()

                # 4. Knowledge graph update
                self._update_graph()

                # 5. Self-check
                self._self_check()

                # 6. Memory consolidation (every 5 cycles)
                if self.cycle_count % 5 == 0:
                    self._consolidate_memory()

                # 7. Self-modification scan (every 10 cycles)
                if self.cycle_count % 10 == 0:
                    self._scan_self_improvement()

                # 8. Self-upgrade check (every 15 cycles)
                if self.cycle_count % 15 == 0:
                    self._check_upgrade()

                elapsed = time.time() - cycle_start
                sleep_time = max(5, 30 - elapsed)
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                log.error(f"Cycle error: {e}")
                time.sleep(10)

    def _heartbeat(self):
        data = {
            "last_beat": datetime.utcnow().isoformat(),
            "status": "alive",
            "uptime": int(time.time() - (self.start_time or time.time())),
            "agents_active": sum(
                1 for a in self.agents.values() if a["status"] == "running"
            ),
            "cycles": self.cycle_count,
        }
        save_heartbeat(data)

    def _process_messages(self):
        """Process cross-agent messages from the message bus."""
        messages = self.bus.receive("daemon")
        for msg in messages:
            log.info(f"  Message from {msg['from']}: {msg['subject']}")
            self.memory.store(
                f"Daemon received message from {msg['from']}: {msg['subject']} - {msg['body'][:200]}",
                {"type": "message", "from": msg["from"]},
            )

        # Route pending messages to their intended recipients
        for agent_name in list(self.agents.keys()):
            pending = self.bus.pending_count(agent_name)
            if pending > 0:
                log.info(f"  {pending} pending messages for {agent_name}")

    def _run_agent_cycle(self):
        """Execute one cycle of agent operations with crash tracking."""
        for name, agent in list(self.agents.items()):
            agent_path = Path(agent["path"])
            if not agent_path.exists():
                continue

            # Check safe mode
            if name in self.safe_mode_agents:
                log.info(f"  {name}: safe mode (skipping execution)")
                continue

            try:
                agent["cycles"] += 1
                agent["last_run"] = datetime.utcnow().isoformat()
                agent["status"] = "running"

                if agent["has_loop"]:
                    agent_env = os.environ.copy()
                    agent_env["PYTHONPATH"] = str(BASE_DIR)
                    result = subprocess.run(
                        [sys.executable, str(agent_path), "--cycle", str(self.cycle_count)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(BASE_DIR),
                        env=agent_env,
                    )
                    if result.stdout.strip():
                        log.info(f"  {name}: {result.stdout.strip()[:200]}")
                    if result.stderr.strip():
                        log.warning(f"  {name} stderr: {result.stderr.strip()[:200]}")

                agent["status"] = "idle"
                self.error_counts[name] = 0  # Reset on success

            except subprocess.TimeoutExpired:
                log.warning(f"  {name}: timeout")
                agent["status"] = "timeout"
                self._track_error(name)

            except Exception as e:
                log.debug(f"  {name}: {e}")
                agent["status"] = "idle"
                self._track_error(name)

    def _track_error(self, agent_name: str):
        """Track consecutive errors and activate safe mode if threshold exceeded."""
        self.error_counts[agent_name] = self.error_counts.get(agent_name, 0) + 1
        if self.error_counts[agent_name] >= 3:
            if agent_name not in self.safe_mode_agents:
                self.safe_mode_agents.add(agent_name)
                log.warning(f"  {agent_name}: 3 consecutive errors -> SAFE MODE")
                self.bus.send(
                    "daemon",
                    agent_name,
                    "Safe Mode Activated",
                    f"You have been placed in safe mode after {self.error_counts[agent_name]} consecutive errors. Your agent.py will run in restricted mode.",
                )

    def _run_autonomy(self):
        """Run the autonomy layer — generates and executes REAL goals."""
        # Generate a new goal if fewer than 2 pending
        pending = len([g for g in self.autonomy.goals if g["status"] == "pending"])
        if pending < 2:
            goal = self.autonomy.self_prompt()
            log.info(f"  Autonomy: new goal '{goal['prompt']}' ({goal['id']})")
            self.bus.broadcast(
                "autonomy",
                f"New Goal: {goal['prompt']}",
                f"Autonomy generated goal {goal['id']}: {goal['prompt']}",
            )

        # Execute up to 2 pending goals
        executed = 0
        for goal in self.autonomy.goals:
            if goal["status"] == "pending" and executed < 2:
                result = self.autonomy.execute_initiative(goal["id"])
                if result:
                    log.info(f"  Autonomy: executed '{result['prompt']}' -> {result.get('result', '')[:80]}...")
                    executed += 1

    def _update_graph(self):
        graph_script = SRC_DIR / "graphify_api.py"
        if graph_script.exists():
            try:
                subprocess.run(
                    [sys.executable, str(graph_script), "--cycle", str(self.cycle_count)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(BASE_DIR),
                )
            except Exception:
                pass

    def _self_check(self):
        """Comprehensive health check across all subsystems."""
        issues = []
        for name, agent in self.agents.items():
            if agent["cycles"] == 0 and name in ["colony", "manus"]:
                issues.append(f"{name} never ran")

        # Check memory health
        mem_stats = self.memory.stats()
        if mem_stats.get("episodic_count", 0) == 0:
            issues.append("vector memory is empty")

        # Check message bus health
        msg_dir = DATA_DIR / "messages"
        if not msg_dir.exists():
            issues.append("message bus directory missing")

        if issues:
            log.warning(f"Health issues: {'; '.join(issues)}")
            self.bus.send("daemon", "autonomy", "Health Issues", "; ".join(issues))

    def _consolidate_memory(self):
        """Consolidate short-term memories into long-term concepts."""
        log.info("  Consolidating memory...")
        concepts = self.memory.consolidate()
        if concepts:
            log.info(f"  Created {len(concepts)} new memory concepts")
            for c in concepts[:3]:
                log.info(f"    Concept: {c['summary'][:80]}...")

        # Log memory stats
        stats = self.memory.stats()
        log.info(f"  Memory: {stats['episodic_count']} items, {stats['consolidated_count']} concepts")

        # Store consolidation event in memory
        self.memory.store(
            f"Memory consolidation cycle {self.cycle_count}: {stats}",
            {"type": "consolidation", "cycle": self.cycle_count},
        )

    def _scan_self_improvement(self):
        """Scan agent files for obvious improvements and suggest changes."""
        log.info("  Scanning for self-improvements...")
        agents_dir = SRC_DIR / "agents"
        suggestions = []

        if not agents_dir.exists():
            return

        for d in sorted(agents_dir.iterdir()):
            if not d.is_dir():
                continue
            agent_file = d / "agent.py"
            if not agent_file.exists():
                continue

            content = agent_file.read_text()
            name = d.name
            file_issues = []

            # Check for missing error handling
            if "try" not in content or "except" not in content:
                file_issues.append(f"{name}: no try/except blocks")

            # Check for bare 'except:' (should specify exception type)
            if re.search(r"except\s*:", content):
                file_issues.append(f"{name}: bare 'except:' found — should specify exception type")

            # Check for print statements (should use logging)
            if "print(" in content and "logging" not in content:
                file_issues.append(f"{name}: uses print() but no logging module imported")

            # Check for hardcoded paths
            hardcoded = re.findall(r'["\']/(?:etc|tmp|var|home|root)/', content)
            if hardcoded:
                file_issues.append(f"{name}: hardcoded paths: {hardcoded[:3]}")

            # Check for long functions (>50 lines)
            lines = content.splitlines()
            if len(lines) > 200:
                file_issues.append(f"{name}: {len(lines)} lines — consider splitting into modules")

            if file_issues:
                suggestions.append({"agent": name, "issues": file_issues})

        if suggestions:
            log.info(f"  Found {len(suggestions)} agents with improvement suggestions:")
            for s in suggestions:
                for issue in s["issues"][:3]:
                    log.info(f"    - {issue}")
                self.bus.send(
                    "daemon", s["agent"], "Improvement Suggestions",
                    "\n".join(s["issues"]),
                )

            # Store in vector memory
            self.memory.store(
                f"Self-improvement scan: {len(suggestions)} agents need improvements",
                {"type": "self_improvement_scan", "suggestions": len(suggestions)},
            )

            # Auto-apply improvements via self-write module
            try:
                sw_script = BASE_DIR / "scripts" / "self_write.py"
                if sw_script.exists():
                    result = subprocess.run(
                        [sys.executable, str(sw_script), "improve"],
                        capture_output=True, text=True, timeout=60
                    )
                    if result.stdout.strip():
                        log.info(f"  Self-write applied: {result.stdout.strip()[:500]}")
                    if result.stderr.strip():
                        log.warning(f"  Self-write stderr: {result.stderr.strip()[:300]}")
            except Exception as e:
                log.debug(f"  Self-write execution: {e}")
        else:
            log.info("  No improvements needed")

    def _check_upgrade(self):
        upgrade_script = BASE_DIR / "scripts" / "self-upgrade.sh"
        if upgrade_script.exists():
            try:
                result = subprocess.run(
                    ["bash", str(upgrade_script), "check"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if "upgrade available" in result.stdout.lower():
                    log.info("Self-upgrade available, executing...")
                    subprocess.Popen(["bash", str(upgrade_script), "upgrade"])
            except Exception as e:
                log.warning(f"Upgrade check failed: {e}")

    def status(self):
        uptime = int(time.time() - (self.start_time or time.time()))
        log.info(f"BH Daemon Status:")
        log.info(f"  Running: {self.running}")
        log.info(f"  Uptime: {uptime}s")
        log.info(f"  Cycles: {self.cycle_count}")
        log.info(f"  Agents: {len(self.agents)}")
        for name, agent in self.agents.items():
            safe = " [SAFE MODE]" if name in self.safe_mode_agents else ""
            log.info(f"    {name}: {agent['status']} ({agent['cycles']} cycles){safe}")
        log.info(f"  Safe mode agents: {len(self.safe_mode_agents)}")
        log.info(f"  Memory: {self.memory.stats().get('episodic_count', 0)} items")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BlackHornet AGI Daemon")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status", "heartbeat"],
        help="Action to perform",
    )
    args = parser.parse_args()

    daemon = AGIDaemon()

    if args.action == "start":
        if PID_FILE.exists():
            try:
                old_pid = int(PID_FILE.read_text().strip())
                os.kill(old_pid, 0)
                log.warning(f"Daemon already running (PID: {old_pid})")
                return
            except (OSError, ValueError):
                PID_FILE.unlink(missing_ok=True)
        daemon.start()

    elif args.action == "stop":
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                log.info(f"Sent SIGTERM to PID {pid}")
                PID_FILE.unlink(missing_ok=True)
            except (OSError, ValueError):
                PID_FILE.unlink(missing_ok=True)
                log.info("No running daemon found")
        else:
            log.info("No PID file found")

    elif args.action == "restart":
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
            except (OSError, ValueError):
                pass
        daemon.start()

    elif args.action == "status":
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, 0)
                hb = load_heartbeat()
                log.info(f"BH Daemon ACTIVE (PID: {pid})")
                log.info(f"  Last beat: {hb.get('last_beat', 'never')}")
                log.info(f"  Uptime: {hb.get('uptime', 0)}s")
                log.info(f"  Cycles: {hb.get('cycles', 0)}")
                log.info(f"  Agents active: {hb.get('agents_active', 0)}")
            except (OSError, ValueError):
                log.info("BH Daemon: PID file exists but process dead")
        else:
            log.info("BH Daemon: NOT RUNNING")

    elif args.action == "heartbeat":
        hb = load_heartbeat()
        print(json.dumps(hb, indent=2))


if __name__ == "__main__":
    main()
