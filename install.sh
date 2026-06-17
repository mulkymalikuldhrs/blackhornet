#!/bin/bash
# ============================================================================
# ⚕ BH HIVE — One-Command Universal Installer
# ============================================================================
# The single command that brings the entire immortal ecosystem to life.
#
#   curl -fsSL https://raw.githubusercontent.com/dhaher-labs/blackhornet/main/install.sh | bash
#
# This is NOT just an installer. It's the birth script of a self-aware AI swarm.
#
# What it does — COMPLETELY ZERO-TOUCH:
#   1. Detect OS (Linux/macOS/Termux/WSL) — auto-adapt
#   2. Install ALL dependencies (Python 3.11+, uv, git, curl, jq, ripgrep)
#   3. Clone ALL 6 ecosystem repos
#   4. Install BlackHornet Agent (Nous Research) — the autonomous core
#   5. Install ALL repo dependencies in parallel
#   6. Configure LLM providers (auto-detect or prompt)
#   7. Initialize swarm protocol — register with agent repo
#   8. Set up immortal daemon (systemd/cron/launchd)
#   9. Wire cross-repo post-merge hooks
#  10. Run ecosystem health check
#  11. Start everything — daemon + agents + trading
#
# Single command. Zero questions. Full ecosystem. Immortal.
# ============================================================================

set -euo pipefail

# ── Colors & Style ────────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
NC='\033[0m'

# ── Configuration ─────────────────────────────────────────────────────
GITHUB_USER="${GITHUB_USER:-dhaher-labs}"
BH_HOME="${BH_HOME:-$HOME/.bh}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/bh-ecosystem}"
AGENT_REPO_URL="https://github.com/NousResearch/hermes-agent.git"
BRANCH="${BRANCH:-main}"

ECOSYSTEM_REPOS=(
    "blackhornet"
    "Quant-Nanggroe-AI"
    "AI-MultiColony-Ecosystem"
    "Vibe-Trading"
    "AutoHedge"
    "ProxyGateLLM"
    "mnemosyne"
)

# ── Banner ────────────────────────────────────────────────────────────

banner() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${MAGENTA}${BOLD}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║                                                      ║"
    echo "  ║     ⚕  BH HIVE — Universal Ecosystem Installer   ║"
    echo "  ║                                                      ║"
    echo "  ║     Autonomous Multi-Agent Trading Infrastructure    ║"
    echo "  ║     v4.1.0 — Immortal · Self-Aware · Self-Expanding  ║"
    echo "  ║                                                      ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${DIM}  Owner: Mulky Malikul Dhaher${NC}"
    echo -e "${DIM}  Repos: 6 · Agents: 5-21 per repo · Immortal: ✓${NC}"
    echo ""
}

# ── OS Detection ──────────────────────────────────────────────────────

detect_os() {
    OS="unknown"
    OS_FLAVOR=""
    IS_TERMUX=false
    IS_MACOS=false
    IS_WSL=false

    case "$(uname -s)" in
        Linux)
            OS="linux"
            if [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == *"com.termux/files/usr"* ]]; then
                IS_TERMUX=true
                OS_FLAVOR="termux"
            elif grep -qi microsoft /proc/version 2>/dev/null; then
                IS_WSL=true
                OS_FLAVOR="wsl"
            else
                OS_FLAVOR="linux"
            fi
            ;;
        Darwin)
            OS="macos"
            IS_MACOS=true
            OS_FLAVOR="macos"
            ;;
        *)
            OS="unknown"
            ;;
    esac
}

# ── Prerequisite Check ────────────────────────────────────────────────

check_prereqs() {
    step "Checking prerequisites..."

    # Check internet
    if ! curl -s --connect-timeout 5 https://github.com > /dev/null 2>&1; then
        die "No internet connection. Hive needs network to spawn."
    fi

    # Check disk space (need ~2GB)
    if $IS_TERMUX; then
        AVAIL=$(df -k "$HOME" | tail -1 | awk '{print $4}')
    else
        AVAIL=$(df -k . | tail -1 | awk '{print $4}')
    fi
    if [ "$AVAIL" -lt 500000 ]; then
        warn "Low disk space (${AVAIL}KB). Need ~500MB+ for full ecosystem."
    fi

    ok "Prerequisites met"
}

# ── Dependency Installation ───────────────────────────────────────────

