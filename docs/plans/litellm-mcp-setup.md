# LiteLLM + MCP Infrastructure Setup — BlackHornet AGI

**Date:** 2026-06-20
**Platform:** Alpine Linux v3.21 / aarch64 (ARM64) — Termux PRoot
**Status:** Research Complete — Plan Ready

---

## 1. Environment Analysis

| Factor | Status |
|--------|--------|
| OS | Alpine Linux v3.21 (musl libc) |
| Arch | aarch64 (ARM64) |
| Python | 3.12.13 (system) + pip 26.1.2 |
| Memory | ~744MB free |
| numpy/pandas/scipy | ✅ Installed via `apk add py3-numpy py3-pandas py3-scipy` |

**Alpine/ARM Considerations:**
- Many PyPI packages lack pre-built `musllinux_aarch64` wheels → pip compiles from source, which is slow and may need build deps (`gcc`, `python3-dev`, `musl-dev`)
- LiteLLM works on Alpine/ARM but `pip install` can take 5-15 minutes on first run
- Known issue: `libsndfile` missing for audio features — irrelevant for BH (no STT/TTS)
- Docker tag `v1.83.14-stable` had mislabeled arm64 images (contained amd64 binaries) — use `main-stable` or `v1.84.0+` for clean ARM64 support

---

## 2. LiteLLM Setup

### 2.1 Installation

```bash
# Install LiteLLM (will compile from source on musl ARM — be patient, ~5-15 min)
pip install litellm

# Verify
python3 -c "import litellm; print(litellm.__version__)"
```

**Known deps that may need system packages:**
```bash
apk add --no-cache gcc musl-dev python3-dev
```

### 2.2 Current BH LiteLLM Integration

**File:** `src/core/llm_provider.py`

BH already has a complete `LLMProvider` class wrapping LiteLLM with:
- ✅ Multi-provider support via LiteLLM
- ✅ Token counting with tiktoken (heuristic fallback)
- ✅ Retry with exponential backoff
- ✅ Cost tracking per model/per day
- ✅ Streaming support
- ✅ Graceful mock fallback when litellm is not installed

**Current state:** `litellm` is NOT in `pyproject.toml` or `requirements.txt`. The provider runs in MOCK MODE — all responses are simulated `[MOCK]` strings.

### 2.3 Add LiteLLM to Project Dependencies

Add to `pyproject.toml` under `[project.dependencies]`:
```toml
"litellm>=1.50.0",
```

Or to `requirements.txt`:
```
litellm>=1.50.0
```

### 2.4 Multi-Provider Configuration Template

**File:** `config/litellm_config.yaml`

```yaml
# LiteLLM Proxy Configuration — BH Multi-Provider Router
# All API keys sourced from config/.env

general_settings:
  master_key: "${LITELLM_MASTER_KEY}"      # Optional: protect proxy with API key
  database_url: ""                          # Optional: SQLite/Postgres for spend tracking

model_list:
  # === PRIMARY: NexusRouter (free tier, $100M) ===
  - model_name: nexusrouter
    litellm_params:
      model: openai/gpt-4o
      api_key: "${OPENAI_API_KEY}"
      api_base: "${OPENAI_API_BASE}"
      rpm: 60
      tpm: 100000
    model_info:
      mode: completion
      cost_per_token: 0.0                   # NexusRouter is free

  # === FALLBACK 1: NVIDIA NIM ===
  - model_name: nvidia-fallback
    litellm_params:
      model: openai/meta/llama-3.1-nemotron-70b-instruct
      api_key: "${NVIDIA_API_KEY}"
      api_base: "${NVIDIA_API_BASE}"
      rpm: 30
      tpm: 50000
    model_info:
      mode: completion

  # === FALLBACK 2: Groq (fast inference) ===
  - model_name: groq-fallback
    litellm_params:
      model: openai/llama-3.1-8b-instant
      api_key: "${GROQ_API_KEY}"
      api_base: "${GROQ_API_BASE}"
      rpm: 30
      tpm: 30000
    model_info:
      mode: completion

  # === FALLBACK 3: OpenCode Zen (free) ===
  - model_name: opencode-zen
    litellm_params:
      model: openai/nemotron-3-ultra-free
      api_key: "${OPENCODE_ZEN_API_KEY}"
      api_base: "https://opencode.ai/zen/v1"
      rpm: 20
    model_info:
      mode: completion

router_settings:
  routing_strategy: "cost-based-routing"    # Cheapest provider first
  num_retries: 2
  request_timeout: 30
  fallbacks:
    - nexusrouter:
        - nvidia-fallback
        - groq-fallback
        - opencode-zen
  allowed_fails: 3
  cooldown_time: 30
  enable_tag_filtering: false

litellm_settings:
  drop_params: true
  set_verbose: false
  request_timeout: 30
  success_callback: ["langfuse"]            # Optional: observability
  failure_callback: ["langfuse"]
```

