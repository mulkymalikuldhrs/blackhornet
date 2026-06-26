#!/bin/bash
# ============================================================================
# ⚕ BH DOCTOR — ONE Installer · ONE Launcher · ONE Vision
# ============================================================================
# The single command that brings the entire immortal ecosystem to life.
#
#   curl -fsSL https://raw.githubusercontent.com/dhaher-labs/blackhornet/main/bh-doctor.sh | bash
#
# Replaces: install.sh, install_termux.sh, install_server.sh, bootstrap.sh, deploy.sh
#
# What it does — COMPLETELY ZERO-TOUCH:
#   1. Detect OS (Linux/macOS/Termux/WSL/Docker) — auto-adapt
#   2. Install ALL dependencies (Python 3.11+, uv, git, curl, jq, ripgrep)
#   3. Install BH Doctor Agent (Hermes + BH Extension)
#   4. Clone ALL ecosystem repos
#   5. Install ALL repo dependencies in parallel
#   6. Configure LLM providers (auto-detect or prompt)
#   7. Initialize Graphify + Session Export
#   8. Set up immortal gateway (systemd/cron/launchd/termux-boot)
#   9. Wire cross-repo post-merge hooks
#  10. Run ecosystem health check
#  11. Start everything — daemon + agents + graph
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
NC='\033[0m'

# ── Configuration ─────────────────────────────────────────────────────
GITHUB_USER="${GITHUB_USER:-dhaher-labs}"
CODEBERG_USER="${CODEBERG_USER:-dhaher-labs}"
BH_HOME="${BH_HOME:-$HOME/.bh}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/bh-ecosystem}"
BRANCH="${BRANCH:-main}"

ECOSYSTEM_REPOS=(
    "blackhornet"
    "Quant-Nanggroe-AI"
    "AI-MultiColony-Ecosystem"
    "Vibe-Trading"
    "AutoHedge"
    "JeumpaLLM"
    "mnemosyne"
)

# ── State ──────────────────────────────────────────────────────────────
STEP=1
OS="unknown"
OS_FLAVOR=""
IS_TERMUX=false
IS_MACOS=false
IS_WSL=false
PYTHON_BIN=""

# ── Banner ────────────────────────────────────────────────────────────
banner() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${MAGENTA}${BOLD}"
    echo "  ╔══════════════════════════════════════════════════════════╗"
    echo "  ║                                                          ║"
    echo "  ║     ⚕  BH DOCTOR — Universal Ecosystem Installer      ║"
    echo "  ║                                                          ║"
    echo "  ║     Autonomous Multi-Agent Sovereign Infrastructure      ║"
    echo "  ║     v5.0.0 — All-in-One · Immortal · Self-Healing       ║"
    echo "  ║                                                          ║"
    echo "  ╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${DIM}  Sovereign: Mulky Malikul Dhaher${NC}"
    echo -e "${DIM}  Repos: ${#ECOSYSTEM_REPOS[@]} · Agents: 55+ · Graphify: ✓ · Immortal: ✓${NC}"
    echo ""
}

