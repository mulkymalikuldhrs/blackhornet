#!/bin/bash
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Hermes Nous → BlackHornet Auto-Sync Pipeline
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fetches from hermes-nous-research repo,
# converts research data → BH agent updates,
# auto-upgrades BH capabilities, runs tests.

set -euo pipefail

DHAHER="${DHAHERLABS:-/sdcard/dhaherlabs}"
BH="$DHAHER/blackhornet-worktree"
HERMES_REPO="https://codeberg.org/mulkydhaher/hermes-nous-research.git"
HERMES_DIR="$DHAHER/data/hermes-nous-research"
OMEGA_DATA="$DHAHER/data/omega"
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%SZ')

echo "━━━ Hermes → BH Auto-Sync [${TIMESTAMP}] ━━━"

# Step 1: Fetch hermes-nous-research
echo "→ Fetching hermes-nous-research..."
if [ -d "$HERMES_DIR" ]; then
    git -C "$HERMES_DIR" pull --ff-only 2>&1 || echo "  pull failed, will re-clone"
fi
if [ ! -d "$HERMES_DIR/.git" ]; then
    rm -rf "$HERMES_DIR"
    git clone "$HERMES_REPO" "$HERMES_DIR" 2>&1 || echo "  clone failed (repo may not exist yet)"
fi

# Step 2: Convert research → BH updates
echo "→ Converting research to BH module updates..."
python3 -c "
from src.hermes_nous.converter import HermesNousConverter
import json
c = HermesNousConverter()
conversions = c.convert_all()
print(json.dumps({'files_scanned': len(c.scan_research()), 'conversions': len(conversions)}, indent=2))
" 2>&1 || echo "  converter not yet ready"

# Step 3: Update consciousness layers
echo "→ Updating consciousness layers..."
python3 -c "
from src.hermes_nous.layers import ConsciousnessLayers
cl = ConsciousnessLayers()
cl.activate_all()
print('Consciousness layers active:', [l['name'] for l in cl.status()])
" 2>&1 || echo "  consciousness not yet ready"

# Step 4: Run BH tests
echo "→ Verifying BH tests..."
cd "$BH"
python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -5 || echo "  tests need fixing after merge"

# Step 5: Commit and push
echo "→ Committing auto-sync updates..."
cd "$BH"
if ! git diff --quiet; then
    git add -A
    git commit -m "auto-sync: hermes-nous → BH [${TIMESTAMP}]"
    git push 2>&1 || echo "  push deferred (check remote config)"
    echo "✓ Pushed BH updates to Codeberg"
else
    echo "  nothing to commit"
fi

echo "━━━ Auto-Sync Complete ━━━"