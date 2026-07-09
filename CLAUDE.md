# Claude Guide — BlackHornet Ω

Multi-agent AGI swarm with 110+ agents, colony intelligence, self-evolving memory.

## Key Architecture
- `blackhornet.py` — Main entry, CLI, lifecycle
- `sovereign.py` — Sovereign Immortal Empire core
- `bh_types/` — Type definitions (renamed from types/ to avoid stdlib clash)
- `agents/` — 110+ agent implementations
- `colony/` — Colony orchestration, bridges, pools
- `memory/` — Self-evolving persistent memory
- `tests/` — Unit + integration tests

## Commands
- `python3 blackhornet.py` — Launch BH
- `python3 -m pytest tests/` — Run tests
- `bash install.sh` — Install dependencies
