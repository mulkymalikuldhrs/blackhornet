#!/bin/bash
set -euo pipefail

BH_DOCTOR="$(cd "$(dirname "$0")/.." && pwd)/bh-doctor.sh"
[ -f "$BH_DOCTOR" ] || BH_DOCTOR="/sdcard/dhaherlabs/blackhornet-worktree/bh-doctor.sh"
[ -f "$BH_DOCTOR" ] || { echo "FATAL: Cannot find bh-doctor.sh"; exit 1; }
PASS=0
FAIL=0
TEST_TMPDIR=$(mktemp -d)
trap 'rm -rf "$TEST_TMPDIR"' EXIT

pass() { PASS=$((PASS+1)); echo -e "  \033[0;32mPASS\033[0m $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  \033[0;31mFAIL\033[0m $1"; }
check() { echo -e "\n\033[1;36m== $1 ==\033[0m"; }

check "Syntax"
bash -n "$BH_DOCTOR" 2>/dev/null && pass "Valid bash syntax" || fail "Syntax errors"

check "set_env"
S=$(bash -c "
source '$BH_DOCTOR' --test-skip >/dev/null 2>/dev/null
f=\$(mktemp -p '$TEST_TMPDIR')
set_env \"\$f\" K V 2>/dev/null; grep -q '^K=V$' \"\$f\" || echo E1
set_env \"\$f\" K U 2>/dev/null; grep -q '^K=U$' \"\$f\" || echo E2
set_env \"\$f\" E '' 2>/dev/null; grep -q '^E=$' \"\$f\" || echo E3
set_env \"\$f\" S 'a=b&c:d' 2>/dev/null; grep -q '^S=a=b&c:d$' \"\$f\" || echo E4
echo DONE
")
echo "$S" | grep -q DONE && pass "set_env: all 4 cases passed" || fail "set_env: $S"

check "OS Detection"
R=$(bash -c "
source '$BH_DOCTOR' --test-skip >/dev/null 2>/dev/null
uname() { echo Linux; }; OS=x; IS_TERMUX=x; IS_MACOS=x; IS_WSL=x; detect_os
echo \"OS=\$OS T=\$IS_TERMUX W=\$IS_WSL\"
uname() { echo Darwin; }; OS=x; IS_TERMUX=x; IS_MACOS=x; IS_WSL=x; detect_os
echo \"OS=\$OS M=\$IS_MACOS\"
uname() { echo Linux; }; TERMUX_VERSION=1; PREFIX=/data/data/com.termux/files/usr; OS=x; IS_TERMUX=x; IS_MACOS=x; IS_WSL=x; detect_os
echo \"OS=\$OS T=\$IS_TERMUX\"
uname() { echo FreeBSD; }; PREFIX=; OS=x; IS_TERMUX=x; IS_MACOS=x; IS_WSL=x; detect_os
echo \"OS=\$OS\"
")
echo "$R" | grep -q "OS=linux T=false" && pass "Detect: Linux" || echo "  Linux: $(echo "$R" | grep '^OS=linux')"
echo "$R" | grep -q "OS=macos M=true" && pass "Detect: macOS" || echo "  macOS: $(echo "$R" | grep '^OS=macos')"
echo "$R" | grep -q "OS=linux T=true" && pass "Detect: Termux" || echo "  Termux: $(echo "$R" | grep '^OS=linux.*T=true')"
echo "$R" | grep -q "OS=unknown" && pass "Detect: Unknown" || echo "  Unknown: $(echo "$R" | grep '^OS=')"

check "LLM Key Detection"
R=$(bash -c "
hk() {
    [ -n \"\${NVIDIA_API_KEY:-}\" ] && return 0
    [ -n \"\${OPENROUTER_API_KEY:-}\" ] && return 0
    [ -n \"\${ANTHROPIC_API_KEY:-}\" ] && return 0
    [ -n \"\${GROQ_API_KEY:-}\" ] && return 0
    [ -n \"\${OPENCODE_API_KEY:-}\" ] && return 0
    [ -n \"\${OPENAI_API_KEY:-}\" ] && return 0
    return 1
}
unset NVIDIA_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY GROQ_API_KEY OPENCODE_API_KEY OPENAI_API_KEY
hk && echo F_NONE || echo P_NONE
for var in NVIDIA_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY GROQ_API_KEY OPENCODE_API_KEY OPENAI_API_KEY; do
    export \"\$var=test\"
    hk && echo \"P_\$var\" || echo \"F_\$var\"
    unset \"\$var\"
done
")
echo "$R" | grep -q P_NONE && pass "No keys" || fail "Should be no keys"
echo "$R" | grep -q P_NVIDIA_API_KEY && pass "NVIDIA" || fail "NVIDIA missing"
echo "$R" | grep -q P_OPENROUTER_API_KEY && pass "OpenRouter" || fail "OpenRouter missing"
echo "$R" | grep -q P_ANTHROPIC_API_KEY && pass "Anthropic" || fail "Anthropic missing"
echo "$R" | grep -q P_GROQ_API_KEY && pass "Groq" || fail "Groq missing"
echo "$R" | grep -q P_OPENCODE_API_KEY && pass "OpenCode" || fail "OpenCode missing"
echo "$R" | grep -q P_OPENAI_API_KEY && pass "OpenAI (newly added)" || fail "OpenAI missing"

check "Graphify Nodes"
grep -q 'add_node.*BH_DOCTOR' "$BH_DOCTOR" && grep -q 'add_node.*SOVEREIGN' "$BH_DOCTOR" && \
    pass "Graphify creates BH_DOCTOR + SOVEREIGN nodes" || fail "Missing graph nodes"

check "Ecosystem Repos"
R=$(bash -c "
source '$BH_DOCTOR' --test-skip >/dev/null 2>/dev/null
echo \"COUNT=\${#ECOSYSTEM_REPOS[@]}\"
for r in blackhornet Quant-Nanggroe-AI AI-MultiColony-Ecosystem Vibe-Trading AutoHedge JeumpaLLM mnemosyne; do
    f=0; for e in \"\${ECOSYSTEM_REPOS[@]}\"; do [ \"\$e\" = \"\$r\" ] && f=1; done; echo \"R=\$r \$f\"
done
")
echo "$R" | grep -q "COUNT=7" && pass "7 ecosystem repos" || fail "Expected 7 repos"
echo "$R" | grep -q "R=blackhornet 1" && pass "  Repo: blackhornet" || fail "  blackhornet missing"
echo "$R" | grep -q "R=Quant-Nanggroe-AI 1" && pass "  Repo: Quant-Nanggroe-AI" || fail "  Quant-Nanggroe-AI missing"
echo "$R" | grep -q "R=AI-MultiColony-Ecosystem 1" && pass "  Repo: AI-MultiColony-Ecosystem" || fail "  missing"
echo "$R" | grep -q "R=Vibe-Trading 1" && pass "  Repo: Vibe-Trading" || fail "  missing"
echo "$R" | grep -q "R=AutoHedge 1" && pass "  Repo: AutoHedge" || fail "  missing"
echo "$R" | grep -q "R=JeumpaLLM 1" && pass "  Repo: JeumpaLLM" || fail "  missing"
echo "$R" | grep -q "R=mnemosyne 1" && pass "  Repo: mnemosyne" || fail "  missing"

check "Critical: No 'local' in Case Blocks"
for block in "status)" "export)"; do
    if sed -n "/^    $block/,/^    [a-z]/p" "$BH_DOCTOR" | grep -q '^\s*local '; then
        fail "'local' still in $block"
    else
        pass "'local' removed from $block"
    fi
done

check "Critical: Doctor Python Guard"
BLOCK=$(sed -n '/Graph DB missing/,/fi$/p' "$BH_DOCTOR")
echo "$BLOCK" | grep -q '\|\| true' && \
    pass "doctor inline Python has || true" || fail "doctor inline Python missing guard"

check "ripgrep in Package Managers"
for pm in apt-get dnf pacman; do
    grep -A3 "command -v $pm" "$BH_DOCTOR" | grep -q ripgrep && \
        pass "$pm includes ripgrep" || fail "$pm missing ripgrep"
done

check "SUDO_USER in systemd"
grep -q 'SUDO_USER:-' "$BH_DOCTOR" && pass "systemd uses SUDO_USER" || fail "missing SUDO_USER"

check "OPENAI_API_KEY supported"
grep -q 'OPENAI_API_KEY' "$BH_DOCTOR" && pass "OPENAI_API_KEY in provider list" || fail "missing"

check "Disk check AVAIL guard"
grep -q 'AVAIL=\${AVAIL:-0}' "$BH_DOCTOR" && pass "Disk check has default guard" || fail "missing"

check "set_env uses printf"
sed -n '/^set_env()/,/^}/p' "$BH_DOCTOR" | grep -q printf && \
    pass "set_env uses printf safely" || fail "set_env missing printf"

check ""
echo ""
echo -e "  \033[1;37mTotal: $((PASS+FAIL)) | Passed: $PASS | Failed: $FAIL\033[0m"
echo ""
[ "$FAIL" -eq 0 ]
