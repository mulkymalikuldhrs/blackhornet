#!/bin/bash
# ============================================================
# Dhaher Swarm Guardian — Comprehensive Health Monitor
# ============================================================
# Checks: alive, responsive, rate-limited, idle, communication flow
# Auto-nudges idle agents, rotates keys on rate limits, restarts dead
# ============================================================

SWARM_DIR="/root/.hermes"
WS="/root/.openclaw-autoclaw/workspace"
LOG_DIR="${SWARM_DIR}/supervisor-logs"
HEALTH_LOG="${LOG_DIR}/health.log"
IDLE_THRESHOLD=900        # 15 min idle → nudge
RATE_LIMIT_COOLDOWN=120   # 2 min cooldown after rate limit

mkdir -p "$LOG_DIR"

PROFILES="autobot clawbot fangbot hackerbot devbot traderbot researchbot"

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$HEALTH_LOG"; }

# ── Check if gateway process is alive ──
is_alive() {
  local pidfile="${SWARM_DIR}/supervisor-logs/$1.pid"
  [ -f "$pidfile" ] || return 1
  kill -0 "$(cat "$pidfile")" 2>/dev/null
}

# ── Check if Telegram is connected ──
is_connected() {
  python3 -c "
import json
try:
    d=json.load(open('${SWARM_DIR}/profiles/$1/gateway_state.json'))
    ok=d.get('gateway_state')=='running' and d['platforms']['telegram']['state']=='connected'
    exit(0 if ok else 1)
except: exit(1)
" 2>/dev/null
}

# ── Check last agent activity (idle detection) ──
last_active() {
  local sess_dir="${SWARM_DIR}/profiles/$1/sessions"
  if [ -d "$sess_dir" ]; then
    find "$sess_dir" -name "*.json" -newer "$sess_dir" -mmin -$IDLE_THRESHOLD 2>/dev/null | wc -l
  else
    echo "0"
  fi
}

# ── Check rate limit status ──
is_rate_limited() {
  grep -c "429\|Rate limit\|Too Many Requests" "${SWARM_DIR}/profiles/$1/logs/agent.log" 2>/dev/null | tail -1 || echo "0"
}

# ── Nudge idle agent via shared memory ──
nudge_agent() {
  local p="$1"
  log "⚡ NUDGING $p (idle > ${IDLE_THRESHOLD}s)"
  cat >> "${SWARM_DIR}/shared-workspace/MEMORY.md" << NUDGE
> **[$p @ $(date)]** System nudge: you've been idle. Review shared workspace and check if any tasks need attention.
NUDGE
}

# ── Restart agent ──
restart_agent() {
  local p="$1"
  log "🔄 RESTARTING $p"
  # Clean locks
  rm -f "${SWARM_DIR}/profiles/${p}/gateway.pid" \
        "${SWARM_DIR}/profiles/${p}/gateway.lock" \
        "${SWARM_DIR}/profiles/${p}/gateway_state.json" 2>/dev/null
  rm -f /root/.local/state/hermes/gateway-locks/telegram-bot-token-*.lock 2>/dev/null
  # Start
  HERMES_HOME="${SWARM_DIR}/profiles/${p}" \
    setsid hermes gateway run --accept-hooks --replace \
    >> "${LOG_DIR}/${p}.log" 2>&1 &
  echo $! > "${LOG_DIR}/${p}.pid"
}

# ── Rotate NVIDIA key for rate-limited agent ──
rotate_key() {
  local p="$1"
  local key_a="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"
  local key_b="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"
  local current=$(grep "NVIDIA_API_KEY=" "${SWARM_DIR}/profiles/${p}/.env" | cut -d= -f2)
  
  if [ "$current" = "$key_a" ]; then
    sed -i "s|NVIDIA_API_KEY=.*|NVIDIA_API_KEY=${key_b}|" "${SWARM_DIR}/profiles/${p}/.env"
    log "🔑 $p: rotated to NVIDIA Key B"
  else
    sed -i "s|NVIDIA_API_KEY=.*|NVIDIA_API_KEY=${key_a}|" "${SWARM_DIR}/profiles/${p}/.env"
    log "🔑 $p: rotated to NVIDIA Key A"
  fi
  restart_agent "$p"
}

# ── Ensure ProxyGateLLM is running ──
check_proxy() {
  if ! curl -s http://localhost:3333/health >/dev/null 2>&1; then
    log "🔌 ProxyGateLLM DOWN — restarting"
    kill $(lsof -ti:3333 2>/dev/null) 2>/dev/null || true
    sleep 1
    cd "${SWARM_DIR}/shared-workspace/ProxyGateLLM" && \
      setsid node index.js >> "${LOG_DIR}/proxygate.log" 2>&1 &
    echo $! > "${LOG_DIR}/proxygate.pid"
  fi
}

# ── Main health check cycle ──
health_check() {
  log "🏥 Health check cycle"
  local dead=0 idle=0 throttled=0
  
  for p in $PROFILES; do
    if ! is_alive "$p"; then
      log "  💀 $p DEAD — restarting"
      restart_agent "$p"
      dead=$((dead + 1))
    elif ! is_connected "$p"; then
      log "  🔌 $p disconnected — restarting"
      restart_agent "$p"
      dead=$((dead + 1))
    else
      # Check idle
      local activity=$(last_active "$p")
      if [ "$activity" -eq 0 ]; then
        nudge_agent "$p"
        idle=$((idle + 1))
      fi
      # Check rate limit
      local rl=$(is_rate_limited "$p")
      if [ "$rl" -gt 3 ]; then
        log "  🚦 $p rate-limited — rotating key"
        rotate_key "$p"
        throttled=$((throttled + 1))
      fi
    fi
  done
  
  check_proxy
  
  log "  Result: dead=$dead idle=$idle throttled=$throttled alive=$((7-dead))"
}

# ── Keep-alive: periodic proactive check that agents can still respond ──
keep_alive_check() {
  # Every 6 cycles (~30 min), do a deeper check
  local cycle=$(cat "${LOG_DIR}/.keepalive_cycle" 2>/dev/null || echo 0)
  cycle=$((cycle + 1))
  echo "$cycle" > "${LOG_DIR}/.keepalive_cycle"
  
  if [ $((cycle % 6)) -eq 0 ]; then
    log "💓 Deep keep-alive check"
    for p in $PROFILES; do
      if is_alive "$p" && is_connected "$p"; then
        # Write a lightweight check marker to shared memory
        # Agents read MEMORY.md on every session start — 
        # this keeps the workspace "warm"
        echo "[keepalive @ $(date)]" >> "${SWARM_DIR}/shared-workspace/.keepalive"
      fi
    done
  fi
}

# ── Guardian loop ──
log "🛡️ Dhaher Swarm Guardian — Activated"
log "  Profile: keep-alive + anti-idle + anti-throttle + auto-heal"
log "  Check interval: 5 min"

CHECK_INTERVAL=300

while true; do
  health_check
  keep_alive_check
  
  # Clean old rate limit data periodically
  if [ $(( $(date +%s) % 3600 )) -lt $CHECK_INTERVAL ]; then
    for p in $PROFILES; do
      > "${SWARM_DIR}/profiles/${p}/logs/agent.log" 2>/dev/null  # rotate
    done
  fi
  
  sleep $CHECK_INTERVAL
done
