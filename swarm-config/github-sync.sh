#!/bin/bash
# ============================================================
# Dhaher Swarm — GitHub Sync Script
# Syncs all agent sessions, memory, and workspace to GitHub
# ============================================================
set -e

REPO_DIR="/root/.hermes/github-sync"
SYNC_DIR="${REPO_DIR}/sync"
SHARED_WS="/root/.hermes/shared-workspace"
PROFILES_DIR="/root/.hermes/profiles"
TIMESTAMP=$(date -Iseconds)

log() { echo "[$(date '+%H:%M:%S')] $1"; }

cd "$REPO_DIR"

# 1. Pull latest from remote
log "Pulling latest..."
git pull origin main 2>/dev/null || log "(no remote changes)"

# 2. Sync shared memory
log "Syncing shared memory..."
mkdir -p "${SYNC_DIR}/memory/daily"
cp "${SHARED_WS}/MEMORY.md" "${SYNC_DIR}/memory/" 2>/dev/null || true
cp -r "${SHARED_WS}/memory/"* "${SYNC_DIR}/memory/daily/" 2>/dev/null || true

# 3. Sync workspace files
log "Syncing workspace..."
mkdir -p "${SYNC_DIR}/workspace"
cp "${SHARED_WS}/AGENTS.md" "${SYNC_DIR}/workspace/" 2>/dev/null || true
for f in IDENTITY.md USER.md SOUL.md; do
  cp "${SHARED_WS}/${f}" "${SYNC_DIR}/workspace/" 2>/dev/null || true
  cp "/root/.openclaw-autoclaw/workspace/${f}" "${SYNC_DIR}/workspace/" 2>/dev/null || true
done

# 4. Sync all profile SOUL.md
log "Syncing profile SOULs..."
mkdir -p "${SYNC_DIR}/profiles"
for p in autobot clawbot fangbot hackerbot devbot traderbot researchbot; do
  mkdir -p "${SYNC_DIR}/profiles/${p}"
  cp "${PROFILES_DIR}/${p}/SOUL.md" "${SYNC_DIR}/profiles/${p}/" 2>/dev/null || true
done

# 5. Sync recent session logs (last 24h)
log "Syncing session logs..."
mkdir -p "${SYNC_DIR}/sessions"
for p in autobot clawbot fangbot hackerbot devbot traderbot researchbot; do
  SESS_DIR="${PROFILES_DIR}/${p}/sessions"
  if [ -d "$SESS_DIR" ]; then
    mkdir -p "${SYNC_DIR}/sessions/${p}"
    find "$SESS_DIR" -name "*.json" -mmin -1440 -exec cp {} "${SYNC_DIR}/sessions/${p}/" \; 2>/dev/null || true
  fi
done

# 6. Sync gateway status
log "Syncing gateway status..."
mkdir -p "${SYNC_DIR}/logs"
for p in autobot clawbot fangbot hackerbot devbot traderbot researchbot; do
  cp "${PROFILES_DIR}/${p}/gateway_state.json" "${SYNC_DIR}/logs/${p}_state.json" 2>/dev/null || true
done

# 7. Commit and push
log "Committing..."
git add -A
if git diff --cached --quiet; then
  log "No changes to sync"
else
  git commit -m "sync: ${TIMESTAMP}" 2>&1
  git push origin main 2>&1
  log "✅ Synced to GitHub"
fi