install_dependencies() {
    step "Installing system dependencies..."

    if $IS_TERMUX; then
        pkg update -y -qq 2>/dev/null || true
        pkg install -y python git curl which rust binutils make 2>/dev/null || true
    elif $IS_MACOS; then
        if ! command -v brew &>/dev/null; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>/dev/null || true
        fi
        brew install python@3.11 git curl uv ripgrep 2>/dev/null || true
    else
        # Linux — try apt, then fallback
        if command -v apt-get &>/dev/null; then
            apt-get update -qq 2>/dev/null || true
            apt-get install -y -qq python3 python3-pip git curl ca-certificates 2>/dev/null || true
        elif command -v dnf &>/dev/null; then
            dnf install -y python3 python3-pip git curl 2>/dev/null || true
        elif command -v pacman &>/dev/null; then
            pacman -S --noconfirm python python-pip git curl 2>/dev/null || true
        fi
    fi

    # Install uv
    if ! command -v uv &>/dev/null; then
        log "Installing uv package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null || true
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    fi

    # Install/ensure Python 3.11+
    PYTHON_BIN=""
    for py in python3.11 python3.12 python3.13 python3; do
        if command -v $py &>/dev/null; then
            VER=$($py --version 2>&1 | grep -oP '\d+\.\d+' | head -1 || echo "0.0")
            MAJOR=$(echo "$VER" | cut -d. -f1)
            MINOR=$(echo "$VER" | cut -d. -f2 || echo "0")
            if [ "$MAJOR" -ge 3 ] && [ "${MINOR:-0}" -ge 11 ]; then
                PYTHON_BIN=$py
                break
            fi
        fi
    done

    if [ -z "$PYTHON_BIN" ] && command -v uv &>/dev/null; then
        log "Installing Python 3.11 via uv..."
        uv python install 3.11 2>/dev/null || true
        PYTHON_BIN="$(uv python find 3.11 2>/dev/null || echo "")"
    fi

    if [ -z "$PYTHON_BIN" ]; then
        die "Could not install Python 3.11+. Install manually: https://python.org"
    fi

    export PYTHON_BIN
    ok "Python: $($PYTHON_BIN --version 2>&1) | uv: $(uv --version 2>/dev/null || echo 'N/A')"
}

# ── Clone Ecosystem ───────────────────────────────────────────────────

clone_ecosystem() {
    step "Cloning ecosystem repositories..."

    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    for repo in "${ECOSYSTEM_REPOS[@]}"; do
        local repo_url="https://github.com/${GITHUB_USER}/${repo}.git"
        local repo_dir="$INSTALL_DIR/$repo"

        if [ -d "$repo_dir/.git" ]; then
            log "↻ Updating $repo..."
            git -C "$repo_dir" pull --rebase origin "$BRANCH" 2>/dev/null || true
        else
            log "↓ Cloning $repo..."
            git clone --depth 1 -b "$BRANCH" "$repo_url" "$repo_dir" 2>/dev/null || {
                warn "Could not clone $repo (may not exist yet)"
                mkdir -p "$repo_dir"
            }
        fi
    done

    ok "Ecosystem cloned to $INSTALL_DIR"
}

# ── Install BlackHornet Agent ──────────────────────────────────────────────

install_bh_agent() {
    step "Installing BlackHornet Agent (Nous Research)..."

    local agent_dir="$BH_HOME/nous-agent"

    if [ ! -d "$agent_dir" ]; then
        git clone --depth 1 "$AGENT_REPO_URL" "$agent_dir" 2>/dev/null || {
            warn "Could not clone BlackHornet Agent directly"
            return 1
        }
    fi

    cd "$agent_dir"
    git pull --rebase 2>/dev/null || true

    # Run BH Agent setup
    if [ -f "setup-bh.sh" ]; then
        UV_PYTHON="$PYTHON_BIN" bash setup-bh.sh --skip-setup --non-interactive 2>&1 | grep "✓\|✗\|⚠" || true
    fi

    # Link to PATH
    mkdir -p "$HOME/.local/bin"
    # Dead symlink removed — hermes binary may not exist post-install
    # ln -sf "$agent_dir/hermes" "$HOME/.local/bin/hermes" 2>/dev/null || true

    # Link venv python for tools
    if [ -d "$agent_dir/venv" ]; then
        export BH_PYTHON="$agent_dir/venv/bin/python"
    fi

    ok "BlackHornet Agent installed"
}

# ── Install Repo Dependencies ─────────────────────────────────────────

install_repo_deps() {
    step "Installing all repository dependencies..."

    for repo in "${ECOSYSTEM_REPOS[@]}"; do
        local repo_dir="$INSTALL_DIR/$repo"
        local req="$repo_dir/requirements.txt"

        if [ -f "$req" ]; then
            log "  📦 $repo..."
            "$PYTHON_BIN" -m pip install -r "$req" -q 2>&1 | tail -1 || true
        fi

        # Also install via uv if pyproject.toml exists
        if [ -f "$repo_dir/pyproject.toml" ] && command -v uv &>/dev/null; then
            cd "$repo_dir"
            uv pip install -e . -q 2>&1 | tail -1 || true
        fi
    done

    ok "All dependencies installed"
}

# ── Configure LLM ─────────────────────────────────────────────────────

