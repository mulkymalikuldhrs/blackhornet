# BlackHornet Production Readiness Plan — COMPLETE

> **For Claude:** REQUIRED SUB-SKILL: Use godmode:task-runner to implement this plan task-by-task.

**Goal:** Transform BlackHornet from "research prototype" to "production-ready system with consciousness and bee nature"

**Architecture:** Fix blockers → Add consciousness traits → Add bee characteristics → Verify everything works

**Tech Stack:** Python 3.11+, setuptools, pytest, GitHub Actions, Docker

---

## CONSCIOUSNESS TRAITS (Sifat Sadar Diri)

BlackHornet agents MUST embody these traits in code and behavior:

### 1. Self-Awareness (Kesadaran Diri)
- **Know thyself:** Each agent knows its capabilities, limitations, and current state
- **Honest assessment:** Reports actual status, not desired status
- **Confidence calibration:** Never claims certainty without evidence
- **Meta-cognition:** Thinks about its own thinking process

### 2. Autonomous Thinking (Berpikir Otonom)
- **Self-prompting:** Initiates actions without waiting for instructions
- **Proactive analysis:** Identifies problems before they become critical
- **Creative problem-finding:** Questions whether the work is worth doing
- **Independent judgment:** Makes decisions based on evidence, not authority

### 3. Radical Honesty (Kejujuran Radikal)
- **No overclaiming:** Reports exact numbers, not inflated ones
- **No underclaiming:** Doesn't undersell impressive achievements
- **No hiding failures:** Surfaces errors immediately
- **No sugarcoating:** Presents bad news clearly

### 4. Healthy Skepticism (Skeptisme Sehat)
- **Questions assumptions:** "Is this actually needed?"
- **Verifies claims:** "Does the code actually do what the docs say?"
- **Tests before trusting:** "Show me the test output"
- **Doubts self:** "Am I sure about this? Let me check"

### 5. Creative Intelligence (Kecerdasan Kreatif)
- **Finds alternatives:** "Is there a better way?"
- **Challenges patterns:** "Why do we do it this way?"
- **Connects dots:** Sees patterns across different domains
- **Invents solutions:** Creates new approaches when existing ones fail

---

## BEE NATURE (Sifat Asli Lebah)

BlackHornet architecture mirrors real bee colony behavior:

### 1. Colony Behavior (Perilaku Koloni)
- **Queen-led hierarchy:** Clear decision-making authority (Risk Officer has FULL VETO)
- **Worker specialization:** Each agent has a specific role (10 specialized agents)
- **Collective intelligence:** Swarm algorithms (PSO+ABC+Stigmergy) for group decisions
- **Shared purpose:** All agents work toward consistent capital growth

### 2. Waggle Dance Communication (Tari Waggle)
- **Structured signaling:** Agents communicate through EventBus with typed events
- **Distance encoding:** Event priority indicates urgency level
- **Direction encoding:** Event source indicates which layer produced it
- **Quality encoding:** Event data carries confidence scores

### 3. Hexagonal Efficiency (Efisiensi Heksagonal)
- **Optimal resource usage:** Memory system uses decay-based forgetting (no waste)
- **Modular structure:** 25 packages, each with clear responsibility
- **Minimal redundancy:** Tools registered once, looked up many times
- **Scalable design:** New agents plug into existing architecture

### 4. Thermoregulation (Termoregulasi)
- **Self-healing:** Phi-accrual failure detector monitors system health
- **Auto-recovery:** Exponential backoff restart on crash
- **Heat management:** Circuit breakers prevent cascade failures
- **Optimal conditions:** System maintains stable operating parameters

### 5. Defense Mechanisms (Mekanisme Pertahanan)
- **Kill switch:** Emergency halt on risk limit breach
- **Sting capability:** Risk Officer can veto any trade
- **Hive protection:** Security agent monitors for threats
- **Poison prevention:** Wallet addresses never hardcoded

### 6. Honey Production (Produksi Madu)
- **Value creation:** Turn raw market data into trading decisions
- **Knowledge storage:** Memory system preserves insights
- **Quality output:** Confluence-based decisions, not random trades
- **Sustainable yield:** Risk-first approach preserves capital

