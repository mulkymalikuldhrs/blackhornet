# Changelog — BlackHornet

## [4.1.0] — 2026-06-17

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
- Rebrand: completed 12 remaining hermes references
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
