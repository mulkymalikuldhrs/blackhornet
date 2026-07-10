# BlackHornet — Autonomous Multi-Agent Swarm Framework

A self-improving, immortal, autonomous AGI colony system implementing PSO ring topology, ABC role-switching, and stigmergic communication for distributed autonomous agents.

## Architecture

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:D9A441,100:00D1C7&height=180&section=header&text=BlackHornet&fontSize=35&fontColor=ffffff&animation=fadeIn" width="100%" />

[![GitHub](https://img.shields.io/badge/GitHub-mulkymalikuldhaher%2FBlackHornet-181717?logo=github)](https://github.com/mulkymalikuldhaher/BlackHornet)
[![Codeberg](https://img.shields.io/badge/Codeberg-Mirror-2185D0?logo=codeberg)](https://codeberg.org/Dhaher-Labs/BlackHornet)
[![GitLab](https://img.shields.io/badge/Gitlab-Mirror-FC6D26?logo=gitlab)](https://gitlab.com/mulkymalikuldhr/BlackHornet)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p align="center">
  <em>Part of <a href="https://dhaher-labs.codeberg.page">Dhaher Labs</a> &mdash; Autonomous Multi-Agent Swarm Framework</em>
</p>

## 📋 Overview

A self-improving, immortal, autonomous AGI colony system implementing PSO ring topology, ABC role-switching, and stigmergic communication for distributed autonomous agents.

## 🏗️ Architecture

```
src/
├── __init__.py           # Top-level package exports
├── colony_types/         # Pydantic v2 type system
├── bh_types/              # Unified type system (Pydantic v2) [renamed from types/]
├── core/                 # Core framework (agents, LLM, event bus, tools)
├── agents/               # Agent implementations (manus, coder, researcher)
├── agent_tools/          # MCP-based tool implementations
├── config/               # Pydantic settings
├── swarm/                # PSO, ABC, stigmergy orchestration
├── memory/               # Memory system (semantic, vector, episodic)
├── colony/               # Colony evolution, self-modify, skill learner
├── api/                  # Starlette API server
├── harness/              # LangGraph harness (legacy)
└── integration/          # External integrations
```

## ✨ Key Features

- **Swarm Intelligence**: PSO with 4 topologies, ABC role-switching, stigmergic coordination
- **Self-Healing**: Phi-accrual failure detector with automatic recovery
- **Self-Modification**: Propose-approve-apply pipeline with safety gating
- **Multi-LLM**: 15+ providers via JeumpaLLM, Hermes, or direct API
- **Immortal Daemon**: Auto-upgrade, cross-repo sync, crash recovery

## ⚡ Quick Start

```bash
git clone https://github.com/mulkymalikuldhaher/BlackHornet.git
cd BlackHornet
pip install -e .
# Single launcher + single UI (control center on :8080)
python blackhornet.py --start
# or directly:
python -m src.integration.unified_launcher --port 8080
```

Open `http://localhost:8080` — the unified control center (10 panels: graph, agents,
colonies, tasks, tools, ecosystem, trading, memory, events, status).

## 🖤 Unified Launcher & Control Center (v6.2.0)

**One launcher, one UI.** `blackhornet.py --start` delegates to `unified_launcher`,
which boots **17 components** (event bus, graph store, memory, web server, dashboard,
provider hub, AMC bridge, BHQuant trading, colony health/radar/mesh, ecosystem orchestrator, …)
and serves the single UI.

- **Daemon**: `python blackhornet.py --deploy` (provisions the nest) · `--immortal` (self-healing loop)
- **UI API**: `src/ui/api_bridge.py` — 10 live REST endpoints (`/api/v1/*`)
- **Audit**: `AUDIT_IMPLEMENTATION_2026-07-10.md` — full gap report, verified live

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.11+ |
| Framework | Pydantic v2, asyncio |
| Storage | SQLite (FTS5), ChromaDB, Qdrant |
| LLM | JeumpaLLM, OpenAI, Anthropic |
| UI | stdlib `http.server` (no JS framework) |

## 🤝 Contributing

Part of [Dhaher Labs](https://dhaher-labs.codeberg.page) ecosystem.

## 📄 License

MIT License

---

## Audit Report

**Score: 62/100** | Last audit: 2026-06-27

| Category | Score |
|----------|-------|
| Architecture & Scope | 85 |
| Code Volume & Activity | 90 |
| Documentation | 80 |
| Test Coverage | 50 |
| Production Readiness | 40 |
| **Overall** | **62/100** |

### Known Gaps
1. ~~Circular import (`src/types` shadowing stdlib)~~ ✅ Fixed
2. **Bare repo behind** — worktree 29 commits ahead of bare; needs `git push bare main`
3. **Tests not runnable** — individual modules work but full suite blocked
4. **Credential exposure risk** — `.env` files in worktree (gitignored but present)
5. **Philosophical doc bloat** — 30+ doc files, some AI-hallucinated; needs pruning

---

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:D9A441,100:00D1C7&height=100&section=footer" width="100%" />
</div>
