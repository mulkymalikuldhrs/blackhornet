# Architecture — BlackHornet Ω

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  BLACKHORNET Ω ENGINE                │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Omega    │  │ Hermes   │  │ Bridges          │  │
│  │ Engine   │  │ Nous     │  │ (AO/TS compat)   │  │
│  └────┬─────┘  └────┬─────┘  └──────────────────┘  │
│       │              │                               │
│  ┌────▼──────────────▼──────────────────────────┐   │
│  │           FOUNDING PILLARS                    │   │
│  │  ┌──────┐ ┌────┐ ┌────────┐ ┌──────────┐    │   │
│  │  │SCS   │ │Cnc│ │Predict │ │  Brain   │    │   │
│  │  │      │ │l  │ │or (L9) │ │  (L0)    │    │   │
│  │  └──────┘ └────┘ └────────┘ └──────────┘    │   │
│  │  ┌──────┐ ┌────┐ ┌────────┐ ┌──────────┐    │   │
│  │  │Genome│ │Evl │ │Score   │ │  Sync    │    │   │
│  │  │      │ │tn  │ │        │ │          │    │   │
│  │  └──────┘ └────┘ └────────┘ └──────────┘    │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              AGENT LAYER                      │   │
│  │  Coder  Browser  Executor  Planner  Manus    │   │
│  │  Researcher  Colony  Auditor  ORCA  BabyAGI  │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              MEMORY LAYER                     │   │
│  │  STM  LTM  Episodic  Vector  Second Brain    │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              INFRASTRUCTURE                   │   │
│  │  Config  Logging  CircuitBreaker  Channels   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Key Design Decisions
1. **Omega Engine** is the brain — all founding pillars are modules inside it
2. **Agents** are independent — each can run in its own worktree (ORCA pattern)
3. **Memory** is tiered — STM for speed, LTM for persistence, Second Brain for life
4. **Bridges** enable cross-language communication (Python ↔ TS)
5. **Sync** is mandatory — ecosystem must always be current