### 2.5 Provider Routing Priority (Cost-Based)

The `cost-based-routing` strategy routes to the cheapest provider first:

1. **NexusRouter** — $0 cost (free tier) → always try first
2. **NVIDIA NIM** — ~$0.0002/1K tokens → fallback
3. **Groq** — ~$0.0001/1K tokens (fast but lower rate limits) → secondary
4. **OpenCode Zen** — free, lowest rate limits → last resort

### 2.6 Testing LiteLLM

```bash
# Test basic completion
python3 -c "
import litellm
import os
os.environ['OPENAI_API_KEY'] = 'sk-nx-...'
os.environ['OPENAI_API_BASE'] = 'https://nexusrouter.dev/v1'
response = litellm.completion(
    model='openai/gpt-4o',
    messages=[{'role': 'user', 'content': 'Say hello in 3 words'}],
)
print(response.choices[0].message.content)
"

# Test BH LLMProvider
cd /sdcard/dhaherlabs/blackhornet-worktree
python3 -c "
import asyncio
from src.core.llm_provider import LLMProvider
async def test():
    p = LLMProvider(default_model='openai/gpt-4o')
    r = await p.chat([{'role': 'user', 'content': 'Hi'}])
    print(f'Content: {r.content}')
    print(f'Mock mode: {p.mock_mode}')
    print(f'Cost: \${r.cost:.6f}')
asyncio.run(test())
"
```

---

## 3. MCP Server Setup

### 3.1 Current BH MCP Infrastructure — Already Extensive

BH already has a production-grade MCP implementation:

| File | Purpose |
|------|---------|
| `src/mcp/server.py` | Production MCPServer — JSON-RPC 2.0, circuit breaker, rate limiter, permission engine, audit logging, batch support |
| `src/mcp/mcp_server.py` | Lightweight MCP server (simpler, stdio transport) |
| `src/mcp/protocol.py` | JSON-RPC 2.0 protocol — Pydantic v1/v2 compatible, 388 lines |
| `src/mcp/client.py` | MCPClient — connect, discover tools, invoke with retries, 315 lines |
| `src/mcp/permissions.py` | Permission engine with autonomy levels |
| `src/mcp/transport/sse.py` | SSE transport — GET /mcp/sse + POST /mcp/messages, 186 lines |
| `scripts/test_mcp.py` | Smoke tests for MCP server |

**What's missing:** MCP SDK (`mcp[cli]`) is not installed. The code has conditional import:
```python
try:
    from mcp.server import Server as MCPServer  # Official SDK
    HAS_MCP = True
except ImportError:
    HAS_MCP = False  # Falls back to LightweightMCPServer
```

### 3.2 Install MCP Python SDK

```bash
# Install MCP SDK (v1.x stable — avoid v2 alpha for now)
pip install "mcp>=1.20,<2"

# Verify
python3 -c "from mcp.server.fastmcp import FastMCP; print('MCP SDK OK')"
```

**Pin in requirements.txt:**
```
mcp>=1.20,<2
```

### 3.3 Tool Registration Pattern

**Current BH pattern** (`src/mcp/mcp_server.py`):
```python
server.register_tool(
    name="agent_status",
    description="Get status of all BH agents",
    handler=self._get_agent_status,
    input_schema={"type": "object", "properties": {}},
)
```

**Recommended: Dual registration** — register tools on both the BH MCPServer AND the official MCP SDK FastMCP for maximum interoperability:
```python
from mcp.server.fastmcp import FastMCP

# Official MCP SDK server
fastmcp = FastMCP("blackhornet", json_response=True)

@fastmcp.tool()
def agent_status() -> dict:
    """Get status of all BH agents"""
    return {"status": "running", "agents": [...]}

# Also register on BH internal server
bh_server.register_tool("agent_status", ..., handler)
```

