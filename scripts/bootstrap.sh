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
#   2. Hermes Agent from Nous Research (autonomous core)
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

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
AGENT_REPO="https://github.com/dhaher-labs/agent.git"
HERMES_AGENT_REPO="https://github.com/NousResearch/hermes-agent.git"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo -e "${MAGENTA}${BOLD}⚕ BLACKHORNET - Bootstrap${NC}"
echo -e "${CYAN}Autonomous Multi-Agent Trading Infrastructure${NC}"
echo ""

# ── Guard: don't reinstall if already bootstrapped ──────────────────
if [ -f "$HERMES_HOME/.bootstrapped" ]; then
    echo -e "${GREEN}✓ Already bootstrapped at $HERMES_HOME${NC}"
    echo -e "${CYAN}→ Run 'hermes chat' to start the agent${NC}"
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

# ── Hermes Agent (Nous Research) ──────────────────────────────────────
echo -e "${CYAN}[3/6]${NC} Installing Hermes Agent (Nous Research)..."
HERMES_AGENT_DIR="$HERMES_HOME/hermes-agent"
if [ ! -d "$HERMES_AGENT_DIR" ]; then
    git clone "$HERMES_AGENT_REPO" "$HERMES_AGENT_DIR" --depth 1
fi
cd "$HERMES_AGENT_DIR"

# Run Hermes Agent setup (non-interactive)
UV_PYTHON="$PYTHON_BIN" bash setup-hermes.sh --skip-setup 2>&1 | tail -5
echo -e "${GREEN}✓ Hermes Agent v$(./venv/bin/python hermes --version 2>/dev/null | grep -oP 'v[\d.]+' | head -1)${NC}"

# ── Hermes Agent → system PATH ────────────────────────────────────────
mkdir -p "$HOME/.local/bin"
ln -sf "$HERMES_AGENT_DIR/hermes" "$HOME/.local/bin/hermes"
chmod +x "$HOME/.local/bin/hermes" 2>/dev/null || true
echo -e "${GREEN}✓ 'hermes' command linked to ~/.local/bin${NC}"

# ── blackhornet dependencies ────────────────────────────────────────
echo -e "${CYAN}[4/6]${NC} Installing blackhornet dependencies..."
cd "$REPO_DIR"
"$PYTHON_BIN" -m pip install -r requirements.txt -q 2>&1 | tail -3
echo -e "${GREEN}✓ Trading tools dependencies installed${NC}"

# ── Agent Memory Sync Bridge ──────────────────────────────────────────
echo -e "${CYAN}[5/6]${NC} Setting up Agent Swarm memory sync..."
AGENT_SYNC_DIR="$HERMES_HOME/agent-sync"

if [ ! -d "$AGENT_SYNC_DIR" ]; then
    git clone "$AGENT_REPO" "$AGENT_SYNC_DIR" 2>/dev/null || {
        echo -e "${YELLOW}⚠ Could not clone agent repo (needs auth).${NC}"
        echo -e "${YELLOW}  Set GITHUB_TOKEN env var and re-run.${NC}"
        mkdir -p "$AGENT_SYNC_DIR"
    }
fi

# Copy memory bridge module
mkdir -p "$REPO_DIR/src/bridge"
cp "$REPO_DIR/src/memory_bridge.py" "$REPO_DIR/src/bridge/__init__.py" 2>/dev/null || true

echo -e "${GREEN}✓ Agent memory sync bridge ready${NC}"

# ── Immortal setup (auto-restart + cron) ──────────────────────────────
echo -e "${CYAN}[6/6]${NC} Configuring immortal auto-restart..."

# Install cron job for auto-restart every minute
CRON_JOB="* * * * * cd $REPO_DIR && bash hermes.sh health > /dev/null 2>&1 || bash hermes.sh start > /dev/null 2>&1"
(crontab -l 2>/dev/null | grep -v "hermes.sh" ; echo "$CRON_JOB") | crontab - 2>/dev/null || {
    echo -e "${YELLOW}⚠ Cron not available — will use watchdog.py instead${NC}"
}

# Make scripts executable
chmod +x "$REPO_DIR/hermes.sh" 2>/dev/null || true
chmod +x "$REPO_DIR/src/watchdog.py" 2>/dev/null || true
chmod +x "$REPO_DIR/src/memory_bridge.py" 2>/dev/null || true

echo -e "${GREEN}✓ Immortal auto-restart configured${NC}"

# ── Mark as bootstrapped ──────────────────────────────────────────────
mkdir -p "$HERMES_HOME"
touch "$HERMES_HOME/.bootstrapped"

echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ⚕ BLACKHORNET — INSTALLED & IMMORTAL  ${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Hermes Agent:${NC}   $HERMES_AGENT_DIR"
echo -e "  ${BOLD}blackhornet:${NC}  $REPO_DIR"
echo -e "  ${BOLD}Agent Swarm:${NC}    $AGENT_SYNC_DIR"
echo ""
echo -e "${CYAN}Quick start:${NC}"
echo "  hermes chat              # Start autonomous agent"
echo "  bash hermes.sh start     # Start trading system"
echo "  bash hermes.sh status    # Check system status"
echo ""
echo -e "${YELLOW}⚠  Set LLM API key in $HERMES_AGENT_DIR/.env before starting:${NC}"
echo "  OPENROUTER_API_KEY=your_key_here"
echo ""
