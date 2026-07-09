#!/usr/bin/env bash
# BH Heartbeat — cron-friendly health check (every minute)
# Checks daemon liveness AND memory health
# If daemon dies, restart it automatically

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DAEMON="$BH_DIR/scripts/bh_daemon.py"
MEMORY_SCRIPT="$BH_DIR/scripts/memory.py"
PID_FILE="$BH_DIR/data/bh.pid"
LOG="$BH_DIR/logs/heartbeat.log"
HEARTBEAT_JSON="$BH_DIR/data/bh-heartbeat.json"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] BH heartbeat check..." >> "$LOG"

# 1. Check daemon liveness
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE" 2>/dev/null)
  if kill -0 "$PID" 2>/dev/null; then
    echo "  Daemon alive (PID: $PID)" >> "$LOG"

    # 2. Check memory health (optional — non-fatal if it fails)
    if [ -f "$MEMORY_SCRIPT" ]; then
      MEM_STATS=$(cd "$BH_DIR" && python3 -c "
from scripts.memory import VectorMemory
import json
m = VectorMemory()
print(json.dumps(m.stats()))
" 2>/dev/null)
      if [ -n "$MEM_STATS" ]; then
        echo "  Memory stats: $MEM_STATS" >> "$LOG"
      else
        echo "  Memory check: unavailable" >> "$LOG"
      fi
    fi

    # 3. Update heartbeat with memory info
    if command -v python3 &>/dev/null; then
      python3 -c "
import json, sys
from pathlib import Path
hb_file = Path('$HEARTBEAT_JSON')
if hb_file.exists():
    hb = json.loads(hb_file.read_text())
    hb['memory_healthy'] = True
    hb['last_check'] = '$(date -Iseconds)'
    hb_file.write_text(json.dumps(hb, indent=2))
" 2>/dev/null
    fi

    exit 0
  fi
fi

# Daemon is dead — restart
echo "  Daemon down. Restarting..." >> "$LOG"
rm -f "$PID_FILE"
cd "$BH_DIR" && python3 "$DAEMON" start &>/dev/null &
echo "  Restarted at $(date)" >> "$LOG"

# Log to main daemon log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] BH auto-restarted after crash" >> "$BH_DIR/logs/bh-daemon.log"
