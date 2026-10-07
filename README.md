# BlackHornet — Autonomous Multi-Agent Swarm Framework

A self-improving, immortal, autonomous AGI colony system implementing PSO ring topology, ABC role-switching, and stigmergic communication for distributed autonomous agents.

## Architecture

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:D9A441,100:00D1C7&height=180&section=header&text=BlackHornet&fontSize=35&fontColor=ffffff&animation=fadeIn" width="100%" />

[![Codeberg](https://img.shields.io/badge/Codeberg-Dhaher--Labs%2FBlackHornet-2185D0?logo=codeberg)](https://codeberg.org/Dhaher-Labs/BlackHornet)
[![GitLab](https://img.shields.io/badge/Gitlab-Mirror-FC6D26?logo=gitlab)](https://gitlab.com/mulkymalikuldhr/BlackHornet)
[![GitHub](https://img.shields.io/badge/GitHub-Archive-181717?logo=github)](https://github.com/dhaher-labs/BlackHornet)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p align="center">
  <em>Part of <a href="https://dhaher-labs.codeberg.page">Dhaher Labs</a> &mdash; Autonomous Multi-Agent Swarm Framework</em>
</p>

## Overview

A self-improving, immortal, autonomous AGI colony system implementing PSO ring topology, ABC role-switching, and stigmergic communication for distributed autonomous agents.

## Architecture

```
src/
├── __init__.py           # Top-level package
├── colony_types/         # Pydantic v2 type system
├── bh_types/             # Unified type system (Pydantic v2)
├── core/                 # Core framework + SamanAI integration
│   ├── ast_sanitizer.py  # AST security gate (SamanAI §3.1)
│   ├── consensus_engine.py # Consensus + scoring (SamanAI §3.2)
│   ├── debate_arena.py   # Proposer/Challenger/Judge debate (SamanAI §3.2)
│   ├── workforce/        # OWL Agent Factory layer (SamanAI §3.3)
│   │   ├── agent_factory.py
│   │   ├── prompter.py
│   │   └── task_planner.py
├── agents/               # Agent implementations (9 core + 38 audit + 42 specialist)
├── agent_tools/          # MCP-based tool implementations
├── config/               # Pydantic settings + logging
├── swarm/                # PSO, ABC, stigmergy, swarm orchestrator
├── memory/               # Memory system (semantic, vector, episodic, 22 modules)
├── colony/               # Colony evolution, orchestrator, queen, nest
├── api/                  # Starlette REST API server
├── omega/                # Omega Engine (autonomous loop, SCS, council, brain, genome)
├── tools/                # 21 trading tools (L1-L5 layers)
├── mcp/                  # MCP protocol implementation + server
├── graph/                # Knowledge graph (10 modules)
├── thinking/             # Cognition modules (intention, goal, curiosity, priority)
├── sandbox/              # Code executor, Docker, WASM sandbox
├── security/             # Permissions, audit, analyzer
├── ui/                   # Dashboard, WebSocket, TUI, Cytoscape
├── browser/              # Browser automation
├── channels/             # Discord, Slack, Telegram, WhatsApp
├── integration/          # External integrations
├── integrations/         # Framework adapters
├── auto_discovery/       # LLM/model auto-discovery
├── delta/                # Delta engine (JS)
├── llm_router/           # LLM router (JS)
├── hermes_nous/          # Consciousness layers
├── bridge/               # QNA bridge + BH core bridge
└── harness/              # LangGraph-compatible harness (~100 files)
```

## Key Features

- **Swarm Intelligence**: PSO with 4 topologies, ABC role-switching, stigmergic coordination
- **Omega Engine**: Autonomous self-improvement loop with SCS, Council, Predictor, Brain
- **21 Trading Tools**: Full L1-L5 trading agent stack (market data → execution → journal)
- **Self-Healing**: Phi-accrual failure detector with automatic recovery
- **Self-Modification**: Propose-approve-apply pipeline with safety gating
- **104 Agents**: 9 core + 38 audit + 42 specialist agents
- **Multi-LLM**: 15+ providers via JeumpaLLM, Hermes, or direct API
- **Immortal Daemon**: Auto-upgrade, cross-repo sync, crash recovery
- **MCP Protocol**: Full Model Context Protocol implementation

## Quick Start

```bash
git clone https://codeberg.org/Dhaher-Labs/BlackHornet.git
cd BlackHornet
pip install -e .

# Entry points
bh-omega          # Omega Engine CLI
bh-colony         # Unified launcher
python -m src.hermes_quant   # Trading system
```

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.11+ |
| Framework | Pydantic v2, asyncio, Starlette |
| Storage | SQLite (FTS5), ChromaDB, Qdrant |
| LLM | JeumpaLLM, OpenAI, Anthropic, 15+ providers |
| Trading | yfinance, MT5, OANDA, Binance |

## Contributing

Part of [Dhaher Labs](https://dhaher-labs.codeberg.page) ecosystem.

## License

MIT License

---

## Audit Report

**Score: 62/100** | Last audit: 2026-07-25

| Category | Score |
|----------|-------|
| Architecture & Scope | 85 |
| Code Volume & Activity | 90 |
| Documentation | 80 |
| Test Coverage | 50 |
| Production Readiness | 40 |
| **Overall** | **62/100** |

### Fixed (2026-07-25)
- 39 broken import paths (`from tools.xxx` → `from src.tools.xxx`)
- Windows compatibility (hardcoded Linux paths removed)
- Type safety (`float = None` → `Optional[float]`)
- Orphan cleanup (dead modules deleted)
- Phantom docs removed (16 files)
- CI/CD pipeline added (GitHub Actions)

### Known Remaining Gaps
1. **Version crisis** — pyproject.toml=5.0.0, CHANGELOG=1.0.0, SOUL.md=5.0.0 (needs alignment)
2. **Test coverage** — 348 passing but low coverage for ~400 source files
3. **~150 modules undocumented** — only 11 classes have API docs
4. **8 numbered doc slots missing** — docs/04-08, 15-21

---

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:D9A441,100:00D1C7&height=100&section=footer" width="100%" />
</div>
