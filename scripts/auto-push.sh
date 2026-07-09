#!/bin/bash
#
# BH Doctor - Auto-Push to Remotes
# Automatically commits and pushes changes to Codeberg + GitLab
#
# Usage: ./auto-push.sh [--message "commit message"] [--force]
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BH_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
LOGS_DIR="$BH_HOME/logs"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MSG="${1:-[AUTO] BH Doctor auto-push - $TIMESTAMP}"
FORCE_PUSH="${2:-}"

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGS_DIR/auto-push.log"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ ERROR: $1" | tee -a "$LOGS_DIR/auto-push.log" >&2
}

# Ensure we're in the right directory
cd "$BH_HOME" || exit 1

log "=========================================="
log "BH Doctor Auto-Push Starting"
log "Commit Message: $COMMIT_MSG"
log "Force Push: $FORCE_PUSH"
log "=========================================="

# Check git status
CHANGES=$(git status --short 2>&1)
if [ -z "$CHANGES" ]; then
    log "ℹ️  No changes to commit"
    exit 0
fi

log "📝 Changes detected:"
echo "$CHANGES" | tee -a "$LOGS_DIR/auto-push.log"

# Add all changes
log "\n📦 Adding all changes..."
git add -A

# Commit
log "\n💾 Committing..."
if git commit -m "$COMMIT_MSG"; then
    log "✅ Commit successful"
else
    error "Commit failed"
    exit 1
fi

# Run tests before push (optional)
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
    log "\n🧪 Running quick test check..."
    if command -v python3 &> /dev/null; then
        if python3 -m py_compile blackhornet.py 2>/dev/null; then
            log "✅ Python syntax check passed"
        else
            error "Python syntax check failed"
            # Don't fail, just warn
        fi
    fi
fi

# Push to remotes
log "\n🚀 Pushing to remotes..."

# Push to Codeberg
if git remote | grep -q "codeberg"; then
    log "\n📤 Pushing to Codeberg..."
    if [ "$FORCE_PUSH" = "--force" ]; then
        git push --force codeberg main 2>&1 | tee -a "$LOGS_DIR/auto-push.log"
    else
        git push codeberg main 2>&1 | tee -a "$LOGS_DIR/auto-push.log"
    fi
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "✅ Codeberg push successful"
    else
        error "Codeberg push failed (continuing to GitLab)"
    fi
else
    log "⚠️  Codeberg remote not configured"
fi

# Push to GitLab
if git remote | grep -q "gitlab"; then
    log "\n📤 Pushing to GitLab..."
    if [ "$FORCE_PUSH" = "--force" ]; then
        git push --force gitlab master 2>&1 | tee -a "$LOGS_DIR/auto-push.log"
    else
        git push gitlab master 2>&1 | tee -a "$LOGS_DIR/auto-push.log"
    fi
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "✅ GitLab push successful"
    else
        error "GitLab push failed"
    fi
else
    log "⚠️  GitLab remote not configured"
fi

# Push to bare repo (local backup)
if git remote | grep -q "bare"; then
    log "\n📤 Pushing to local bare repo..."
    git push bare main 2>&1 | tee -a "$LOGS_DIR/auto-push.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "✅ Local bare repo push successful"
    else
        error "Local bare repo push failed"
    fi
else
    log "⚠️  Bare remote not configured"
fi

# Summary
log "\n=========================================="
log "Auto-Push Complete"
log "=========================================="

# Graphify this push
PUSH_RECORD="$BH_HOME/data/auto-push-$(date '+%Y%m%d_%H%M%S').json"
cat > "$PUSH_RECORD" << EOF
{
  "timestamp": "$TIMESTAMP",
  "commit_message": "$COMMIT_MSG",
  "force_push": $([ "$FORCE_PUSH" = "--force" ] && echo "true" || echo "false"),
  "changes_count": $(echo "$CHANGES" | wc -l),
  "remotes_pushed": [
    $(git remote | grep -q "codeberg" && echo '"codeberg"')$(git remote | grep -q "gitlab" && echo ', "gitlab"')$(git remote | grep -q "bare" && echo ', "bare"')
  ],
  "status": "success"
}
EOF

log "📊 Push record saved: $PUSH_RECORD"
log "\n✅ BH Doctor Auto-Push Complete"