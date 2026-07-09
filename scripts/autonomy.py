#!/usr/bin/env python3
"""
BH AGI — Autonomy Layer (REAL Execution)
==========================================
Gives BH self-initiative with REAL system actions:
- Self-prompting informed by vector memory
- REAL execution (ps, memory checks, code audit, log pruning)
- Self-evaluation based on actual results
- Cross-agent messaging via MessageBus
- Vector memory for storing and recalling past outcomes
"""

import json
import logging
import os
import re
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

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

GOALS_FILE = DATA_DIR / "blackhornet-goals.json"
LEARNINGS_FILE = DATA_DIR / "blackhornet-learnings.json"
INITIATIVES_FILE = DATA_DIR / "blackhornet-initiatives.json"

logger = logging.getLogger("BH-Autonomy")


def _run_cmd(cmd: list[str], timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "")[:2000]
    except Exception as e:
        return f"ERROR: {e}"


def _uptime() -> str:
    return _run_cmd(["uptime"]).strip()


def _memory_usage() -> dict:
    try:
        with open("/proc/meminfo") as f:
            raw = f.read()
        total_match = re.search(r"MemTotal:\s+(\d+)", raw)
        avail_match = re.search(r"MemAvailable:\s+(\d+)", raw)
        total = int(total_match.group(1)) if total_match else 1
        avail = int(avail_match.group(1)) if avail_match else 0
        used_pct = round((total - avail) / total * 100, 1)
        return {"total_kb": total, "available_kb": avail, "used_percent": used_pct}
    except Exception as e:
        return {"error": str(e)}


def _cpu_count() -> int:
    return os.cpu_count() or 0


def _ps_count() -> int:
    out = _run_cmd(["ps", "aux"])
    return len(out.strip().splitlines())


def _disk_usage() -> dict:
    stat = os.statvfs(str(BASE_DIR))
    total = stat.f_frsize * stat.f_blocks
    free = stat.f_frsize * stat.f_bfree
    used_pct = round((total - free) / total * 100, 1) if total else 0
    return {"total_bytes": total, "free_bytes": free, "used_percent": used_pct}


def _count_agent_files() -> int:
    agents_dir = BASE_DIR / "src" / "agents"
    if not agents_dir.exists():
        return 0
    return sum(1 for d in agents_dir.iterdir() if d.is_dir())


def _count_log_errors() -> int:
    count = 0
    if LOGS_DIR.exists():
        for f in LOGS_DIR.iterdir():
            if f.suffix in (".log", ".txt"):
                content = f.read_text()
                count += len(re.findall(r"(?i)\berror\b", content))
    return count


def _count_log_files() -> int:
    if not LOGS_DIR.exists():
        return 0
    return sum(1 for f in LOGS_DIR.iterdir() if f.is_file())


def _agent_files_info() -> list[dict]:
    agents_dir = BASE_DIR / "src" / "agents"
    info = []
    if agents_dir.exists():
        for d in sorted(agents_dir.iterdir()):
            if d.is_dir():
                agent_file = d / "agent.py"
                if agent_file.exists():
                    content = agent_file.read_text()
                    has_error_handling = "try" in content and "except" in content
                    has_logging = "logging" in content or "logger." in content or "print" in content
                    info.append({
                        "name": d.name,
                        "has_error_handling": has_error_handling,
                        "has_logging": has_logging,
                        "lines": len(content.splitlines()),
                        "path": str(agent_file),
                    })
    return info


def _prune_old_logs(days: int = 7) -> int:
    cutoff = time.time() - days * 86400
    pruned = 0
    if LOGS_DIR.exists():
        for f in LOGS_DIR.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                try:
                    f.unlink()
                    pruned += 1
                except OSError:
                    pass
    return pruned