### 3.4 NexusRouter MCP Integration (Already Available)

Credentials show NexusRouter already exposes MCP endpoints:
```json
{
  "mcpServers": {
    "nexusrouter-linear": {
      "url": "https://nexusrouter.dev/api/mcp/linear",
      "headers": { "Authorization": "Bearer <API_KEY>" }
    },
    "nexusrouter-notion": {
      "url": "https://nexusrouter.dev/api/mcp/notion",
      "headers": { "Authorization": "Bearer <API_KEY>" }
    }
  }
}
```

These can be consumed by BH's `MCPClient` (`src/mcp/client.py`) to give agents access to Linear/Notion.

### 3.5 MCP Tool Registration — BH Agent Capabilities

Register BH's core capabilities as MCP tools:

```python
# In src/mcp/register_tools.py or integrated into MCPIntegration

TOOLS = [
    {
        "name": "agent_status",
        "description": "Get status and health of all BH agents",
        "handler": "get_agent_status",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "memory_search",
        "description": "Search BH agent vector memory",
        "handler": "search_memory",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "execute_task",
        "description": "Execute a task through a BH agent",
        "handler": "execute_agent_task",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "agent_type": {"type": "string", "enum": ["executor", "planner", "coder", "researcher"]},
            },
            "required": ["task"],
        },
    },
    {
        "name": "colony_radar",
        "description": "Scan the colony mesh for agent availability",
        "handler": "colony_radar",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "llm_chat",
        "description": "Send a chat to any LLM provider via LiteLLM router",
        "handler": "llm_chat",
        "input_schema": {
            "type": "object",
            "properties": {
                "messages": {"type": "array", "items": {"type": "object"}},
                "model": {"type": "string", "default": "nexusrouter"},
            },
            "required": ["messages"],
        },
    },
]
```

### 3.6 Testing MCP

```bash
# Test existing BH MCP server
cd /sdcard/dhaherlabs/blackhornet-worktree
python3 scripts/test_mcp.py

# Test with full SDK (if installed)
python3 -c "
import asyncio
from src.mcp.mcp_server import LightweightMCPServer, MCPIntegration

async def test():
    server = LightweightMCPServer()
    integration = MCPIntegration(server=server)
    
    # List tools
    resp = await server.handle_request({
        'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'
    })
    tools = resp['result']['tools']
    print(f'{len(tools)} tools registered:')
    for t in tools:
        print(f'  - {t[\"name\"]}: {t[\"description\"][:50]}')

    # Call a tool
    resp = await server.handle_request({
        'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
        'params': {'name': 'agent_status', 'arguments': {}}
    })
    print(f'Agent status: {resp[\"result\"]}')

asyncio.run(test())
"
```

---

## 4. Integration with Existing BH Daemon

### 4.1 Startup Sequence

The BH daemon should start LiteLLM proxy + MCP server on boot:

```python
# src/daemon.py — startup additions

async def start_infrastructure():
    """Start LiteLLM proxy and MCP server"""

    # 1. Start LiteLLM proxy (if installed)
    try:
        import litellm
        # LiteLLM runs in-process via LLMProvider — no separate proxy needed
        # LLMProvider handles routing internally
        logger.info("LiteLLM available — LLMProvider active")
    except ImportError:
        logger.warning("LiteLLM not installed — LLM mock mode")

    # 2. Start MCP server (SSE transport)
    from src.mcp.server import MCPServer
    from src.mcp.transport.sse import SSETransport

    mcp_server = MCPServer()
    sse_transport = SSETransport(mcp_server, host="127.0.0.1", port=5989)

    # Register BH tools
    from src.mcp.register_tools import register_all_tools
    register_all_tools(mcp_server)

    # Start transport
    asyncio.create_task(sse_transport.start())
    logger.info("MCP server started on port 5989")
```

### 4.2 Environment Variables

Add to `config/.env`:
```bash
# LiteLLM
LITELLM_MASTER_KEY=sk-bh-litellm-master    # Optional proxy auth key
LITELLM_CONFIG=config/litellm_config.yaml

# MCP Server
BH_MCP_PORT=5989
BH_MCP_HOST=127.0.0.1
BH_MCP_ENABLED=true
```

