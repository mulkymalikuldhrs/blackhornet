#!/usr/bin/env python3
"""
BH Self-Write Module
====================
Gives BlackHornet the ability to read, analyze, and modify its own source code.
This is a core AGI capability — the system can improve itself.

Capabilities:
1. Analyze agent code for patterns, issues, improvement opportunities
2. Generate improved versions of agent files
3. Apply changes safely (with rollback)
4. Generate new agent files from templates
5. Log all self-modifications for audit

Usage:
  python3 self_write.py analyze        # Analyze all agent files
  python3 self_write.py improve [name]  # Generate improvement for one agent
  python3 self_write.py new [name] [desc]  # Create new agent from template
"""

import os
import sys
import json
import time
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
AGENTS_DIR = BASE_DIR / "src" / "agents"
BACKUP_DIR = BASE_DIR / "data" / "agent_backups"
CHANGE_LOG = BASE_DIR / "data" / "self_write_log.json"
os.makedirs(BACKUP_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BH-SelfWrite] %(message)s")
log = logging.getLogger("BH-SelfWrite")


def _load_changelog() -> List[Dict]:
    if CHANGE_LOG.exists():
        return json.loads(CHANGE_LOG.read_text())
    return []


def _save_changelog(entries: List[Dict]):
    CHANGE_LOG.write_text(json.dumps(entries, indent=2))


