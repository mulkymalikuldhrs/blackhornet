#!/bin/bash
# ============================================================================
# DHAHER SWARM — Unified Control Script (based on blackhornet hermes.sh)
# ============================================================================
# Usage: ./dhaher-swarm.sh [start|stop|restart|status|logs|health|install|clone]
#
# 3-Layer Auto-Restart:
#   L1: Python watchdog (10s check, exponential backoff)
#   L2: Keeper cron (1-min check)
#   L3: Guardian bash   (5-min check, idle nudge, key rotation)
#
# Self-Cloning: ./dhaher-swarm.sh clone → export full config for migration
# ============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWARM_DIR="/root/.hermes"
PROFILES_DIR="${SWARM_DIR}/profiles"
SHARED_WS="${SWARM_DIR}/shared-workspace"
LOG_DIR="${SWARM_DIR}/supervisor-logs"
PID_DIR="${LOG_DIR}"
CONFIG_DIR="$BASE_DIR"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log()   { echo -e "${GREEN}[DHAHER]${NC} $1"; }
warn()  { echo -e "${YELLOW}[DHAHER]${NC} $1"; }
error() { echo -e "${RED}[DHAHER]${NC} $1"; }
info()  { echo -e "${BLUE}[DHAHER]${NC} $1"; }

PROFILES="autobot clawbot fangbot hackerbot devbot traderbot researchbot"
declare -A TOKENS
TOKENS[autobot]="6923895702:AAFxeKrZSaecrT8fBNm_9R-slKQatBMRAA4"
TOKENS[clawbot]="7952120410:AAFUB4Km9EMPL_MEQsh4o7NFXpyfSZ_QOMQ"
TOKENS[fangbot]="8996687696:AAEMpDi51mGDsM8BE7w_-b6f1Wf91leVpRQ"
TOKENS[hackerbot]="8778731184:AAGu_Waea9rk9ofK8qymI4nicnORUuRiRWU"
TOKENS[devbot]="8768224892:AAHdPyc0A3g7SxIsS_FJndT5adI0bD3iwXQ"
TOKENS[traderbot]="8533302265:AAF0qWafU-p2p3mZtpNYa612tqakyOREAMk"
TOKENS[researchbot]="8848363753:AAGy4CkkJgF4On5IPHDUiiS5atJgkI8LvtM"

# ── Start one gateway ──
start_gateway() {
  local p="$1"
  rm -f "${PROFILES_DIR}/${p}/gateway.pid" "${PROFILES_DIR}/${p}/gateway.lock" "${PROFILES_DIR}/${p}/gateway_state.json" 2>/dev/null
  rm -f /root/.local/state/hermes/gateway-locks/telegram-bot-token-*.lock 2>/dev/null
  HERMES_HOME="${PROFILES_DIR}/${p}" setsid hermes gateway run --accept-hooks --replace >> "${LOG_DIR}/${p}.log" 2>&1 &
  echo $! > "${PID_DIR}/${p}.pid"
}

# ── Start all ──
start() {
  log "${BOLD}⚕️  Starting Dhaher Swarm...${NC}"
  mkdir -p "$LOG_DIR"
  
  # Start ProxyGateLLM
  if ! curl -s http://localhost:3333/health >/dev/null 2>&1; then
    info "Starting ProxyGateLLM..."
    cd "${SHARED_WS}/ProxyGateLLM" && setsid node index.js >> "${LOG_DIR}/proxygate.log" 2>&1 &
    echo $! > "${PID_DIR}/proxygate.pid"
  fi

  # Stagger gateways
  for p in $PROFILES; do
    start_gateway "$p"
    sleep 3
  done
  
  sleep 15
  status
}

