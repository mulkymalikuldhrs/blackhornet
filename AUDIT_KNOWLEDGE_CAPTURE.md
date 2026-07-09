# Knowledge Capture: BlackHornet Deep Audit
## Date: 2026-06-17

### Insight 1: Overclaiming Erodes Trust
- **Context:** Found 22 agents claimed (10 actual), SQLite claimed (Python dicts), 40+ indicators claimed (zero in config)
- **Insight:** When documentation claims more than reality, every other claim becomes suspect. The honest numbers (486 tests, 7126 memory lines, 3 real algorithms) are MORE impressive than the inflated ones.
- **Confidence:** HIGH

### Insight 2: Build System is Gate-1
- **Context:** pyproject.toml build backend is broken. No one can `pip install -e .`.
- **Insight:** If the build system doesn't work, nothing else matters. This is the first thing to fix before any other work.
- **Confidence:** HIGH

### Insight 3: Secrets in Config = Security Theater
- **Context:** config/.env has 9 real API keys/tokens. Project has security agent + kill switch.
- **Insight:** A project with "SecurityAgent" and "KillSwitch" that commits real secrets to the repo has a fundamental security culture problem. The code is clean (uses os.getenv), but the config is not.
- **Confidence:** HIGH

### Insight 4: Three MemoryManager Abstractions = Architecture Debt
- **Context:** src.core.memory_manager.MemoryManager, src.memory.manager.MemoryManager, and src.memory.system.MemorySystem all manage memory differently.
- **Insight:** Same concern, three implementations, import ambiguity. This is the #1 architectural debt item.
- **Confidence:** HIGH

### Insight 5: Import-Only Tests Don't Count
- **Context:** 26 of 54 tests in test_bh_units.py are pure `from X import Y` checks. src/core/tests.py has 8 hasattr-only tests.
- **Insight:** Tests that only verify imports pass don't provide behavioral coverage. A module can import successfully and still be completely broken at runtime.
- **Confidence:** HIGH

### Insight 6: Silent Failure is Worse Than Loud Failure
- **Context:** unified_launcher.py uses 12 lazy try/except ImportError blocks. Launcher reports "ok" when components fail.
- **Insight:** Graceful degradation is good for user experience but bad for debugging. Log the failures.
- **Confidence:** MEDIUM

### Insight 7: Version Numbers Must Be Authoritative
- **Context:** pyproject=12.0.0, CHANGELOG=1.0.0-rc.1, Dockerfile=4.0.0
- **Insight:** Three different version numbers means no one knows what version this actually is. Pick one, use it everywhere.
- **Confidence:** HIGH

### Effective Patterns Found
- Lazy imports with try/except for optional dependencies (unified_launcher.py)
- numpy shim for aarch64 compatibility (src/swarm/_numpy_shim.py)
- Phi-accrual failure detector pattern (src/core/self_healing.py)
- Self-modification pipeline with test gate (src/sandbox/)

### Failure Patterns Found
- Overclaiming in documentation (inflated counts everywhere)
- Secrets committed to repo (config/.env)
- Build system broken (pyproject.toml)
- CI references deleted files (ci.yml)
- Version number chaos (3 different numbers)
- Three competing implementations of same concern (MemoryManager)

### User Preference: Honest CTO Assessment
- **Context:** User asked for self-aware, skeptical, creative assessment as "Claude Mythos and Dhaher Labs CTO"
- **Insight:** The user values honest assessment over optimistic framing. They explicitly asked for "skepticism" and "kejujuran" (honesty).
- **Confidence:** HIGH