class SelfWriter:
    """Analyzes and improves BH's own agent code."""

    def __init__(self):
        self.changelog = _load_changelog()

    def analyze(self) -> Dict:
        """Analyze all agent files for improvement opportunities."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "issues_found": 0,
            "improvements": [],
        }

        if not AGENTS_DIR.exists():
            results["error"] = f"Agents directory not found: {AGENTS_DIR}"
            return results

        for agent_dir in sorted(AGENTS_DIR.iterdir()):
            if not agent_dir.is_dir():
                continue
            agent_file = agent_dir / "agent.py"
            if not agent_file.exists():
                continue

            content = agent_file.read_text()
            agent_info = {
                "path": str(agent_file),
                "lines": len(content.split("\n")),
                "size": len(content),
                "issues": [],
            }

            # Analyze for common issues
            if "try:" not in content and "except" not in content:
                agent_info["issues"].append("missing error handling (no try/except)")
                results["issues_found"] += 1
            if "except:" in content or "except :" in content:
                agent_info["issues"].append("bare except clause (catches all)")
                results["issues_found"] += 1
            if "print(" in content and "import logging" not in content:
                agent_info["issues"].append("uses print() instead of logging")
                results["issues_found"] += 1
            if "import os" not in content:
                agent_info["issues"].append("no os import (may need it)")
            if agent_info["lines"] > 400:
                agent_info["issues"].append(f"large file ({agent_info['lines']} lines, consider splitting)")
                results["issues_found"] += 1
            if "TODO" in content or "FIXME" in content:
                agent_info["issues"].append("contains TODO/FIXME markers")
                results["issues_found"] += 1
            if "while True" in content and "sleep" not in content:
                agent_info["issues"].append("infinite loop without sleep")

            # Check for has_loop detection
            has_loop = any(kw in content for kw in ["def run", "def start", "while True", "async def"])
            agent_info["has_loop"] = has_loop

            results["agents"][agent_dir.name] = agent_info

        # Generate improvement suggestions
        self._suggest_improvements(results)

        return results

    def _suggest_improvements(self, results: Dict):
        """Generate specific improvement suggestions."""
        for name, info in results["agents"].items():
            for issue in info["issues"]:
                if "error handling" in issue:
                    results["improvements"].append({
                        "agent": name,
                        "type": "add_error_handling",
                        "suggestion": f"Wrap main logic of {name}/agent.py in try/except blocks",
                        "priority": "high" if info.get("has_loop") else "medium",
                    })
                elif "print()" in issue:
                    results["improvements"].append({
                        "agent": name,
                        "type": "replace_print_with_logging",
                        "suggestion": f"Replace print() calls in {name}/agent.py with logging",
                        "priority": "medium",
                    })

    def improve(self, agent_name: str) -> Dict:
        """Generate an improved version of an agent file."""
        agent_file = AGENTS_DIR / agent_name / "agent.py"
        if not agent_file.exists():
            return {"error": f"Agent {agent_name} not found"}

        # Backup original
        backup_path = BACKUP_DIR / f"{agent_name}_{int(time.time())}.py"
        shutil.copy2(str(agent_file), str(backup_path))

        content = agent_file.read_text()
        improvements = []
        new_content = content

        # 1. Add missing import logging if using print
        if "print(" in content and "import logging" not in content:
            new_content = "import logging\n" + new_content
            new_content = new_content.replace(
                'import logging\n', '', 1
            ) if 'import logging' in new_content else new_content
            # Insert logging after existing imports
            lines = new_content.split('\n')
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_at = i + 1
            log_setup = (
                '\nlogging.basicConfig(level=logging.INFO, '
                'format="%(asctime)s [BH] %(message)s")\nlog = logging.getLogger("BH")\n'
            )
            lines.insert(insert_at, log_setup)
            new_content = '\n'.join(lines)
            improvements.append("added logging")

        # 2. Wrap main logic in try/except if missing
        if "try:" not in new_content and "def main" in new_content or any(
            kw in new_content for kw in ["if __name__", "__main__"]):
            new_content = new_content + "\n\nif __name__ == '__main__':\n" if "if __name__" not in new_content else new_content
            improvements.append("ensure main guard present")

        # 3. Add agent metadata header
        if not content.startswith('"""'):
            header = (
                f'"""\n{agent_name.upper()} Agent — Auto-improved\n'
                f'Last modified: {datetime.now().isoformat()}\n'
                f'Improved by: BH Self-Write\n"""\n\n'
            )
            new_content = header + new_content
            improvements.append("added metadata header")

        if improvements:
            agent_file.write_text(new_content)
            entry = {
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "action": "improve",
                "improvements": improvements,
                "backup": str(backup_path),
            }
            self.changelog.append(entry)
            _save_changelog(self.changelog)
            log.info(f"Improved {agent_name}: {', '.join(improvements)}")
            return {"status": "improved", "agent": agent_name, "improvements": improvements}
        else:
            log.info(f"No improvements needed for {agent_name}")
            return {"status": "clean", "agent": agent_name, "message": "no improvements needed"}

    def new_agent(self, name: str, description: str) -> Dict:
        """Create a new agent from template."""
        agent_dir = AGENTS_DIR / name
        if agent_dir.exists():
            return {"error": f"Agent {name} already exists"}

        agent_dir.mkdir(parents=True, exist_ok=True)

        template = f'''"""
{name.upper()} Agent — {description}
Generated by BH Self-Write
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AGENT_NAME = "{name}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BH-{{AGENT_NAME}}] %(message)s")
log = logging.getLogger(f"BH-{{AGENT_NAME}}")


def run():
    """
    Main agent logic.
    Called by BH daemon every cycle.
    """
    log.info(f"{{AGENT_NAME}} agent cycle started")
    try:
        # TODO: implement agent logic
        result = {{"status": "ok", "agent": AGENT_NAME, "cycle": int(time.time())}}
        return result
    except Exception as e:
        log.error(f"Error in {{AGENT_NAME}} agent: {{e}}")
        return {{"status": "error", "error": str(e)}}


def analyze(data):
    """Process input data and return insights."""
    log.info(f"Analyzing data: {{type(data).__name__}}")
    return {{"insights": [], "data_points": len(data) if hasattr(data, '__len__') else 0}}


if __name__ == "__main__":
    run()
'''
        agent_file = agent_dir / "agent.py"
        agent_file.write_text(template)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": name,
            "action": "create",
            "description": description,
        }
        self.changelog.append(entry)
        _save_changelog(self.changelog)
        log.info(f"Created new agent: {name} ({description})")
        return {"status": "created", "agent": name, "file": str(agent_file)}

    def rollback(self, agent_name: str, version: str = "latest") -> Dict:
        """Rollback to a previous backup."""
        backups = sorted(BACKUP_DIR.glob(f"{agent_name}_*.py"))
        if not backups:
            return {"error": f"No backups found for {agent_name}"}

        backup = backups[-1] if version == "latest" else backups[0]
        agent_file = AGENTS_DIR / agent_name / "agent.py"
        shutil.copy2(str(backup), str(agent_file))

        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "action": "rollback",
            "restored_from": str(backup),
        }
        self.changelog.append(entry)
        _save_changelog(self.changelog)
        log.info(f"Rolled back {agent_name} to {backup.name}")
        return {"status": "rolled_back", "agent": agent_name, "backup": str(backup)}

    def status(self) -> Dict:
        """Return self-write module status."""
        return {
            "agents_count": len(list(AGENTS_DIR.iterdir())) if AGENTS_DIR.exists() else 0,
            "backups_count": len(list(BACKUP_DIR.glob("*.py"))),
            "modifications": len(self.changelog),
            "last_modification": self.changelog[-1] if self.changelog else None,
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BH Self-Write Module")
    parser.add_argument("action", choices=["analyze", "improve", "new", "rollback", "status"])
    parser.add_argument("--name", help="Agent name")
    parser.add_argument("--desc", help="Description for new agent")
    args = parser.parse_args()

    sw = SelfWriter()

    if args.action == "analyze":
        result = sw.analyze()
        print(f"Analysis at {result['timestamp']}")
        print(f"Issues found: {result['issues_found']}")
        for name, info in sorted(result["agents"].items()):
            print(f"\n  {name}: {info['lines']} lines")
            if info["issues"]:
                for issue in info["issues"]:
                    print(f"    ⚠ {issue}")
        print(f"\nSuggestions:")
        for imp in result["improvements"][:5]:
            print(f"  → {imp['agent']}: {imp['suggestion']} [{imp['priority']}]")

    elif args.action == "improve":
        if not args.name:
            result = sw.analyze()
            for imp in result["improvements"]:
                r = sw.improve(imp["agent"])
                print(f"  {r.get('status')}: {imp['agent']} — {r.get('improvements', [])}")
        else:
            r = sw.improve(args.name)
            print(json.dumps(r, indent=2))

    elif args.action == "new":
        if not args.name or not args.desc:
            print("Usage: self_write.py new --name <agent> --desc <description>")
            return
        r = sw.new_agent(args.name, args.desc)
        print(json.dumps(r, indent=2))

    elif args.action == "rollback":
        if not args.name:
            print("Usage: self_write.py rollback --name <agent>")
            return
        r = sw.rollback(args.name)
        print(json.dumps(r, indent=2))

    elif args.action == "status":
        s = sw.status()
        for k, v in s.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
