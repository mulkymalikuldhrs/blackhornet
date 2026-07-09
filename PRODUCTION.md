# BlackHornet Hive — Production Deployment Guide

> **Sovereign:** Mulky Malikul Dhaher  
> **Empire:** 25 packages, 10 specialized agents, swarm intelligence  
> **Status:** PRODUCTION READY (v4.1.0)

---

## Quick Deploy (30 seconds)

```bash
curl -fsSL https://raw.githubusercontent.com/dhaher-labs/blackhornet/main/install.sh | bash
```

This single command:
1. Detects your OS (Linux/macOS/Termux/WSL)
2. Installs all dependencies (Python 3.11+, Node.js, Git)
3. Clones all 7 ecosystem repos
4. Installs BlackHornet Agent (Nous Research)
5. Starts JeumpaLLM (10 free LLM providers, 468 models)
6. Configures Mnemosyne (knowledge memory + RAG)
7. Initializes swarm protocol
8. Starts immortal daemon
9. Registers your machine in the swarm
10. Begins autonomous operation

---

## Deployment Methods

### Method 1: Bare Metal (Recommended)

```bash
# Prerequisites: git, curl
curl -fsSL https://raw.githubusercontent.com/dhaher-labs/blackhornet/main/install.sh | bash
cd ~/blackhornet-ecosystem/blackhornet

# Start everything
bash blackhornet.sh all

# Verify
bash blackhornet.sh status
bash blackhornet.sh agent-status
bash blackhornet.sh daemon-status
```

### Method 2: Docker

```bash
docker run -d \
  --name blackhornet-hive \
  --restart always \
  -v ~/.blackhornet:/root/.blackhornet \
  -p 3333:3333 \
  -e NVIDIA_API_KEY=your_key \
  ghcr.io/dhaher-labs/blackhornet-hive:latest
```

### Method 3: systemd (Linux servers)

```bash
sudo cp deploy/blackhornet-hive.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now blackhornet-hive
```

### Method 4: Termux (Android)

```bash
pkg install git curl python
bash install.sh
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   BLACKHORNET HIVE — Sovereign Empire             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 0: LLM Gateway                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  JeumpaLLM v6.0.0                                 │    │
│  │  10 providers · 468 models · Auto-failover · FREE    │    │
│  │  /v1/chat/completions · /health · /models · /status  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 1: Autonomous Core                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  BlackHornet Agent (Nous Research)                        │    │
│  │  Self-improving · Tool-calling · Memory · Skills     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 2: Swarm Intelligence                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  SwarmOrchestrator · PSO · ABC · Stigmergy          │    │
│  │  Discovery · Sync · Upgrade · Heal · Expand          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 3: Trading Pipeline                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  L1 Data → L2 Analysis → L3 Decision → L4 Execution  │    │
│  │  → L5 Learning (21 specialized agents)               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 4: Knowledge Memory                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Mnemosyne · RAG · Knowledge Graph · 500+ models     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 5: Ecosystem Repos                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  blackhornet · QuantNanggroe · MultiColony         │    │
│  │  VibeTrading · AutoHedge · JeumpaLLM · Mnemosyne  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Verification Checklist

Run these commands to verify production readiness:

```bash
# 1. Install
pip install -e .
# Expected: Successfully installed blackhornet-colony-4.1.0

# 2. Run tests (non-numpy)
python3 -m pytest src/memory/tests.py src/thinking/tests.py src/core/tests.py \
  src/types/tests.py src/ui/tests.py src/graph/tests.py src/config/tests.py \
  src/sandbox/tests.py src/auto_discovery/tests.py src/integration/tests.py -v
# Expected: All tests pass

# 3. Lint
ruff check src/ --select E,F,W --ignore E501
# Expected: 0 errors

# 4. Verify no secrets
grep -r "nvapi-\|ghp_\|sk-" config/ src/ 2>/dev/null
# Expected: No output (no secrets in code)

# 5. Verify version
python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml'))['project']['version'])"
# Expected: 4.1.0
```

All should return ✅ without errors for production readiness.

---

## Security

- **API keys:** Use `config/.env` (gitignored). Never commit real values.
- **Wallet addresses:** Use environment variables only. Never hardcode.
- **Risk limits:** Hardcoded in source. No agent can override.
- **Deployment stage:** Defaults to `research_lab` (paper trading only).
- **Secrets scan:** `grep -r "nvapi-\|ghp_\|sk-" config/ src/` should return 0 hits.

---

## Upgrading

Pull latest changes and restart:

```bash
cd ~/blackhornet-ecosystem/blackhornet
git pull
pip install -e .
# Restart services as needed
```

---

## Support

- GitHub: https://github.com/dhaher-labs/blackhornet
- Swarm: https://github.com/dhaher-labs/agent
- Owner: Mulky Malikul Dhaher
