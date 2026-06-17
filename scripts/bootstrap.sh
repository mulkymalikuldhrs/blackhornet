#!/bin/bash
# ============================================================================
# BLACKHORNET - Bootstrap Installer
# ============================================================================
# Auto-installer: one command to install everything.
# Run: curl -fsSL https://raw.githubusercontent.com/dhaher-labs/blackhornet/main/scripts/bootstrap.sh | bash
# Or:  bash scripts/bootstrap.sh
#
# Installs:
#   1. Python 3.11+ (if needed)
#   2. BlackHornet Agent from Nous Research (autonomous core)
#   3. blackhornet trading tools + dependencies
#   4. Shared memory sync bridge → dhaher-labs/agent
#   5. Immortal cron/auto-restart setup
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

BH_HOME="${BH_HOME:-$HOME/.bh}"
AGENT_REPO="https://github.com/dhaher-labs/agent.git"
HERMES_AGENT_REPO="https://github.com/NousResearch/hermes-agent.git"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo -e "${MAGENTA}${BOLD}⚕ BLACKHORNET - Bootstrap${NC}"
echo -e "${CYAN}Autonomous Multi-Agent Trading Infrastructure${NC}"
echo ""

# ── Guard: don't reinstall if already bootstrapped ──────────────────
if [ -f "$BH_HOME/.bootstrapped" ]; then
    echo -e "${GREEN}✓ Already bootstrapped at $BH_HOME${NC}"
    echo -e "${CYAN}→ Run 'bh chat' to start the agent${NC}"
    exit 0
fi

# ── Python 3.11+ check ───────────────────────────────────────────────
echo -e "${CYAN}[1/6]${NC} Checking Python 3.11+..."
PYTHON_BIN=""
for py in python3.11 python3.12 python3.13 python3; do
    if command -v $py &>/dev/null; then
        VER=$($py --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        MAJOR=$(echo $VER | cut -d. -f1)
        MINOR=$(echo $VER | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_BIN=$py
            echo -e "${GREEN}✓ $py $VER${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${YELLOW}⚠ Python 3.11+ not found, installing via uv...${NC}"
    if ! command -v uv &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    uv python install 3.11
    PYTHON_BIN="$(uv python find 3.11)"
    echo -e "${GREEN}✓ Python 3.11 installed: $PYTHON_BIN${NC}"
fi

# ── uv package manager ────────────────────────────────────────────────
echo -e "${CYAN}[2/6]${NC} Installing uv package manager..."
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
echo -e "${GREEN}✓ uv $(uv --version)${NC}"

# ── BlackHornet Agent (Nous Research) ──────────────────────────────────────
echo -e "${CYAN}[3/6]${NC} Installing BlackHornet Agent (Nous Research)..."
BH_AGENT_DIR="$BH_HOME/nous-agent"
if [ ! -d "$BH_AGENT_DIR" ]; then
    git clone "$HERMES_AGENT_REPO" "$BH_AGENT_DIR" --depth 1
fi
cd "$BH_AGENT_DIR"

# Run BlackHornet Agent setup (non-interactive)
UV_PYTHON="$PYTHON_BIN" bash setup-bh.sh --skip-setup 2>&1 | tail -5
echo -e "${GREEN}✓ BlackHornet Agent v$(./venv/bin/python bh --version 2>/dev/null | grep -oP 'v[\d.]+' | head -1)${NC}"

# ── BlackHornet Agent → system PATH ────────────────────────────────────────
mkdir -p "$HOME/.local/bin"
ln -sf "$BH_AGENT_DIR/bh" "$HOME/.local/bin/bh"
chmod +x "$HOME/.local/bin/bh" 2>/dev/null || true
echo -e "${GREEN}✓ 'bh' command linked to ~/.local/bin${NC}"

# ── blackhornet dependencies ────────────────────────────────────────
echo -e "${CYAN}[4/6]${NC} Installing blackhornet dependencies..."
cd "$REPO_DIR"
"$PYTHON_BIN" -m pip install -r requirements.txt -q 2>&1 | tail -3
echo -e "${GREEN}✓ Trading tools dependencies installed${NC}"

# ── Agent Memory Sync Bridge ──────────────────────────────────────────
echo -e "${CYAN}[5/6]${NC} Setting up Agent Swarm memory sync..."
AGENT_SYNC_DIR="$BH_HOME/agent-sync"

if [ ! -d "$AGENT_SYNC_DIR" ]; then
    git clone "$AGENT_REPO" "$AGENT_SYNC_DIR" 2>/dev/null || {
        echo -e "${YELLOW}⚠ Could not clone agent repo (needs auth).${NC}"
        echo -e "${YELLOW}  Set GITHUB_TOKEN env var and re-run.${NC}"
        mkdir -p "$AGENT_SYNC_DIR"
    }
fi

# BH Doctor handles memory sync
echo -e "${GREEN}✓ BH Doctor memory sync available${NC}"

# ── Immortal setup (auto-restart + cron) ──────────────────────────────
echo -e "${CYAN}[6/6]${NC} Configuring immortal auto-restart..."

# Install cron job for auto-restart every minute
CRON_JOB="* * * * * cd $REPO_DIR && bash bh.sh health > /dev/null 2>&1 || bash bh.sh start > /dev/null 2>&1"
(crontab -l 2>/dev/null | grep -v "bh.sh" ; echo "$CRON_JOB") | crontab - 2>/dev/null || {
    echo -e "${YELLOW}⚠ Cron not available — will use watchdog.py instead${NC}"
}

# Make scripts executable
chmod +x "$REPO_DIR/bh.sh" 2>/dev/null || true
chmod +x "$REPO_DIR/src/watchdog.py" 2>/dev/null || true
chmod +x "$REPO_DIR/bh-doctor" "$REPO_DIR/bh-doctor.sh" 2>/dev/null || true

echo -e "${GREEN}✓ Immortal auto-restart configured${NC}"

# ── Mark as bootstrapped ──────────────────────────────────────────────
mkdir -p "$BH_HOME"
touch "$BH_HOME/.bootstrapped"

echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ⚕ BLACKHORNET — INSTALLED & IMMORTAL  ${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}BlackHornet Agent:${NC}   $BH_AGENT_DIR"
echo -e "  ${BOLD}blackhornet:${NC}  $REPO_DIR"
echo -e "  ${BOLD}Agent Swarm:${NC}    $AGENT_SYNC_DIR"
echo ""
echo -e "${CYAN}Quick start:${NC}"
echo "  bh chat              # Start autonomous agent"
echo "  bash bh.sh start     # Start trading system"
echo "  bash bh.sh status    # Check system status"
echo ""
echo -e "${YELLOW}⚠  Set LLM API key in $BH_AGENT_DIR/.env before starting:${NC}"
echo "  OPENROUTER_API_KEY=your_key_here"
echo ""
