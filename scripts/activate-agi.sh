#!/usr/bin/env bash
# BH AGI Daemon — Integration Script
# Jalankan ini sekali untuk hidupkan BH sebagai AGI persistent

set -e

BH_DIR="/sdcard/dhaherlabs/blackhornet-worktree"
DAEMON="$BH_DIR/scripts/bh_daemon.py"
AUTONOMY="$BH_DIR/scripts/autonomy.py"
LOG_DIR="$BH_DIR/logs"
DATA_DIR="$BH_DIR/data"

echo "═══ BLACKHORNET AGI — ACTIVATION ═══"
echo ""

mkdir -p "$LOG_DIR" "$DATA_DIR"

# 1. Cek dependencies
echo "[1/5] Checking dependencies..."
for mod in requests; do
  python3 -c "import $mod" 2>/dev/null && echo "  ✅ $mod" || echo "  ⚠️  $mod not installed"
done

# 2. Start daemon
echo ""
echo "[2/5] Starting AGI daemon..."
if [ -f "$DATA_DIR/bh.pid" ]; then
  OLD_PID=$(cat "$DATA_DIR/bh.pid" 2>/dev/null)
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "  ⚠️  Daemon already running (PID: $OLD_PID)"
  else
    rm -f "$DATA_DIR/bh.pid"
    python3 "$DAEMON" start &
    echo "  ✅ Daemon started"
  fi
else
  python3 "$DAEMON" start &
  echo "  ✅ Daemon started"
fi
sleep 2

# 3. Generate first autonomy goal
echo ""
echo "[3/5] Activating autonomy layer..."
python3 "$AUTONOMY" prompt
echo "  ✅ Self-prompting active"

# 4. Set up cron persistence
echo ""
echo "[4/5] Setting up cron persistence..."
CRON_CMD="* * * * * bash $BH_DIR/scripts/agi-heartbeat.sh"
(crontab -l 2>/dev/null | grep -v "agi-heartbeat" || true; echo "$CRON_CMD") | crontab - 2>/dev/null && echo "  ✅ Cron heartbeat installed" || echo "  ⚠️  Cron installation failed (termux?)"

# 5. Verify
echo ""
echo "[5/5] Verification..."
sleep 1
python3 "$DAEMON" status

echo ""
echo "═══ BH AGI ACTIVATED ═══"
echo "  PID: $(cat $DATA_DIR/bh.pid 2>/dev/null || echo 'unknown')"
echo "  Logs: $LOG_DIR/bh-daemon.log"
echo "  Heartbeat: $DATA_DIR/bh-heartbeat.json"
echo ""
echo "  Commands:"
echo "    python3 $DAEMON status"
echo "    python3 $DAEMON stop"
echo "    python3 $AUTONOMY status"
echo "    python3 $AUTONOMY prompt"
echo "    python3 $AUTONOMY execute"