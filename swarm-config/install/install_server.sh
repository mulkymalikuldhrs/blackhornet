#!/bin/bash
# ============================================================
# Dhaher Swarm — Linux Server Installer
# Auto-clones entire swarm to a new Linux server
# ============================================================
set -e
echo "🧬 Dhaher Swarm — Server Installer"
echo "=================================="

# 1. Install BlackHornet Agent
if ! command -v hermes &>/dev/null; then
  echo "[1/5] Installing BlackHornet Agent..."
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
fi

# 2. Create profiles
echo "[2/5] Creating profiles..."
for p in autobot clawbot fangbot hackerbot devbot traderbot researchbot; do
  hermes profile create "$p" --clone-from default --no-alias 2>/dev/null || true
done

# 3. Clone repos
echo "[3/5] Cloning repositories..."
mkdir -p ~/.bh/shared-workspace
cd ~/.bh/shared-workspace
git clone https://github.com/dhaher-labs/ProxyGateLLM.git 2>/dev/null || (cd ProxyGateLLM && git pull)
git clone https://github.com/dhaher-labs/mnemosyne.git 2>/dev/null || echo "⚠ mnemosyne not cloned (optional)"
git clone https://github.com/dhaher-labs/blackhornet.git 2>/dev/null || (cd blackhornet && git pull)
git clone https://github.com/dhaher-labs/agent.git github-sync 2>/dev/null || (cd github-sync && git pull)

# 4. Install ProxyGateLLM deps
echo "[4/5] Installing ProxyGateLLM..."
cd ~/.bh/shared-workspace/ProxyGateLLM && npm install --silent 2>/dev/null || true

# 5. Setup auto-start
echo "[5/5] Setting up auto-start..."
# systemd service
sudo tee /etc/systemd/system/dhaher-swarm.service > /dev/null << SERVICEEOF
[Unit]
Description=Dhaher Swarm — Autonomous Multi-Agent System
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
ExecStart=/root/.openclaw-autoclaw/workspace/dhaher-swarm.sh start
ExecStop=/root/.openclaw-autoclaw/workspace/dhaher-swarm.sh stop
Restart=on-failure
RestartSec=30
User=root
WorkingDirectory=/root/.openclaw-autoclaw/workspace

[Install]
WantedBy=multi-user.target
SERVICEEOF
sudo systemctl daemon-reload
sudo systemctl enable dhaher-swarm 2>/dev/null || true

echo ""
echo "✅ Dhaher Swarm server installation complete!"
echo ""
echo "Next steps:"
echo "  1. Edit ~/.bh/profiles/*/.env with your TELEGRAM_BOT_TOKEN + API keys"
echo "  2. Run: sudo systemctl start dhaher-swarm"
echo "  3. Check: sudo systemctl status dhaher-swarm"
