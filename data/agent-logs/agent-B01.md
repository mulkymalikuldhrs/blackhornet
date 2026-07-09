# Agent B01 — BaseAgent Audit Summary

## Files Audited
- `src/core/base_agent.py`
- `src/core/agent_loop.py`
- `src/core/tool_base.py`
- `src/core/tool_registry.py`
- `src/core/tests.py`

## Issues Found & Fixed

### 1. Missing Lifecycle Hooks (base_agent.py)
**Problem:** `on_start`, `on_pause`, `on_resume`, `on_shutdown` lifecycle hooks were documented concepts but not defined. Subclasses had no extension points.

**Fix:** Added empty async hooks at `base_agent.py:101-116`. `run()` now calls `await self.on_start()`, `pause()` calls `await self.on_pause()`, `resume()` calls `await self.on_resume()`, `terminate()` calls `await self.on_shutdown()`.

### 2. Invalid Exception Kwargs (base_agent.py, agent_loop.py)
**Problem:** `AgentError`, `AgentTimeoutError`, and `AgentStateError` constructors don't accept `agent_id` or `current_state` kwargs, yet code was passing them. Would raise `TypeError` at runtime on every error/state-transition path.

| File | Line (old) | Exception | Removed kwargs |
|---|---|---|---|
| `base_agent.py` | 181-183 | `AgentStateError` | `agent_id`, `current_state` |
| `base_agent.py` | 269 | `AgentError` | `agent_id` |
| `base_agent.py` | 322-326 | `AgentTimeoutError` | `agent_id` |
| `agent_loop.py` | 186-190 | `AgentTimeoutError` | `agent_id` |
| `agent_loop.py` | 245 | `AgentError` | `agent_id` |
| `agent_loop.py` | 261 | `AgentError` | `agent_id` |

**Fix:** Removed all unsupported kwargs from exception constructors across both files (6 call sites).

### 3. AgentTimeoutError timeout_ms Incorrect (base_agent.py)
**Problem:** `timeout_ms` was set to `max_iter * 1000` (e.g., `10 * 1000 = 10000ms`), an arbitrary value not tied to actual wall-clock time.

**Fix:** Changed to `int((time.time() - started_at) * 1000)` — actual elapsed milliseconds.

### 4. FunctionTool Missing super().__init__() (tool_registry.py)
**Problem:** `FunctionTool.__init__` didn't call `super().__init__()`, so `_id` and `_config` from `BaseTool` were never initialized. Accessing `.id` on a `FunctionTool` would raise `AttributeError`.

**Fix:** Added `super().__init__()` call.

### 5. Logger Placement (tool_registry.py)
**Problem:** `logger = get_logger(__name__)` was on line 53, after `FunctionTool` class definition instead of at the top.

**Fix:** Moved to line 19, directly after imports.

## Tests Added (tests.py)
8 new test methods in `TestCorePackage`:

| Test | Verifies |
|---|---|
| `test_base_agent_on_start_hook_exists` | `on_start` is defined and callable |
| `test_base_agent_on_pause_hook_exists` | `on_pause` is defined and callable |
| `test_base_agent_on_resume_hook_exists` | `on_resume` is defined and callable |
| `test_base_agent_on_shutdown_hook_exists` | `on_shutdown` is defined and callable |
| `test_function_tool_has_id` | `FunctionTool.id` works (super init call) |
| `test_agent_timeout_error_timeout_ms` | `timeout_ms` param stored correctly |
| `test_agent_timeout_error_no_extra_kwargs` | No `agent_id` kwarg in ctor |
| `test_agent_state_error_no_extra_kwargs` | No `agent_id`/`current_state` kwargs |

## Test Results
All 16 tests pass (8 original + 8 new).
