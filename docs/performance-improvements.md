# Performance Improvements

## Overview
This document records the incremental performance work applied to the BlackHornet ecosystem. It introduces asynchronous I/O for repository cloning/pulling and provides a lightweight profiling harness.

## Async Repository Management
The async deployment flow:
- For each repository, if it exists locally, perform an async `git pull --rebase`.
- If it does not exist, perform an async `git clone --depth 1` from the first reachable mirror.
- Record status and continue to the next repository.

## Profiling Harness
- **File:** `profiling_blackhornet.py`
- **Metrics:** Total seconds for `deploy_nest` (sync), `async_deploy_nest` (async), and `start_hornets`.
- **Output:** `data/performance-profile.json`

## Next Steps
1. Run `python3 profiling_blackhornet.py` and compare sync vs async times.
2. If async shows ≥20% improvement, replace calls to `deploy_nest` with `async_deploy_nest` in production scripts.
3. Extend async handling to other subprocess‑heavy sections (service startup, health checks) as needed.