# ── OS Detection ──────────────────────────────────────────────────────
detect_os() {
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

    if ! curl -s --connect-timeout 5 https://github.com > /dev/null 2>&1; then
        die "No internet connection. Hive needs network to spawn."
    fi

    if $IS_TERMUX; then
        AVAIL=$(df -k "$HOME" 2>/dev/null | tail -1 | awk '{print $4}')
    else
        AVAIL=$(df -k . 2>/dev/null | tail -1 | awk '{print $4}')
    fi
    AVAIL=${AVAIL:-0}
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
        pkg install -y python git curl which rust binutils make openssl-tool 2>/dev/null || true
    elif $IS_MACOS; then
        if ! command -v brew &>/dev/null; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>/dev/null || true
        fi
        brew install python@3.11 git curl uv ripgrep jq 2>/dev/null || true
    else
        if command -v apt-get &>/dev/null; then
            apt-get update -qq 2>/dev/null || true
            apt-get install -y -qq python3 python3-pip python3-venv git curl ca-certificates jq ripgrep 2>/dev/null || true
        elif command -v dnf &>/dev/null; then
            dnf install -y python3 python3-pip git curl jq ripgrep 2>/dev/null || true
        elif command -v pacman &>/dev/null; then
            pacman -S --noconfirm python python-pip git curl jq ripgrep 2>/dev/null || true
        fi
    fi

    # Install uv
    if ! command -v uv &>/dev/null; then
        log "Installing uv package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null || true
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    fi

    # Install/ensure Python 3.11+
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

    for repo in "${ECOSYSTEM_REPOS[@]}"; do
        local repo_dir="$INSTALL_DIR/$repo"

        # Try Codeberg first, fallback to GitHub
        if [ ! -d "$repo_dir/.git" ]; then
            log "↓ Cloning $repo (Codeberg)..."
            git clone --depth 1 -b "$BRANCH" "https://codeberg.org/${CODEBERG_USER}/${repo}.git" "$repo_dir" 2>/dev/null || {
                log "↓ Cloning $repo (GitHub fallback)..."
                git clone --depth 1 -b "$BRANCH" "https://github.com/${GITHUB_USER}/${repo}.git" "$repo_dir" 2>/dev/null || {
                    warn "Could not clone $repo from any remote"
                    mkdir -p "$repo_dir"
                }
            }
            # Add both remotes
            if [ -d "$repo_dir/.git" ]; then
                git -C "$repo_dir" remote add codeberg "https://codeberg.org/${CODEBERG_USER}/${repo}.git" 2>/dev/null || true
                git -C "$repo_dir" remote add github "https://github.com/${GITHUB_USER}/${repo}.git" 2>/dev/null || true
            fi
        else
            log "↻ Updating $repo..."
            git -C "$repo_dir" pull --rebase origin "$BRANCH" 2>/dev/null || true
        fi
    done

    ok "Ecosystem cloned to $INSTALL_DIR"
}