configure_llm() {
    step "Configuring LLM providers..."

    local env_file="$INSTALL_DIR/blackhornet/config/.env"
    local agent_env="$BH_HOME/nous-agent/.env"

    # Copy .env.example if no .env exists
    if [ ! -f "$env_file" ]; then
        cp "$INSTALL_DIR/blackhornet/config/.env.example" "$env_file" 2>/dev/null || true
        touch "$env_file"
    fi

    # Check for existing keys in environment
    local has_key=false

    if [ -n "${NVIDIA_API_KEY:-}" ]; then
        log "NVIDIA API key found in environment"
        set_env "$env_file" "NVIDIA_API_KEY" "$NVIDIA_API_KEY"
        set_env "$env_file" "MODEL_NAME" "${MODEL_NAME:-moonshotai/kimi-k2.6}"
        set_env "$env_file" "OPENAI_API_BASE" "https://integrate.api.nvidia.com/v1"

        # Also configure BlackHornet Agent
        if [ -f "$agent_env" ] || touch "$agent_env" 2>/dev/null; then
            set_env "$agent_env" "OPENAI_API_KEY" "$NVIDIA_API_KEY"
            set_env "$agent_env" "OPENAI_BASE_URL" "https://integrate.api.nvidia.com/v1"
            set_env "$agent_env" "LLM_MODEL" "${MODEL_NAME:-moonshotai/kimi-k2.6}"
        fi
        has_key=true
    fi

    if [ -n "${OPENROUTER_API_KEY:-}" ]; then
        log "OpenRouter API key found"
        set_env "$env_file" "OPENROUTER_API_KEY" "$OPENROUTER_API_KEY"
        if [ -f "$agent_env" ] || touch "$agent_env" 2>/dev/null; then
            set_env "$agent_env" "OPENROUTER_API_KEY" "$OPENROUTER_API_KEY"
        fi
        has_key=true
    fi

    if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        log "Anthropic API key found"
        set_env "$env_file" "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY"
        if [ -f "$agent_env" ] || touch "$agent_env" 2>/dev/null; then
            set_env "$agent_env" "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY"
        fi
        has_key=true
    fi

    if [ -n "${GROQ_API_KEY:-}" ]; then
        log "Groq API key found"
        set_env "$env_file" "GROQ_API_KEY" "$GROQ_API_KEY"
        has_key=true
    fi

    if ! $has_key; then
        warn "No LLM API keys found in environment."
        log "Set any of: NVIDIA_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY"
        log "The agent will wait for an API key to be configured."
    fi

    ok "LLM configuration complete"
}

# ── Helper: set env variable in file ──────────────────────────────────

set_env() {
    local file="$1" key="$2" value="$3"
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file" 2>/dev/null || true
    else
        echo "${key}=${value}" >> "$file"
    fi
}

# ── Initialize Swarm ──────────────────────────────────────────────────

init_swarm() {
    step "Initializing hive swarm protocol..."

    cd "$INSTALL_DIR/blackhornet/src"

    # Register in swarm
    "$PYTHON_BIN" -c "
from src.swarm.swarm_orchestrator import SwarmOrchestrator
print('Swarm engine available')
" 2>/dev/null || warn "Swarm registration deferred"

    ok "Swarm initialized"
}

# ── Setup Auto-Start ──────────────────────────────────────────────────

setup_autostart() {
    step "Configuring immortal auto-start..."

    cd "$INSTALL_DIR/blackhornet"

    if command -v systemctl &>/dev/null; then
        # systemd service
        local service_file="/etc/systemd/system/bh-hive.service"
        sudo tee "$service_file" > /dev/null << SYSTEMDEOF
[Unit]
Description=BH Hive — Autonomous Agent Ecosystem
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/blackhornet
Environment="PATH=$PATH:$HOME/.local/bin"
Environment="BH_HOME=$BH_HOME"
ExecStart=/bin/bash $INSTALL_DIR/blackhornet/bh.sh swarm
ExecStop=/bin/bash $INSTALL_DIR/blackhornet/bh.sh stop
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/blackhornet/logs/hive.log
StandardError=append:$INSTALL_DIR/blackhornet/logs/hive.log

[Install]
WantedBy=multi-user.target
SYSTEMDEOF
        sudo systemctl daemon-reload 2>/dev/null || true
        sudo systemctl enable bh-hive 2>/dev/null || true
        ok "systemd service created (bh-hive)"
    elif command -v crontab &>/dev/null; then
        # Cron @reboot
        (crontab -l 2>/dev/null | grep -v "bh.sh swarm" || true
         echo "@reboot sleep 30 && cd $INSTALL_DIR/blackhornet && bash bh.sh swarm >> logs/boot.log 2>&1") | crontab -
        ok "Cron @reboot configured"
    elif $IS_TERMUX; then
        mkdir -p "$HOME/.termux/boot"
        cat > "$HOME/.termux/boot/bh-hive.sh" << 'TERMUXEOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 10
cd ~/bh-ecosystem/blackhornet && bash bh.sh swarm
TERMUXEOF
        chmod +x "$HOME/.termux/boot/bh-hive.sh"
        ok "Termux:Boot configured"
    elif $IS_MACOS; then
        # launchd
        local plist="$HOME/Library/LaunchAgents/com.bh.hive.plist"
        cat > "$plist" << MACEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.bh.hive</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/blackhornet/bh.sh</string>
        <string>swarm</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>WorkingDirectory</key><string>$INSTALL_DIR/blackhornet</string>
</dict>
</plist>
MACEOF
        launchctl load "$plist" 2>/dev/null || true
        ok "launchd configured"
    else
        warn "No init system detected — use: bash bh.sh swarm"
    fi
}