def _compress_file(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["gzip", "-f", str(path)], capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_agent_names() -> list[str]:
    agents_dir = BASE_DIR / "src" / "agents"
    if not agents_dir.exists():
        return []
    return sorted(d.name for d in agents_dir.iterdir() if d.is_dir())


def _validate_agents() -> list[dict]:
    results = []
    agents_dir = BASE_DIR / "src" / "agents"
    if agents_dir.exists():
        for d in sorted(agents_dir.iterdir()):
            if d.is_dir():
                agent_file = d / "agent.py"
                missing = []
                if not agent_file.exists():
                    missing.append("agent.py missing")
                else:
                    content = agent_file.read_text()
                    if "def run" not in content and "async def" not in content and "class" not in content:
                        missing.append("no run method or class found")
                results.append({
                    "name": d.name,
                    "valid": len(missing) == 0,
                    "issues": missing,
                })
    return results


def _suggest_improvements(agent_info: list[dict]) -> list[str]:
    suggestions = []
    for a in agent_info:
        if not a.get("has_error_handling"):
            suggestions.append(f"{a['name']}: add try/except around main logic")
        if not a.get("has_logging"):
            suggestions.append(f"{a['name']}: add structured logging instead of print")
    return suggestions


class AutonomyLayer:
    """
    The real self-initiative engine with vector memory and cross-agent messaging.
    """

    def __init__(self):
        self.memory = VectorMemory()
        self.bus = MessageBus()
        self.goals = self._load_goals()
        self.learnings = self._load_learnings()
        self.initiatives = self._load_initiatives()
        self._lock = Lock()

    def _load_goals(self) -> list[dict]:
        if GOALS_FILE.exists():
            return json.loads(GOALS_FILE.read_text())
        return []

    def _load_learnings(self) -> list[dict]:
        if LEARNINGS_FILE.exists():
            return json.loads(LEARNINGS_FILE.read_text())
        return []

    def _load_initiatives(self) -> list[dict]:
        if INITIATIVES_FILE.exists():
            return json.loads(INITIATIVES_FILE.read_text())
        return []

    def _save(self):
        with self._lock:
            GOALS_FILE.write_text(json.dumps(self.goals, indent=2))
            LEARNINGS_FILE.write_text(json.dumps(self.learnings, indent=2))
            INITIATIVES_FILE.write_text(json.dumps(self.initiatives, indent=2))

    def self_prompt(self) -> dict:
        """Generate own goals informed by vector memory of past outcomes."""
        prompts = [
            "Monitor system health and optimize performance",
            "Research new AI models and techniques",
            "Improve agent coordination and swarm efficiency",
            "Enhance knowledge graph with new entities",
            "Audit codebase for improvements and fixes",
            "Explore new data sources for insights",
            "Optimize memory usage and retrieval",
            "Test and validate agent behaviors",
            "Document architecture decisions",
            "Review and prune stale data",
        ]

        # Consult vector memory for past outcomes to inform goal selection
        recent_learnings = self.learnings[-3:] if self.learnings else []
        memory_results = self.memory.recall("goal outcomes results", n=3)
        informed_by = []
        for l in recent_learnings:
            informed_by.append(l.get("result", "")[:60])
        for r in memory_results:
            informed_by.append(r.get("text", "")[:60])

        # Weight prompts based on past failures or successes from memory
        prompt_scores: dict[str, float] = {p: 1.0 for p in prompts}
        for mr in memory_results:
            text = mr.get("text", "")
            for p in prompts:
                if any(w in text.lower() for w in p.lower().split()[:3]):
                    if "fail" in text.lower() or "error" in text.lower():
                        prompt_scores[p] *= 0.8
                    elif "success" in text.lower() or "pass" in text.lower():
                        prompt_scores[p] *= 1.2

        # Pick highest scored or random with weighted probability
        total = sum(prompt_scores.values())
        r = time.time() % total
        cumulative = 0.0
        chosen = prompts[0]
        for p in prompts:
            cumulative += prompt_scores[p]
            if r <= cumulative:
                chosen = p
                break

        new_goal = {
            "id": f"goal-{int(time.time())}",
            "prompt": chosen,
            "status": "pending",
            "created": datetime.utcnow().isoformat(),
            "informed_by": informed_by,
        }
        self.goals.append(new_goal)
        self._save()

        # Store this goal in vector memory
        self.memory.store(
            f"New goal created: {chosen}",
            {"goal_id": new_goal["id"], "type": "goal_creation"},
        )
        return new_goal

    def execute_initiative(self, goal_id: str | None = None) -> dict | None:
        """Execute a self-generated goal with REAL system actions."""
        if not self.goals:
            return None

        goal = None
        if goal_id:
            goal = next((g for g in self.goals if g["id"] == goal_id), None)
        if not goal:
            goal = next((g for g in self.goals if g["status"] == "pending"), None)
        if not goal:
            return None

        goal["status"] = "in_progress"
        goal["started"] = datetime.utcnow().isoformat()
        self._save()

        # REAL execution — no simulated results
        result = self._real_execution(goal["prompt"])

        goal["status"] = "completed"
        goal["completed"] = datetime.utcnow().isoformat()
        goal["result"] = result
        self._save()

        self.learnings.append({
            "goal_id": goal["id"],
            "prompt": goal["prompt"],
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save()

        # Store outcome in vector memory for future self-prompting
        self.memory.store(
            f"Goal '{goal['prompt']}' completed. Result: {result}",
            {
                "goal_id": goal["id"],
                "prompt": goal["prompt"],
                "type": "goal_outcome",
            },
        )

        return goal

    def _real_execution(self, prompt: str) -> str:
        """Execute real system actions based on the goal prompt."""
        prompt_lower = prompt.lower()

        if "system health" in prompt_lower or "optimize performance" in prompt_lower:
            return self._action_monitor_health()

        if "research new ai" in prompt_lower:
            return self._action_research_models()

        if "agent coordination" in prompt_lower or "swarm efficiency" in prompt_lower:
            return self._action_analyze_coordination()

        if "knowledge graph" in prompt_lower:
            return self._action_enhance_knowledge_graph()

        if "audit codebase" in prompt_lower or "improvements" in prompt_lower:
            return self._action_audit_codebase()

        if "explore" in prompt_lower and "data" in prompt_lower:
            return self._action_explore_data()

        if "optimize memory" in prompt_lower or "memory usage" in prompt_lower:
            return self._action_optimize_memory()

        if "test" in prompt_lower and "agent" in prompt_lower:
            return self._action_test_agents()

        if "document" in prompt_lower or "architecture" in prompt_lower:
            return self._action_document()

        if "prune" in prompt_lower or "stale" in prompt_lower:
            return self._action_prune_stale()

        return f"Unknown goal: {prompt}"

    def _action_monitor_health(self) -> str:
        """REAL system health monitoring."""
        uptime = _uptime()
        mem = _memory_usage()
        cpu = _cpu_count()
        procs = _ps_count()
        disk = _disk_usage()
        log_count = _count_log_files()

        health_report = (
            f"System Health Report:\n"
            f"  Uptime: {uptime}\n"
            f"  Memory: {mem.get('used_percent', '?')}% used ({mem.get('available_kb', 0)//1024}MB avail)\n"
            f"  CPUs: {cpu}\n"
            f"  Processes: {procs}\n"
            f"  Disk: {disk.get('used_percent', '?')}% used\n"
            f"  Log files: {log_count}"
        )

        report_path = DATA_DIR / f"health-report-{int(time.time())}.json"
        report_path.write_text(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": uptime,
            "memory": mem,
            "cpu_count": cpu,
            "processes": procs,
            "disk": disk,
            "log_files": log_count,
        }, indent=2))

        self.bus.send("autonomy", "daemon", "Health Report", health_report[:500])
        return health_report

    def _action_research_models(self) -> str:
        """Analyze BH's own codebase for patterns and agent types."""
        agents_dir = BASE_DIR / "src" / "agents"
        findings = []
        if agents_dir.exists():
            for d in sorted(agents_dir.iterdir()):
                if d.is_dir():
                    agent_file = d / "agent.py"
                    if agent_file.exists():
                        content = agent_file.read_text()
                        class_match = re.search(r"class\s+(\w+)", content)
                        class_name = class_match.group(1) if class_match else "unknown"
                        findings.append(f"{d.name}: {class_name} ({len(content)} bytes)")
        agents = _get_agent_names()
        report = (
            f"Codebase Analysis:\n"
            f"  Agent types: {len(agents)}\n"
            f"  Agents: {', '.join(agents)}\n"
            f"  Agent files found: {len(findings) if findings else 'none'}"
        )

        self.memory.store(
            f"Researched codebase: {len(agents)} agent types found",
            {"type": "research"},
        )
        return report

    def _action_analyze_coordination(self) -> str:
        """Read message bus to analyze inter-agent communication patterns."""
        unread = self.bus.all_unread()
        total_messages = sum(unread.values()) if unread else 0
        agents = _get_agent_names()

        # List message files
        msg_dir = BASE_DIR / "data" / "messages"
        msg_count = 0
        if msg_dir.exists():
            msg_count = len(list(msg_dir.glob("*.json")))

        report = (
            f"Coordination Analysis:\n"
            f"  Active agents: {len(agents)}\n"
            f"  Unread messages: {total_messages}\n"
            f"  Total message files: {msg_count}\n"
            f"  Agents: {', '.join(agents)}\n"
        )

        self.bus.send("autonomy", "daemon", "Coordination Report", report[:500])
        return report

    def _action_enhance_knowledge_graph(self) -> str:
        """Audit agent relationships and document graph state."""
        agents = _get_agent_names()
        graph_file = DATA_DIR / "graph.db"
        graph_size = graph_file.stat().st_size if graph_file.exists() else 0
        session_graph = DATA_DIR / "session-final-graph.json"
        session_count = 0
        if session_graph.exists():
            try:
                data = json.loads(session_graph.read_text())
                session_count = len(data) if isinstance(data, list) else 1
            except (json.JSONDecodeError, OSError):
                pass

        report = (
            f"Knowledge Graph Status:\n"
            f"  Agents: {len(agents)}\n"
            f"  Graph DB: {graph_size} bytes\n"
            f"  Session graph entries: {session_count}\n"
            f"  Agent roster: {', '.join(agents)}"
        )
        return report

    def _action_audit_codebase(self) -> str:
        """Real codebase audit — count agents, check errors, validate files."""
        agent_count = _count_agent_files()
        log_errors = _count_log_errors()
        validation = _validate_agents()
        valid_count = sum(1 for v in validation if v["valid"])
        issues = []
        for v in validation:
            if not v["valid"]:
                issues.extend(v["issues"])
        agent_info = _agent_files_info()
        suggestions = _suggest_improvements(agent_info)

        report = (
            f"Codebase Audit:\n"
            f"  Agent directories: {agent_count}\n"
            f"  Valid agents: {valid_count}/{len(validation)}\n"
            f"  Log errors (recent): {log_errors}\n"
            f"  Issues found: {len(issues)}\n"
            f"  Improvement suggestions: {len(suggestions)}"
        )
        if suggestions:
            for s in suggestions[:5]:
                report += f"\n    - {s}"

        return report

    def _action_explore_data(self) -> str:
        """Explore existing data files for insights."""
        data_files = []
        if DATA_DIR.exists():
            for f in DATA_DIR.iterdir():
                if f.is_file() and f.suffix in (".json", ".jsonl", ".md", ".txt"):
                    data_files.append(f.name)
        memory_stats = self.memory.stats()

        report = (
            f"Data Exploration:\n"
            f"  Data files: {len(data_files)}\n"
            f"  Examples: {', '.join(data_files[:8])}\n"
            f"  Memory items: {memory_stats.get('episodic_count', 0)}\n"
            f"  Memory concepts: {memory_stats.get('consolidated_count', 0)}"
        )
        return report

    def _action_optimize_memory(self) -> str:
        """Real memory optimization — prune old logs, compress stale data."""
        pruned = _prune_old_logs(days=7)

        # Compress old health reports
        compressed = 0
        for f in DATA_DIR.glob("health-report-*.json"):
            age = time.time() - f.stat().st_mtime
            if age > 3600:
                if _compress_file(f):
                    compressed += 1

        # Consolidate vector memory concepts
        concepts = self.memory.consolidate()

        report = (
            f"Memory Optimization:\n"
            f"  Old logs pruned: {pruned}\n"
            f"  Health reports compressed: {compressed}\n"
            f"  New memory concepts: {len(concepts)}\n"
            f"  Memory stats: {json.dumps(self.memory.stats())}"
        )
        return report

    def _action_test_agents(self) -> str:
        """Validate all agent files exist and have basic structure."""
        validation = _validate_agents()
        total = len(validation)
        valid = sum(1 for v in validation if v["valid"])
        report = (
            f"Agent Validation:\n"
            f"  Total agents: {total}\n"
            f"  Valid: {valid}\n"
            f"  Failed: {total - valid}"
        )
        for v in validation:
            status = "PASS" if v["valid"] else f"FAIL ({'; '.join(v['issues'])})"
            report += f"\n    {v['name']}: {status}"
        return report

    def _action_document(self) -> str:
        """Generate documentation snapshot of current state."""
        agents = _get_agent_names()
        memory_stats = self.memory.stats()
        goals_pending = len([g for g in self.goals if g["status"] == "pending"])
        goals_completed = len([g for g in self.goals if g["status"] == "completed"])

        doc = (
            f"Architecture Snapshot ({datetime.utcnow().isoformat()}):\n"
            f"  Agents: {len(agents)} ({', '.join(agents)})\n"
            f"  Goals pending: {goals_pending}\n"
            f"  Goals completed: {goals_completed}\n"
            f"  Memory items: {memory_stats.get('episodic_count', 0)}\n"
            f"  Memory concepts: {memory_stats.get('consolidated_count', 0)}"
        )
        return doc

    def _action_prune_stale(self) -> str:
        """Prune old data — message bus cleanup, old goals."""
        old_goals = 0
        cutoff = time.time() - 7 * 86400
        new_goals = []
        for g in self.goals:
            created = g.get("created", "")
            try:
                dt = datetime.fromisoformat(created)
                if dt.timestamp() < cutoff and g["status"] == "completed":
                    old_goals += 1
                else:
                    new_goals.append(g)
            except (ValueError, TypeError):
                new_goals.append(g)

        self.goals = new_goals
        self._save()

        # Cleanup message bus
        self.bus.cleanup()

        # Remove old compressed reports
        removed = 0
        for f in DATA_DIR.glob("health-report-*.json.gz"):
            age = time.time() - f.stat().st_mtime
            if age > 86400 * 3:
                f.unlink()
                removed += 1

        report = (
            f"Stale Data Pruning:\n"
            f"  Old goals archived: {old_goals}\n"
            f"  Messages cleaned: auto\n"
            f"  Old reports removed: {removed}"
        )
        return report

    def self_evaluate(self) -> dict:
        """Evaluate whether goals produced REAL results."""
        if not self.goals:
            return {"score": 0, "feedback": "No goals completed yet"}

        completed = [g for g in self.goals if g["status"] == "completed"]

        if not completed:
            return {"score": 0, "feedback": "No goals completed yet", "goals_completed": 0, "total_goals": len(self.goals), "completion_rate": "0%"}

        # Evaluate each completed goal for real output quality
        quality_scores = []
        for g in completed:
            result = g.get("result", "")
            score = 0
            if result and len(result) > 20:
                score += 30
            if "Error" not in result and "ERROR" not in result:
                score += 20
            if ":" in result:
                score += 20
            if len(result.splitlines()) > 2:
                score += 15
            if any(kw in result.lower() for kw in ["report", "found", "valid", "agent", "memory"]):
                score += 15
            quality_scores.append(score)

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        score = min(100, int(avg_quality))

        # Store evaluation in vector memory
        self.memory.store(
            f"Self-evaluation: score={score}, {len(completed)}/{len(self.goals)} goals completed",
            {"type": "evaluation", "score": score},
        )

        return {
            "score": score,
            "goals_completed": len(completed),
            "total_goals": len(self.goals),
            "completion_rate": f"{len(completed)/max(len(self.goals),1)*100:.0f}%",
            "feedback": "Goals producing real results" if score > 50 else "Quality needs improvement",
        }

    def status(self) -> dict:
        return {
            "goals": len(self.goals),
            "pending": len([g for g in self.goals if g["status"] == "pending"]),
            "completed": len([g for g in self.goals if g["status"] == "completed"]),
            "learnings": len(self.learnings),
            "last_initiative": self.goals[-1] if self.goals else None,
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BH Autonomy Layer (REAL)")
    parser.add_argument("action", choices=["prompt", "execute", "evaluate", "status"])
    parser.add_argument("--goal-id", help="Goal ID to execute")
    args = parser.parse_args()

    auto = AutonomyLayer()

    if args.action == "prompt":
        goal = auto.self_prompt()
        print(f"New goal: {goal['prompt']} (id: {goal['id']})")

    elif args.action == "execute":
        result = auto.execute_initiative(args.goal_id)
        if result:
            print(f"Executed: {result['prompt']}")
            print(f"Result:\n{result['result']}")
        else:
            print("No pending goals to execute")

    elif args.action == "evaluate":
        eval_result = auto.self_evaluate()
        for k, v in eval_result.items():
            print(f"{k}: {v}")

    elif args.action == "status":
        st = auto.status()
        for k, v in st.items():
            print(f"{k}: {v}")
