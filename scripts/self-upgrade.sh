#!/bin/bash
# ============================================================================
# BLACKHORNET Self-Upgrade Pipeline
# ============================================================================
# Auto: check upstream → sandbox → verify → commit → push
# Usage: bash scripts/self-upgrade.sh [check|dry-run|upgrade]
# ============================================================================
set -euo pipefail

BH_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_DIR="/tmp/hermes-agent"
LOG_DIR="$BH_HOME/logs"
SANDBOX_DIR="/tmp/bh-sandbox"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$LOG_DIR"

log() { echo "[BH-UPGRADE] $*"; echo "[$(date +%H:%M:%S)] $*" >> "$LOG_DIR/upgrade.log"; }
warn() { echo "[BH-UPGRADE] ⚠️ $*"; }
error() { echo "[BH-UPGRADE] ❌ $*"; }

# ── Check mode ──
check_upstream() {
    log "Checking Hermes upstream..."
    if [ ! -d "$HERMES_DIR/.git" ]; then
        warn "Hermes Agent not cloned at $HERMES_DIR"
        return 1
    fi
    cd "$HERMES_DIR"
    git fetch origin 2>/dev/null || true
    BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "0")
    if [ "$BEHIND" -gt 0 ]; then
        log "Found $BEHIND new commits upstream"
        git log HEAD..origin/main --oneline -5 2>/dev/null | while read line; do log "  $line"; done
        return 0
    else
        log "Already up to date"
        return 2
    fi
}

# ── Sandbox test mode ──
sandbox_test() {
    log "Creating sandbox at $SANDBOX_DIR..."
    rm -rf "$SANDBOX_DIR"
    mkdir -p "$SANDBOX_DIR"

    # Clone BH to sandbox
    cd "$BH_HOME"
    git clone --local . "$SANDBOX_DIR" 2>/dev/null || {
        cp -a "$BH_HOME" "$SANDBOX_DIR"
    }
    cd "$SANDBOX_DIR"

    # Apply Hermes upstream changes
    if [ -d "$HERMES_DIR/.git" ]; then
        log "Applying Hermes upstream changes in sandbox..."
        cd "$HERMES_DIR"
        UPSTREAM_FILES=$(git diff --name-only HEAD..origin/main -- 'src/' '*.py' '*.js' '*.ts' 2>/dev/null || echo "")
        if [ -n "$UPSTREAM_FILES" ]; then
            echo "$UPSTREAM_FILES" | while read f; do
                target="$SANDBOX_DIR/hermes-patch/$f"
                mkdir -p "$(dirname "$target")"
                git show origin/main:"$f" > "$target" 2>/dev/null || true
            done
        fi
    fi

    # Run ALL tests
    log "Running test suite in sandbox..."
    cd "$SANDBOX_DIR"
    RESULTS=""
    for testfile in src/*/tests.py; do
        if [ -f "$testfile" ]; then
            log "  Running $testfile..."
            if python3 "$testfile" 2>&1 >> "$LOG_DIR/sandbox-test-$TIMESTAMP.log"; then
                RESULTS="$RESULTS ✅ $testfile"
            else
                RESULTS="$RESULTS ❌ $testfile"
                warn "Test failed: $testfile"
            fi
        fi
    done
    for testfile in tests/*.py; do
        if [ -f "$testfile" ]; then
            log "  Running $testfile..."
            if python3 "$testfile" 2>&1 >> "$LOG_DIR/sandbox-test-$TIMESTAMP.log"; then
                RESULTS="$RESULTS ✅ $testfile"
            else
                RESULTS="$RESULTS ❌ $testfile"
                warn "Test failed: $testfile"
            fi
        fi
    done

    log "Sandbox test results:$RESULTS"

    # Check for failures
    if echo "$RESULTS" | grep -q "❌"; then
        error "Sandbox tests FAILED. Aborting merge."
        return 1
    fi
    log "All sandbox tests PASSED."
    return 0
}

# ── Commit & Push mode ──
commit_and_push() {
    log "Committing and pushing..."
    cd "$BH_HOME"

    # Stage all changes
    git add -A 2>/dev/null || true

    # Check if there's anything to commit
    if git diff --cached --quiet 2>/dev/null; then
        log "No changes to commit"
        return 0
    fi

    # Get upstream commit info
    cd "$HERMES_DIR"
    UPSTREAM_HASH=$(git rev-parse --short origin/main 2>/dev/null || echo "unknown")
    UPSTREAM_MSG=$(git log -1 --format=%s origin/main 2>/dev/null || echo "upstream sync")
    cd "$BH_HOME"

    git commit -m "chore: auto-sync Hermes upstream ($UPSTREAM_HASH)

$UPSTREAM_MSG

Auto-merged by BH Self-Upgrade Pipeline on $TIMESTAMP"

    # Push to Codeberg
    log "Pushing to Codeberg..."
    git push origin main 2>&1 || {
        warn "Push failed — will retry on next cycle"
        return 1
    }
    log "Push successful."
    return 0
}

# ── Main ──
MODE="${1:-check}"

case "$MODE" in
    check)
        check_upstream
        ;;
    dry-run)
        check_upstream && sandbox_test
        ;;
    upgrade)
        check_upstream && sandbox_test && commit_and_push
        ;;
    *)
        echo "Usage: $0 [check|dry-run|upgrade]"
        echo ""
        echo "  check     — Check Hermes upstream for new commits"
        echo "  dry-run   — Check + test in sandbox (no commit)"
        echo "  upgrade   — Full pipeline: check → sandbox → commit → push"
        exit 1
        ;;
esac