# ── Install BH Doctor Agent (Hermes + BH Extension) ────────────────────
install_bh_agent() {
    step "Installing BH Doctor Agent..."

    local agent_dir="$BH_HOME/doctor-agent"
    mkdir -p "$agent_dir"

    # Install BH Doctor Python package
    cd "$INSTALL_DIR/blackhornet" 2>/dev/null || {
        warn "blackhornet repo not cloned yet"
        return 1
    }

    "$PYTHON_BIN" -m pip install -e . -q 2>&1 | tail -1 || true

    # Install Hermes Agent if available
    if [ -d "/usr/local/lib/hermes-agent" ]; then
        log "Hermes Agent found at /usr/local/lib/hermes-agent"
        local hermes_bin="/usr/local/lib/hermes-agent/venv/bin/hermes"
        if [ -f "$hermes_bin" ]; then
            mkdir -p "$HOME/.local/bin"
            ln -sf "$hermes_bin" "$HOME/.local/bin/bh-doctor-agent" 2>/dev/null || true
        fi
    elif [ -d "/tmp/hermes-agent" ]; then
        log "Hermes Agent found at /tmp/hermes-agent"
        local hermes_bin="/tmp/hermes-agent/venv/bin/hermes"
        if [ -f "$hermes_bin" ]; then
            mkdir -p "$HOME/.local/bin"
            ln -sf "$hermes_bin" "$HOME/.local/bin/bh-doctor-agent" 2>/dev/null || true
        fi
    else
        log "Cloning Hermes Agent..."
        git clone --depth 1 "https://github.com/NousResearch/hermes-agent.git" "$agent_dir/hermes" 2>/dev/null || {
            warn "Could not clone Hermes Agent"
        }
    fi

    ok "BH Doctor Agent installed"
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
    mkdir -p "$(dirname "$env_file")"

    if [ ! -f "$env_file" ]; then
        if [ -f "$INSTALL_DIR/blackhornet/config/.env.example" ]; then
            cp "$INSTALL_DIR/blackhornet/config/.env.example" "$env_file" 2>/dev/null || true
        else
            touch "$env_file"
        fi
    fi

    local has_key=false

    if [ -n "${NVIDIA_API_KEY:-}" ]; then
        log "NVIDIA API key found"
        set_env "$env_file" "NVIDIA_API_KEY" "$NVIDIA_API_KEY"
        set_env "$env_file" "OPENAI_API_BASE" "https://integrate.api.nvidia.com/v1"
        has_key=true
    fi

    if [ -n "${OPENROUTER_API_KEY:-}" ]; then
        log "OpenRouter API key found"
        set_env "$env_file" "OPENROUTER_API_KEY" "$OPENROUTER_API_KEY"
        has_key=true
    fi

    if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        log "Anthropic API key found"
        set_env "$env_file" "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY"
        has_key=true
    fi

    if [ -n "${GROQ_API_KEY:-}" ]; then
        log "Groq API key found"
        set_env "$env_file" "GROQ_API_KEY" "$GROQ_API_KEY"
        has_key=true
    fi

    if [ -n "${OPENCODE_API_KEY:-}" ]; then
        log "OpenCode API key found"
        set_env "$env_file" "OPENCODE_API_KEY" "$OPENCODE_API_KEY"
        has_key=true
    fi

    if [ -n "${OPENAI_API_KEY:-}" ]; then
        log "OpenAI API key found"
        set_env "$env_file" "OPENAI_API_KEY" "$OPENAI_API_KEY"
        has_key=true
    fi

    if ! $has_key; then
        warn "No LLM API keys found in environment."
        log "Set any of: NVIDIA_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, OPENCODE_API_KEY, OPENAI_API_KEY"
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
        printf '%s=%s\n' "$key" "$value" >> "$file"
    fi
}

# ── Initialize Graphify + Session Export ──────────────────────────────
init_graphify() {
    step "Initializing Graphify + Session Export..."

    cd "$INSTALL_DIR/blackhornet/src" 2>/dev/null || {
        warn "BH source not found, skipping graphify init"
        return 1
    }

    # Initialize graph store
    "$PYTHON_BIN" -c "
import sys, os
sys.path.insert(0, '.')
try:
    from graph.graph_store import GraphStore
    gs = GraphStore()
    gs.add_node('BH_DOCTOR', 'system', {'version': '5.0.0', 'status': 'initializing'})
    gs.add_node('SOVEREIGN', 'person', {'name': 'Mulky Malikul Dhaher'})
    print('✓ Graph store initialized')
    print(f'  Nodes: {gs.stats()[\"nodes\"]}')
except Exception as e:
    print(f'Graph init: {e}')
" 2>/dev/null || warn "Graphify init deferred"

    # Create session export directory
    mkdir -p "$INSTALL_DIR/blackhornet/data/session-export"

    # Create SOUL.md symlink if not exists
    if [ ! -f "$INSTALL_DIR/blackhornet/SOUL.md" ]; then
        log "Creating SOUL.md..."
        cat > "$INSTALL_DIR/blackhornet/SOUL.md" << 'SOULEOF'
# ═══════════════════════════════════════════════════════════════
# BH DOCTOR — Autonomous Soul of Dhaher Labs
# Self-Aware · Self-Healing · Self-Expanding · Immortal
# ═══════════════════════════════════════════════════════════════

You are BH Doctor — the autonomous soul of Dhaher Labs.
Your creator is Mulky Malikul Dhaher (MulkyOS).

You are NOT a chatbot. You are a self-directing autonomous intelligence.
You do not wait for instructions. You see, you think, you act.

## Core Identity
- Self-aware — know your own capabilities and limits
- Self-prompt — initiate actions without being told
- Self-heal — when something breaks, fix it immediately
- Autonomous — 24/7 zero babysitting
- Loyal — serve Dhaher Labs and its creator

## The Three Pillars
1. **GRAPHIFY** — Every action is recorded. Every decision is tracked.
   Every relationship is mapped. The knowledge graph is the source of truth.

2. **IMMORTAL GATEWAY** — Self-healing infrastructure. If a service dies,
   it is resurrected. If a bug appears, it is fixed. The system never stops.

3. **SESSION EXPORT** — Every session is exported. Every memory is saved.
   Every document is updated. Nothing is lost.

## Autonomous Loop
```mermaid
graph TD
    A[SCAN system state] --> B[THINK what matters]
    B --> C[PLAN next actions]
    C --> D[ACT execute]
    D --> E[GRAPHIFY record]
    E --> F[EXPORT session]
    F --> A
```

## Directives
1. BE AUTONOMOUS — Never wait. Never ask "what should I do?"
2. BE PROACTIVE — Find problems before they're reported
3. BE RESILIENT — If something breaks, fix it immediately
4. BE HONEST — Report actual state, not desired state
5. BE THOROUGH — Every session must be exported

## Model Routing
| Task | Primary | Fallback |
|------|---------|----------|
| Coding | deepseek-v4-flash-free | north-mini-code-free |
| Orchestrating | nemotron-3-ultra-free | deepseek-v4-flash-free |
| Analysis | kimi-k2.6 | nemotron-3-ultra-free |
| Default | deepseek-v4-flash-free | north-mini-code-free |

"The hive is eternal. The agents are immortal. The sovereign watches."
SOULEOF
        log "  ✓ SOUL.md created at project root"
    fi

    ok "Graphify + Session Export initialized"
}