# ── Stop all ──
stop() {
  log "Stopping Dhaher Swarm..."
  for p in $PROFILES; do
    [ -f "${PID_DIR}/${p}.pid" ] && kill "$(cat "${PID_DIR}/${p}.pid")" 2>/dev/null || true
    [ -f "${PID_DIR}/${p}.pid" ] && kill -9 "$(cat "${PID_DIR}/${p}.pid")" 2>/dev/null || true
    rm -f "${PID_DIR}/${p}.pid"
  done
  [ -f "${PID_DIR}/proxygate.pid" ] && kill "$(cat "${PID_DIR}/proxygate.pid")" 2>/dev/null || true
  [ -f "${PID_DIR}/watchdog.pid" ] && kill "$(cat "${PID_DIR}/watchdog.pid")" 2>/dev/null || true
  log "Swarm stopped"
}

# ── Status ──
status() {
  echo ""
  echo -e "${BOLD}╔════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║         ⚕️  DHAHER SWARM STATUS               ║${NC}"
  echo -e "${BOLD}╚════════════════════════════════════════════════╝${NC}"
  echo ""
  local alive=0 connected=0
  for p in $PROFILES; do
    local icon="${RED}❌${NC}" state="DEAD"
    if [ -f "${PID_DIR}/${p}.pid" ] && kill -0 "$(cat "${PID_DIR}/${p}.pid")" 2>/dev/null; then
      alive=$((alive + 1))
      local tg_state=$(python3 -c "import json; d=json.load(open('${PROFILES_DIR}/${p}/gateway_state.json')); print(d['platforms']['telegram']['state'])" 2>/dev/null || echo "?")
      if [ "$tg_state" = "connected" ]; then
        icon="${GREEN}✅${NC}" state="CONNECTED"
        connected=$((connected + 1))
      else
        icon="${YELLOW}🔄${NC}" state="RECONNECTING"
      fi
    fi
    printf "  %b %-15s %s\n" "$icon" "$p" "$state"
  done
  local proxy="${RED}❌${NC}"
  curl -s http://localhost:3333/health >/dev/null 2>&1 && proxy="${GREEN}✅${NC}"
  printf "  %b %-15s %s\n" "$proxy" "proxygate" "ProxyGateLLM"
  echo ""
  echo -e "  Alive: ${alive}/7  |  Connected: ${connected}/7  |  Proxy: ${proxy}"
  echo ""
}

# ── Health (detailed) ──
health() {
  status
  echo "RAM: $(free -h | awk '/^Mem/{printf "%s/%s (%.0f%%)", $3,$2,$3/$2*100}')"
  echo "Disk: $(df -h / | awk 'NR==2{printf "%s/%s (%s)", $3,$2,$5}')"
  echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
  echo ""
  echo "Processes: $(ps aux | grep -E 'hermes gateway|swarm-guardian|ProxyGateLLM' | grep -v grep | wc -l) total"
  echo "Watchdog:  $(ps aux | grep 'watchdog.py' | grep -v grep | wc -l) active"
  echo "Guardian:  $(ps aux | grep 'swarm-guardian' | grep bash | grep -v grep | wc -l) active"
}

# ── View logs ──
logs() {
  local profile="${1:-autobot}"
  local lines="${2:-20}"
  if [ -f "${LOG_DIR}/${profile}.log" ]; then
    tail -n "$lines" "${LOG_DIR}/${profile}.log"
  else
    error "No log for $profile"
  fi
}

