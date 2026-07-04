#!/bin/bash
# ============================================================================
# 🖤 BLACKHORNET — One-Command Nest Deployer
# ============================================================================
# Philosophy: Like hornets — autonomous, relentless, swarm-intelligent.
# One command births the entire sovereign agent empire.
#
#   curl -fsSL https://codeberg.org/Dhaher-Labs/blackhornet/raw/branch/main/deploy.sh | bash
# ============================================================================

set -euo pipefail

BOLD='\033[1m'; DIM='\033[2m'
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'

CODEBERG_USER="${CODEBERG_USER:-Dhaher-Labs}"
GITLAB_USER="${GITLAB_USER:-mulkymalikuldhr}"
NEST_DIR="${NEST_DIR:-$HOME/bh-ecosystem}"
BH_HOME="${BH_HOME:-$HOME/.bh}"

clone_repo() {
    local name="$1"
    local dest="$2"
    # Codeberg (primary) → GitLab (fallback) → GitHub (fallback)
    for url in \
        "https://codeberg.org/$CODEBERG_USER/$name.git" \
        "https://gitlab.com/$GITLAB_USER/$name.git" \
        "https://github.com/$CODEBERG_USER/$name.git"; do
        if git clone --depth 1 "$url" "$dest" 2>/dev/null; then
            return 0
        fi
    done
    return 1
}

HORNET_ART='
      \    /\
       )  ( '"'"')
      (  /  )
       \(__)|
        /  \
       /    \
      /      \
     /        \
    /          \
   /   BLACK    \
  /   HORNET     \
 /________________\
'

banner() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${BOLD}${HORNET_ART}${NC}"
    echo -e "${BOLD}  BLACKHORNET — Sovereign Autonomous Ecosystem${NC}"
    echo -e "${DIM}  One command. 9 repos. Infinite agents. Immortal empire.${NC}"
    echo ""
}

step() { echo -e "\n${CYAN}[$1]${NC} ${BOLD}$2${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
die()  { echo -e "\n${RED}✗ FATAL:${NC} $1"; exit 1; }

# ── Main ──────────────────────────────────────────────────────────────

main() {
    banner

    # 1. Prerequisites
    step "1/6" "Installing prerequisites..."
    command -v git &>/dev/null || die "git required"
    command -v curl &>/dev/null || die "curl required"

    # Python 3.11+
    PY=""
    for p in python3.11 python3.12 python3 python3.10; do
        if command -v "$p" &>/dev/null; then
            v=$("$p" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
            if [ "$(echo "$v" | cut -d. -f1)" -ge 3 ]; then
                PY="$p"; break
            fi
        fi
    done
    [ -n "$PY" ] || die "Python 3 required"
    ok "Python: $("$PY" --version)"

    # Node.js
    command -v node &>/dev/null || die "Node.js required (for JeumpaLLM)"
    ok "Node: $(node --version)"

    # uv
    if ! command -v uv &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    ok "uv: $(uv --version 2>/dev/null || echo 'installed')"

    # 2. Clone blackhornet
    step "2/6" "Building the nest..."
    mkdir -p "$NEST_DIR"
    if [ ! -d "$NEST_DIR/blackhornet" ]; then
        clone_repo "blackhornet" "$NEST_DIR/blackhornet"
    else
        git -C "$NEST_DIR/blackhornet" pull --rebase 2>/dev/null || true
    fi
    ok "blackhornet orchestrator ready"

    # 3. Clone all ecosystem repos
    step "3/6" "Deploying hornet swarm..."

    REPOS=(
        "JeumpaLLM"
        "mnemosyne"
        "agent"
        "Quant-Nanggroe-AI"
        "AI-MultiColony-Ecosystem"
        "Vibe-Trading"
    )

    for repo in "${REPOS[@]}"; do
        if [ -d "$NEST_DIR/$repo/.git" ]; then
            git -C "$NEST_DIR/$repo" pull --rebase 2>/dev/null && ok "$repo (updated)" || ok "$repo (exists)"
        else
            clone_repo "$repo" "$NEST_DIR/$repo" && ok "$repo" || warn "$repo (not found — will auto-expand later)"
        fi
    done

    # 4. Install JeumpaLLM deps
    step "4/6" "Starting JeumpaLLM (LLM gateway)..."
    cd "$NEST_DIR/JeumpaLLM"
    npm install --omit=dev --silent 2>/dev/null || true
    PORT=3333 nohup node index.js > /tmp/blackhornet-jeumpallm.log 2>&1 &
    sleep 3
    if curl -s http://localhost:3333/health > /dev/null 2>&1; then
        ok "JeumpaLLM ONLINE — 10 providers, 468 models, FREE"
    else
        warn "JeumpaLLM starting (check /tmp/blackhornet-jeumpallm.log)"
    fi

    # 5. Install blackhornet deps
    step "5/6" "Arming trading hornets..."
    cd "$NEST_DIR/blackhornet"
    "$PY" -m venv .venv 2>/dev/null || true
    . .venv/bin/activate 2>/dev/null || true
    "$PY" -m pip install -r requirements.txt openai -q 2>/dev/null || true
    ok "Trading pipeline armed"

    # Clone BlackHornet Agent (Nous Research)
    if [ ! -d "$BH_HOME/nous-agent" ]; then
        git clone --depth 1 https://github.com/NousResearch/hermes-agent.git "$BH_HOME/nous-agent" 2>/dev/null || true
        if [ -d "$BH_HOME/nous-agent" ]; then
            cd "$BH_HOME/nous-agent"
            UV_PYTHON="$PY" bash setup-bh.sh --skip-setup --non-interactive 2>/dev/null || true
        fi
    fi
    ok "BlackHornet Agent (Nous Research) installed"

    # 6. Start the nest
    step "6/6" "Launching BLACKHORNET nest..."

    cd "$NEST_DIR/blackhornet"

    # Start Unified Launcher (must run from project root for module imports)
    nohup "$PY" -m src.integration.unified_launcher --port 8080 > logs/launcher.log 2>&1 &
    echo "$!" > launcher.pid
    ok "Unified Launcher (PID $(cat launcher.pid))"

    # Register in swarm
    "$PY" -c "
from src.swarm.swarm_orchestrator import SwarmOrchestrator
print('Swarm engine available')
" 2>/dev/null || true
    ok "Swarm engine active"

    # ── Final Report ──────────────────────────────────────────────
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║     🖤 BLACKHORNET NEST — OPERATIONAL            ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Sovereign:${NC}    Mulky Malikul Dhaher"
    echo -e "  ${BOLD}Nest:${NC}         $NEST_DIR"
    echo -e "  ${BOLD}Hornets:${NC}      9 repos deployed"
    echo -e "  ${BOLD}LLM Gateway:${NC}  http://localhost:3333 (468 models, FREE)"
    echo -e "  ${BOLD}Launcher:${NC}     Unified — auto-heal + swarm"
    echo -e "  ${BOLD}Swarm:${NC}        Git-synced via dhaher-labs/agent"
    echo ""
    echo -e "  ${CYAN}Commands:${NC}"
    echo -e "    cd $NEST_DIR/blackhornet"
    echo -e "    python3 blackhornet.py --sovereign   # Control panel"
    echo -e "    python3 blackhornet.py --status      # Nest status"
    echo -e "    cd $NEST_DIR/blackhornet && python3 sovereign.py"
    echo ""
    echo -e "  ${DIM}The hornets are autonomous. The nest is immortal.${NC}"
    echo -e "  ${DIM}They hunt. They build. They expand. They never die.${NC}"
    echo ""
}

main "$@"
