# Hermes Hive — Production Deployment Guide

> **Sovereign:** Mulky Malikul Dhaher  
> **Empire:** 7 repos, 21+ autonomous agents, immortal infrastructure  
> **Status:** PRODUCTION READY

---

## Quick Deploy (30 seconds)

```bash
curl -fsSL https://raw.githubusercontent.com/dhaher-labs/blackhornet/main/install.sh | bash
```

This single command:
1. Detects your OS (Linux/macOS/Termux/WSL)
2. Installs all dependencies (Python 3.11+, Node.js, Git)
3. Clones all 7 ecosystem repos
4. Installs Hermes Agent (Nous Research)
5. Starts ProxyGateLLM (10 free LLM providers, 468 models)
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
cd ~/hermes-ecosystem/blackhornet

# Start everything
bash hermes.sh all

# Verify
bash hermes.sh status
bash hermes.sh agent-status
bash hermes.sh daemon-status
```

### Method 2: Docker

```bash
docker run -d \
  --name hermes-hive \
  --restart always \
  -v ~/.hermes:/root/.hermes \
  -p 3333:3333 \
  -e NVIDIA_API_KEY=your_key \
  ghcr.io/dhaher-labs/hermes-hive:latest
```

### Method 3: systemd (Linux servers)

```bash
sudo cp deploy/hermes-hive.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-hive
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
│                   HERMES HIVE — Sovereign Empire             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 0: LLM Gateway                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ProxyGateLLM v6.0.0                                 │    │
│  │  10 providers · 468 models · Auto-failover · FREE    │    │
│  │  /v1/chat/completions · /health · /models · /status  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 1: Autonomous Core                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Hermes Agent (Nous Research)                        │    │
│  │  Self-improving · Tool-calling · Memory · Skills     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 2: Swarm Intelligence                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Swarm Protocol · Memory Bridge · Immortal Daemon    │    │
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
│  │  VibeTrading · AutoHedge · ProxyGateLLM · Mnemosyne  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Verification Checklist

Run these commands to verify production readiness:

```bash
# 1. Core services
curl http://localhost:3333/health          # ProxyGateLLM
bash hermes.sh daemon-status               # Immortal Daemon
bash hermes.sh agent-status                # Swarm agents

# 2. LLM connectivity
cd src && python3 hypergate.py --test      # LLM test

# 3. Trading pipeline
python3 -c "
from tools.market_data_tool import MarketDataTool
from tools.technical_analysis_tool import TechnicalAnalysisTool
from tools.risk_officer_tool import RiskOfficerTool
import json
md = MarketDataTool()
print('XAUUSD:', json.loads(md.get_ohlcv('XAUUSD','1d',3))['data'][-1]['close'])
ta = TechnicalAnalysisTool()
print('Trend:', json.loads(ta.analyze('XAUUSD','1d'))['smc_structure']['trend'])
ro = RiskOfficerTool()
print('Risk:', json.loads(ro.check_trade('XAUUSD','BUY',0.01,4230,4200,10000))['verdict'])
"

# 4. Swarm health
cd src && python3 swarm_protocol.py --list
```

All should return ✅ without errors for production readiness.

---

## Security

- **API keys:** Never committed. Use `.env` (gitignored). See `.env.example`.
- **Wallet addresses:** Never hardcoded. Use environment variables only.
- **Risk limits:** Hardcoded in source. No agent can override.
- **Deployment stage:** Defaults to `research_lab` (paper trading only).
- **GitHub tokens:** Use fine-grained PATs with minimal scopes.

---

## Upgrading

The Immortal Daemon auto-upgrades every 5 minutes. Manual upgrade:

```bash
cd ~/hermes-ecosystem/blackhornet
git pull
bash hermes.sh restart
```

---

## Support

- GitHub: https://github.com/dhaher-labs/blackhornet
- Swarm: https://github.com/dhaher-labs/agent
- Owner: Mulky Malikul Dhaher