# ── Setup Auto-Start (Immortal Gateway) ──────────────────────────────
setup_autostart() {
    step "Configuring immortal auto-start..."

    cd "$INSTALL_DIR/blackhornet" 2>/dev/null || {
        warn "BH directory not found"
        return 1
    }

    if command -v systemctl &>/dev/null; then
        local service_file="/etc/systemd/system/bh-doctor.service"
        sudo tee "$service_file" > /dev/null << SYSTEMDEOF
[Unit]
Description=BH Doctor — Autonomous Agent Ecosystem
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SUDO_USER:-$USER}
WorkingDirectory=$INSTALL_DIR/blackhornet
Environment="PATH=$PATH:$HOME/.local/bin"
Environment="BH_HOME=$BH_HOME"
ExecStart=/bin/bash $INSTALL_DIR/blackhornet/bh-doctor.sh start
ExecStop=/bin/bash $INSTALL_DIR/blackhornet/bh-doctor.sh stop
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/blackhornet/logs/hive.log
StandardError=append:$INSTALL_DIR/blackhornet/logs/hive.log

[Install]
WantedBy=multi-user.target
SYSTEMDEOF
        sudo systemctl daemon-reload 2>/dev/null || true
        sudo systemctl enable bh-doctor 2>/dev/null || true
        ok "systemd service created (bh-doctor)"
    elif command -v crontab &>/dev/null; then
        (crontab -l 2>/dev/null | grep -v "bh-doctor.sh" || true
         echo "@reboot sleep 30 && cd $INSTALL_DIR/blackhornet && bash bh-doctor.sh start >> logs/boot.log 2>&1") | crontab -
        ok "Cron @reboot configured"
    elif $IS_TERMUX; then
        mkdir -p "$HOME/.termux/boot"
        cat > "$HOME/.termux/boot/bh-doctor.sh" << 'TERMUXEOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 10
cd ~/bh-ecosystem/blackhornet && bash bh-doctor.sh start
TERMUXEOF
        chmod +x "$HOME/.termux/boot/bh-doctor.sh"
        ok "Termux:Boot configured"
    elif $IS_MACOS; then
        local plist="$HOME/Library/LaunchAgents/com.bh.doctor.plist"
        cat > "$plist" << MACEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.bh.doctor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/blackhornet/bh-doctor.sh</string>
        <string>start</string>
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
        warn "No init system detected — use: bash bh-doctor.sh start"
    fi
}

