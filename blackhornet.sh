#!/bin/bash
# ============================================================================
# BLACKHORNET - Main Control Script
# ============================================================================
# Usage: ./bh.sh [start|stop|restart|status|logs|watchdog|health|install]
#
# Features:
#   - On-boot auto-start via systemd or Termux:Boot
#   - Auto-restart on crash via watchdog daemon
#   - Health monitoring via keeper (cron)
#   - Telegram alerts on status changes
# ============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$BASE_DIR/bh.pid"
WATCHDOG_PID="$BASE_DIR/watchdog.pid"
LOG_DIR="$BASE_DIR/logs"
HEALTH_FILE="$BASE_DIR/.bh/health.json"
CONFIG_ENV="$BASE_DIR/config/.env"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[BH]${NC} $1"; }
warn()  { echo -e "${YELLOW}[BH]${NC} $1"; }
error() { echo -e "${RED}[BH]${NC} $1"; }
info()  { echo -e "${BLUE}[BH]${NC} $1"; }

# ============================================================================
# START - Launches watchdog (which starts and monitors BH)
# ============================================================================

start() {
    # Check if already running
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        warn "BH is already running (PID $(cat $PID_FILE))"
        return 0
    fi

    if [ -f "$WATCHDOG_PID" ] && kill -0 "$(cat "$WATCHDOG_PID")" 2>/dev/null; then
        warn "Watchdog is already running (PID $(cat $WATCHDOG_PID))"
        return 0
    fi

    log "${BOLD}Starting BLACKHORNET...${NC}"
    mkdir -p "$LOG_DIR"
    mkdir -p "$BASE_DIR/.bh"

    # Load env
    if [ -f "$CONFIG_ENV" ]; then
        set -a
        source "$CONFIG_ENV"
        set +a
    fi

    # Start watchdog (which will start and monitor BH)
    log "Starting Watchdog (Always-On Mode)..."
    cd "$BASE_DIR/src"
    nohup python3 watchdog.py > "$LOG_DIR/watchdog_stdout.log" 2>&1 &
    WDOG_PID=$!
    echo "$WDOG_PID" > "$WATCHDOG_PID"

    sleep 3

    # Verify watchdog started
    if kill -0 "$WDOG_PID" 2>/dev/null; then
        log "${GREEN}${BOLD}Watchdog RUNNING - BLACKHORNET is Always-On!${NC}"
        log "  Watchdog PID: $WDOG_PID"
        log "  Check Interval: 10s"
        log "  Max Restarts/Hour: 10"
        log "  Backoff: 5s → 120s (exponential)"
        log ""
        log "To view logs:"
        log "  tail -f $LOG_DIR/bh_quant_$(date +%Y%m%d).log"
        log ""
        log "To stop:"
        log "  ./bh.sh stop"
    else
        error "Watchdog failed to start! Check logs: $LOG_DIR/watchdog_stdout.log"
        # Fallback: start BH directly
        warn "Falling back to direct BH start..."
        nohup python3 bh_quant.py > "$LOG_DIR/stdout.log" 2>&1 &
        H_PID=$!
        echo "$H_PID" > "$PID_FILE"
        log "BH started directly (PID: $H_PID) - no watchdog protection"
    fi
}

# ============================================================================
# STOP - Graceful shutdown
# ============================================================================

stop() {
    log "Stopping BLACKHORNET..."

    # Stop watchdog first (so it doesn't restart BH)
    if [ -f "$WATCHDOG_PID" ]; then
        WPID=$(cat "$WATCHDOG_PID")
        if kill -0 "$WPID" 2>/dev/null; then
            log "Stopping watchdog (PID $WPID)..."
            kill "$WPID" 2>/dev/null || true
            sleep 2
            if kill -0 "$WPID" 2>/dev/null; then
                kill -9 "$WPID" 2>/dev/null || true
            fi
        fi
        rm -f "$WATCHDOG_PID"
    fi

    # Kill any remaining watchdog processes
    pkill -f "watchdog.py" 2>/dev/null || true
    sleep 1

    # Stop BH
    if [ -f "$PID_FILE" ]; then
        HPID=$(cat "$PID_FILE")
        if kill -0 "$HPID" 2>/dev/null; then
            log "Stopping BH (PID $HPID)..."
            kill "$HPID" 2>/dev/null || true
            sleep 3

            if kill -0 "$HPID" 2>/dev/null; then
                warn "Force killing BH..."
                kill -9 "$HPID" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Kill any remaining BH processes
    pkill -f "bh_quant.py" 2>/dev/null || true

    log "${GREEN}BLACKHORNET stopped.${NC}"
}

