# BLACKHORNET OPERATING SYSTEM - PROJECT STRUCTURE

> **This document reflects the actual file structure as of 2026-07-25.**
> Phantom references from prior versions have been removed.

## Directory Tree

```
blackhornet-os/
├── README.md                              # Quick Start Guide
├── README_id.md                           # Indonesian README
├── README_zh.md                           # Chinese README
├── STRUCTURE.md                           # This file - Project Structure
├── PR.md                                  # Pull Request Guide & Templates
├── UPGRADE_PLAN.md                        # Autonomous Upgrade Roadmap
├── SECURITY.md                            # Security Policy
├── MASTER_SYSTEM_PROMPT.md                # Master System Prompt
├── SOUL.md                                # Soul / Identity Definition
├── LICENSE                                # License
├── pyproject.toml                         # Python Project Config
├── requirements.txt                       # Python Dependencies
├── docker-compose.yml                     # Docker Compose
├── Dockerfile                             # Docker Build
├── e2b.json                               # E2B Config
├── e2b.toml                               # E2B Config (alt)
├── deploy.sh                              # Deploy Script
├── hermes.sh                              # Hermes Control Script
├── install.sh                             # Install Script
├── sovereign.py                           # Sovereign Entry Point
├── test.sh                                # Test Runner Script
├── PRODUCTION.md                          # Production Overview
├── PRODUCTION_CHECKLIST.md                # Production Checklist
├── PRODUCTION_STATUS.md                   # Production Status
├── FINAL_REALIZATION.md                   # Final Realization Notes
├── REALIZATION_REPORT.md                  # Realization Report
├── SESSION-SUMMARY.md                     # Session Summary
├── HYPERGATE_MNEMOSYNE_STATUS.md          # Hypergate/Mnemosyne Status
├── GEMINI.md                              # Gemini Integration Notes
├── Dhaher_Labs_Constitution_v1.0.md       # Dhaher Labs Constitution
├── MULKY_REALISTIC_WEALTH_PLAN.md         # Wealth Plan
├── WEALTH_REALITY_CHECK.md               # Wealth Reality Check
├── PLAN.md                                # General Plan
├── REFERENCES_V2_FULL.md                  # Full References v2
├── PROXYGATELLM_FORENSIC_AUDIT_100pct.md  # ProxyGateLLM Audit
├── PROXYGATELLM_FULL_AUDIT_REPORT.md     # ProxyGateLLM Full Audit
│
├── src/                                   # Source Code (~29 packages)
│   ├── hermes_quant.py                # Main Trading Orchestrator (replaces bh_quant.py)
│   ├── watchdog.py                         # Watchdog Daemon
│   ├── immortal_daemon.py                  # Immortal Daemon
│   ├── hypergate.py                        # Hypergate Integration
│   ├── swarm_protocol.py                   # Swarm Protocol
│   ├── graphify_api.py                     # Graphify API
│   ├── memory_bridge.py                    # Memory Bridge
│   ├── mnemosyne_bridge.py                 # Mnemosyne Bridge
│   ├── colony_bridge.py                    # Colony Bridge
│   ├── upgrade_loop.py                     # Upgrade Loop
│   ├── user_alignment.py                   # User Alignment
│   ├── cin.py                              # CIN Module
│   ├── exceptions.py                       # Exceptions
│   │
│   ├── harness/                         # LangGraph-compatible Harness Framework (~226 files)
│   │   ├── agents/                        # Agent implementations
│   │   ├── community/                     # Community agents
│   │   ├── config/                        # Harness config
│   │   ├── guardrails/                    # Safety guardrails
│   │   ├── mcp/                           # MCP integration
│   │   ├── models/                        # LLM model configs
│   │   ├── persistence/                   # State persistence
│   │   ├── reflection/                    # Self-reflection
│   │   ├── runtime/                       # Runtime engine
│   │   ├── sandbox/                       # Sandboxed execution
│   │   ├── skills/                        # Skill registry
│   │   ├── subagents/                     # Sub-agent orchestration
│   │   ├── tools/                         # Tool framework
│   │   ├── tracing/                       # Observability tracing
│   │   ├── uploads/                       # Upload handling
│   │   ├── utils/                         # Utilities
│   │   ├── client.py                      # Harness client
│   │   └── __init__.py
│   │
│   ├── agents/                          # Agent Definitions (~146 files)
│   │   ├── autonomy/                     # Autonomous agent loop
│   │   │   ├── audit/, browser/, coder/, colony/, daemon/
│   │   │   ├── executor/, manus/, planner/, researcher/
│   │   │   ├── security/, specialists/, voice/
│   │   │   ├── audit_orchestrator.py, base.py, babyagi.py
│   │   │   ├── graph.py, orca.py, registry.py, state.py
│   │   │   └── ...
│   │   ├── agent_tools/                  # Agent tool implementations (~25 files)
│   │   ├── auto_discovery/               # Auto-discovery engine (~11 files)
│   │   ├── bh_types/                     # BH type definitions (~8 files)
│   │   ├── bridge/                       # Bridge implementations
│   │   ├── browser/                      # Browser automation
│   │   ├── channels/                     # Channel adapters (Telegram, Discord, Slack, WhatsApp)
│   │   ├── colony/                       # Colony system (~40 files)
│   │   ├── colony_types/                 # Colony type definitions (~11 files)
│   │   ├── config/                       # Configuration management
│   │   ├── core/                         # Core agent logic (~27 files)
│   │   ├── delta/                        # Delta computation
│   │   ├── graph/                        # Graph operations (~10 files)
│   │   ├── integration/                  # Integration layer
│   │   ├── integrations/                 # Third-party integrations (~8 files)
│   │   ├── llm_router/                   # LLM routing (~12 files)
│   │   ├── mcp/                          # Model Context Protocol
│   │   ├── memory/                       # Memory system (~23 files)
│   │   ├── omega/                        # Omega engine (~12 files)
│   │   ├── plugins/                      # Plugins
│   │   ├── sandbox/                      # Sandboxed execution (~9 files)
│   │   ├── security/                     # Security layer
│   │   ├── swarm/                        # Swarm intelligence (~7 files)
│   │   ├── thinking/                     # Cognitive reasoning (~18 files)
│   │   └── ui/                           # UI components (~11 files)
│   │
│   ├── tools/                           # Trading Tools (21 Agent Modules)
│   │   │
│   │   │   # ── L1: Data Layer ──────────────────────────────
│   │   ├── market_data_tool.py            # Market Data Agent: OHLCV, economic calendar, market overview
│   │   ├── chart_vision_tool.py           # Chart Vision Agent: Chart image analysis via vision LLM
│   │   │
│   │   │   # ── L2: Analysis Layer ──────────────────────────
│   │   ├── technical_analysis_tool.py     # Technical Analyst: SMC (BOS/CHoCH/OB/FVG/sweeps), indicators
│   │   ├── macro_sentiment_tool.py        # Macro/Fundamental/Sentiment: Risk-on/off regime, economic context
│   │   ├── smc_agent_enhanced.py          # Enhanced SMC Agent: Order Blocks, FVG, Liquidity Sweeps + Neural Grounding
│   │   ├── news_sentinel.py               # News Sentinel: Macro impact scoring with logarithmic time decay
│   │   ├── market_state_engine.py         # Market Regime Engine: TRENDING/RANGE/RISK_OFF/PANIC/NO_TRADE detection
│   │   │
│   │   │   # ── L3: Decision Layer ──────────────────────────
│   │   ├── strategy_tool.py               # Strategy Agent: 3-scenario analysis, confluence scoring
│   │   ├── risk_officer_tool.py           # Risk Officer: FULL VETO, 9 checkpoints, lot sizing (HARDCODED limits)
│   │   ├── portfolio_tool.py              # Portfolio Manager: Allocation, position management
│   │   ├── decision_engine.py             # Decision Synthesis Engine: Decision Matrix → Entry/SL/TP1-3
│   │   ├── pressure_engine.py             # Pressure Normalization: BUY_PRESSURE / SELL_PRESSURE vectors (0.0-1.0)
│   │   ├── strategy_lifecycle.py          # Darwinian Strategy Lifecycle: Auto-KILL on negative expectancy
│   │   │
│   │   │   # ── L4: Execution Layer ─────────────────────────
│   │   ├── execution_tool.py              # Execution Agent: Paper/MT5/OANDA/Binance execution
│   │   ├── kill_switch_tool.py            # Kill Switch: Emergency halt, auto-trigger, manual reset
│   │   ├── autoswitch_engine.py           # Auto-Switch Engine: Seamless provider failover
│   │   │
│   │   │   # ── L5: Learning Layer ──────────────────────────
│   │   ├── journal_tool.py                # Journal Agent: Trade logging, PnL, performance stats
│   │   ├── auditor_research_tool.py       # Post-Trade Auditor + Research: Plan vs execution, edge decay
│   │   ├── audit_logger.py                # Audit Logger: Full trail from sensor to final decision
│   │   ├── backtest_engine.py             # Backtest Engine: Dynamic Spread, Slippage, Latency Simulation
│   │   ├── math_engine.py                 # Math Engine: Statistical analysis, probability calculations
│   │   ├── shared_state.py                # Shared State between tools
│   │   ├── tests.py                       # Tool-level tests
│   │   └── __init__.py
│   │
│   ├── graph/                           # Knowledge Graph (Graphify)
│   │   ├── session_recorder.py            # Session Recorder: entity/relationship tracking
│   │   ├── graph_store.py                 # Graph Storage (SQLite property graph)
│   │   ├── entity_tracker.py              # Entity Tracker
│   │   ├── relationship_mapper.py         # Relationship Mapper
│   │   ├── graphify_pipeline.py           # Graphify Pipeline
│   │   ├── graph_visualizer.py            # Graph Visualization
│   │   ├── auto_updater.py                # Auto Graph Updater
│   │   └── ...
│   │
│   ├── api/                             # API Layer
│   │   ├── routes/                        # API Routes
│   │   ├── app.py                         # FastAPI App
│   │   ├── middleware.py                   # Middleware
│   │   └── schemas.py                     # Pydantic Schemas
│   │
│   ├── llm_router/                      # LLM Router
│   │   ├── cli.py, router.py, health.py, fallback.py
│   │   ├── cost_tracker.py, data_scanner.py, llm_scanner.py
│   │   └── ...
│   │
│   ├── memory/                          # Memory System
│   │   ├── manager.py, semantic.py, episodic.py, short_term.py
│   │   ├── long_term.py, vector.py, knowledge.py
│   │   ├── knowledge_graph.py, session.py
│   │   ├── condenser.py, condensers.py, consolidation.py
│   │   ├── hermes_bridge.py, memory_federation.py, unified_bridge.py
│   │   └── ...
│   │
│   ├── omega/                           # Omega Engine
│   │   ├── autopath.py, brain.py, cli.py, constitution.py
│   │   ├── council.py, evolution.py, genome.py
│   │   ├── predictor.py, score.py, scs.py, sync.py
│   │   └── ...
│   │
│   ├── mcp/                             # Model Context Protocol
│   │   ├── client.py, server.py, mcp_server.py
│   │   ├── permissions.py, protocol.py
│   │   └── ...
│   │
│   ├── core/                            # Core System
│   │   ├── agent_contracts.py, agent_loop.py, base_agent.py
│   │   ├── circuit_breaker.py, event_bus.py
│   │   ├── llm_provider.py, memory_manager.py
│   │   ├── meta_cognition.py, monitoring.py, observability.py
│   │   ├── persistence.py, pii_redaction.py
│   │   ├── reflexion.py, self_healing.py, self_improving.py
│   │   ├── skill_crystallizer.py, tool_base.py, tool_registry.py
│   │   └── ...
│   │
│   ├── sandbox/                         # Sandboxed Execution
│   │   ├── auto_merger.py, code_executor.py, docker.py
│   │   ├── sandbox_manager.py, self_modifier.py, wasm.py
│   │   └── test_runner.py
│   │
│   ├── integrations/                    # Third-party Adapters
│   │   ├── autogen_adapter.py, crewai_adapter.py
│   │   ├── langgraph_adapter.py, hermes_bridge.py
│   │   ├── blackhornet_quant_bridge.py, crucix_client.py
│   │   └── organism_bridge.py
│   │
│   └── (other packages: security/, swarm/, thinking/, ui/, etc.)
│
├── deploy/                              # Deployment Configuration
│   ├── blackhornet-hive.service          # Systemd service
│   ├── hermes-hive.service               # Hermes systemd service
│   ├── entrypoint.sh                     # Container entrypoint
│   └── entrypoint-omega.sh               # Omega entrypoint
│
├── skills/                              # 22 Skill Packages
│   ├── academic-paper-review/            bootstrap/              chart-visualization/
│   ├── claude-to-deerflow/               code-documentation/     consulting-analysis/
│   ├── data-analysis/                    deep-research/          find-skills/
│   ├── frontend-design/                  github-deep-research/   image-generation/
│   ├── music-generation/                 newsletter-generation/  podcast-generation/
│   ├── ppt-generation/                   skill-creator/          surprise-me/
│   ├── systematic-literature-review/     vercel-deploy-claimable/
│   ├── video-generation/                 web-design-guidelines/
│   └── (each contains SKILL.md + references/scripts/templates as needed)
│
├── scripts/                             # Infrastructure Scripts (~20 files)
│   ├── keeper.py                          # Cron-based health monitor (1-minute intervals)
│   ├── install_termux.sh                  # Android Termux installer with Termux:Boot
│   ├── install_server.sh                  # Linux server installer with systemd
│   ├── blackhornet_daemon.py              # Main daemon
│   ├── blackhornet_watchdog.py            # Watchdog daemon
│   ├── blackhornet-cli.py                 # CLI tool
│   ├── autonomy.py                        # Autonomy script
│   ├── activate-agi.sh                    # AGI activation
│   ├── agi-heartbeat.sh                   # AGI heartbeat
│   ├── auto-push.sh                       # Auto git push
│   ├── bootstrap.sh                       # Bootstrap script
│   ├── hermes-to-bh.sh                    # Hermes-to-BH bridge
│   ├── integrate_bridges.py               # Bridge integration
│   ├── keeper.py                          # Health keeper
│   ├── memory.py                          # Memory management
│   ├── message_bus.py                     # Message bus
│   ├── push-all.sh                        # Push all repos
│   ├── rebrand.py                         # Rebranding script
│   ├── run_mvp_tests.py                   # MVP test runner
│   ├── self-upgrade.sh                    # Self-upgrade script
│   ├── self_write.py                      # Self-write utility
│   ├── test_blackhornet_imports.py        # Import tests
│   ├── test_colony_bridge.py              # Colony bridge tests
│   ├── test_installer.sh                  # Installer tests
│   ├── test_launcher.py                   # Launcher tests
│   ├── test_llm_router_bridge.py          # LLM router bridge tests
│   ├── test_mcp.py                        # MCP tests
│   └── data/                              # Script runtime data
│       └── blackhornet-heartbeat.json
│
├── schemas/                             # Database Schemas
│   └── trading_journal.sql               # SQL schema for trade audit trail
│
├── tests/                               # Test Suite
│   ├── conftest.py                        # Pytest fixtures
│   ├── test_babyagi.py                    # BabyAGI tests
│   ├── test_blackhornet_units.py          # Unit tests
│   ├── test_bridges.py                    # Bridge tests
│   ├── test_core_behavior.py              # Core behavior tests
│   ├── test_hermes_nous.py               # Hermes Nous tests
│   ├── test_immortal_e2e.py              # End-to-end tests
│   ├── test_omega.py                      # Omega tests
│   ├── test_omega_cli.py                  # Omega CLI tests
│   ├── test_orca.py                       # Orca tests
│   ├── agents/                            # Agent-specific tests
│   ├── agent_tools/                       # Agent tool tests
│   ├── colony/                            # Colony tests
│   ├── core/                              # Core tests
│   └── memory/                            # Memory tests
│
├── ui/                                  # Web UI
│   ├── index.html                         # Main UI
│   ├── game.js                            # Game logic
│   ├── style.css                          # Styles
│   └── server.py                          # UI server
│
├── swarm-config/                        # Swarm Configuration
│   ├── dhaher-swarm.sh                    # Swarm control
│   ├── github-sync.sh                     # GitHub sync
│   ├── swarm-guardian.sh                  # Swarm guardian
│   ├── watchdog.py                        # Swarm watchdog
│   └── install/                           # Install helpers
│
├── exports/                             # Exported Data
│   └── session-2026-06-18/               # Exported session
│
├── docs/                                # Documentation
│   ├── 00-vision/                        VISION.md
│   ├── 01-prd/                           PRD.md
│   ├── 02-arch/                          ARCHITECTURE.md, BH_V2_RESEARCH_ARCHITECTURE.md
│   ├── 03-spec/                          SPEC.md
│   ├── 07-security/                      SECURITY.md
│   ├── 09-testing/                       TESTING.md
│   ├── 10-roadmap/                       ROADMAP.md
│   ├── 11-adr/                           ADR-001-omega-as-core-engine.md
│   ├── 12-tasks/                         TASKS.md
│   ├── 13-changelog/                     CHANGELOG.md
│   ├── 14-rules/                         PROJECT_RULES.md
│   ├── 17-glossary/                      GLOSSARY.md
│   ├── plans/                            # Planning documents
│   │   ├── 2026-06-17-phase14-mesh-mcp-ui-trading.md
│   │   ├── 2026-06-17-production-readiness.md
│   │   └── 2026-06-26-bh-qna-convergence.md
│   ├── BH_SYSTEM.md                      # BH System documentation
│   ├── api.md                            # API documentation
│   ├── litellm-mcp-setup.md              # LiteLLM MCP setup guide
│   └── performance-improvements.md       # Performance docs
│
└── data/                                # Runtime Data (generated)
    └── session-export/                   # Session export directory
```