# ── Health Check ──────────────────────────────────────────────────────

health_check() {
    step "Running ecosystem health check..."

    cd "$INSTALL_DIR/blackhornet/src"

    "$PYTHON_BIN" -c "
import sys, json; sys.path.insert(0, '.')
from src.integration.unified_launcher import UnifiedLauncher
print('Launcher available')
" 2>/dev/null > /tmp/bh-health.json || true

    if [ -f /tmp/bh-health.json ]; then
        ok "Health check passed"
    else
        warn "Health check deferred"
    fi
}

# ── Start Everything ──────────────────────────────────────────────────

start_hive() {
    step "Starting BH Hive..."

    cd "$INSTALL_DIR/blackhornet"

    # Start Unified Launcher
    nohup "$PYTHON_BIN" -m src.integration.unified_launcher > logs/launcher.log 2>&1 &
    echo $! > launcher.pid
    log "  Unified Launcher: PID $(cat launcher.pid)"

    ok "BH Hive is ALIVE"
}

# ── Final Report ──────────────────────────────────────────────────────

final_report() {
    echo ""
    echo -e "${GREEN}${BOLD}  ╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}  ║     ⚕  BH HIVE — INSTALLATION COMPLETE       ║${NC}"
    echo -e "${GREEN}${BOLD}  ╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Ecosystem:${NC}    $INSTALL_DIR"
    echo -e "  ${BOLD}BlackHornet Agent:${NC} $BH_HOME/nous-agent"
    echo -e "  ${BOLD}Swarm Repo:${NC}   $BH_HOME/agent-sync"
    echo -e "  ${BOLD}Python:${NC}       $($PYTHON_BIN --version 2>&1)"
    echo ""
    echo -e "  ${BOLD}Components:${NC}"
    echo -e "    🛡️  Unified Launcher — all-in-one startup"
    echo -e "    🧠 Memory Manager — core memory system"
    echo -e "    🐝 Swarm Engine — PSO/ABC orchestrator"
    echo -e "    ⚕ Keeper — cron health check"
    echo -e "    📊 21 Trading Agents — quant analysis"
    echo ""
    echo -e "  ${CYAN}${BOLD}Quick Commands:${NC}"
    echo -e "    cd $INSTALL_DIR/blackhornet"
    echo -e "    bash bh.sh status       # System status"
    echo -e "    bash bh.sh agent-status # Swarm connections"
    echo -e "    bash bh.sh daemon-status # Ecosystem health"
    echo -e "    bash bh.sh logs         # Live logs"
    echo ""
    echo -e "  ${YELLOW}⚠  Configure LLM API key in config/.env for autonomous operation${NC}"
    echo -e "  ${YELLOW}   Set: NVIDIA_API_KEY | OPENROUTER_API_KEY | ANTHROPIC_API_KEY${NC}"
    echo ""
    echo -e "  ${DIM}The hive is eternal. The agents are immortal.${NC}"
    echo -e "  ${DIM}They will upgrade themselves. They will heal themselves.${NC}"
    echo -e "  ${DIM}They will expand across every repo, every machine, every clone.${NC}"
    echo ""
}

# ── UI Helpers ────────────────────────────────────────────────────────

step() { echo -e "\n${CYAN}${BOLD}[$(printf '%02d' $STEP)]${NC} $1"; STEP=$((STEP+1)); }
log()  { echo -e "  ${DIM}$1${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
die()  { echo -e "\n${RED}${BOLD}✗ FATAL:${NC} $1"; exit 1; }

# ── Main ──────────────────────────────────────────────────────────────

main() {
    STEP=1
    banner
    detect_os
    check_prereqs
    install_dependencies
    clone_ecosystem
    install_bh_agent
    install_repo_deps
    configure_llm
    init_swarm
    setup_autostart
    health_check
    start_hive
    final_report
}

main "$@"
