#!/usr/bin/env bash
set -euo pipefail
echo "=== BlackHornet Test Suite ==="
cd "$(dirname "$0")"
echo "  Python files: $(find . -name '*.py' -not -path './.git/*' -not -path './__pycache__/*' | wc -l)"
echo "  Test files: $(find tests/ -name '*.py' -not -path './__pycache__/*' 2>/dev/null | wc -l)"
python3 -m pytest tests/ -q 2>&1 | tail -5
echo "=== Done ==="
