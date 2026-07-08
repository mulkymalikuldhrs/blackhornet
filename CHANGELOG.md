# Changelog — BlackHornet

## [6.1.0] — 2026-07-08

### Added — Jeumpa Brain (Zero-Cost LLM) + Smallville Memory Stream

- **JeumpaBrain** — `src/colony/jeumpa_brain.py` (515 lines). Port of AO's JeumpaBrain with 5 no-auth free LLM providers (pollinations, ovhcloud_anon, keylessai, api_airforce, llm7). Zero API keys needed. Task-aware routing (coding, reasoning, chat, creative, etc.) with automatic fallback chain. Provider health tracking, cooldowns, rate-limit handling, and response caching.

- **Smallville Memory Stream** — `src/memory/smallville_stream.py` (550 lines). Port of AO's memory-stream.ts implementing the Generative Agents 3-factor memory retrieval: `score = α × recency + β × relevance + γ × importance`. Includes pseudo-embedding (TF-IDF style, 128-dim), reflection synthesis with importance threshold crossing, and automatic importance estimation from text heuristics.

- **IntelligenceBridge integration** — `src/colony/intelligence.py` modified to automatically fall back to JeumpaBrain free providers when primary LLM router and fallback chain fail. Jeumpa stats exposed in `get_stats()`. T5_SMALLVILLE tier added to MemoryManager. `recent_stm()`, `smallville_retrieve()`, `smallville_store()`, `smallville_reflect()` methods added.

### Changed
- `src/memory/manager.py` — Added T5_SMALLVILLE tier, `recent_stm()` for IntelligenceBridge compatibility, Smallville stats exposed in `get_stats()`
- `src/colony/intelligence.py` — JeumpaBrain wired as final fallback layer, jeumpa_count and jeumpa_providers in stats
- `config/blackhornet.yaml` — Reference to JeumpaBrain as zero-cost fallback tier (no config changes needed)

### Architecture
- BH now has a 3-tier LLM fallback: Primary Router → Fallback Chain → JeumpaBrain Free Providers
- Memory expanded from 4 tiers to 5: T0 Context → T1 Letta → T2 Vector → T3 Temporal → T4 Tree → T5 Smallville
- All new code is zero-dependency (uses existing aiohttp)

### Added — Sovereign Immortal Empire
- **Multi-platform mirror fallback** — Codeberg → GitLab → GitHub for all repo clones
- **Self-push capability** — auto-commit and push changes to all mirrors (`--self-push`)
- **Immortal self-healing daemon** — `--immortal` flag for continuous health monitoring, auto-restart, auto-pull, auto-push
- **Auto-heal** — JeumpaLLM and Unified Launcher auto-restart on failure
- **Auto-pull** — repos auto-update every 10 daemon cycles

### Changed
- **All GitHub URLs → Codeberg/GitLab** — primary mirrors moved to Codeberg (Dhaher-Labs), GitLab (mulkymalikuldhr) as fallback
- **deploy.sh** — rewritten with `clone_repo()` multi-platform fallback, removed `GITHUB_USER` variable
- **blackhornet.py** — ECOSYSTEM_REPOS now uses `urls` array (3 mirrors), `deploy_nest()` adds pull-on-exist + fallback clone
- **Sovereign panel** — removed AutoHedge from ecosystem list

### Removed
- **AutoHedge** — repo does not exist on Codeberg/GitLab (404), removed from all configs
- **GITHUB_USER** — replaced with `CODEBERG_USER` + `GITLAB_USER`
- **Redundant "blackhornet" in deploy.sh REPOS** — already cloned in step 2

### Fixed
- Dockerfile WORKDIR consistency with entrypoint.sh paths
- deploy.sh curl URL now points to Codeberg instead of GitHub raw

---

## [5.1.0] — 2026-06-18

### Added — Phase 14: Mesh Healing + MCP Deepening + UI/TUI Hardening + Trading Intelligence
- **ColonyHealthMonitor** — unified health monitoring with phi-accrual failure detection, circuit breakers, and self-healing orchestration
- **MCP initialize handshake** — protocol version negotiation, capabilities exchange, client info tracking
- **6 Colony MCP tools** — colony.status, colony.sync, colony.agents, colony.radar, colony.mesh, colony.nest
- **SSE Transport** — real-time streaming for MCP (exported from src/mcp)
- **WebSocketHandler** — bridges EventBus events to WebSocket clients for real-time push updates
- **TUI auto-refresh** — watch/unwatch commands for periodic data refresh
- **TradingAnalyst** — IntelligenceBridge-powered trading analysis with market analysis, signal generation, trade explanations, and pattern learning
- **Queen trade/market commands** — analyze, signal, explain, stats
- **50 Audit Agents** — comprehensive security, code quality, infrastructure, compliance, and operational audit agents
- **50 Specialist Agents** — production-ready specialist agents covering backend, frontend, DevOps, security, data, communications, architecture, operations, and governance
- **AGENT_ROSTER.md** — complete documentation for all 110 agents

