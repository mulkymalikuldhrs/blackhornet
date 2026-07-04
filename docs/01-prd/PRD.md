# Product Requirements Document — BlackHornet Ω

## Product Overview
BlackHornet Ω is an autonomous AGI engine that manages the Dhaher Labs ecosystem. It scores projects, fixes gaps, syncs to Codeberg, and improves itself.

## Target Users
- **Primary:** Autonomous AGI agents (operate without human supervision)
- **Secondary:** Founder (Mulky Malikul Dhaher) — receives reports, not requests
- **Tertiary:** Developer ecosystem tools (CI/CD, deployment, monitoring)

## Functional Requirements

### Core Engine
- FR1: Boot sequence auto-detects paths, recalls memory, scores projects
- FR2: Main loop continuously: SCAN → SCORE → PRIORITIZE → PLAN → ACT → VERIFY → LOG → SAVE → SYNC → EVOLVE
- FR3: All decisions include council deliberation (parallel, non-blocking)
- FR4: Every action has confidence score ≥70%

### Memory
- FR5: Second Brain auto-captures all code, decisions, sessions
- FR6: Session start auto-recalls chronology and relevant context
- FR7: Knowledge persists indefinitely across sessions

### Quality
- FR8: Projects scored on Constitution (25), Quality (50), Operations (25)
- FR9: Below 50 = critical auto-fix. Below 80 = auto-repair.
- FR10: Tests must pass before any commit

### Sync
- FR11: Pages sync mandatory every loop
- FR12: Hermes Nous research repo auto-fetched and converted
- FR13: All changes pushed to Codeberg

## Non-Functional Requirements
- NFR1: Zero human intervention required for normal operation
- NFR2: Recovery from any failure mode (see Resilience table)
- NFR3: Fitness ≥0.7 to avoid self-mutation
- NFR4: SCS calibration between 70-95%
