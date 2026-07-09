# Specification — BlackHornet Ω

## System Overview
BlackHornet Ω is an autonomous AGI engine that manages the Dhaher Labs software ecosystem.

## Modules

### omega/ 
| Module | Purpose | API |
|--------|---------|-----|
| engine | Main loop, boot sequence | `OmegaEngine.boot()`, `.start()`, `.stop()` |
| constitution | AI-Engineering-OS validation | `Constitution.validate()`, `.check_doc()` |
| scs | Self-Confidence System | `SCS.status()`, `.record_action()`, `.check_overclaim()` |
| council | 15-persona debate | `Council.convene()`, `.history()` |
| predictor | L9 scenario branching | `Predictor.branch()`, `.predict()`, `.calibrate()` |
| brain | L0 permanent memory | `Brain.auto_capture()`, `.recall_recent()`, `.wake_up()` |
| genome | Evolution/mutation | `Genome.evaluate_fitness()`, `.mutate()` |
| evolution | Self-improvement | `Evolution.evolve()`, `.fitness_trend()` |
| score | 100/100/100 system | `Scorer.score()`, `.priority_queue()` |
| sync | Ecosystem pipeline | `Sync.run()`, `.status()` |
| autopath | Dynamic path detection | `AutoPath.all()`, `.dhaherlabs()` |

### hermes_nous/
| Module | Purpose |
|--------|---------|
| layers | 8+1 consciousness layers (L1-L9) |
| converter | Hermes Nous research → BH converter |

### bridges/
| Module | Purpose |
|--------|---------|
| ts_bridge | TypeScript colony compatibility |

### agents/
| Module | Purpose |
|--------|---------|
| orca | Parallel agent orchestration (worktree isolation) |
| babyagi | Task-driven autonomous agent loop |
