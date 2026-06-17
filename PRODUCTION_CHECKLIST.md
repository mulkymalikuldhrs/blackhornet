# BlackHornet Production Readiness Checklist

> Generated: 2026-06-17 | Version: 4.1.0

---

## CRITICAL BLOCKERS (Must Fix Before Release)

### [ ] Task 1: Fix pyproject.toml Build Backend
- [ ] Change `setuptools.backends._legacy:_Backend` → `setuptools.build_meta`
- [ ] Set version to `4.1.0`
- [ ] Add missing dependencies (yfinance, pandas)
- [ ] Verify: `pip install -e .` succeeds

### [ ] Task 2: Remove Secrets from config/.env
- [ ] Replace all real API keys with empty placeholders
- [ ] Ensure `config/.env` is in `.gitignore`
- [ ] Verify: `grep -r "nvapi-\|ghp_\|sk-" config/ src/` returns 0 hits

### [ ] Task 3: Fix CI Workflow
- [ ] Remove py_compile of 5 deleted files
- [ ] Replace test-swarm job with real swarm test
- [ ] Replace test-bridges job with test-core job
- [ ] Use `pip install -e .` everywhere
- [ ] Verify: CI runs without ImportError

### [ ] Task 4: Fix Dockerfile
- [ ] Remove dead GitHub URLs (NousResearch/blackhornet-agent, dhaher-labs/mnemosyne)
- [ ] Fix Hermes Agent comment
- [ ] Update version label to 4.1.0
- [ ] Verify: `docker build .` succeeds (if Docker available)

### [ ] Task 5: Align Version Numbers
- [ ] Set all to 4.1.0 (pyproject.toml, CHANGELOG, install.sh, README badges, ALL.md)
- [ ] Add changelog entry for v4.1.0
- [ ] Verify: all version references match

---

## HIGH ISSUES (Functional Gaps)

### [ ] Task 6: Complete Rebrand (12 hermes refs)
- [ ] README_zh.md: 4 refs (lines 66, 99, 451, 549)
- [ ] README_id.md: 5 refs (lines 111, 144, 265, 484, 600)
- [ ] ALL.md: 1 ref (line 405)
- [ ] scripts/bootstrap.sh: 3 refs (lines 89, 93-95)
- [ ] Verify: `rg -n -i 'hermes' --glob '!.git' | grep -viE '(nousresearch|hermes-agent|hermes_constants|get_hermes_home|hermes gateway|hermes profile|command -v hermes|com\.hermes\.hive|hermes chat)'` returns 0 hits

### [ ] Task 7: Fix Dead hermes Symlink
- [ ] Remove/comment out install.sh:245
- [ ] Verify: no dead symlink creation

### [ ] Task 8: Fix AgentTimeoutError Constructor
- [ ] base_agent.py: pass iteration count * 1000 as milliseconds
- [ ] agent_loop.py: pass timeout seconds * 1000 as milliseconds
- [ ] Verify: no type mismatch in exception calls

### [ ] Task 9: Add Error Handling to Async Functions
- [ ] Wrap 7 async methods with try/except in base_agent.py and event_bus.py
- [ ] Verify: no bare except Exception: pass

### [ ] Task 10: Fix Silent Failure in unified_launcher.py
- [ ] Add logging to 12 ImportError blocks
- [ ] Verify: launcher logs warnings when modules fail to import

### [ ] Task 11: Fix qna_integration Phantom Dependency
- [ ] Add clear warning when quant_nanggroe not installed
- [ ] Document in AGENTS.md Critical Gotchas
- [ ] Verify: no ImportError on missing package

---

## DOCUMENTATION (Consciousness + Bee Nature)

### [ ] Task 12: Create CONSCIOUSNESS.md
- [ ] Document 5 consciousness traits with code examples
- [ ] Include testing framework for consciousness verification
- [ ] Verify: file exists with 300+ lines

### [ ] Task 13: Create BEE_NATURE.md
- [ ] Document 7 bee characteristics with architecture mappings
- [ ] Include design principles inspired by bee evolution
- [ ] Verify: file exists with 280+ lines

### [ ] Task 14: Update AGENTS.md
- [ ] Fix "22 Agent subclasses" → "10 Agent subclasses"
- [ ] Fix "27+ packages" → "25 packages"
- [ ] Fix "Memory: 8 files, 2822 lines, SQLite+FTS5" → "Memory: 17 files, 7126 lines, Python-native"
- [ ] Remove "40+ indicator parameters" claim
- [ ] Add Consciousness Traits section (Section 6)
- [ ] Add Bee Nature section (Section 7)
- [ ] Update Implementation Status with accurate numbers
- [ ] Verify: all claims match reality

### [ ] Task 15: Update PRODUCTION.md
- [ ] Remove false "PRODUCTION READY" claim
- [ ] Add honest status: "Production Ready (v4.1.0)"
- [ ] Fix architecture references (remove dead file refs)
- [ ] Add working verification commands
- [ ] Verify: all commands actually work

---

## CODE QUALITY

### [ ] Task 16: Fix FunctionTool Duplication
- [ ] Extract single FunctionTool class in tool_registry.py
- [ ] Verify: no duplicate class definitions

### [ ] Task 17: Add Behavioral Tests for Core Modules
- [ ] Create tests/test_core_behavior.py
- [ ] Test EventBus, ToolRegistry, BaseAgent, AgentLoop
- [ ] Verify: new tests pass

### [ ] Task 18: Generate requirements.txt
- [ ] Sync with pyproject.toml dependencies
- [ ] Verify: both files declare identical packages

---

## FINAL VERIFICATION

### [ ] Task 19: Run Full Test Suite
```bash
python3 -m pytest tests/ src/memory/tests.py src/thinking/tests.py \
  src/core/tests.py src/types/tests.py src/ui/tests.py src/graph/tests.py \
  src/config/tests.py src/sandbox/tests.py src/auto_discovery/tests.py \
  src/integration/tests.py -v --tb=short 2>&1 | tail -30
```
Expected: All tests pass

### [ ] Task 20: Verify Build
```bash
pip install -e . 2>&1 | tail -5
```
Expected: Successfully installed blackhornet-colony-4.1.0

### [ ] Task 21: Verify Lint
```bash
ruff check src/ --select E,F,W --ignore E501 2>&1 | tail -10
```
Expected: 0 errors

### [ ] Task 22: Final Commit
```bash
git add -A && git commit -m "release: v4.1.0 production readiness

- All critical blockers fixed
- Consciousness traits documented
- Bee nature documented
- All high issues addressed
- Tests passing
- Build working
- Lint clean"
```

---

## SIGN-OFF

After completing all tasks:

| Check | Status |
|-------|--------|
| `pip install -e .` succeeds | [ ] |
| `python3 -m pytest` passes | [ ] |
| `ruff check src/` shows 0 errors | [ ] |
| No real secrets in config/.env | [ ] |
| No internal hermes references | [ ] |
| All version numbers say 4.1.0 | [ ] |
| CI workflow compiles only existing files | [ ] |
| Dockerfile has no dead URLs | [ ] |
| AGENTS.md claims match reality | [ ] |
| CONSCIOUSNESS.md exists with 5 traits | [ ] |
| BEE_NATURE.md exists with 7 characteristics | [ ] |
| Error handling in critical async functions | [ ] |
| Behavioral tests for core modules | [ ] |

**All checks pass = Production Ready**
