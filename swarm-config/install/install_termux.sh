#!/bin/bash
# ============================================================
# Dhaher Swarm — Termux (Android) Installer
# ============================================================
set -e
echo "🧬 Dhaher Swarm — Termux Installer"
echo "==================================="

pkg update -y
pkg install -y git curl python nodejs termux-api termux-boot 2>/dev/null || true

# 1. Install BlackHornet Agent
if ! command -v hermes &>/dev/null; then
  echo "[1/4] Installing BlackHornet Agent..."
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
fi

# 2. Create profiles
echo "[2/4] Creating profiles..."
for p in autobot clawbot fangbot hackerbot devbot traderbot researchbot; do
  hermes profile create "$p" --clone-from default --no-alias 2>/dev/null || true
done

# 3. Clone repos
echo "[3/4] Cloning repositories..."
mkdir -p ~/.bh/shared-workspace
cd ~/.bh/shared-workspace
for repo in JeumpaLLM mnemosyne blackhornet; do
  git clone "https://github.com/dhaher-labs/${repo}.git" 2>/dev/null || true
done
cd ~/.bh && git clone https://github.com/dhaher-labs/agent.git github-sync 2>/dev/null || true

# 4. Termux:Boot
echo "[4/4] Setting up Termux:Boot..."
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/dhaher-swarm << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 10
cd /data/data/com.termux/files/home/.openclaw-autoclaw/workspace
bash dhaher-swarm.sh start
BOOTEOF
chmod +x ~/.termux/boot/dhaher-swarm

# Start proxy
cd ~/.bh/shared-workspace/JeumpaLLM && npm install --silent 2>/dev/null || true

echo ""
echo "✅ Dhaher Swarm Termux installation complete!"
echo "  Auto-start on boot via Termux:Boot enabled"
echo "  Edit ~/.bh/profiles/*/.env with your tokens"