---

## File-by-File Breakdown

### Root Files

| File | Purpose |
|------|---------|
| `README.md` | Quick start, architecture overview, commands |
| `README_id.md` | Indonesian README |
| `README_zh.md` | Chinese README |
| `STRUCTURE.md` | This file - project structure documentation |
| `PR.md` | PR templates, review criteria, workflow |
| `UPGRADE_PLAN.md` | Autonomous upgrade roadmap |
| `SECURITY.md` | Security policy |
| `MASTER_SYSTEM_PROMPT.md` | Master system prompt for LLM |
| `SOUL.md` | Soul / identity definition |
| `pyproject.toml` | Python project configuration |
| `requirements.txt` | Python dependencies |
| `docker-compose.yml` | Docker Compose config |
| `Dockerfile` | Docker build definition |
| `deploy.sh` | Deploy script |
| `hermes.sh` | Hermes control script |
| `install.sh` | Install script |
| `sovereign.py` | Sovereign entry point |
| `test.sh` | Test runner |
| `PRODUCTION.md` | Production overview |
| `PRODUCTION_CHECKLIST.md` | Production checklist |
| `PRODUCTION_STATUS.md` | Production status |

### Source Code (`src/`)

| File | Purpose |
|------|---------|
| `hermes_quant.py` | **Main Trading Orchestrator** (Telegram bot, tool orchestration, memory management) |
| `watchdog.py` | Process monitor with exponential backoff, crash loop detection |
| `immortal_daemon.py` | Immortal daemon process |
| `hypergate.py` | Hypergate integration |
| `swarm_protocol.py` | Swarm protocol handler |
| `graphify_api.py` | Graphify API interface |
| `memory_bridge.py` | Memory bridge to external systems |
| `mnemosyne_bridge.py` | Mnemosyne bridge integration |
| `colony_bridge.py` | Colony bridge integration |