### 4.3 Systemd/Cron Integration

For the Alpine PRoot environment (no systemd), add to `cron-jobs.txt`:
```
# Start MCP server on boot
@reboot cd /sdcard/dhaherlabs/blackhornet-worktree && python3 -m src.mcp.start_mcp

# Health check every 5 minutes
*/5 * * * * curl -s http://127.0.0.1:5989/health > /dev/null || python3 -m src.mcp.start_mcp
```

---

## 5. Issues Found

### Critical
1. **LiteLLM NOT in dependencies** — `src/core/llm_provider.py` uses it but `pyproject.toml` and `requirements.txt` lack `litellm`. Entire BH runs in MOCK MODE — all "AI" responses are fake.
2. **MCP SDK NOT installed** — `mcp_server.py` has `try/except ImportError` fallback, so the official SDK is never used. Falls back to `LightweightMCPServer`.
3. **Dual MCP implementation** — `src/mcp/mcp_server.py` (lightweight) and `src/mcp/server.py` (production) duplicate functionality. Should be unified.

### Medium
4. **MCP SDK v2 alpha available** — v1.x is stable (`<2` pin), v2 alpha targets 2026-07-28. BH should stay on v1.x for now.
5. **NexusRouter MCP endpoints exist but unused** — credentials.md lists NexusRouter MCP for Linear/Notion but BH has no consumer.
6. **`config/.env` has no LiteLLM config vars** — no `LITELLM_CONFIG`, `LITELLM_MASTER_KEY`, etc.

### Low
7. **pip install on Alpine ARM is slow** — many packages compile from source on `musllinux_aarch64`. Use `--prefer-binary` or pre-install build deps.
8. **libsndfile not needed** — BH has no audio processing, but the known Alpine ARM issue exists for STT/TTS features.

---

## 6. Quick-Start Commands

```bash
# 1. Install system build deps
apk add --no-cache gcc musl-dev python3-dev

# 2. Install LiteLLM + MCP SDK
pip install litellm "mcp>=1.20,<2"

# 3. Verify installations
python3 -c "import litellm; print(f'LiteLLM {litellm.__version__}')"
python3 -c "from mcp.server.fastmcp import FastMCP; print('MCP SDK OK')"

# 4. Test BH MCP server
cd /sdcard/dhaherlabs/blackhornet-worktree
python3 scripts/test_mcp.py

# 5. Test BH LLMProvider with real API
python3 -c "
import asyncio
from src.core.llm_provider import LLMProvider
async def t():
    p = LLMProvider(default_model='openai/gpt-4o')
    r = await p.chat([{'role': 'user', 'content': 'Hi'}])
    print(f'Mock: {p.mock_mode}, Response: {r.content[:60]}')
asyncio.run(t())
"

# 6. Start LiteLLM proxy (standalone, optional)
# litellm --config config/litellm_config.yaml --port 4000
```

---

## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    BH Agent Colony                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Colony   │ │Executor  │ │Researcher│ │ Planner      │  │
│  │ Agents   │ │Agents    │ │Agents    │ │ Agents       │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │
│       │            │            │              │           │
│  ┌────▼────────────▼────────────▼──────────────▼───────┐   │
│  │              LLMProvider (LiteLLM)                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │NexusRouter│  │  NVIDIA  │  │   Groq   │  ...     │   │
│  │  │ (free)    │  │  (NIM)   │  │ (fast)   │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                │
│  ┌────────────────────────▼────────────────────────────┐   │
│  │              MCPServer (port 5989)                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │   │
│  │  │BH Tools  │ │Memory    │ │NexusRouter MCP   │    │   │
│  │  │(6 reg'd) │ │Search    │ │(Linear, Notion)  │    │   │
│  │  └──────────┘ └──────────┘ └──────────────────┘    │   │
│  │  Transport: SSE (GET /mcp/sse, POST /mcp/messages) │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                │
│                   ◄───────┴───────►                        │
│              External LLMs     External Tools              │
│              (OpenCode, etc.)  (Linear, Notion)            │
└─────────────────────────────────────────────────────────────┘
```