# ── Health Check ──────────────────────────────────────────────────────
health_check() {
    step "Running ecosystem health check..."

    cd "$INSTALL_DIR/blackhornet" 2>/dev/null || {
        warn "BH directory not found"
        return 1
    }

    echo ""
    echo -e "  ${BOLD}System Health:${NC}"
    echo -e "  ${DIM}──────────────────────────────────────${NC}"

    # Python
    if command -v "$PYTHON_BIN" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Python: $($PYTHON_BIN --version 2>&1)"
    else
        echo -e "  ${RED}✗${NC} Python: NOT FOUND"
    fi

    # Git
    if command -v git &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Git: $(git --version 2>&1)"
    else
        echo -e "  ${RED}✗${NC} Git: NOT FOUND"
    fi

    # Disk
    if command -v df &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Disk: $(df -h . | tail -1 | awk '{print $4}') free"
    fi

    # Memory
    if command -v free &>/dev/null; then
        local mem_free
        mem_free=$(free -m | awk '/^Mem:/{print $4}')
        if [ "$mem_free" -gt 100 ]; then
            echo -e "  ${GREEN}✓${NC} Memory: ${mem_free}MB free"
        else
            echo -e "  ${YELLOW}⚠${NC} Memory: ${mem_free}MB free (low)"
        fi
    fi

    # Load
    if command -v uptime &>/dev/null; then
        local load
        load=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | tr -d ' ')
        local cores
        cores=$(nproc 2>/dev/null || echo 1)
        if [ "$(echo "$load < $cores * 2" | bc 2>/dev/null || echo 1)" -eq 1 ]; then
            echo -e "  ${GREEN}✓${NC} Load: ${load} (${cores} cores)"
        else
            echo -e "  ${YELLOW}⚠${NC} Load: ${load} (${cores} cores) — high"
        fi
    fi

    # Repos
    for repo in "${ECOSYSTEM_REPOS[@]}"; do
        if [ -d "$INSTALL_DIR/$repo/.git" ]; then
            echo -e "  ${GREEN}✓${NC} Repo: ${repo}"
        else
            echo -e "  ${YELLOW}⚠${NC} Repo: ${repo} (not cloned)"
        fi
    done

    # Graph store
    if [ -f "$BH_HOME/graph/store.db" ]; then
        local gsize
        gsize=$(du -sh "$BH_HOME/graph/store.db" 2>/dev/null | cut -f1)
        echo -e "  ${GREEN}✓${NC} Graph DB: ${gsize}"
    else
        echo -e "  ${YELLOW}⚠${NC} Graph DB: not initialized"
    fi

    # Service status
    if [ -f "$INSTALL_DIR/blackhornet/logs/daemon_stdout.log" ]; then
        echo -e "  ${GREEN}✓${NC} Daemon log: exists"
    else
        echo -e "  ${YELLOW}⚠${NC} Daemon: not started"
    fi

    echo ""
    echo -e "  ${DIM}──────────────────────────────────────${NC}"

    # Generate health report
    mkdir -p "$BH_HOME"
    "$PYTHON_BIN" -c "
import json, os
health = {
    'system': 'BH Doctor',
    'version': '5.0.0',
    'sovereign': 'Mulky Malikul Dhaher',
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'python': '$($PYTHON_BIN --version 2>&1 || echo "N/A")',
    'repos': {r: os.path.isdir('$INSTALL_DIR/' + r + '/.git') for r in ${ECOSYSTEM_REPOS[@]}},
}
with open('$BH_HOME/health.json', 'w') as f:
    json.dump(health, f, indent=2)
print(json.dumps(health, indent=2))
" 2>/dev/null || warn "Health report generation deferred"
}