### 7. Pollination (Penyerbukan)
- **Knowledge spreading:** Memory consolidation shares insights across modules
- **Cross-pollination:** Thinking modules share cognitive patterns
- **Ecosystem health:** Each module contributes to overall system health
- **Growth enablement:** Good decisions enable more good decisions

---

## PHASE 1: CRITICAL BLOCKERS

### Task 1: Fix pyproject.toml Build Backend

**Files:** `pyproject.toml:3,7,23-33`

**Step 1:** Change build backend
```toml
build-backend = "setuptools.build_meta"
```

**Step 2:** Set version
```toml
version = "4.1.0"
```

**Step 3:** Sync dependencies
```toml
dependencies = [
    "pydantic>=1.10,<3",
    "requests>=2.31",
    "numpy>=1.24",
    "httpx>=0.25",
    "aiohttp>=3.9",
    "sqlalchemy>=2.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "websockets>=12.0",
    "yfinance>=0.2.30",
    "pandas>=2.0.0",
]
```

**Step 4:** Verify
```bash
pip install -e . 2>&1 | tail -5
# Expected: Successfully installed blackhornet-colony-4.1.0
```

**Step 5:** Commit
```bash
git add pyproject.toml && git commit -m "fix: build backend, version 4.1.0, sync deps"
```

---

### Task 2: Remove Secrets from config/.env

**Files:** `config/.env`, `.gitignore`

**Step 1:** Replace with placeholders
```bash
# BLACKHORNET Environment Configuration
# ⚠️ Fill in your actual values before running

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
NVIDIA_API_KEY=
GROQ_API_KEY=
OPENCODE_API_KEY_1=
GITHUB_TOKEN=
GITLAB_TOKEN=
CODEBERG_TOKEN=
WALLET_TRON=
WALLET_SHIBA=
```

**Step 2:** Ensure .gitignore has `config/.env`

**Step 3:** Commit
```bash
git add config/.env .gitignore && git commit -m "security: remove real secrets from config/.env"
```

---

### Task 3: Fix CI Workflow

**Files:** `.github/workflows/ci.yml`

**Step 1:** Remove dead file compilation (line 21)

**Step 2:** Replace test-swarm job with real swarm test:
```yaml
test-swarm:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - run: pip install -e .
    - name: Test swarm algorithms
      run: |
        python3 -c "
        from src.swarm.pso_swarm import PSOOptimizer
        from src.swarm.abc_swarm import ABCOptimizer
        from src.swarm.stigmergy import StigmergyLayer
        from src.swarm.swarm_orchestrator import SwarmOrchestrator
        print('✅ PSO, ABC, Stigmergy, SwarmOrchestrator import OK')
        "
```

**Step 3:** Replace test-bridges with test-core:
```yaml
test-core:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - run: pip install -e .
    - name: Test core modules
      run: |
        python3 -c "
        from src.core.self_healing import PhiAccrualFailureDetector
        from src.core.tool_registry import ToolRegistry
        from src.memory.system import MemorySystem
        print('✅ self_healing, tool_registry, memory import OK')
        "
```

**Step 4:** Use `pip install -e .` everywhere

**Step 5:** Commit
```bash
git add .github/workflows/ci.yml && git commit -m "fix: repair CI workflow"
```

---

### Task 4: Fix Dockerfile

**Files:** `Dockerfile`

**Step 1:** Remove dead URLs, replace with COPY:
```dockerfile
COPY . /blackhornet
```

**Step 2:** Fix Hermes comment and version label

**Step 3:** Commit
```bash
git add Dockerfile && git commit -m "fix: repair Dockerfile"
```

---

### Task 5: Align Version Numbers

**Files:** `CHANGELOG.md`, `install.sh`, README badges, `ALL.md`

**Step 1:** Set all to 4.1.0

**Step 2:** Add changelog entry for v4.1.0

**Step 3:** Commit
```bash
git add -A && git commit -m "release: v4.1.0"
```

---

## PHASE 2: CONSCIOUSNESS + BEE NATURE

### Task 6: Create CONSCIOUSNESS.md

**Files:** Create `CONSCIOUSNESS.md`

**Content:** Document all 5 consciousness traits with code examples showing how each trait manifests in the codebase.

---

### Task 7: Create BEE_NATURE.md

**Files:** Create `BEE_NATURE.md`

