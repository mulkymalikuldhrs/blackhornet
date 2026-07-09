# BH V2.0 — Research-Backed Self-Evolving Architecture

## Overview

BlackHornet v2.0 introduces 4 research-backed modules that enable
self-evolution, skill crystallization, resource governance, and
multi-agent coordination engineering. All modules are integrated via
`EvolutionBridge` — a single hook point into the AgentLoop.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   AgentLoop (BH Engine)                      │
│  pre_iteration  →  execute  →  post_iteration  →  on_error  │
│       ↑               ↑             ↑               ↑       │
│       └───────────────┼─────────────┼───────────────┘       │
│                       │    EvolutionBridge                   │
│          ┌────────────┴────────────┐                         │
│          │                         │                         │
│   ┌──────┴──────┐          ┌──────┴──────┐                  │
│   │  Skill      │          │  Agent      │                  │
│   │  Crystallizer│         │  Contracts  │                  │
│   │  (arXiv:    │          │  (arXiv:    │                  │
│   │   2604.17091│          │   2601.08815│                  │
│   │   +2510.16079)         │             │                  │
│   └─────────────┘          └─────────────┘                  │
│                                                              │
│   ┌─────────────┐          ┌─────────────┐                  │
│   │  Self       │          │  Swarm      │                  │
│   │  Consolidation│         │  Skills    │                  │
│   │  (arXiv:    │          │  (arXiv:    │                  │
│   │   2602.01966)         │   2605.10052│                  │
│   └─────────────┘          └─────────────┘                  │
│                                                              │
│   ┌──────────────────────────────────────────────────┐      │
│   │           EcosystemOrchestrator                   │      │
│   │  sync loop → EvolutionBridge.evolve() every tick  │      │
│   └──────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────┘
```

## Module Reference

### 1. SkillCrystallizer (`src/core/skill_crystallizer.py`)
- **Papers:** GenericAgent (arXiv:2604.17091), EvolveR (arXiv:2510.16079), Recursive Knowledge Crystallization (Tanaike, 2026)
- **Purpose:** Crystallize execution trajectories into reusable Skills
- **Lifecycle:** execute → record trajectory → validate quality → distill → persist as Skill (markdown+JSON) → recall on similar tasks → learn from failures
- **Key API:** `crystallize()`, `recall()`, `record_usage()`, `learn_from_failures()`, `record_trajectory()`

### 2. SelfConsolidation (`src/memory/self_consolidation.py`)
- **Paper:** Self-Consolidation for Self-Evolving Agents (arXiv:2602.01966)
- **Purpose:** Contrastive Reflection + Latent Consolidation — extract error patterns and compress trajectories into compact parameterized memories
- **Key API:** `record_experience()`, `reflect()`, `consolidate()`, `recall_consolidated()`, `get_actionable_advice()`

### 3. SwarmSkillsManager (`src/swarm/swarm_skills.py`)
- **Paper:** Swarm Skills: A Portable, Self-Evolving Multi-Agent System Specification (arXiv:2605.10052)
- **Purpose:** Portable multi-agent coordination spec with E/U/F scoring (Effectiveness/Utilization/Freshness), auto-discovery, and self-evolution
- **Components:** AgentRole, WorkflowStep, ExecutionBound, SwarmSkill, SwarmSkillScore, CoordinationRecord
- **Key API:** `register_skill()`, `record_coordination()`, `evolve()`, `create_coordination_plan()`

### 4. AgentContractManager (`src/core/agent_contracts.py`)
- **Paper:** Agent Contracts: A Formal Framework for Resource-Bounded Autonomous AI Systems (arXiv:2601.08815)
- **Purpose:** Formal resource governance — cost budgets, temporal deadlines, success criteria, conservation laws, circuit-breaking
- **Components:** AgentContract, ContractStatus, SuccessCriteria, ConservationLaw, ContractViolation
- **Key API:** `create_contract()`, `check_contract()`, `record_cost()`, `complete_contract()`, `create_subcontract()`

### Integration Hub: EvolutionBridge (`src/core/evolution_bridge.py`)
- **Purpose:** Single integration point wiring all 4 modules into AgentLoop hooks and EcosystemOrchestrator sync
- **Hooks:** pre_iteration, post_iteration, on_tool_call, on_error
- **Lifecycle:** `finish_task()` → crystallize + reflect + consolidate, `evolve()` → reflect + consolidate + learn_from_failures + swarm evolve

## Hooks into EcosystemOrchestrator

Located in `src/colony/orchestrator.py`:

1. **Init:** EvolutionBridge created with SwarmSkillsManager during `wire()`
2. **Sync loop:** `EvolutionBridge.evolve()` called every sync tick
3. **Status:** Evolution stats included in `full_status()` under `"evolution"` key

## References

- GenericAgent: arXiv:2604.17091 — Self-evolving agents with skill memory
- EvolveR: arXiv:2510.16079 — Evolutionary reinforcement via skill distillation
- Self-Consolidation: arXiv:2602.01966 — Contrastive reflection + latent memory
- Swarm Skills: arXiv:2605.10052 — Portable multi-agent coordination engineering
- Agent Contracts: arXiv:2601.08815 — Formal resource-bounded governance
- Recursive Knowledge Crystallization: Tanaike, 2026 — Knowledge crystallization patterns
- Autonomous Organism V2 Constitution: `/sdcard/dhaherlabs/DHAHER_LABS_AUTONOMOUS_ORGANISM_V2.md`