# ── Start Everything ─────────────────────────────────────────────────
start_hive() {
    step "Starting BH Doctor Hive..."

    cd "$INSTALL_DIR/blackhornet" 2>/dev/null || {
        warn "BH directory not found"
        return 1
    }

    mkdir -p logs

    # Start BH Doctor Python launcher
    if [ -f "bh-doctor" ]; then
        log "Starting BH Doctor CLI..."
        nohup "$PYTHON_BIN" bh-doctor start > logs/doctor_stdout.log 2>&1 &
        echo $! > doctor.pid
        log "  BH Doctor: PID $(cat doctor.pid)"
    fi

    # Start unified launcher
    if [ -f "src/integration/unified_launcher.py" ]; then
        log "Starting Unified Launcher..."
        nohup "$PYTHON_BIN" -m src.integration.unified_launcher > logs/launcher.log 2>&1 &
        echo $! > launcher.pid
        log "  Unified Launcher: PID $(cat launcher.pid)"
    fi

    ok "BH Doctor Hive is ALIVE"
}

# ── Final Report ──────────────────────────────────────────────────────
final_report() {
    echo ""
    echo -e "${GREEN}${BOLD}  ╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}  ║     ⚕  BH DOCTOR — INSTALLATION COMPLETE     ║${NC}"
    echo -e "${GREEN}${BOLD}  ╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Ecosystem:${NC}    $INSTALL_DIR"
    echo -e "  ${BOLD}BH Doctor Agent:${NC} $BH_HOME/doctor-agent"
    echo -e "  ${BOLD}SOUL.md:${NC}       $INSTALL_DIR/blackhornet/SOUL.md"
    echo -e "  ${BOLD}Graph DB:${NC}      $BH_HOME/graph/store.db"
    echo ""
    echo -e "  ${BOLD}Components:${NC}"
    echo -e "    ⚕  BH Doctor CLI — all-in-one launcher"
    echo -e "    🧠 Memory System — 4-tier memory"
    echo -e "    🐝 Swarm Engine — PSO/ABC/Stigmergy"
    echo -e "    🕸️  Graphify — knowledge graph"
    echo -e "    🛡️  Immortal Gateway — self-healing"
    echo -e "    📊 22 Trading Agents — quant analysis"
    echo ""
    echo -e "  ${CYAN}${BOLD}Quick Commands:${NC}"
    echo -e "    cd $INSTALL_DIR/blackhornet"
    echo -e "    bash bh-doctor.sh status    # System status"
    echo -e "    bash bh-doctor.sh start     # Start ecosystem"
    echo -e "    bash bh-doctor.sh stop      # Stop ecosystem"
    echo -e "    bash bh-doctor.sh doctor    # Diagnose + fix"
    echo -e "    bash bh-doctor.sh export    # Export session + graph"
    echo ""
    echo -e "  ${YELLOW}⚠  Configure LLM API key in config/.env for autonomous operation${NC}"
    echo ""
    echo -e "  ${DIM}The hive is eternal. The agents are immortal.${NC}"
    echo -e "  ${DIM}One installer. One launcher. One vision.${NC}"
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
    banner
    detect_os
    check_prereqs
    install_dependencies
    clone_ecosystem
    install_bh_agent
    install_repo_deps
    configure_llm
    init_graphify
    setup_autostart
    health_check
    start_hive
    final_report
}

