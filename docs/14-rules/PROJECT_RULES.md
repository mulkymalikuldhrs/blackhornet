# Project Rules — BlackHornet Ω

## Code Rules
1. No hardcoded paths — use AutoPath or detect dynamically
2. All new modules need tests
3. Docstrings required for all public APIs
4. Imports: stdlib → third-party → local
5. Type hints on all function signatures
6. No circular imports — use TYPE_CHECKING if needed
7. No secrets in code — env vars only

## Git Rules
1. Commit messages: `type: description` (feat, fix, docs, chore, test)
2. Tests must pass before commit
3. No force push to main
4. Changes are self-explanatory — commit messages tell the story

## Architecture Rules
1. `src/omega/` — engine layer, no agent dependencies
2. `src/agents/` — agent implementations, depends on omega
3. `src/bridges/` — cross-language compatibility
4. `src/hermes_nous/` — consciousness integration
5. Tests mirror src structure (`tests/test_<module>.py`)
