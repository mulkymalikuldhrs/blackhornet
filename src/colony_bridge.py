#!/usr/bin/env python3
"""
🖤 BLACKHORNET — MultiColony Integration Bridge
=================================================
Integrates AI-MultiColony-Ecosystem's production patterns into BLACKHORNET.

Patterns absorbed:
  1. Daemon Manager → multi-agent lifecycle orchestration
  2. Engine Pipeline → backtest + risk + execution + strategies
  3. MCP Server → AI assistant protocol bridge
  4. Exchange Connectors → multi-venue execution
  5. Strategy Registry → 10+ strategy types (SMC, ICT, Wyckoff, etc.)
  6. Factor Pipeline → alpha101, gtja191, qlib158 factors
  7. Risk Engine → VaR, Kelly, drawdown, correlation, kill switch
  8. Screener System → multi-timeframe market screening
  9. Auto-Release → autonomous deployment pipeline
  10. Shadow Scanner → code archaeology & extraction
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger("BlackHornet.MultiColony")

# ── Colony Discovery ──────────────────────────────────────────────────
MULTICOLONY_DIR = Path(os.getenv("MULTICOLONY_DIR",
    Path(__file__).parent.parent.parent / "AI-MultiColony-Ecosystem"))

COLONY_CAPABILITIES = {
    "engine.backtest":       "Walk-forward, Monte Carlo, CPCV, multi-asset",
    "engine.risk":           "VaR, Kelly, drawdown, correlation, kill-switch",
    "engine.strategies":     "SMC, ICT, Wyckoff, Fibonacci, Market Profile, VSA",
    "engine.factors":        "alpha101, gtja191, qlib158, academic, technical",
    "engine.execution":      "Paper, MT5, Alpaca, Binance, multi-venue",
    "engine.screener":       "Macro, intermarket, liquidity, positioning, DEX",
    "engine.ml":             "Feature engineering, ensemble models, signal gen",
    "daemon_manager":        "Multi-agent lifecycle, auto-start, health check",
    "mcp_server":            "Model Context Protocol for AI assistants",
    "exchange_connectors":   "MT5, Alpaca, IBKR, Binance, OKX, Bybit",
    "auto_release":          "Autonomous deployment & versioning",
}


class ColonyBridge:
    """
    Bridges BLACKHORNET nest with AI-MultiColony-Ecosystem patterns.
    Absorbs the best from both worlds.
    """

    def __init__(self):
        self.available = MULTICOLONY_DIR.exists()
        self.capabilities = self._scan_capabilities()
        self.colony_agents = self._discover_agents()

    def _scan_capabilities(self) -> Dict[str, bool]:
        """Scan which colony capabilities are available."""
        caps = {}
        base = MULTICOLONY_DIR / "quant_nanggroe"

        checks = {
            "backtest_engine":    base / "engine" / "backtest" / "engine.py",
            "risk_engine":        base / "engine" / "risk" / "manager.py",
            "strategy_registry":  base / "engine" / "strategies" / "registry.py",
            "factor_pipeline":    base / "engine" / "factors" / "pipeline.py",
            "execution_manager":  base / "engine" / "execution" / "manager.py",
            "ml_pipeline":        base / "engine" / "ml" / "signal_generator.py",
            "screener":           base / "engine" / "screener" / "orchestrator.py",
            "mcp_server":         base / "mcp" / "server.py",
            "daemon_manager":     MULTICOLONY_DIR / "daemon_manager.py",
            "auto_release":       MULTICOLONY_DIR / "AUTO_RELEASE_SYSTEM.py",
            "ecosystem_integration": MULTICOLONY_DIR / "ENHANCED_ECOSYSTEM_INTEGRATION.py",
        }

        for name, path in checks.items():
            caps[name] = path.exists()

        return caps

    def _discover_agents(self) -> List[Dict]:
        """Discover agents registered in the colony."""
        agents = []
        if not self.available:
            return agents

        # Check daemon_manager for agent configs
        dm_path = MULTICOLONY_DIR / "daemon_manager.py"
        if dm_path.exists():
            try:
                # Parse agent configs from daemon_manager
                import ast
                tree = ast.parse(dm_path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Dict):
                        agents_found = False
                        for key in node.keys:
                            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                if any(kw in key.value.lower() for kw in ['agent', 'bot', 'worker']):
                                    agents_found = True
                        if agents_found:
                            for key, value in zip(node.keys, node.values):
                                if isinstance(key, ast.Constant):
                                    agents.append({
                                        "agent_id": str(key.value),
                                        "config": "present",
                                        "source": "daemon_manager"
                                    })
            except Exception:
                pass

        return agents

    def get_engine_modules(self) -> List[str]:
        """List all available engine modules for import."""
        modules = []
        engine_dir = MULTICOLONY_DIR / "quant_nanggroe" / "engine"
        if engine_dir.exists():
            for py_file in engine_dir.rglob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                rel = py_file.relative_to(MULTICOLONY_DIR / "quant_nanggroe")
                mod = str(rel.with_suffix('')).replace('/', '.')
                modules.append(mod)
        return sorted(modules)

    def get_strategies(self) -> List[Dict]:
        """List all available trading strategies."""
        strategies = []
        strat_dir = MULTICOLONY_DIR / "quant_nanggroe" / "engine" / "strategies"
        if strat_dir.exists():
            for f in sorted(strat_dir.glob("*.py")):
                if f.name.startswith("_"):
                    continue
                size = f.stat().st_size
                strategies.append({
                    "name": f.stem.replace('_', ' ').title(),
                    "file": f.name,
                    "size_kb": round(size / 1024, 1),
                })
        return strategies

    def get_exchanges(self) -> List[str]:
        """List supported exchange connectors."""
        exchanges = []
        exc_dir = MULTICOLONY_DIR / "quant_nanggroe" / "exchange"
        if exc_dir.exists():
            for f in exc_dir.glob("*.py"):
                if f.name.startswith("_") or f.name == "base.py":
                    continue
                exchanges.append(f.stem.replace('_broker', '').replace('_', ' ').title())
        return exchanges

    def get_risk_modules(self) -> List[str]:
        """List available risk management modules."""
        risk_dir = MULTICOLONY_DIR / "quant_nanggroe" / "engine" / "risk"
        if risk_dir.exists():
            return [f.stem for f in sorted(risk_dir.glob("*.py"))
                    if not f.name.startswith("_")]
        return []

    def status(self) -> Dict:
        """Full colony status report."""
        return {
            "available": self.available,
            "colony_dir": str(MULTICOLONY_DIR) if self.available else None,
            "capabilities": self.capabilities,
            "available_count": sum(1 for v in self.capabilities.values() if v),
            "total_capabilities": len(self.capabilities),
            "engine_modules": len(self.get_engine_modules()),
            "strategies": len(self.get_strategies()),
            "exchanges": self.get_exchanges(),
            "risk_modules": self.get_risk_modules(),
            "agents_discovered": len(self.colony_agents),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def integrate_to_hornet(self) -> Dict[str, bool]:
        """
        Wire MultiColony patterns into BLACKHORNET.
        Returns status of each integration.
        """
        results = {}

        # 1. Import engine patterns into blackhornet context
        engine_dir = MULTICOLONY_DIR / "quant_nanggroe" / "engine"
        if engine_dir.exists():
            sys.path.insert(0, str(MULTICOLONY_DIR / "quant_nanggroe"))
            results["engine_path"] = True
            logger.info("MultiColony engine path added to BLACKHORNET")
        else:
            results["engine_path"] = False

        # 2. Link MCP server
        mcp_server = MULTICOLONY_DIR / "quant_nanggroe" / "mcp" / "server.py"
        results["mcp_linked"] = mcp_server.exists()

        # 3. Link exchange connectors
        exchange_dir = MULTICOLONY_DIR / "quant_nanggroe" / "exchange"
        results["exchanges_linked"] = exchange_dir.exists()

        # 4. Link daemon manager
        dm = MULTICOLONY_DIR / "daemon_manager.py"
        results["daemon_linked"] = dm.exists()

        return results

    def print_colony_report(self):
        """Pretty-print colony status."""
        s = self.status()
        print(f"\n{'='*60}")
        print(f"  🏛️  AI-MultiColony-Ecosystem → BLACKHORNET")
        print(f"{'='*60}")
        print(f"  Available: {'✅' if s['available'] else '❌'}")
        if not s['available']:
            print(f"  Clone: git clone https://github.com/dhaher-labs/AI-MultiColony-Ecosystem")
            return

        print(f"  Capabilities: {s['available_count']}/{s['total_capabilities']} available")
        print(f"\n  📊 Engine: {s['engine_modules']} modules")
        print(f"  📈 Strategies: {s['strategies']} types")
        print(f"  💱 Exchanges: {', '.join(s['exchanges'][:5])}")
        print(f"  🛡️  Risk: {len(s['risk_modules'])} modules")
        print(f"  🤖 Agents: {s['agents_discovered']} discovered")
        print(f"\n  Active Capabilities:")
        for cap, available in s['capabilities'].items():
            icon = "✅" if available else "❌"
            desc = COLONY_CAPABILITIES.get(cap.replace('engine.', 'engine.'), cap)
            print(f"    {icon} {cap:<25} {desc}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BLACKHORNET ← MultiColony Bridge")
    parser.add_argument("--status", action="store_true", help="Colony status")
    parser.add_argument("--integrate", action="store_true", help="Wire into hornet")
    parser.add_argument("--strategies", action="store_true", help="List strategies")
    parser.add_argument("--exchanges", action="store_true", help="List exchanges")
    parser.add_argument("--report", action="store_true", help="Full report")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    bridge = ColonyBridge()

    if args.report or args.status:
        bridge.print_colony_report()
        if args.status:
            print(json.dumps(bridge.status(), indent=2, default=str))
    elif args.integrate:
        results = bridge.integrate_to_hornet()
        print(json.dumps(results, indent=2))
    elif args.strategies:
        for s in bridge.get_strategies():
            print(f"  📈 {s['name']:<25} ({s['size_kb']}KB)")
    elif args.exchanges:
        for e in bridge.get_exchanges():
            print(f"  💱 {e}")


if __name__ == "__main__":
    main()
