# Testing Strategy — BlackHornet Ω

## Test Layers
1. **Unit tests** — Individual modules, no dependencies (pytest)
2. **Integration tests** — Module interactions, real I/O
3. **Acceptance tests** — Full workflow validation
4. **Property-based tests** — Edge case discovery

## Running Tests
```bash
# All tests
python3 -m pytest tests/ -v

# Specific module
python3 -m pytest tests/test_omega.py -v

# Quick mode (fail fast)
python3 -m pytest tests/ -x -q --tb=short
```

## Coverage Requirements
- Total: ≥80%
- Core modules: ≥90%
- Agent modules: ≥75%

## Test Categories
| Category | Tests | Files |
|----------|-------|-------|
| Omega Engine | 41 | test_omega.py |
| Hermes Nous | 14 | test_hermes_nous.py |
| Bridges | 8 | test_bridges.py |
| Vector | 50+ | test_vector.py |
| Core | 120+ | test_core*.py |
| Agents | 100+ | test_agent*.py |

Current: 375 passed, 22 skipped, 0 failed (as of 2026-07-04)
