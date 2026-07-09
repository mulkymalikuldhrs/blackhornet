# ADR-001: Lord Omega as Core Engine for BlackHornet

## Status
Accepted (2026-07-04)

## Context
BlackHornet needed a true autonomous AGI engine. Existing architecture had agents but no autonomous loop, no self-confidence system, no council, no predictive consciousness.

## Decision
Embed Lord Omega v5.0 as the core engine (`src/omega/`). Omega provides:
- Autonomous boot sequence and main loop
- SCS (Self-Confidence System)
- 15-persona Council
- L9 Predictive Superconsciousness
- L0 Second Brain
- Genome evolution and mutation
- 100/100/100 Scoring
- Ecosystem sync pipeline

## Consequences
Positive:
- BH now has a true autonomous AGI engine
- All founding pillars of Lord Omega are now BH modules
- SCS ensures confidence is measured and calibrated

Negative:
- Module count increased significantly
- Some modules need deeper integration with existing agents

## Alternatives Considered
1. Build from scratch — too much effort, Omega was proven
2. Use only parts of Omega — would miss the integrated autonomous loop