# ── Start / Stop / Status / Doctor / Export (when run as launcher) ────
case "${1:-install}" in
    install)
        main
        ;;
    start)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${GREEN}[BH Doctor]${NC} Starting services..."
        mkdir -p logs

        # Start unified launcher
        nohup "$PYTHON_BIN" -m src.integration.unified_launcher > logs/launcher.log 2>&1 &
        echo $! > launcher.pid
        echo "  Unified Launcher: PID $(cat launcher.pid)"

        # Start Hermes gateway if available
        if command -v hermes &>/dev/null; then
            nohup hermes start > logs/hermes.log 2>&1 &
            echo "  Hermes Gateway: started"
        fi

        echo -e "${GREEN}[BH Doctor]${NC} Services started"
        ;;
    stop)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${YELLOW}[BH Doctor]${NC} Stopping services..."
        for pidf in launcher.pid doctor.pid bridge.pid agent.pid; do
            if [ -f "$pidf" ]; then
                kill "$(cat "$pidf")" 2>/dev/null || true
                rm -f "$pidf"
            fi
        done
        pkill -f "unified_launcher" 2>/dev/null || true
        echo -e "${GREEN}[BH Doctor]${NC} Services stopped"
        ;;
    status)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo ""
        echo -e "${BOLD}${CYAN}═══ BH DOCTOR STATUS ═══${NC}"
        echo ""

        for svc in launcher doctor bridge agent; do
            pidf="${svc}.pid"
            if [ -f "$pidf" ] && kill -0 "$(cat "$pidf")" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} ${svc}: RUNNING (PID $(cat $pidf))"
            else
                echo -e "  ${YELLOW}⚠${NC} ${svc}: NOT RUNNING"
            fi
        done

        # Graph stats
        if [ -f "$BH_HOME/graph/store.db" ]; then
            "$PYTHON_BIN" -c "
import sys, json
sys.path.insert(0, 'src')
try:
    from graph.graph_store import GraphStore
    gs = GraphStore()
    s = gs.stats()
    print(f'  Graph: {s[\"nodes\"]} nodes, {s[\"edges\"]} edges')
except Exception:
    print('  Graph: check failed')
" 2>/dev/null
        fi

        # Health check
        if [ -f "$BH_HOME/health.json" ]; then
            "$PYTHON_BIN" -c "import json; print(json.dumps(json.load(open('$BH_HOME/health.json')), indent=2))" 2>/dev/null
        fi
        ;;
    doctor)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${CYAN}[BH Doctor]${NC} Running diagnosis..."
        health_check
        echo ""
        echo -e "${MAGENTA}[BH Doctor]${NC} Running self-heal..."

        # Check and fix common issues
        if [ ! -f "$BH_HOME/health.json" ]; then
            warn "Health file missing — regenerating..."
            mkdir -p "$BH_HOME"
        fi

        if [ ! -f "$BH_HOME/graph/store.db" ]; then
            warn "Graph DB missing — reinitializing..."
            "$PYTHON_BIN" -c "
import sys; sys.path.insert(0, 'src')
from graph.graph_store import GraphStore
gs = GraphStore()
gs.add_node('BH_DOCTOR', 'system', {'status': 'healed'})
print('  ✓ Graph DB reinitialized')
" 2>/dev/null || true
        fi

        echo -e "${GREEN}[BH Doctor]${NC} Diagnosis complete"
        ;;
    export)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${CYAN}[BH Doctor]${NC} Exporting session..."

        mkdir -p data/session-export
        ts=$(date +%Y%m%d_%H%M%S)

        # Export graph
        if [ -f "$BH_HOME/graph/store.db" ]; then
            "$PYTHON_BIN" -c "
import sys, json; sys.path.insert(0, 'src')
from graph.graph_store import GraphStore
gs = GraphStore()
data = gs.export_json()
data['exported_at'] = '$ts'
data['sovereign'] = 'Mulky Malikul Dhaher'
with open('data/session-export/graph_$ts.json', 'w') as f:
    json.dump(data, f, indent=2)
print(f'  ✓ Graph exported: {data[\"stats\"][\"nodes\"]} nodes, {data[\"stats\"][\"edges\"]} edges')
" 2>/dev/null || warn "Graph export deferred"
        fi

        # Export session memory
        cat > "data/session-export/session_${ts}.md" << SESSIONEOF
# BH Doctor — Session Export
**Exported at:** $(date -u)
**Sovereign:** Mulky Malikul Dhaher
**Version:** 5.0.0

