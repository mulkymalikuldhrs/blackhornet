#!/bin/bash
# Hermes Hive — Docker Entrypoint
# Starts the entire sovereign empire in one container

set -e

echo "╔══════════════════════════════════════╗"
echo "║   HERMES HIVE — Docker Bootstrap    ║"
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

# Start Immortal Daemon
echo "[3/4] Starting Immortal Daemon..."
cd /hermes/src && nohup python3 immortal_daemon.py > ../logs/daemon.log 2>&1 &
echo "  ✅ Daemon started"

# Start Memory Bridge
echo "[4/4] Starting Memory Bridge..."
nohup python3 memory_bridge.py --bot docker-traderbot > ../logs/bridge.log 2>&1 &
echo "  ✅ Bridge started"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   HERMES HIVE — OPERATIONAL         ║"
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