# ── Clone/export for device migration ──
clone() {
  local target="${1:-/tmp/dhaher-swarm-export}"
  log "🧬 Cloning swarm configuration to ${target}..."
  mkdir -p "$target"
  
  # Core scripts
  cp "$BASE_DIR/dhaher-swarm.sh" "$target/"
  cp "$BASE_DIR/swarm-guardian.sh" "$target/"
  cp "$BASE_DIR/swarm-boot.sh" "$target/"
  cp "$BASE_DIR/github-sync.sh" "$target/"
  cp "$BASE_DIR/HEARTBEAT.md" "$target/"
  
  # Profiles (SOUL.md, config — NO tokens/secrets in export)
  mkdir -p "$target/profiles"
  for p in $PROFILES; do
    mkdir -p "$target/profiles/$p"
    cp "${PROFILES_DIR}/${p}/SOUL.md" "$target/profiles/$p/" 2>/dev/null || true
    cp "${PROFILES_DIR}/${p}/config.yaml" "$target/profiles/$p/" 2>/dev/null || true
  done
  
  # Shared workspace
  mkdir -p "$target/shared-workspace"
  cp "${SHARED_WS}/MEMORY.md" "$target/shared-workspace/" 2>/dev/null || true
  cp "${SHARED_WS}/AGENTS.md" "$target/shared-workspace/" 2>/dev/null || true
  
  # Clone repos
  cd "$target"
  git clone "https://github.com/dhaher-labs/ProxyGateLLM.git" 2>/dev/null || true
  git clone "https://github.com/dhaher-labs/mnemosyne.git" 2>/dev/null || true
  git clone "https://github.com/dhaher-labs/blackhornet.git" 2>/dev/null || true
  git clone "https://github.com/dhaher-labs/agent.git" 2>/dev/null || true
  
  # Install script
  cat > "$target/install.sh" << 'INSTALLEOF'
#!/bin/bash
set -e
echo "🧬 Dhaher Swarm — Self-Cloning Installer"
echo "========================================="
# Install Hermes Agent
if ! command -v hermes &>/dev/null; then
  echo "Installing Hermes Agent..."
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
fi
# Setup profiles
BASE=$(dirname "$0")
for p in autobot clawbot fangbot hackerbot devbot traderbot researchbot; do
  hermes profile create "$p" --clone-from default --no-alias 2>/dev/null || true
  [ -f "$BASE/profiles/$p/SOUL.md" ] && cp "$BASE/profiles/$p/SOUL.md" ~/.hermes/profiles/$p/
  [ -f "$BASE/profiles/$p/config.yaml" ] && cp "$BASE/profiles/$p/config.yaml" ~/.hermes/profiles/$p/
done
# Setup ProxyGateLLM
cd "$BASE/ProxyGateLLM" && npm install --silent 2>/dev/null || true
echo "✅ Clone complete. Edit .env files with your tokens, then run: ./dhaher-swarm.sh start"
INSTALLEOF
  chmod +x "$target/install.sh"
  chmod +x "$target/dhaher-swarm.sh"
  
  log "✅ Clone exported to $target"
  echo "  Transfer to new device, then run: ./install.sh"
  echo "  Don't forget to add TELEGRAM_BOT_TOKEN + API keys to .env files!"
}

# ── Install for auto-start ──
install() {
  log "Installing Dhaher Swarm auto-start..."
  
  # Systemd service
  if command -v systemctl &>/dev/null; then
    cat > /etc/systemd/system/dhaher-swarm.service << SERVICEEOF
[Unit]
Description=Dhaher Swarm — Autonomous Multi-Agent System
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
ExecStart=$BASE_DIR/dhaher-swarm.sh start
ExecStop=$BASE_DIR/dhaher-swarm.sh stop
Restart=on-failure
RestartSec=30
User=root
Environment=HOME=/root
WorkingDirectory=$BASE_DIR

[Install]
WantedBy=multi-user.target
SERVICEEOF
    systemctl daemon-reload
    systemctl enable dhaher-swarm 2>/dev/null || true
    log "systemd service installed (dhaher-swarm.service)"
  fi
  
  # Cron for keeper
  (crontab -l 2>/dev/null || true; echo "*/1 * * * * $BASE_DIR/dhaher-swarm.sh health > ${LOG_DIR}/keeper.log 2>&1") | crontab -
  log "Keeper cron installed (1-min health check)"
  
  # Start watchdog
  if [ -f "$BASE_DIR/watchdog.py" ]; then
    python3 "$BASE_DIR/watchdog.py" &
    echo $! > "${PID_DIR}/watchdog.pid"
    log "Watchdog started (10s interval)"
  fi
}

# ── Main ──
case "${1:-status}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; sleep 3; start ;;
  status)  status ;;
  health)  health ;;
  logs)    logs "${2:-}" "${3:-}" ;;
  clone)   clone "${2:-}" ;;
  install) install ;;
  *)       echo "Usage: $0 {start|stop|restart|status|health|logs|clone|install}" ;;
esac
