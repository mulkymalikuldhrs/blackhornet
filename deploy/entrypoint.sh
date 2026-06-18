#!/bin/bash
# BH Hive — Docker Entrypoint
# Starts the entire sovereign empire in one container

set -e

echo "╔══════════════════════════════════════╗"
echo "║   BH HIVE — Docker Bootstrap        ║"
echo "╚══════════════════════════════════════╝"

BH_HOME="${BH_HOME:-/root/.bh}"

# ── 1. ProxyGateLLM (LLM gateway) ──────────────────────────────
echo "[1/5] Starting ProxyGateLLM..."
if [ -d /blackhornet/vendor/ProxyGateLLM ]; then
    cd /blackhornet/vendor/ProxyGateLLM && PORT=3333 nohup node index.js > /tmp/proxygate.log 2>&1 &
    sleep 3
    if curl -s http://localhost:3333/health > /dev/null 2>&1; then
        echo "  ✅ ProxyGateLLM ONLINE"
    else
        echo "  ⚠️  ProxyGateLLM starting (check /tmp/proxygate.log)"
    fi
else
    echo "  ⚠️  ProxyGateLLM not vendored — LLM gateway unavailable"
fi

# ── 2. Mnemosyne (Web UI, Next.js) ─────────────────────────────
echo "[2/5] Starting Mnemosyne..."
if [ -d /blackhornet/vendor/mnemosyne/.next ]; then
    cd /blackhornet/vendor/mnemosyne && PORT=3001 nohup npm start > /tmp/mnemosyne.log 2>&1 &
    echo "  ✅ Mnemosyne started on :3001"
else
    echo "  ⚠️  Mnemosyne not built (run: npm run build in vendor/mnemosyne)"
fi

# ── 3. BH Doctor (health daemon) ───────────────────────────────
echo "[3/5] Starting BH Doctor..."
cd /blackhornet && nohup python3 bh-doctor start > logs/doctor.log 2>&1 &
echo "  ✅ BH Doctor started"

# ── 4. Unified Launcher (all internal services) ─────────────────
echo "[4/5] Starting Unified Launcher..."
cd /blackhornet && nohup python3 -m src.integration.unified_launcher --port 8080 > logs/daemon.log 2>&1 &
echo "  ✅ Unified Launcher started on :8080"

# ── 5. Swarm Engine ────────────────────────────────────────────
echo "[5/5] Swarm Engine..."
echo "  ✅ Swarm engine available via src.swarm"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   BH HIVE — OPERATIONAL                     ║"
echo "║   ProxyGateLLM :3333 | Web UI :8080         ║"
echo "║   Mnemosyne    :3001 | BH Doctor ⚕️          ║"
echo "║   Daemon 🛡️    | Swarm active               ║"
echo "╚══════════════════════════════════════════════╝"

# Keep alive + health monitoring
while true; do
    sleep 60
    if [ -d /blackhornet/vendor/ProxyGateLLM ] && ! curl -s http://localhost:3333/health > /dev/null 2>&1; then
        echo "[WARN] ProxyGateLLM down — restarting..."
        cd /blackhornet/vendor/ProxyGateLLM && PORT=3333 nohup node index.js > /tmp/proxygate.log 2>&1 &
    fi
done