# ============================================================================
# STATUS - Show system status
# ============================================================================

status() {
    echo ""
    log "${BOLD}${CYAN}═══ BLACKHORNET STATUS ═══${NC}"
    echo ""

    # Check BH
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        log "${GREEN}BH: RUNNING (PID $(cat $PID_FILE))${NC}"
    else
        warn "BH: NOT RUNNING"
    fi

    # Check Watchdog
    if [ -f "$WATCHDOG_PID" ] && kill -0 "$(cat "$WATCHDOG_PID")" 2>/dev/null; then
        log "${GREEN}Watchdog: RUNNING (PID $(cat $WATCHDOG_PID))${NC}"
    else
        warn "Watchdog: NOT RUNNING"
    fi

    # Health file
    if [ -f "$HEALTH_FILE" ]; then
        echo ""
        info "Health Status:"
        python3 -c "import json; d=json.load(open('$HEALTH_FILE')); print(json.dumps(d, indent=2))" 2>/dev/null || echo "  Could not read health file"
    fi

    # Resource usage
    echo ""
    info "Resource Usage:"
    ps aux | grep -E "(bh_quant|watchdog)" | grep -v grep || echo "  No processes found"

    # Disk usage
    echo ""
    info "Disk:"
    du -sh "$BASE_DIR" 2>/dev/null || echo "  Unknown"
    du -sh "$LOG_DIR" 2>/dev/null || echo "  Logs: Unknown"

    echo ""
}

# ============================================================================
# LOGS - Tail log files
# ============================================================================

logs() {
    local log_type="${1:-bh}"

    case "$log_type" in
        bh)
            local logf="$LOG_DIR/bh_quant_$(date +%Y%m%d).log"
            if [ -f "$logf" ]; then
                tail -f "$logf"
            else
                warn "No BH log found for today. Checking stdout..."
                tail -f "$LOG_DIR/stdout.log" 2>/dev/null || error "No logs found"
            fi
            ;;
        watchdog)
            tail -f "$LOG_DIR/watchdog_stdout.log" 2>/dev/null || \
            tail -f "$LOG_DIR/watchdog_$(date +%Y%m%d).log" 2>/dev/null || \
            error "No watchdog logs found"
            ;;
        keeper)
            tail -f "$LOG_DIR/keeper_$(date +%Y%m%d).log" 2>/dev/null || \
            error "No keeper logs found"
            ;;
        all)
            tail -f "$LOG_DIR"/*.log 2>/dev/null || error "No logs found"
            ;;
        *)
            echo "Usage: ./bh.sh logs [bh|watchdog|keeper|all]"
            ;;
    esac
}

# ============================================================================
# HEALTH - Run health check
# ============================================================================

health() {
    python3 "$BASE_DIR/scripts/keeper.py"
}

# ============================================================================
# RESTART
# ============================================================================

restart() {
    stop
    sleep 3
    start
}

# ============================================================================
# WATCHDOG - Start only the watchdog
# ============================================================================

watchdog_start() {
    if [ -f "$WATCHDOG_PID" ] && kill -0 "$(cat "$WATCHDOG_PID")" 2>/dev/null; then
        warn "Watchdog already running (PID $(cat $WATCHDOG_PID))"
        return 0
    fi

    log "Starting watchdog only..."
    mkdir -p "$LOG_DIR"
    cd "$BASE_DIR/src"
    nohup python3 watchdog.py > "$LOG_DIR/watchdog_stdout.log" 2>&1 &
    echo $! > "$WATCHDOG_PID"
    log "Watchdog started (PID $(cat $WATCHDOG_PID))"
}

# ============================================================================
# INSTALL - Setup on-boot and auto-restart
# ============================================================================

install_on_boot() {
    log "${BOLD}Installing BLACKHORNET as system service...${NC}"
    echo ""

    # Detect environment
    if command -v termux-info &> /dev/null; then
        install_termux_boot
    elif command -v systemctl &> /dev/null; then
        install_systemd
    elif command -v crontab &> /dev/null; then
        install_cron
    else
        error "No supported init system found!"
        error "Supported: systemd, Termux:Boot, cron"
        return 1
    fi
}

install_systemd() {
    log "Installing systemd service..."

    cat > /tmp/blackhornet.service << EOF
[Unit]
Description=BlackHornet Operating System - Autonomous Trading
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
User=$(whoami)
WorkingDirectory=$BASE_DIR
ExecStart=/bin/bash $BASE_DIR/bh.sh start
ExecStop=/bin/bash $BASE_DIR/bh.sh stop
ExecReload=/bin/bash $BASE_DIR/bh.sh restart
PIDFile=$WATCHDOG_PID
Restart=on-failure
RestartSec=10
StandardOutput=append:$LOG_DIR/systemd.log
StandardError=append:$LOG_DIR/systemd.log

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/blackhornet.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable blackhornet
    log "${GREEN}Systemd service installed and enabled!${NC}"
    log "Start: sudo systemctl start blackhornet"
    log "Status: sudo systemctl status blackhornet"
}

install_termux_boot() {
    log "Installing Termux:Boot service..."

    BOOT_DIR="$HOME/.termux/boot"
    mkdir -p "$BOOT_DIR"

    cat > "$BOOT_DIR/blackhornet.sh" << EOF
#!/data/data/com.termux/files/usr/bin/bash
# BLACKHORNET - Auto-start on boot

# Wait for network
sleep 10

# Start BH
cd $BASE_DIR
bash bh.sh start
EOF

    chmod +x "$BOOT_DIR/blackhornet.sh"
    log "${GREEN}Termux:Boot installed!${NC}"
    log "Install Termux:Boot from F-Droid for auto-start on device boot."
    log "File: $BOOT_DIR/blackhornet.sh"
}

install_cron() {
    log "Installing cron job for health monitoring..."

    CRON_CMD="*/1 * * * * cd $BASE_DIR && python3 scripts/keeper.py >> $LOG_DIR/keeper_cron.log 2>&1"

    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

    log "${GREEN}Cron job installed!${NC}"
    log "Keeper will check every 1 minute."
    log "View: crontab -l"

    # Also add @reboot for on-boot
    REBOOT_CMD="@reboot sleep 30 && cd $BASE_DIR && bash bh.sh start >> $LOG_DIR/boot.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "bh.*start"; echo "$REBOOT_CMD") | crontab -

    log "@reboot also installed for on-boot start."
}