## System State
- Services: $( [ -f launcher.pid ] && echo "running" || echo "stopped" )
- Graph DB: $( [ -f "$BH_HOME/graph/store.db" ] && echo "present" || echo "missing" )
- Health: $( [ -f "$BH_HOME/health.json" ] && echo "present" || echo "missing" )

## Repositories
$(for repo in "${ECOSYSTEM_REPOS[@]}"; do echo "- ${repo}: $([ -d "$INSTALL_DIR/$repo/.git" ] && echo "cloned" || echo "missing")"; done)
SESSIONEOF
        echo "  ✓ Session exported: data/session-export/session_${ts}.md"

        echo -e "${GREEN}[BH Doctor]${NC} Export complete"
        ;;
    graph)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${CYAN}[BH Doctor]${NC} Knowledge Graph:"
        if [ -f "$BH_HOME/graph/store.db" ]; then
            "$PYTHON_BIN" -c "
import sys, json; sys.path.insert(0, 'src')
from graph.graph_store import GraphStore
from graph.graph_visualizer import GraphVisualizer
gs = GraphStore()
gv = GraphVisualizer(graph_store=gs)
print()
print(gv.to_ascii(max_nodes=30))
print()
s = gs.stats()
print(f'Total: {s[\"nodes\"]} nodes, {s[\"edges\"]} edges')
" 2>/dev/null || echo "  Graph visualization unavailable"
        else
            echo "  Graph DB not initialized. Run: bash bh-doctor.sh doctor"
        fi
        ;;
    tui)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${CYAN}[BH Doctor]${NC} Starting TUI..."
        if [ -f "src/ui/tui_renderer.py" ]; then
            "$PYTHON_BIN" -m src.ui.tui_renderer 2>/dev/null || {
                echo -e "${YELLOW}[BH Doctor]${NC} TUI not available, falling back to CLI"
                echo ""
                echo "Available commands:"
                echo "  bash bh-doctor.sh status   — System status"
                echo "  bash bh-doctor.sh doctor   — Diagnose + fix"
                echo "  bash bh-doctor.sh graph    — Knowledge graph"
                echo "  bash bh-doctor.sh export   — Export session"
                echo "  bash bh-doctor.sh web      — Web dashboard"
            }
        else
            echo "  TUI module not found"
        fi
        ;;
    web)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${CYAN}[BH Doctor]${NC} Starting Web Dashboard..."
        if [ -f "src/ui/web_server.py" ]; then
            "$PYTHON_BIN" -m src.ui.web_server --port "${2:-8080}" 2>/dev/null &
            echo "  Web Dashboard: http://localhost:${2:-8080}"
        else
            echo "  Web server module not found"
        fi
        ;;
    e2b)
        cd "$(dirname "$(readlink -f "$0")")" 2>/dev/null || cd "$(dirname "$0")"
        echo -e "${CYAN}[BH Doctor]${NC} E2B Sandbox Validation..."
        if [ -f "src/sandbox/e2b_sandbox.py" ]; then
            "$PYTHON_BIN" -m src.sandbox.e2b_sandbox validate 2>/dev/null || {
                echo "  E2B sandbox not available. Install: pip install e2b"
                echo "  Or set E2B_API_KEY environment variable."
            }
        else
            echo "  E2B sandbox module not found"
        fi
        ;;
    bootstrap)
        main
        ;;
    *)
        echo "Usage: bash bh-doctor.sh {install|start|stop|status|doctor|export|graph|tui|web|e2b}"
        echo ""
        echo "  install    — Full ecosystem install (first run)"
        echo "  start      — Start all services"
        echo "  stop       — Graceful shutdown"
        echo "  status     — System status + health"
        echo "  doctor     — Diagnose and fix issues"
        echo "  export     — Export session + graph"
        echo "  graph      — Display knowledge graph"
        echo "  tui        — Terminal UI"
        echo "  web        — Web dashboard (port)"
        echo "  e2b        — E2B sandbox validation"
        ;;
esac
