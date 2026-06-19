#!/usr/bin/env python3
"""
BLACKHORNET BRIDGE INTEGRATION - AUTO EXECUTE
Integrates HyperGate + MnemosyneBridge into blackhornet.py
"""

from pathlib import Path

BH_HOME = Path("/sdcard/dhaherlabs/blackhornet-worktree")
BLACKHORNET_PY = BH_HOME / "blackhornet.py"

print("=" * 70)
print("BLACKHORNET BRIDGE INTEGRATION - AUTO EXECUTE")
print("=" * 70)

# Read blackhornet.py
if not BLACKHORNET_PY.exists():
    print("ERROR: blackhornet.py not found!")
    exit(1)

with open(BLACKHORNET_PY, 'r') as f:
    lines = f.readlines()

# Find where to add imports (after existing src imports)
import_idx = None
for i, line in enumerate(lines):
    if 'from src.' in line and 'import' in line:
        import_idx = i + 1

if not import_idx:
    print("Could not find import section, adding at line 30")
    import_idx = 30

# Insert bridge imports
bridge_imports = [
    "\n",
    "# ── BRIDGE INTEGRATION: HyperGate & Mnemosyne ────────────────────\n",
    "from src.hypergate import HyperGate\n",
    "from src.mnemosyne_bridge import MnemosyneBridge\n",
    "# ── END BRIDGE INTEGRATION ───────────────────────────────────────\n",
    "\n",
]

lines[import_idx:import_idx] = bridge_imports
print(f"✅ Added bridge imports at line {import_idx}")

# Find main() or initialization section
init_idx = None
for i, line in enumerate(lines):
    if 'def main()' in line or 'if __name__ ==' in line:
        # Find first line inside the function/block
        for j in range(i+1, min(i+15, len(lines))):
            if lines[j].strip() and not lines[j].strip().startswith('#') and not lines[j].strip().startswith('"""'):
                init_idx = j
                break
        if init_idx:
            break

if not init_idx:
    print("WARNING: Could not find initialization point, adding at end")
    init_idx = len(lines) - 1

# Insert initialization code
bridge_init = [
    "    # Initialize Bridge Infrastructure\n",
    "    print('🖤 HyperGate: Initializing LLM Gateway...')\n",
    "    hypergate = HyperGate()\n",
    "    hypergate.start()\n",
    "    print(f'   ✅ HyperGate active on port {hypergate.port}')\n",
    "\n",
    "    print('🧠 Mnemosyne Bridge: Initializing Swarm Memory...')\n",
    "    mnemosyne = MnemosyneBridge()\n",
    "    mnemosyne.start()\n",
    "    print(f'   ✅ Mnemosyne Bridge active on port {mnemosyne.port}')\n",
    "\n",
]

lines[init_idx:init_idx] = bridge_init
print(f"✅ Added bridge initialization at line {init_idx}")

# Write back
with open(BLACKHORNET_PY, 'w') as f:
    f.writelines(lines)

print(f"\n✅ INTEGRATION COMPLETE: {BLACKHORNET_PY}")
print("\nNext steps:")
print("1. Start JeumpaLLM: cd /sdcard/dhaherlabs/JeumpaLLM && npm start")
print("2. Start Mnemosyne: cd /sdcard/dhaherlabs/repositories/mnemosyne-worktree && npm run dev")
print("3. Run BlackHornet: python3 blackhornet.py")