### Trading Tools (`src/tools/`)

| File | Layer | Agent Name | Key Methods |
|------|-------|------------|-------------|
| `market_data_tool.py` | L1 | Market Data Agent | `get_ohlcv()`, `get_economic_calendar()`, `get_market_overview()` |
| `chart_vision_tool.py` | L1 | Chart Vision Agent | `analyze_chart()` |
| `technical_analysis_tool.py` | L2 | Technical Analyst | `analyze()`, SMC detection |
| `macro_sentiment_tool.py` | L2 | Macro/Sentiment | `get_regime()`, `get_sentiment()` |
| `smc_agent_enhanced.py` | L2 | SMC Enhanced | Order Block, FVG, Liquidity Sweep |
| `news_sentinel.py` | L2 | News Sentinel | `score_impact()`, time decay |
| `market_state_engine.py` | L2 | Market Regime Engine | `detect_regime()`, NO_TRADE gate |
| `strategy_tool.py` | L3 | Strategy Agent | `generate_scenarios()`, confluence |
| `risk_officer_tool.py` | L3 | Risk Officer (VETO) | `check_trade()`, 9 checkpoints |
| `portfolio_tool.py` | L3 | Portfolio Manager | `assess()`, `status()` |
| `decision_engine.py` | L3 | Decision Synthesis | Decision Matrix, Entry/SL/TP |
| `pressure_engine.py` | L3 | Pressure Normalization | BUY/SELL pressure vectors |
| `strategy_lifecycle.py` | L3 | Strategy Lifecycle | Auto-KILL, expectancy tracking |
| `execution_tool.py` | L4 | Execution Agent | `paper_trade()`, `status()` |
| `kill_switch_tool.py` | L4 | Kill Switch | `activate()`, `status()`, auto-trigger |
| `autoswitch_engine.py` | L4 | Auto-Switch Engine | Provider failover |
| `journal_tool.py` | L5 | Journal Agent | `log_trade()`, `get_stats()` |
| `auditor_research_tool.py` | L5 | Auditor + Research | `audit_recent()`, `suggest_improvements()` |
| `audit_logger.py` | L5 | Audit Logger | Full decision trail |
| `backtest_engine.py` | L5 | Backtest Engine | Spread, Slippage, Latency sim |
| `math_engine.py` | L5 | Math Engine | Statistical computations |

