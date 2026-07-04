#!/bin/bash
# ============================================================================
# BLACKHORNET — Docker/E2B Entrypoint
# Starts the entire sovereign empire in one container
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1"; }
ok()  { echo -e "${GREEN}  ✓${NC} $1"; }
warn(){ echo -e "${YELLOW}  ⚠${NC} $1"; }
die() { echo -e "${RED}  ✗ FATAL:${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🖤 BLACKHORNET — Docker/E2B Bootstrap       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Create required directories
mkdir -p /app/logs /app/data /root/.hermes /proxygate /mnemosyne /agent /quant-nanggroe

# ── Step 1: Start ProxyGateLLM ────────────────────────────────────────
log "[1/5] Starting ProxyGateLLM (LLM gateway)..."
cd /proxygate

# Check if node is available
if ! command -v node &> /dev/null; then
    warn "Node.js not found — installing..."
    apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*
fi

PORT=3333 nohup node index.js > /tmp/proxygate.log 2>&1 &
PROXYGATE_PID=$!
sleep 3

if kill -0 $PROXYGATE_PID 2>/dev/null; then
    # Verify health endpoint
    if curl -s http://localhost:3333/health > /dev/null 2>&1; then
        ok "ProxyGateLLM ONLINE — http://localhost:3333"
    else
        warn "ProxyGateLLM process running but health check failed"
        warn "Logs: $(tail -5 /tmp/proxygate.log 2>/dev/null)"
    fi
else
    warn "ProxyGateLLM failed to start"
    warn "Logs: $(tail -10 /tmp/proxygate.log 2>/dev/null)"
fi

# ── Step 2: Start Mnemosyne (optional) ────────────────────────────────
log "[2/5] Starting Mnemosyne (memory system)..."
if [ -d /mnemosyne/.next ]; then
    cd /mnemosyne
    PORT=3001 nohup npm start > /tmp/mnemosyne.log 2>&1 &
    sleep 2
    ok "Mnemosyne started — http://localhost:3001"
else
    warn "Mnemosyne not built (skipping)"
fi

# ── Step 3: Start Immortal Daemon ─────────────────────────────────────
log "[3/5] Starting Immortal Daemon..."
cd /app/src

if [ -f immortal_daemon.py ]; then
    nohup python3 immortal_daemon.py > /app/logs/daemon.log 2>&1 &
    DAEMON_PID=$!
    echo $DAEMON_PID > /app/logs/daemon.pid
    ok "Immortal Daemon started (PID: $DAEMON_PID)"
elif [ -f /app/src/immortal_daemon.py ]; then
    cd /app/src
    nohup python3 immortal_daemon.py > /app/logs/daemon.log 2>&1 &
    DAEMON_PID=$!
    echo $DAEMON_PID > /app/logs/daemon.pid
    ok "Immortal Daemon started (PID: $DAEMON_PID)"
else
    warn "immortal_daemon.py not found — skipping"
fi

# ── Step 4: Start Memory Bridge ───────────────────────────────────────
log "[4/5] Starting Memory Bridge..."
cd /app/src
if [ -f memory_bridge.py ]; then
    nohup python3 memory_bridge.py --bot docker-traderbot > /app/logs/bridge.log 2>&1 &
    BRIDGE_PID=$!
    echo $BRIDGE_PID > /app/logs/bridge.pid
    ok "Memory Bridge started (PID: $BRIDGE_PID)"
elif [ -f /app/src/memory_bridge.py ]; then
    nohup python3 memory_bridge.py --bot docker-traderbot > /app/logs/bridge.log 2>&1 &
    BRIDGE_PID=$!
    echo $BRIDGE_PID > /app/logs/bridge.pid
    ok "Memory Bridge started (PID: $BRIDGE_PID)"
else
    warn "memory_bridge.py not found — skipping"
fi

# ── Step 5: Health Monitor ────────────────────────────────────────────
log "[5/5] Starting health monitor..."

self_heal() {
    # Restart ProxyGateLLM if down
    if ! curl -s http://localhost:3333/health > /dev/null 2>&1; then
        warn "ProxyGateLLM down — restarting..."
        cd /proxygate && PORT=3333 nohup node index.js > /tmp/proxygate.log 2>&1 &
        sleep 2
    fi
    
    # Restart Daemon if down
    if [ -f /app/logs/daemon.pid ]; then
        if ! kill -0 $(cat /app/logs/daemon.pid 2>/dev/null) 2>/dev/null; then
            warn "Daemon down — restarting..."
            cd /app/src && nohup python3 immortal_daemon.py > /app/logs/daemon.log 2>&1 &
            echo $! > /app/logs/daemon.pid
        fi
    fi
    
    # Restart Bridge if down
    if [ -f /app/logs/bridge.pid ]; then
        if ! kill -0 $(cat /app/logs/bridge.pid 2>/dev/null) 2>/dev/null; then
            warn "Bridge down — restarting..."
            cd /app/src && nohup python3 memory_bridge.py --bot docker-traderbot > /app/logs/bridge.log 2>&1 &
            echo $! > /app/logs/bridge.pid
        fi
    fi
}

health_check() {
    local status=0
    
    # Check ProxyGateLLM
    if ! curl -s http://localhost:3333/health > /dev/null 2>&1; then
        warn "ProxyGateLLM down — restarting..."
        cd /proxygate && PORT=3333 nohup node index.js > /tmp/proxygate.log 2>&1 &
        sleep 2
        status=1
    fi
    
    # Check Daemon
    if [ -f /app/logs/daemon.pid ]; then
        if ! kill -0 $(cat /app/logs/daemon.pid 2>/dev/null) 2>/dev/null; then
            warn "Daemon down — restarting..."
            cd /app/src && nohup python3 immortal_daemon.py > /app/logs/daemon.log 2>&1 &
            echo $! > /app/logs/daemon.pid
            status=1
        fi
    fi
    
    # Check Bridge
    if [ -f /app/logs/bridge.pid ]; then
        if ! kill -0 $(cat /app/logs/bridge.pid 2>/dev/null) 2>/dev/null; then
            warn "Bridge down — restarting..."
            cd /app/src && nohup python3 memory_bridge.py --bot docker-traderbot > /app/logs/bridge.log 2>&1 &
            echo $! > /app/logs/bridge.pid
            status=1
        fi
    fi
    
    return $status
}

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     🖤 BLACKHORNET — OPERATIONAL                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}ProxyGateLLM:${NC}  http://localhost:3333 (LLM Gateway)"
echo -e "  ${CYAN}Mnemosyne:${NC}     http://localhost:3001 (Memory)"
echo -e "  ${CYAN}Daemon:${NC}        Immortal — auto-heal enabled"
echo -e "  ${CYAN}Bridge:${NC}        Memory sync active"
echo ""

# Keep alive + health monitoring
log "Health monitor active — checking every 30s"
while true; do
    sleep 30
    self_heal || true
done
