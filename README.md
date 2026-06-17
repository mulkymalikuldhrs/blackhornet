# BlackHornet — Autonomous Multi-Agent Swarm Framework

A self-improving, immortal, autonomous AGI colony system implementing PSO ring topology, ABC role-switching, and stigmergic communication for distributed autonomous agents.

## Architecture

```
src/
├── __init__.py           # Top-level package exports
├── types/                # Unified type system (Pydantic v2)
│   ├── models.py              # 40+ enums and models
│   ├── colony.py              # ColonyConfig, TaskAssignment
│   ├── agent.py               # Agent type definitions
│   ├── messages.py            # Message models
│   ├── memory.py              # Memory models
│   ├── events.py              # Event models
│   ├── tools.py               # Tool models
│   └── tests.py               # Unit tests
├── core/                 # Core framework
│   ├── base_agent.py          # BaseAgent with state machine
│   ├── agent_loop.py          # Think-act-observe loop
│   ├── llm_provider.py        # Multi-provider LLM interface
│   ├── event_bus.py           # Pub/sub inter-agent messaging
│   ├── tool_registry.py       # Decorator-based tool registration
│   ├── tool_base.py           # Base tool class
│   ├── channel.py             # Multi-channel communication
│   ├── circuit_breaker.py     # Fault tolerance
│   ├── memory_manager.py      # Memory management
│   ├── persistence.py         # Storage backends
│   ├── observability.py       # Logging, metrics, tracing
│   ├── self_healing.py        # Phi-accrual failure detection
│   ├── pii_redaction.py       # PII redaction
│   ├── edge_cases.py          # Graceful degradation
│   └── tests.py               # Unit tests
├── agents/               # Agent implementations
│   ├── base.py                # BaseAgent, EventBus, CircuitBreaker
│   ├── registry.py            # AgentRegistry
│   ├── graph.py               # AgentGraph orchestration
│   ├── state.py               # Shared state models
│   ├── {manus,planner,...}.py # Agent implementations
│   └── {manus,planner,...}/   # Agent subpackages (prompts, agent code)
├── config/               # Configuration
│   └── settings.py            # Pydantic/dataclass settings
├── swarm/                # Swarm intelligence
│   ├── pso_swarm.py           # PSO ring/star/wheel/von-neumann
│   ├── abc_swarm.py           # ABC with role-switching
│   ├── stigmergy.py           # Pheromone field communication
│   └── swarm_orchestrator.py  # Unified PSO+ABC+Stigmergy
├── graph/                # Knowledge graph
│   ├── graph_store.py         # SQLite-backed graph DB
│   └── tests.py               # Unit tests
├── memory/               # Memory system
│   ├── working_memory.py      # Working memory management
│   ├── long_term_memory.py    # LTM with vector storage
│   └── tests.py               # Unit tests
├── thinking/             # Thinking engine
│   ├── thinking_engine.py     # Reasoning engine
│   ├── thought_tree.py        # Tree-of-thought
│   └── tests.py               # Unit tests
├── sandbox/              # Sandbox execution
│   ├── sandbox_manager.py     # Docker/WASM sandbox
│   └── tests.py               # Unit tests
├── auto_discovery/       # Module auto-discovery
│   ├── module_discovery.py    # Module discovery system
│   └── tests.py               # Unit tests
├── ui/                   # TUI interface
│   ├── tui.py                 # Terminal UI
│   └── tests.py               # Unit tests
├── integration/          # Integration launcher
│   ├── unified_launcher.py    # Main entry point
│   ├── event_hub.py           # Event hub
│   └── tests.py               # Unit tests
├── security/             # Security & audit
│   ├── audit.py               # Audit trail
│   └── permission.py          # Permission system
├── mcp/                  # MCP protocol integration
│   └── mcp_handler.py         # MCP message handling
├── channels/             # Communication channels
│   ├── telegram.py            # Telegram integration
│   ├── discord.py             # Discord integration
│   └── slack.py               # Slack integration
├── api/                  # API server
│   ├── app.py                 # Starlette API
│   └── routes/                # API routes
├── colony/               # Colony management
│   ├── manager.py             # ColonyManager
│   └── scheduler.py           # TaskScheduler
├── tools/                # Tool implementations
│   ├── browser/               # Browser automation
│   ├── vcs/                   # Version control
│   └── compute/               # Compute tools
├── browser/              # Browser automation
│   └── browser_manager.py     # Pooled browser management
├── harness/              # Original harness (legacy)
│   ├── agents/                # Legacy agent types
│   ├── community/             # Community integrations
│   └── persistence/           # Alembic migrations
├── integrations/         # External integrations
│   ├── autogen_adapter.py     # AutoGen adapter
│   ├── crewai_adapter.py      # CrewAI adapter
│   └── langgraph_adapter.py   # LangGraph adapter
├── delta/                # Delta system
├── organism/             # Organism system
└── plugins/              # Plugin system
    └── memory/                # Memory plugins
```

## Key Features

- **Swarm Intelligence**: PSO optimization with 4 topologies, ABC with dynamic role-switching
- **Stigmergic Communication**: Indirect agent coordination via pheromone field (O(n) scaling)
- **Self-Healing**: Phi-accrual failure detector with automatic recovery
- **Unified Type System**: 40+ Pydantic v2 models and enums across all domains
- **Multi-LLM Support**: OpenAI, Anthropic, and custom providers
- **MCP Integration**: Standard protocol for LLM↔agent interaction
- **Multi-Channel**: Telegram, Discord, Slack, WhatsApp
- **Security**: Audit trails, RBAC, PII redaction
- **Memory**: Working memory, LTM with vector storage, temporal facts

## Quick Start

```bash
pip install -e .
bh-colony  # Start the colony system
```

## Dependencies

- Python >= 3.11
- pydantic >= 1.10
- numpy, httpx, aiohttp, sqlalchemy
- See `pyproject.toml` for full list

## Running Tests

```bash
python -m unittest discover -s src -p "tests.py"
```

## License

MIT