### Harness Framework (`src/harness/`)

LangGraph-compatible agent orchestration framework. ~226 files across 16 subpackages:
`agents/`, `community/`, `config/`, `guardrails/`, `mcp/`, `models/`, `persistence/`, `reflection/`, `runtime/`, `sandbox/`, `skills/`, `subagents/`, `tools/`, `tracing/`, `uploads/`, `utils/`

### Infrastructure Scripts (`scripts/`)

| File | Purpose |
|------|---------|
| `keeper.py` | Cron-based health monitor (1-minute intervals) |
| `blackhornet_daemon.py` | Main daemon process |
| `blackhornet_watchdog.py` | Watchdog daemon |
| `blackhornet-cli.py` | CLI tool |
| `install_termux.sh` | Android Termux installer |
| `install_server.sh` | Linux server installer with systemd |
| `bootstrap.sh` | Bootstrap script |
| `auto-push.sh` | Auto git push |
| `self-upgrade.sh` | Self-upgrade script |

### Database Schema (`schemas/`)

| File | Purpose |
|------|---------|
| `trading_journal.sql` | SQL schema for trade audit trail |

### Deployment (`deploy/`)

| File | Purpose |
|------|---------|
| `blackhornet-hive.service` | Systemd service for BlackHornet |
| `hermes-hive.service` | Systemd service for Hermes |
| `entrypoint.sh` | Container entrypoint |
| `entrypoint-omega.sh` | Omega-specific entrypoint |

