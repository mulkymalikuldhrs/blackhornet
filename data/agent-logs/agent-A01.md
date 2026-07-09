# Agent A01: Install-Engineer — Audit Summary

## Assignment
Audit and improve `/sdcard/dhaherlabs/blackhornet-worktree/bh-doctor.sh`

## Issues Found & Fixed

### CRITICAL: `local` outside function in case blocks
- **Lines**: `status)` block (line 751) and `export)` block (line 812)
- **Impact**: Bash errors with `local: can only be used in a function` at runtime
- **Fix**: Removed `local` keyword — these variables are at top-level script scope
- **Files**: bh-doctor.sh:751, 812

### CRITICAL: Missing `set -e` guard in doctor inline Python
- **Line**: 795-801 (doctor case)
- **Impact**: If Python import fails, `set -e` aborts the entire script
- **Fix**: Added `|| true` to the inline Python invocation
- **Files**: bh-doctor.sh:808

### MEDIUM: `$USER` in systemd template
- **Line**: 462
- **Impact**: When run with `sudo`, `$USER` may be root; the original user is in `$SUDO_USER`
- **Fix**: Changed `User=$USER` to `User=${SUDO_USER:-$USER}`
- **Files**: bh-doctor.sh:469

### MEDIUM: Missing `OPENAI_API_KEY` support
- **Lines**: 300-341 (configure_llm)
- **Impact**: Standard OpenAI keys were not auto-detected or configured
- **Fix**: Added `OPENAI_API_KEY` detection block alongside existing providers
- **Files**: bh-doctor.sh:332-336

### MEDIUM: Missing `ripgrep` on Linux
- **Lines**: 146-151 (apt/dnf/pacman install)
- **Impact**: ripgrep (declared as dependency in header, installed on macOS) missing on Linux
- **Fix**: Added `ripgrep` to apt-get, dnf, and pacman install lists
- **Files**: bh-doctor.sh:147, 149, 151

### LOW: `set_env` uses `echo` for unsanitized values
- **Lines**: 341-348
- **Impact**: `echo "${key}=${value}"` can mangle strings with escape sequences
- **Fix**: Changed to `printf '%s=%s\n' "$key" "$value"`
- **Files**: bh-doctor.sh:353

### LOW: df disk check missing default guard
- **Lines**: 120-124
- **Impact**: If `df` fails, `AVAIL` is empty and arithmetic comparison errors
- **Fix**: Added `AVAIL=${AVAIL:-0}` default guard
- **Files**: bh-doctor.sh:124

## Test File Created
- **Path**: `scripts/test_installer.sh`
- **Coverage**: 31 tests covering syntax, set_env, OS detection (4 platforms), LLM key detection (6 providers), Graphify nodes, ecosystem repos, case-block `local` safety, doctor inline Python guard, ripgrep inclusion, SUDO_USER, OPENAI_API_KEY, disk guard, printf safety, and `local` scoping

## Verification
- `bash -n bh-doctor.sh` — syntax OK
- `bash scripts/test_installer.sh` — 31/31 tests passing
- All changes match existing shell script style (formatting, colors, patterns)
- No new comments added
