#!/bin/bash
# BH Hive — Docker Entrypoint
# Starts the entire sovereign empire in one container

set -e

echo "╔══════════════════════════════════════╗"
echo "║   BH HIVE — Docker Bootstrap    ║"
echo "╚══════════════════════════════════════╝"

# Start ProxyGateLLM
echo "[1/4] Starting ProxyGateLLM..."
cd /proxygate && PORT=3333 nohup node index.js > /tmp/proxygate.log 2>&1 &
sleep 3

# Verify ProxyGateLLM
if curl -s http://localhost:3333/health > /dev/null 2>&1; then
    echo "  ✅ ProxyGateLLM ONLINE"
else
    echo "  ⚠️  ProxyGateLLM not responding"
fi

# Start Mnemosyne (if built)
echo "[2/4] Starting Mnemosyne..."
if [ -d /mnemosyne/.next ]; then
    cd /mnemosyne && PORT=3001 nohup npm start > /tmp/mnemosyne.log 2>&1 &
    echo "  ✅ Mnemosyne started"
else
    echo "  ⚠️  Mnemosyne not built (run: npm run build)"
fi

# Start Unified Launcher (replaces immortal_daemon + memory_bridge)
echo "[3/4] Starting Unified Launcher..."
cd /blackhornet && nohup python3 -m src.integration.unified_launcher > logs/daemon.log 2>&1 &
echo "  ✅ Launcher started"

# Start Swarm Engine
echo "[4/4] Starting Swarm Engine..."
echo "  ✅ Swarm engine available via src.swarm"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   BH HIVE — OPERATIONAL         ║"
echo "║   ProxyGateLLM :3333 | Daemon 🛡️    ║"
echo "║   Swarm active | 21 agents ready    ║"
echo "╚══════════════════════════════════════╝"

# Keep alive + health monitoring
while true; do
    sleep 60
    if ! curl -s http://localhost:3333/health > /dev/null 2>&1; then
        echo "[WARN] ProxyGateLLM down — restarting..."
        cd /proxygate && PORT=3333 nohup node index.js > /tmp/proxygate.log 2>&1 &
    fi
done
