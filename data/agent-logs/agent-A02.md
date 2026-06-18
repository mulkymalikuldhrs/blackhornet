# Agent A02: Launch-Engineer — Audit Summary

**Date:** 2026-06-17
**Target:** `/sdcard/dhaherlabs/blackhornet-worktree/bh-doctor`
**Tests:** `scripts/test_launcher.py` (38 tests, all passing)

---

## Issues Found & Fixed

### 1. SessionRecorder NOT wired to EventBus (CRITICAL)
- **Root cause:** `start()` created AutoGraphUpdater and EventBus but never instantiated SessionRecorder or subscribed it to EventBus events.
- **Fix:** Added SessionRecorder creation (#7 in startup sequence) with full wiring to `auto_updater`, `graph_store`, `entity_tracker`, `relationship_mapper`, and `event_bus`. Calls `sr.start()` which subscribes to `action`/`observation` event types.

### 2. EventBus not running (CRITICAL)
- **Root cause:** `EventBus.start()` is async; was never called. `publish_event()` silently dropped events because `self._running` was `False`.
- **Fix:** Set `eb._running = True` directly after construction (synchronous context).

### 3. stop() only cleaned 2 of 8 components
- **Root cause:** Only stopped `web_server` and cleared `event_bus` history. Never closed graph_store, never stopped other components.
- **Fix:** Reverse-ordered shutdown loop iterates all `_components` keys; dispatches per-component teardown (web_server.stop, event_bus._running=False + clear_history, auto_graph_updater.on_episode stop, graph_store.close).

### 4. doctor() only checked 5 things
- **Root cause:** Only checked graph_store, memory_system, event_bus (presence), PID files, and log directory. Missed entity_tracker, relationship_mapper, auto_graph_updater, session_recorder, web_server.
- **Fix:** Now checks all 10 critical components with proper diagnostics.

### 5. PID file in project root
- **Root cause:** `self._pid_dir = BASE_DIR` caused `doctor.pid` to land in the repo root.
- **Fix:** Changed to `BASE_DIR / "data"`.

### 6. Web command hung on server failure
- **Root cause:** If `ws.start()` returned `False`, the code fell through to `while True: time.sleep(1)` with no exit.
- **Fix:** Added `else` branch with error message and `sys.exit(1)`.

---

## Files Modified

| File | Change |
|------|--------|
| `bh-doctor` | Lines 47, 59, 119-144, 171-205, 242-318, 492-494 |
| `scripts/test_launcher.py` | Created — 38 tests |

## Files NOT Touched (per constraints)
- All `src/` files
- `bh-doctor.sh`, `bh.sh`, `blackhornet.py`
- `tests/` directory
- `pyproject.toml`

## Test Coverage (38 tests, all pass)

| Test Class | Tests | What it covers |
|------------|-------|----------------|
| TestBHDoctorConstructor | 3 | Initial state, pid_dir location |
| TestBHDoctorStart | 3 | Returns dict, sets running, graceful import error |
| TestBHDoctorStop | 2 | Clears running, handles missing PID |
| TestBHDoctorStatus | 1 | Returns all metadata fields |
| TestBHDoctorDoctor | 6 | Dict keys, all 7 missing components, creates log dir |
| TestBHDoctorGraphExport | 6 | JSON/dot/ascii with and without store, all formats |
| TestBHDoctorExportSession | 2 | Returns path, creates directory |
| TestBHDoctorE2B | 2 | Returns dict, error without sandbox |
| TestMainCommands | 6 | All command dispatches mocked |
| TestRunForever | 2 | Start/stop cycle, periodic doctor |
| TestSessionRecorderEventBusWiring | 2 | start() creates SR with EB + AGU, subscription |
| TestErrorHandling | 4 | Graceful on import fail, stop crash, broken doctor |
