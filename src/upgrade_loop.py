import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger("UpgradeLoop")

BASE_DIR = Path(__file__).parent.parent
MULTICOLONY_DIR = Path(os.getenv("MULTICOLONY_DIR", str(BASE_DIR.parent / "AI-MultiColony-Ecosystem")))

UPGRADE_CATEGORIES = [
    "engine_patterns",
    "risk_modules",
    "exchange_connectors",
    "strategy_types",
    "screening_pipelines",
    "factor_libraries",
    "ml_models",
    "ui_components",
    "external_repos",
]


class BHUpgradeLoop:
    def __init__(self):
        self.cycle = 0
        self.upgrade_log: List[Dict] = []
        self.amc_available = MULTICOLONY_DIR.exists()
        self.current_stage = "plan"

    def detect_amc_changes(self) -> Dict:
        if not self.amc_available:
            return {"available": False}

        changes = {"available": True, "new_patterns": [], "updated_patterns": []}
        colony_state = Path(__file__).parent.parent / "data" / "colony_state.json"

        try:
            from colony_bridge import ColonyBridge
            bridge = ColonyBridge()
            prev = json.loads(colony_state.read_text()) if colony_state.exists() else {}

            s = bridge.status()
            current = {
                "engine_modules": s["engine_modules"],
                "strategies": s["strategies"],
                "exchanges": len(s["exchanges"]),
                "risk_modules": len(s["risk_modules"]),
                "captimestamp": s["timestamp"],
            }

            if prev:
                if current["engine_modules"] > prev.get("engine_modules", 0):
                    changes["new_patterns"].append(f"engine: +{current['engine_modules'] - prev['engine_modules']} modules")
                if current["strategies"] > prev.get("strategies", 0):
                    changes["new_patterns"].append(f"strategies: +{current['strategies'] - prev['strategies']}")

            colony_state.write_text(json.dumps(current, indent=2))
        except Exception as e:
            logger.warning(f"AMC detect failed: {e}")

        return changes

    def pull_from_amc(self) -> Dict[str, bool]:
        results = {}
        try:
            from colony_bridge import ColonyBridge
            bridge = ColonyBridge()
            integration = bridge.integrate_to_hornet()
            results["colony_integration"] = all(integration.values()) if integration else False
            results["engine_path"] = integration.get("engine_path", False)
            results["mcp_linked"] = integration.get("mcp_linked", False)
            results["exchanges_linked"] = integration.get("exchanges_linked", False)
            results["daemon_linked"] = integration.get("daemon_linked", False)

            s = bridge.status()
            results["modules_available"] = s["engine_modules"]
            results["strategies_available"] = s["strategies"]
            results["risk_modules"] = s["risk_modules"]
            results["agents_discovered"] = s["agents_discovered"]
        except Exception as e:
            logger.error(f"AMC pull failed: {e}")
            results["error"] = str(e)

        return results

    def upgrade_self(self) -> Dict:
        results = {}
        from colony_bridge import ColonyBridge
        bridge = ColonyBridge()

        results["pull_from_amc"] = self.pull_from_amc()

        latest = self.upgrade_log[-1] if self.upgrade_log else {}
        if not latest.get("pull_from_amc", {}).get("colony_integration"):
            logger.info("AMC integration pending — retrying on next cycle")
        else:
            logger.info(f"AMC integrated: {latest['pull_from_amc']['modules_available']} modules")

        return results

    def run_cycle(self) -> Dict:
        self.cycle += 1
        logger.info(f"Upgrade cycle #{self.cycle}")
        cycle = {
            "cycle": self.cycle,
            "timestamp": datetime.now().isoformat(),
            "amc_changes": self.detect_amc_changes(),
            "upgrade_result": {},
        }

        if self.amc_available:
            cycle["upgrade_result"] = self.upgrade_self()

        self.upgrade_log.append(cycle)
        if len(self.upgrade_log) > 10:
            self.upgrade_log = self.upgrade_log[-10:]

        # Auto-push after upgrade
        if self.cycle % 5 == 0:
            self.self_push()

        return cycle

    def self_push(self, message: str = "[auto] upgrade sync") -> bool:
        """Auto-commit and push upgrade results."""
        import subprocess
        try:
            r = subprocess.run(["git", "-C", str(BASE_DIR), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=10)
            if not r.stdout.strip():
                return True
            subprocess.run(["git", "-C", str(BASE_DIR), "add", "-A"],
                         capture_output=True, timeout=10)
            subprocess.run(["git", "-C", str(BASE_DIR), "commit", "-m", message],
                         capture_output=True, timeout=10)
            # Push to both remotes
            for remote in ["origin", "gitlab"]:
                subprocess.run(["git", "-C", str(BASE_DIR), "push", remote, "main"],
                             capture_output=True, timeout=60)
            return True
        except Exception as e:
            logger.warning(f"Push failed: {e}")
            return False

    def status(self) -> Dict:
        return {
            "cycle": self.cycle,
            "stage": self.current_stage,
            "amc_connected": self.amc_available,
            "upgrades_performed": len(self.upgrade_log),
            "last_upgrade": self.upgrade_log[-1] if self.upgrade_log else None,
        }


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Run one upgrade cycle')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--status', action='store_true', help='Show status')
    args = parser.parse_args()

    loop = BHUpgradeLoop()

    if args.run:
        result = loop.run_cycle()
        print(json.dumps(result, indent=2, default=str))
    elif args.status:
        print(json.dumps(loop.status(), indent=2, default=str))
    elif args.daemon:
        while True:
            loop.run_cycle()
            time.sleep(300)
    else:
        result = loop.run_cycle()
        print(json.dumps(result, indent=2, default=str))
        print(json.dumps(loop.status(), indent=2, default=str))


if __name__ == "__main__":
    main()
