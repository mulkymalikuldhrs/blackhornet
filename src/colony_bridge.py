#!/usr/bin/env python3
"""
BLACKHORNET — MultiColony Integration Bridge v2
================================================
Maps 6 capability domains with 30+ capabilities from the
AI-MultiColony-Ecosystem into BLACKHORNET's runtime.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger("BlackHornet.MultiColony")

MULTICOLONY_DIR = Path(os.getenv("MULTICOLONY_DIR",
    Path(__file__).parent.parent.parent / "AI-MultiColony-Ecosystem"))

CAPABILITY_DOMAINS = {
    "core": {
        "base_agent": "BaseAgent with state machine, tool invocation, LLM, event bus",
        "agent_loop": "Think-act-observe loop engine",
        "event_bus": "Pub/sub inter-agent communication",
        "llm_provider": "Multi-provider LLM (OpenAI, Anthropic, Google, Groq, NVIDIA, Ollama, vLLM)",
        "circuit_breaker": "Tool call resilience pattern",
        "persistence": "State persistence across restarts",
    },
    "agents": {
        "developer_agent": "Full-cycle software engineering agent",
        "browser_agent": "Playwright-based web automation agent",
        "research_agent": "Web research & synthesis agent",
        "operator_agent": "General-purpose autonomous operator",
        "memory_agent": "Agent with persistent memory subsystem",
        "coder_agent": "Code generation & review agent",
        "file_surfer_agent": "File system navigation agent",
        "web_surfer_agent": "Web browsing & data extraction agent",
        "multimodal_agent": "Vision + text multimodal agent",
    },
    "colony": {
        "coordinator": "Multi-agent task coordinator & dispatcher",
        "hands": "Agent hand-off protocol between specialists",
        "scheduler": "Task scheduling & prioritization engine",
        "a2a": "Agent-to-Agent protocol for inter-agent messaging",
        "mcp_server": "Model Context Protocol server for AI assistants",
        "mcp_client": "MCP client for connecting to external MCP servers",
    },
    "harness": {
        "guardrails": "Input/output safety guardrails & content filtering",
        "sandbox": "Docker/WASM isolated execution environment",
        "skills": "Extensible skill/plugin system for agents",
        "subagents": "Hierarchical subagent delegation framework",
        "models": "Model configuration, routing, and fallback",
        "tracing": "OpenTelemetry distributed tracing & observability",
    },
    "organism": {
        "sense": "Problem scanning engine (RSS, APIs, trend detection)",
        "decision": "Decision scoring with configurable criteria",
        "immune": "Safety system (loop detection, iteration limits, kill switches)",
        "factory": "Solution builder (code generation, service creation)",
        "growth": "Growth and marketing engine",
        "lifecycle": "Full lifecycle orchestrator",
    },
    "memory": {
        "knowledge_graph": "Entity-relation knowledge graph storage",
        "vector_store": "Vector embedding storage & similarity search",
        "session": "Conversation session state management",
        "paging": "Memory paging with sliding window",
        "condenser": "Memory condensation (8 strategies: NoOp, Recent, Observation, LLM, Amortized, BrowserOutput, Attention, Summary)",
    },
}

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
    Exposes 6 capability domains (core, agents, colony, harness, organism, memory)
    plus the original 11 quant_nanggroe engine capabilities.
    """

    def __init__(self):
        self.available = MULTICOLONY_DIR.exists()
        self.capabilities = self._scan_capabilities()
        self.colony_agents = self._discover_agents()

    def get_capabilities(self) -> Dict[str, Dict[str, str]]:
        """Return all capability domains with descriptions."""
        return {
            domain: dict(items)
            for domain, items in CAPABILITY_DOMAINS.items()
        }

    def get_capability(self, name: str) -> Optional[str]:
        """Look up a capability by dotted name (e.g. 'core.base_agent')."""
        if "." in name:
            domain, cap = name.split(".", 1)
            if domain in CAPABILITY_DOMAINS and cap in CAPABILITY_DOMAINS[domain]:
                return CAPABILITY_DOMAINS[domain][cap]
        for domain, items in CAPABILITY_DOMAINS.items():
            if name in items:
                return items[name]
        return COLONY_CAPABILITIES.get(name)

    def report_health(self) -> Dict[str, Any]:
        """Health report with per-domain capability counts."""
        s = self.status()
        domains = {}
        for domain, caps in CAPABILITY_DOMAINS.items():
            domains[domain] = len(caps)
        return {
            "available": s["available"],
            "domains": domains,
            "total_capabilities": sum(domains.values()),
            "quant_nanggroe_capabilities": len(COLONY_CAPABILITIES),
            "colony_available": s["available_count"],
            "colony_total": s["total_capabilities"],
            "strategies": len(self.get_strategies()),
            "agents_discovered": len(self.colony_agents),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

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

        dm_path = MULTICOLONY_DIR / "daemon_manager.py"
        if dm_path.exists():
            try:
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
        """Wire MultiColony patterns into BLACKHORNET."""
        results = {}
        engine_dir = MULTICOLONY_DIR / "quant_nanggroe" / "engine"
        if engine_dir.exists():
            sys.path.insert(0, str(MULTICOLONY_DIR / "quant_nanggroe"))
            results["engine_path"] = True
            logger.info("MultiColony engine path added to BLACKHORNET")
        else:
            results["engine_path"] = False

        mcp_server = MULTICOLONY_DIR / "quant_nanggroe" / "mcp" / "server.py"
        results["mcp_linked"] = mcp_server.exists()

        exchange_dir = MULTICOLONY_DIR / "quant_nanggroe" / "exchange"
        results["exchanges_linked"] = exchange_dir.exists()

        dm = MULTICOLONY_DIR / "daemon_manager.py"
        results["daemon_linked"] = dm.exists()

        return results

    def print_colony_report(self):
        """Pretty-print full colony + domain capability report."""
        s = self.status()
        health = self.report_health()
        print(f"\n{'='*60}")
        print(f"  BLACKHORNET — MultiColony Bridge v2")
        print(f"{'='*60}")
        print(f"  Colony Available: {'YES' if s['available'] else 'NO'}")
        if not s['available']:
            return

        print(f"\n  Capability Domains ({health['total_capabilities']} total):")
        for domain, caps in CAPABILITY_DOMAINS.items():
            print(f"\n    [{domain.upper()}]")
            for name, desc in caps.items():
                print(f"      {name:<25} {desc}")

        print(f"\n  Quant Nanggroe Engine ({s['available_count']}/{s['total_capabilities']}):")
        for cap, available in s['capabilities'].items():
            icon = "+" if available else "-"
            desc = COLONY_CAPABILITIES.get(cap.replace('engine.', 'engine.'), cap)
            print(f"    {icon} {cap:<25} {desc}")

        print(f"\n  Engine Modules: {s['engine_modules']}")
        print(f"  Strategies: {s['strategies']}")
        print(f"  Exchanges: {', '.join(s['exchanges'][:5])}")
        print(f"  Risk Modules: {len(s['risk_modules'])}")
        print(f"  Agents Discovered: {s['agents_discovered']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BLACKHORNET MultiColony Bridge v2")
    parser.add_argument("--status", action="store_true", help="Colony status")
    parser.add_argument("--integrate", action="store_true", help="Wire into hornet")
    parser.add_argument("--strategies", action="store_true", help="List strategies")
    parser.add_argument("--exchanges", action="store_true", help="List exchanges")
    parser.add_argument("--report", action="store_true", help="Full report")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--capabilities", action="store_true", help="List all capabilities")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    bridge = ColonyBridge()

    if args.health:
        print(json.dumps(bridge.report_health(), indent=2, default=str))
    elif args.capabilities:
        caps = bridge.get_capabilities()
        for domain, items in caps.items():
            print(f"\n[{domain}]")
            for name, desc in items.items():
                print(f"  {name:<25} {desc}")
    elif args.report or args.status:
        bridge.print_colony_report()
        if args.status:
            print(json.dumps(bridge.status(), indent=2, default=str))
    elif args.integrate:
        results = bridge.integrate_to_hornet()
        print(json.dumps(results, indent=2))
    elif args.strategies:
        for s in bridge.get_strategies():
            print(f"  {s['name']:<25} ({s['size_kb']}KB)")
    elif args.exchanges:
        for e in bridge.get_exchanges():
            print(f"  {e}")


if __name__ == "__main__":
    main()
