# Changelog — BlackHornet

All notable changes to BlackHornet will be documented in this file.

## [5.1.0] — NEXT (Planned)

### Integration Plan — External Source Projects

#### From A-Evolve (Python, directly copyable)
- **VersionControl** — git-based workspace versioning (branches, worktrees, rollback, tags)
- **AgentWorkspace** — filesystem contract for skills, tools, memory, harness (SKILL.md frontmatter)
- **Observer** — structured JSONL observation collection for agent evolution
- **EGL Metrics** — Evolution Capacity, AULC, Evolutionary Generality Loss
- **Types** — SkillMeta, Observation, Task, Trajectory, Feedback dataclasses

#### From MUE-X (Python, adaptation needed)
- **AST Mutation Engine** — 6 deterministic mutation strategies (repair/optimize/explore/exploit/innovate/prune)
- **DNA Genome + Kernel Integrity** — SHA256 sealing, importable validation, integrity checks
- **Autonomous Signal Generator** — 7 self-motivation drives (curiosity, stagnation, quality, etc.)
- **PAD Emotional Model** — Pleasure-Arousal-Dominance behavioral dynamics
- **Strategy Parameter Evolver** — genetic algorithm-style parameter mutation for trading strategies
- **Memory Lattice** — 6-layer SQLite FTS5 persistent memory with self-reinforcement
- **MCP Plugin Creator** — dynamic MCP tool generation
- **Domain Specialization** — `/specialize trading` instant reconfiguration

#### From Loop-Engineering (TypeScript → Python ports)
- **Circuit Breaker** — stagnation detection, error normalization with trigram similarity, token budget enforcement
- **Mechanical Path Gates** — denylist, auto-merge allowlist, max-file-count enforcement
- **Readiness Audit** — L0-L3 project readiness scoring
- **Cost Estimation** — token budget per pattern with orchestration multipliers
- **Worktree Locking** — advisory path locking with deadlock detection and TTL
- **Drift Detection** — STATE.md vs config vs filesystem drift detection
- **MCP Discovery Server** — expose patterns, skills, state via MCP at runtime

#### From Pixel-Agents (TypeScript → Python concepts)
- **HookProvider Abstraction** — support multiple AI agent types through single interface
- **Session Router** — race-condition-safe agent registration with event buffering
- **Multi-Server Registry** — PID-based liveness, auto-pruning
- **Dual-Mode Detection** — hooks preferred, file-polling fallback
- **Agent Teams** — lead+teammate relationships

### Documentation Updates
- README architecture tree updated (14 missing directories added)
- CHANGELOG rebuilt with missing entries
- ROADMAP aligned to version 5.x reality
- TASKS updated with integration plan
- AGENTS.md created (root-level agent rules)
- STRUCTURE.md cleaned (16 phantom references removed)

### Fixed
- 39 broken import paths across 10 files
- Windows compatibility (11 files — removed `/sdcard/`, `/root/`, `uname -o`)
- Type safety (3 files — `float = None` → `Optional[float]`)
- Deleted dead modules (hermes_nous/converter, organism, plugins, bridges)
- Removed 2 stale test files + 6 organism-dependent test classes

### Added
- CI/CD pipeline (`.github/workflows/ci.yml` — lint, test, typecheck)
- `.gitignore` for Python artifacts
- `AGENTS.md` — agent rules and conventions

## [1.0.0] — 2026-07-04
### Added
- Lord Omega v5.0 founding pillars embedded (src/omega/)
  - Constitution, SCS, Council, Predictor, Brain, Genome, Evolution, Score, Sync, AutoPath
- Hermes Nous integration (src/hermes_nous/)
  - 8+1 consciousness layers + research converter
- Bridges system (src/bridges/)
  - TypeScript colony compatibility
- ORCA parallel agent orchestration (src/agents/orca.py)
- BabyAGI task-driven loop (src/agents/babyagi.py)
- Dhaher_Labs_Constitution_v1.0.md — supreme law
- Full docs structure (docs/00-21)
- CREDITS.md — acknowledgments
- 63 new tests (375 total passing)

### Fixed
- 15 BH test failures (vector, logger, reflexion, CircuitBreaker, RouterResponse, enum types)
- File permissions (755→644)
- Type shadowing (types/ → bh_types/)

## [0.9.0] — 2026-07-03
- Initial BlackHornet Phase 1-2 integration