# ============================================================================
# Main
# ============================================================================

# ============================================================================
# AGENT SWARM — Start BlackHornet Agent (Nous Research) + Memory Bridge
# ============================================================================

agent_start() {
    log "${BOLD}Starting Agent Swarm...${NC}"

    BH_AGENT_DIR="$HOME/.bh/nous-agent"

    # Start BH Doctor (unified launcher)
    bh_doctor_start

    # Start BlackHornet Agent if installed
    if [ -f "$BH_AGENT_DIR/venv/bin/python" ]; then
        log "Starting BlackHornet Agent (Nous Research)..."
        cd "$BH_AGENT_DIR"
        nohup ./venv/bin/python run_agent.py > "$LOG_DIR/agent_stdout.log" 2>&1 &
        echo $! > "$BASE_DIR/agent.pid"
        log "${GREEN}BlackHornet Agent RUNNING (PID $(cat $BASE_DIR/agent.pid))${NC}"
    else
        warn "BlackHornet Agent not installed. Run: bash scripts/bootstrap.sh"
    fi
}

agent_stop() {
    log "Stopping Agent Swarm..."

    if [ -f "$BASE_DIR/agent.pid" ]; then
        APID=$(cat "$BASE_DIR/agent.pid")
        if kill -0 "$APID" 2>/dev/null; then
            kill "$APID" 2>/dev/null || true
            sleep 2
            kill -9 "$APID" 2>/dev/null || true
        fi
        rm -f "$BASE_DIR/agent.pid"
    fi
    pkill -f "run_agent.py" 2>/dev/null || true

    bh_doctor_stop
    log "Agent Swarm stopped."
}

# ============================================================================
# BH DOCTOR — Unified launcher (replaces memory_bridge + immortal_daemon)
# ============================================================================

bh_doctor_start() {
    if [ -f "$BASE_DIR/doctor.pid" ] && kill -0 "$(cat "$BASE_DIR/doctor.pid")" 2>/dev/null; then
        warn "BH Doctor already running (PID $(cat $BASE_DIR/doctor.pid))"
        return 0
    fi

    log "Starting BH Doctor (unified launcher)..."
    cd "$BASE_DIR"
    nohup python3 bh-doctor start > "$LOG_DIR/doctor_stdout.log" 2>&1 &
    echo $! > "$BASE_DIR/doctor.pid"
    log "${GREEN}BH Doctor RUNNING (PID $(cat $BASE_DIR/doctor.pid))${NC}"
}

bh_doctor_stop() {
    if [ -f "$BASE_DIR/doctor.pid" ]; then
        DPID=$(cat "$BASE_DIR/doctor.pid")
        if kill -0 "$DPID" 2>/dev/null; then
            kill "$DPID" 2>/dev/null || true
            sleep 1
            kill -9 "$DPID" 2>/dev/null || true
        fi
        rm -f "$BASE_DIR/doctor.pid"
    fi
    pkill -f "bh-doctor" 2>/dev/null || true
}