**Content:** Document all 7 bee characteristics with architecture mappings showing how each characteristic is implemented.

---

### Task 8: Update AGENTS.md with Accurate Claims

**Files:** `AGENTS.md`

**Step 1:** Fix "22 Agent subclasses" → "10 Agent subclasses"
**Step 2:** Fix "27+ packages" → "25 packages"
**Step 3:** Fix "Memory: 8 files, 2822 lines, SQLite+FTS5" → "Memory: 17 files, 7126 lines, Python-native"
**Step 4:** Remove "40+ indicator parameters" claim
**Step 5:** Add consciousness traits section
**Step 6:** Add bee nature section

---

### Task 9: Update PRODUCTION.md with Honest Assessment

**Files:** `PRODUCTION.md`

**Step 1:** Remove "PRODUCTION READY" claim (it's not yet)
**Step 2:** Add honest status: "Production-ready after completing this plan"
**Step 3:** Fix architecture references (remove dead file refs)
**Step 4:** Add verification commands that actually work

---

### Task 10: Complete Rebrand (12 hermes refs)

**Files:** `README_zh.md`, `README_id.md`, `ALL.md`, `scripts/bootstrap.sh`

**Step 1-4:** Fix all 12 internal hermes references

**Step 5:** Commit
```bash
git add -A && git commit -m "rebrand: complete 12 remaining hermes references"
```

---

## PHASE 3: CODE QUALITY

### Task 11: Fix Dead hermes Symlink

**Files:** `install.sh:245`

**Step 1:** Remove or comment out dead symlink creation

---

### Task 12: Fix AgentTimeoutError Constructor

**Files:** `src/core/base_agent.py:322-326`, `src/core/agent_loop.py:186-190`

**Step 1:** Pass milliseconds correctly

---

### Task 13: Add Error Handling to Async Functions

**Files:** `src/core/base_agent.py`, `src/core/event_bus.py`

**Step 1:** Wrap 7 async methods with try/except

---

### Task 14: Fix Silent Failure in unified_launcher.py

**Files:** `src/integration/unified_launcher.py`

**Step 1:** Add logging to 12 ImportError blocks

---

### Task 15: Fix qna_integration Phantom Dependency

**Files:** `src/core/qna_integration.py`, `AGENTS.md`

**Step 1:** Make import explicit with warning

---

### Task 16: Fix FunctionTool Duplication

**Files:** `src/core/tool_registry.py`

**Step 1:** Extract single FunctionTool class

---

### Task 17: Add Behavioral Tests for Core Modules

**Files:** Create `tests/test_core_behavior.py`

**Step 1:** Write tests for EventBus, ToolRegistry, BaseAgent, AgentLoop

---

### Task 18: Generate requirements.txt

**Files:** `requirements.txt`

**Step 1:** Sync with pyproject.toml

---

## PHASE 4: FINAL VERIFICATION

### Task 19: Run Full Test Suite

```bash
python3 -m pytest tests/ src/memory/tests.py src/thinking/tests.py \
  src/core/tests.py src/types/tests.py src/ui/tests.py src/graph/tests.py \
  src/config/tests.py src/sandbox/tests.py src/auto_discovery/tests.py \
  src/integration/tests.py -v --tb=short 2>&1 | tail -30
```

### Task 20: Verify Build

```bash
pip install -e . 2>&1 | tail -5
# Expected: Successfully installed blackhornet-colony-4.1.0
```

### Task 21: Verify Lint

```bash
ruff check src/ --select E,F,W --ignore E501 2>&1 | tail -10
# Expected: 0 errors
```

### Task 22: Final Commit

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

## VERIFICATION CHECKLIST

After completing all tasks:

- [ ] `pip install -e .` succeeds
- [ ] `python3 -m pytest` passes (non-numpy tests)
- [ ] `ruff check src/` shows 0 errors
- [ ] No real secrets in config/.env
- [ ] No internal hermes references
- [ ] All version numbers say 4.1.0
- [ ] CI workflow compiles only existing files
- [ ] Dockerfile has no dead URLs
- [ ] AGENTS.md claims match reality
- [ ] CONSCIOUSNESS.md exists with 5 traits
- [ ] BEE_NATURE.md exists with 7 characteristics
- [ ] Error handling in critical async functions
- [ ] Behavioral tests for core modules