### Skills (`skills/`)

22 skill packages including: `academic-paper-review`, `bootstrap`, `chart-visualization`, `claude-to-deerflow`, `code-documentation`, `consulting-analysis`, `data-analysis`, `deep-research`, `find-skills`, `frontend-design`, `github-deep-research`, `image-generation`, `music-generation`, `newsletter-generation`, `podcast-generation`, `ppt-generation`, `skill-creator`, `surprise-me`, `systematic-literature-review`, `vercel-deploy-claimable`, `video-generation`, `web-design-guidelines`

### UI (`ui/`)

| File | Purpose |
|------|---------|
| `index.html` | Main web UI |
| `game.js` | Game logic |
| `style.css` | Styles |
| `server.py` | UI server |

### Documentation (`docs/`)

Organized by numbered sections: `00-vision/` through `17-glossary/`, plus `plans/` and supplementary docs.

---

## Source Repository Map

| BH Component | Source Repository | Version | Adaptation Notes |
|------------------|-------------------|---------|------------------|
| Core agent loop | `nousresearch/hermes` | latest | Adapted from Hermes Agent; added trading tools, Telegram bot, risk framework |
| 10 tools (v3.1) | `dhaher-labs/Quant-Nanggroe-AI` | v15.2.0 | Ported from TypeScript services to Python tools; adapted Deterministic Agent Execution |
| Alpha factors | `dhaher-labs/Vibe-Trading` | v0.1.8 | 452 alphas (qlib158, alpha101, gtja191, academic) - planned integration (PR-004) |
| Swarm pipeline | `dhaher-labs/AutoHedge` | latest | Director/Quant/Risk/Execution pipeline - planned integration (PR-005) |
| Colony framework | `dhaher-labs/AI-MultiColony-Ecosystem` | v8.0.0 | Agent registry, lifecycle management concepts - architecture reference |

---

**Document maintained by Mulky Malikul Dhaher**
**Repository: github.com/dhaher-labs/blackhornet-os**