bh_doctor_status() {
    if [ -f "$BASE_DIR/doctor.pid" ] && kill -0 "$(cat "$BASE_DIR/doctor.pid")" 2>/dev/null; then
        log "${GREEN}BH Doctor: RUNNING → $(cat $BASE_DIR/doctor.pid)${NC}"
    else
        warn "BH Doctor: NOT RUNNING"
    fi
}

# ============================================================================
# BOOTSTRAP — Full auto-install
# ============================================================================

bootstrap() {
    if [ -f "$BASE_DIR/scripts/bootstrap.sh" ]; then
        bash "$BASE_DIR/scripts/bootstrap.sh"
    else
        error "bootstrap.sh not found in scripts/"
        return 1
    fi
}

# ============================================================================
# AGENT STATUS — Show agent swarm connections
# ============================================================================

agent_status() {
    echo ""
    log "${BOLD}${MAGENTA}═══ AGENT SWARM STATUS ═══${NC}"
    echo ""

    # BlackHornet Agent
    if [ -f "$BASE_DIR/agent.pid" ] && kill -0 "$(cat "$BASE_DIR/agent.pid")" 2>/dev/null; then
        log "${GREEN}BlackHornet Agent: RUNNING (PID $(cat $BASE_DIR/agent.pid))${NC}"
    else
        warn "BlackHornet Agent: NOT RUNNING"
    fi

    bh_doctor_status

    # Connected repos
    echo ""
    info "Connected Repos:"
    echo "  📊 blackhornet: $BASE_DIR"
    echo "  🧠 Agent Swarm:   $HOME/.bh/agent-sync"
    echo "  🤖 BlackHornet Agent:  $HOME/.bh/nous-agent"
    echo ""
}

# ============================================================================
# DAEMON — Unified Launcher (replaces immortal_daemon)
# ============================================================================

daemon_start() {
    bh_doctor_start
}

daemon_stop() {
    bh_doctor_stop
}

daemon_status() {
    bh_doctor_status
}

case "${1:-start}" in
    start)        start ;;
    stop)         stop ;;
    restart)      restart ;;
    status)       status ;;
    logs)         logs "${2:-bh}" ;;
    health)       health ;;
    watchdog)     watchdog_start ;;
    install)      install_on_boot ;;
    bootstrap)    bootstrap ;;
    agent-start)  agent_start ;;
    agent-stop)   agent_stop ;;
    agent-status) agent_status ;;
    bh-doctor-start) bh_doctor_start ;;
    bh-doctor-stop)  bh_doctor_stop ;;
    bh-doctor-status) bh_doctor_status ;;
    daemon-start) daemon_start ;;
    daemon-stop)  daemon_stop ;;
    daemon-status) daemon_status ;;
    swarm)        bh_doctor_start && agent_start && start ;;
    all)          bootstrap && bh_doctor_start && agent_start && start ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health|watchdog|install|bootstrap|agent-start|agent-stop|agent-status|bh-doctor-start|bh-doctor-stop|bh-doctor-status|swarm|all}"
        echo ""
        echo "Core:"
        echo "  start         - Start BLACKHORNET (with watchdog)"
        echo "  stop          - Stop BLACKHORNET"
        echo "  restart       - Restart BLACKHORNET"
        echo "  status        - Show system status"
        echo "  logs          - Tail logs [bh|watchdog|keeper|all]"
        echo "  health        - Run health check"
        echo ""
        echo "Agent Swarm:"
        echo "  agent-start   - Start BlackHornet Agent + BH Doctor"
        echo "  agent-stop    - Stop BlackHornet Agent + BH Doctor"
        echo "  agent-status  - Show agent swarm connections"
        echo "  bh-doctor-start - Start BH Doctor (unified launcher)"
        echo "  bh-doctor-stop  - Stop BH Doctor"
        echo "  bh-doctor-status - Show BH Doctor status"
        echo ""
        echo "Guardian:"
        echo "  daemon-start  - Start BH Doctor (alias)"
        echo "  daemon-stop   - Stop BH Doctor (alias)"
        echo "  daemon-status - Show BH Doctor status (alias)"
        echo ""
        echo "One-Command:"
        echo "  bootstrap     - Full auto-install (first run)"
        echo "  swarm         - Start full agent swarm + trading"
        echo "  all           - Bootstrap + start everything"
        echo "  install       - Install on-boot + auto-restart"
        exit 1
        ;;
esac
