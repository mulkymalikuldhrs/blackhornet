# AGENTS.md — BlackHornet

## 1. Project Identity

| Field | Value |
|-------|-------|
| Name | BlackHornet |
| Type | Multi-agent AI colony with autonomous Omega Engine |
| Version | 5.0.0 |
| Python | >=3.11 |
| License | MIT |
| Owner | Dhaher Labs |

## 2. Architecture Summary

```
src/
├── agents/          9 core agents + audit/specialists subdirectories
├── omega/           Omega Engine (autonomous loop, SCS, evolution)
├── tools/           21 trading tools (risk, execution, kill switch, etc.)
├── harness/         LangGraph-compatible agent framework (~100 files)
├── core/            Core framework (event bus, circuit breaker, skill crystallizer)
├── memory/          Memory system (semantic, vector, episodic)
├── graph/           Knowledge graph
├── api/             Starlette REST API
├── mcp/             MCP protocol implementation
├── colony/          Colony evolution and orchestration
├── thinking/        Cognition modules
├── swarm/           PSO, ABC, stigmergy orchestration
├── bh_types/        Unified type system (Pydantic v2)
├── config/          Pydantic settings
├── security/        Security primitives
└── integration/     External integrations

skills/              22 agent skill packages
tests/               pytest test suite
scripts/             Infrastructure scripts
docs/                Documentation (VISION, PRD, ARCHITECTURE, SPEC, ADRs)
deploy/              Systemd service files
```

## 3. Build and Run

```bash
# Install in editable mode
pip install -e .

# Run unified colony launcher
bh-colony

# Run Omega CLI
bh-omega

# Run trading subsystem
python -m src.hermes_quant

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src
```

## 4. Code Conventions

### Imports
- Standard: `from src.tools.xxx import YYY`
- Wrong: `from tools.xxx import YYY` (missing `src.` prefix)
- Order: stdlib, third-party, local (blank line between each group)

### Type Hints
- Required on all function signatures
- Use `Optional`, `Dict`, `List` from `typing`

### Cross-Platform Paths
- Use `os.path.expanduser("~")` -- never hardcode `/sdcard/` or `/root/`
- Use `platform.system()` for OS detection, not `uname -o`
- Use `platform.node()` for hostname, not `os.uname().nodename`

### Logging
```python
logger = logging.getLogger("blackhornet.ModuleName")
```

### Communication
- All inter-agent communication uses JSON

### Comments
- Only when the WHY is non-obvious
- No comments that explain WHAT the code does
- No comments for hypothetical future needs

## 5. Key Patterns

- **Risk limits** are enforced in `src/tools/risk_officer_tool.py` -- never override these
- **Kill switch** is fail-closed -- blocks by default when uncertain
- **SharedState** (`src/tools/shared_state.py`) is the single source of truth for runtime state
- **Trading tools** follow a layered architecture (L1 data through L5 execution)
- **Omega Engine** runs an autonomous self-improvement loop -- do not interrupt without reason
- **Circuit breaker** in `src/core/` prevents cascading failures

## 6. Security Rules

1. Never commit secrets (`.env`, API keys, tokens, credentials)
2. All user input must be validated before processing
3. LLM output is untrusted -- validate before use in logic or tool calls
4. External API calls must use `httpx` with explicit timeouts
5. Report vulnerabilities to mulkymalikuldhr@agentmail.to -- do not open public issues

## 7. Git Workflow

- Commit format: `type: description` (feat, fix, docs, chore, test)
- Atomic commits: one logical change per commit
- Feature branches from `main`
- No force-push to shared branches
- Tag releases with semantic versioning (MAJOR.MINOR.PATCH)
- Tests must pass before merging

## 8. What NOT to Do

- Don't use `from tools.xxx` -- always `from src.tools.xxx`
- Don't hardcode Linux paths -- use cross-platform detection
- Don't add comments unless the WHY is non-obvious
- Don't create abstractions for hypothetical needs (YAGNI)
- Don't mix refactoring with feature work in the same commit
- Don't suppress warnings or ignore test failures
- Don't add new dependencies without checking if existing ones cover the need