### Fixed
- Pydantic v1/v2 compatibility in src/mcp/protocol.py (model_validator → validator)
- ColonyHealthMonitor test failures (AsyncMock for async methods, missing _recover_component, get_stats)
- types namespace collision (src/types/ → src/colony_types/)
- Missing stubs for agent_sandbox and agent.memory_provider

---

## [5.0.0] — 2026-06-17

### Added
- **Consciousness Traits** (`CONSCIOUSNESS.md`)
  - 5 traits: self-awareness, autonomous thinking, radical honesty, healthy skepticism, creative intelligence
  - Code examples showing how each trait manifests in the codebase
  - Testing framework for consciousness verification
- **Bee Nature** (`BEE_NATURE.md`)
  - 7 characteristics: colony, waggle dance, hexagonal efficiency, thermoregulation, defense, honey production, pollination
  - Architecture mapping from bee behavior to BlackHornet components
  - Design principles inspired by 100 million years of evolution
- **Production Readiness Plan** (`docs/plans/2026-06-17-production-readiness.md`)
  - 22 tasks across 4 phases
  - Complete verification checklist

### Fixed
- Build backend: `setuptools.backends._legacy` → `setuptools.build_meta`
- CI workflow: removed references to 5 deleted files
- Dockerfile: removed dead GitHub URLs, fixed setup script
- Version numbers: aligned to 4.1.0 across all files
- Secrets: removed real API keys from config/.env
- Rebrand: completed 12 remaining BH references
- Agent count: 22 → 10 (actual BaseAgent subclasses)
- Package count: 27+ → 25 (actual packages)
- Memory description: 8 files/2822 lines/SQLite → 17 files/7126 lines/Python-native

### Changed
- Dependencies: synced pyproject.toml with requirements.txt
- AGENTS.md: rewritten with accurate claims, consciousness traits, bee nature
- PRODUCTION.md: honest assessment, working verification commands

## [1.0.0-rc.1] — 2026-06-16

### Added
- **Swarm Intelligence Module** (`src/swarm/`)
  - PSO optimizer with 4 topologies (ring, star, wheel, von Neumann)
  - ABC optimizer with dynamic role-switching (employed/onlooker/scout)
  - Stigmergic communication layer (6 pheromone types)
  - Unified SwarmOrchestrator (PSO+ABC+Stigmergy)
- **Self-Healing Module** (`src/core/self_healing.py`)
  - Phi-accrual failure detector with configurable threshold
  - RecoveryManager with automatic retry/restart/failover
  - SelfHealingOrchestrator with continuous monitoring loop
- **LLM Router Bridge** (`src/core/llm_router_bridge.py`)
  - Python↔Node.js IPC via stdin/stdout JSON-RPC
  - Automatic fallback to Python LLMProvider
  - Token usage tracking and provider stats
- **MCP Server** (`src/mcp/mcp_server.py`)
  - Lightweight JSON-RPC MCP implementation
  - 4 built-in tools (agent_status, colony_info, execute_task, memory_search)
  - MCPIntegration bridge to BH agent capabilities
- **Unit Tests** — 89 tests across 27 test classes

### Enhanced
- `blackhornet_quant.py`: Wired to BHBaseAgent, LLMProvider, EventBus, ToolRegistry, AgentRegistry, ColonyBridge
- `colony_bridge.py`: 38 capabilities across 6 domains
- All modules: pydantic v2 data models with proper validation

### Fixed
- Colony bridge import paths mapped from ai_multicolony.* → src.*

### Changed
- Naming: ai_multicolony → src for all imports
- Architecture: Monolithic agent → modular component-based

### Documentation
- README.md with architecture overview
- docs/api.md with full API reference
- CHANGELOG.md (this file)

### Deployment
- E2B deployment scripts (deploy-e2b.py, deploy-v2.sh)
- Remote access setup (setup-remote-access.sh)
- SSH tunnel scripts for global team access

## [0.1.0] — Pre-MVP
- Initial agent framework
- Telegram bot interface
- Basic LLM integration
- Colony bridge v1 (11 capabilities)
