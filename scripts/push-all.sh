#!/bin/bash
# push-all.sh — Push main branch to all 3 remotes in sequence
set -euo pipefail

BRANCH="${1:-main}"
REMOTES=("codeberg" "github" "gitlab")

echo "=== PUSHING $BRANCH TO ALL REMOTES ==="
for remote in "${REMOTES[@]}"; do
    echo "→ Pushing to $remote..."
    if git push "$remote" "$BRANCH" 2>&1; then
        echo "  ✅ $remote: success"
    else
        echo "  ❌ $remote: failed (continuing)"
    fi
done
echo "=== DONE ==="
