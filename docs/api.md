# BlackHornet API Reference

## Core

### BaseAgent (`src.core.base_agent`)
- `BaseAgent(config)` — Main agent class with state machine (IDLE→THINKING→ACTING→OBSERVING→LEARNING)
- Methods: `run()`, `think()`, `act()`, `observe()`, `learn()`
- States: IDLE, THINKING, ACTING, OBSERVING, LEARNING, ERROR, STOPPED

### EventBus (`src.core.event_bus`)
- `EventBus()` — Publisher/subscriber event system
- Methods: `subscribe(channel, handler)`, `publish(channel, event)`, `unsubscribe(channel, handler)`

### ToolRegistry (`src.core.tool_registry`)
- `ToolRegistry()` — Decorator-based tool registration
- `@registry.register(name, description)` — Register a function as a tool
- `get_tools()` — Returns OpenAI-compatible tool schemas

### LLMProvider (`src.core.llm_provider`)
- `LLMProvider(config)` — Multi-provider LLM interface
- `chat(messages, temperature, max_tokens)` — Send chat request

### LLMRouterBridge (`src.core.llm_router_bridge`)
- `LLMRouterBridge(config)` — Bridge to Node.js LLM Router
- `start()`, `chat()`, `stop()` — Lifecycle
- Falls back to Python LLMProvider if Node.js unavailable

### SelfHealing (`src.core.self_healing`)
- `PhiAccrualFailureDetector(threshold, window_size)` — Failure detection
- `RecoveryManager(detector)` — Automatic recovery
- `SelfHealingOrchestrator(config)` — Coordinated self-healing

## Swarm Intelligence

### RingPSOSwarm (`src.swarm.pso_swarm`)
- `RingPSOSwarm(n_particles, dimensions, topology)` — PSO optimizer
- Topologies: RING, STAR, WHEEL, VON_NEUMANN
- `initialize(fitness_fn)`, `step()`, `optimize(iterations)`

### ABCSwarm (`src.swarm.abc_swarm`)
- `ABCSwarm(n_employed, n_onlookers, n_scouts)` — Artificial Bee Colony
- Roles: EMPLOYED, ONLOOKER, SCOUT (dynamic switching)
- `initialize(fitness_fn)`, `step()`, `optimize(iterations)`

### PheromoneField (`src.swarm.stigmergy`)
- `PheromoneField(evaporation_rate, diffusion_rate)` — Stigmergic communication
- `deposit(position, type, intensity)`, `sense(position, radius)`, `evaporate(dt)`

### SwarmOrchestrator (`src.swarm.swarm_orchestrator`)
- `SwarmOrchestrator(config)` — Unified PSO+ABC+Stigmergy

## MCP

### LightweightMCPServer (`src.mcp.mcp_server`)
- `LightweightMCPServer(name, version)` — JSON-RPC MCP server
- `register_tool(name, desc, handler)`, `register_resource(uri, handler)`
- `start()`, `stop()`

### MCPIntegration (`src.mcp.mcp_server`)
- `MCPIntegration(server, tool_registry, colony_bridge)` — BH↔MCP bridge
