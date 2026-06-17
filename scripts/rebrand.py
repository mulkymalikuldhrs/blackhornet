#!/usr/bin/env python3
"""Rebrand Hermes → BlackHornet across the codebase.

Usage:
    python3 scripts/rebrand.py --dry-run    # preview only
    python3 scripts/rebrand.py              # apply changes
    python3 scripts/rebrand.py --files      # rename files only
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import sys

BH = "/sdcard/dhaherlabs/blackhornet-worktree"


def file_replacements() -> list[tuple[str, str]]:
    """(old_path_relative, new_path_relative)"""
    return [
        ("src/hermes_quant.py", "src/bh_quant.py"),
        ("src/integrations/hermes_bridge.py", "src/integrations/bh_quant_bridge.py"),
        ("hermes.sh", "bh.sh"),
        ("deploy/hermes-hive.service", "deploy/bh-hive.service"),
    ]


def content_replacements() -> list[tuple[str, str, str]]:
    """(file_glob, old_text, new_text) pairs.
    Empty glob means all .py files.
    """
    py = "*.py"
    sh = "*.sh"
    md = "*.md"
    cfg = "*.{yml,yaml,env,sql,json}"
    all_scripts = "*.{sh,bash,zsh}"

    repls: list[tuple[str, str, str]] = []

    def r(file_glob: str, old: str, new: str):
        repls.append((file_glob, old, new))

    # ── Class names ────────────────────────────────────────────
    r(py, "class HermesWatchdog", "class Watchdog")
    r(py, "HermesQuantBridge", "BlackHornetQuantBridge")

    # ── Function names (only BH-internal) ───────────────────────
    r(py, "def is_hermes_running", "def is_bh_running")
    r(py, "def get_hermes_pid", "def get_bh_pid")
    r(py, "def start_hermes", "def start_process")
    r(py, "def _ensure_hermes_on_path", "def _ensure_bh_on_path")
    r(py, "def _import_hermes_module", "def _import_bh_module")

    # ── Method calls ────────────────────────────────────────────
    r(py, "self.is_hermes_running()", "self.is_bh_running()")
    r(py, "self.get_hermes_pid()", "self.get_bh_pid()")
    r(py, "self.start_hermes()", "self.start_process()")

    # ── Variable/attribute names ────────────────────────────────
    r(py, "self.hermes_pid", "self.bh_pid")
    r(py, "hermes_str", "bh_str")
    r(py, "self._hermes_home", "self._bh_home")
    r(py, "= hermes", "= bh")  # variable assignment like hermes = blackhornet()
    r(py, "hermes.signal_handler", "bh.signal_handler")
    r(py, "hermes.start()", "bh.start()")

    # ── Dict keys with just 'hermes' ────────────────────────────
    r(py, "'hermes':", "'bh':")
    r(py, '"hermes":', '"bh":')
    r(py, "item['hermes']", "item['bh']")
    r(py, 'item["hermes"]', 'item["bh"]')
    r(py, '"**Hermes**"', '"**BH**"')

    # ── Path fallbacks with .hermes ──────────────────────────────
    r(py, '".hermes"', '".bh"')
    r(py, "'.hermes'", "'.bh'")
    r(py, '"hermes.pid"', '"bh.pid"')
    r(py, "'hermes.pid'", "'bh.pid'")

    # ── Comments ─────────────────────────────────────────────────
    r(py, "# Start Hermes", "# Start BH")

    # ── Constants ───────────────────────────────────────────────
    r(py, "HERMES_SCRIPT", "BH_SCRIPT")
    r(py, "HERMES_HOME", "BH_HOME")
    r(py, "_HERMES_SRC", "_BH_SRC")
    r(py, "HERMES_AGENT_DIR", "BH_AGENT_DIR")
    r(py, "HERMES_MEMORY_DIR", "BH_MEMORY_DIR")
    r(py, "HERMES_SESSION_DIR", "BH_SESSION_DIR")
    r(py, "HERMES_PYTHON", "BH_PYTHON")

    # ── Dict keys ───────────────────────────────────────────────
    r(py, '"hermes_quant"', '"bh_quant"')
    r(py, "'hermes_quant'", "'bh_quant'")
    r(py, '"hermes_alive"', '"bh_alive"')
    r(py, '"hermes_pid"', '"bh_pid"')

    # ── String / docstring replacements ─────────────────────────
    # "HERMES QUANT OPERATING SYSTEM" in docstrings and logs
    r(py, "HERMES QUANT OPERATING SYSTEM", "BLACKHORNET QUANT OPERATING SYSTEM")
    # "Hermes Immortal Daemon"
    r(py, "HERMES IMMORTAL DAEMON", "BLACKHORNET IMMORTAL DAEMON")
    r(py, "Hermes Immortal Daemon", "BlackHornet Immortal Daemon")
    # "Hermes Swarm Protocol"
    r(py, "HERMES SWARM PROTOCOL", "BLACKHORNET SWARM PROTOCOL")

    # Log/error messages
    r(py, "HermesQuant", "BlackHornetQuant")
    r(py, "Hermes Process", "BH Process")
    r(py, "Hermes status", "BH status")
    r(py, "Check Hermes", "Check BH")
    r(py, "Hermes process", "BH process")
    r(py, "Hermes not running", "BH not running")
    r(py, "Cannot start Hermes", "Cannot start BH")
    r(py, "Hermes stable", "BH stable")
    r(py, "Hermes DIED", "BH DIED")
    r(py, "Hermes restarted", "BH restarted")
    r(py, "Hermes failed to start", "BH failed to start")
    r(py, "Hermes Script:", "BH Script:")
    r(py, "Hermes Start:", "BH Start:")
    r(py, "Hermes started", "BH started")

    # hermes_quant in strings (log filenames, db paths)
    r(py, "hermes_quant", "bh_quant")

    # Circuit breaker name
    r(py, '"hermes"]', '"bh"]')
    r(py, "'hermes']", "'bh']")

    # Swarm Protocol description
    r(py, '"Hermes Swarm Protocol"', '"BH Swarm Protocol"')
    r(py, "'Hermes Swarm Protocol'", "'BH Swarm Protocol'")

    # "Say HERMES ONLINE"
    r(py, '"HERMES ONLINE"', '"BH ONLINE"')
    r(py, "'HERMES ONLINE'", "'BH ONLINE'")

    # Watchdog class ref
    r(py, "HermesWatchdog()", "Watchdog()")

    # Function calls (where definition was renamed)
    r(py, "_ensure_hermes_on_path()", "_ensure_bh_on_path()")
    r(py, "_import_hermes_module(", "_import_bh_module(")
    r(py, "Hermes Agent", "BlackHornet Agent")
    r(py, "Hermes MemoryProvider", "BlackHornet MemoryProvider")

    # ── Import statements ───────────────────────────────────────
    # from src.integrations.hermes_bridge import HermesQuantBridge
    r(py, "from src.integrations.hermes_bridge import HermesQuantBridge",
         "from src.integrations.bh_quant_bridge import BlackHornetQuantBridge")

    # ── Route paths ─────────────────────────────────────────────
    r(py, '"/hermes"', '"/bh"')
    r(py, "'/hermes'", "'/bh'")
    r(py, "route.*hermes", "route.*bh")
    r(py, "ecosystem_hermes_error", "ecosystem_bh_error")
    r(py, '"hermes":', '"bh":')

    # ── Graphviz / DOT ──────────────────────────────────────────
    # (no changes needed, already graphviz-compatible)

    # ── Shell script patterns ───────────────────────────────────
    r(sh, "HERMES_SCRIPT", "BH_SCRIPT")
    r(sh, "HERMES_HOME", "BH_HOME")
    r(sh, "HERMES_PYTHON", "BH_PYTHON")
    r(sh, "HERMES_AGENT_DIR", "BH_AGENT_DIR")
    r(sh, "hermes_quant.py", "bh_quant.py")
    r(sh, "hermes_quant", "bh_quant")
    r(sh, "hermes.sh", "bh.sh")
    r(sh, "hermes.pid", "bh.pid")
    r(sh, ".hermes/", ".bh/")
    r(sh, 'say "HERMES', 'say "BH')
    r(sh, "# HERMES", "# BH")
    r(sh, "HERMES HIVE", "BH HIVE")
    r(sh, "Hermes Hive", "BH Hive")
    r(sh, "HERMES QUANT", "BH QUANT")
    r(sh, "Hermes Agent", "BlackHornet Agent")
    r(sh, "[HERMES]", "[BH]")

    # ── Config / env patterns ───────────────────────────────────
    r(cfg, "HERMES_HOME", "BH_HOME")
    r(cfg, "Hermes Hive", "BH Hive")
    r(cfg, "hermes-hive", "bh-hive")
    r(cfg, "hermes-ecosystem", "bh-ecosystem")
    r(cfg, "hermes_quant.py", "bh_quant.py")

    # ── SQL patterns ────────────────────────────────────────────
    r("*.sql", "HERMES QUANT OS", "BH QUANT OS")

    # ── Markdown docs ───────────────────────────────────────────
    r(md, "Hermes", "BlackHornet")
    r(md, "hermes", "blackhornet")

    # ── Dockerfile ──────────────────────────────────────────────
    r("Dockerfile", "Hermes Hive", "BH Hive")
    r("Dockerfile", "/hermes", "/blackhornet")
    r("Dockerfile", "setup-hermes.sh", "setup-bh.sh")
    r("Dockerfile", "HERMES_HOME", "BH_HOME")

    # ── CI / GitHub ─────────────────────────────────────────────
    r("*.yml", "Hermes Hive", "BH Hive")

    # ── Service files ───────────────────────────────────────────
    r("*.service", "Hermes Hive", "BH Hive")

    return repls


def should_skip(path: str) -> bool:
    """Skip files that reference external Hermes Agent framework."""
    skip_patterns = [
        "src/plugins/memory/bh_memory/",
        "site-packages/",
        ".git/",
        "__pycache__/",
        "node_modules/",
        ".env/",
        "venv/",
        ".venv/",
        "scripts/rebrand.py",  # ourselves
    ]
    for pat in skip_patterns:
        if pat in path:
            return True
    return False


def is_external_hermes_ref(line: str) -> bool:
    """Check if this line refers to the EXTERNAL Hermes Agent, not BH."""
    external_patterns = [
        "from hermes_constants import",
        "Nous Research Hermes",
        "github.com/nousresearch/hermes",
        "nousresearch/hermes",
    ]
    for pat in external_patterns:
        if pat in line:
            return True
    return False


def apply_content_replacements(dry_run: bool = True) -> int:
    """Apply all content replacements to matching files."""
    repls = content_replacements()
    changed = 0

    # Build file list with one walk
    file_map: dict[str, list[str]] = {}
    for root, dirs, fnames in os.walk(BH):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("__pycache__", "node_modules", "venv", ".venv", "site-packages")]
        for fname in fnames:
            fpath = os.path.join(root, fname)
            if should_skip(fpath):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in (".py", ".sh", ".md", ".yml", ".yaml", ".sql", ".json"):
                file_map.setdefault(ext, []).append(fpath)
            if fname in ("Dockerfile", ".env.example", ".env"):
                file_map.setdefault("cfg", []).append(fpath)
            if fname.endswith(".service"):
                file_map.setdefault("svc", []).append(fpath)

    # Get all unique files that match any glob
    all_files: set[str] = set()
    for file_glob, _, _ in repls:
        if file_glob in ("*.py", ""):
            all_files.update(file_map.get(".py", []))
        elif file_glob == "*.sh":
            all_files.update(file_map.get(".sh", []))
        elif file_glob == "*.md":
            all_files.update(file_map.get(".md", []))
        elif file_glob in ("*.{yml,yaml,env,sql,json}",):
            for ext in (".yml", ".yaml", ".sql", ".json"):
                all_files.update(file_map.get(ext, []))
            all_files.update(file_map.get("cfg", []))
        elif file_glob == "*.sql":
            all_files.update(file_map.get(".sql", []))
        elif file_glob in ("Dockerfile",):
            all_files.update(file_map.get("cfg", []))
        elif file_glob == "*.service":
            all_files.update(file_map.get("svc", []))
        elif file_glob == "*.yml":
            all_files.update(file_map.get(".yml", []))
            all_files.update(file_map.get(".yaml", []))

    # Process each file against ALL applicable replacements
    for fpath in sorted(all_files):
        rel = os.path.relpath(fpath, BH)
        file_changed = False
        total_count = 0
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        if is_external_hermes_ref(content):
            continue

        for file_glob, old_text, new_text in repls:
            if old_text not in content:
                continue
            file_ext = os.path.splitext(fpath)[1].lower()
            fname = os.path.basename(fpath)
            matches_glob = False
            if file_glob in ("*.py", "") and file_ext == ".py":
                matches_glob = True
            elif file_glob == "*.sh" and file_ext == ".sh":
                matches_glob = True
            elif file_glob == "*.md" and file_ext == ".md":
                matches_glob = True
            elif file_glob == "*.{yml,yaml,env,sql,json}" and \
                 file_ext in (".yml", ".yaml", ".sql", ".json", ".env"):
                matches_glob = True
            elif file_glob in ("Dockerfile",) and fname == "Dockerfile":
                matches_glob = True
            elif file_glob == "*.service" and fname.endswith(".service"):
                matches_glob = True
            elif file_glob == "*.sql" and file_ext == ".sql":
                matches_glob = True
            elif file_glob == "*.yml" and file_ext in (".yml", ".yaml"):
                matches_glob = True

            if not matches_glob:
                continue

            count = content.count(old_text)
            content = content.replace(old_text, new_text)
            if count > 0:
                total_count += count
                file_changed = True
                if dry_run:
                    print(f"  [{count}x] {rel}: {old_text!r} -> {new_text!r}")

        if file_changed and not dry_run:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  UPDATED [{total_count}x] {rel}")
            changed += 1
        elif file_changed and dry_run:
            changed += 1

    return changed

    return changed


def _replace_in_file(fpath: str, old_text: str, new_text: str,
                     dry_run: bool) -> int:
    """Replace old_text with new_text in file. Returns replacement count."""
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return 0

    if old_text not in content:
        return 0

    # Skip if this file only references external Hermes
    if is_external_hermes_ref(old_text) or is_external_hermes_ref(content):
        return 0

    new_content = content.replace(old_text, new_text)
    if new_content == content:
        return 0

    rel = os.path.relpath(fpath, BH)
    count = content.count(old_text)
    if dry_run:
        print(f"  [{count}x] {rel}: {old_text!r} -> {new_text!r}")
        return count

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"  REPLACED [{count}x] {rel}")
    return count


def rename_files(dry_run: bool = True) -> int:
    """Rename files listed in file_replacements()."""
    renamed = 0
    for old_rel, new_rel in file_replacements():
        old_path = os.path.join(BH, old_rel)
        new_path = os.path.join(BH, new_rel)
        if not os.path.exists(old_path):
            print(f"  SKIP (not found): {old_rel}")
            continue
        if dry_run:
            print(f"  RENAME: {old_rel} -> {new_rel}")
            renamed += 1
        else:
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.move(old_path, new_path)
            print(f"  RENAMED: {old_rel} -> {new_rel}")
            renamed += 1
    return renamed


def update_imports(dry_run: bool = True) -> int:
    """Update import statements in Python files after file renames."""
    import_patterns = [
        ("import src.hermes_quant", "import src.bh_quant"),
        ("from src.hermes_quant", "from src.bh_quant"),
        ("src.hermes_quant.", "src.bh_quant."),
        ("import hermes_quant", "import bh_quant"),
        ("from hermes_quant", "from bh_quant"),
        ("from src.integrations.hermes_bridge", "from src.integrations.bh_quant_bridge"),
        ("import hermes_bridge", "import bh_quant_bridge"),
        ("from hermes_bridge", "from bh_quant_bridge"),
    ]

    updated = 0
    for root, dirs, fnames in os.walk(os.path.join(BH, "src")):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("__pycache__", "site-packages")]
        for fname in fnames:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            if should_skip(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue

            original = content
            for old, new in import_patterns:
                content = content.replace(old, new)

            if content != original:
                rel = os.path.relpath(fpath, BH)
                count = sum(1 for o, _ in import_patterns if o in original)
                if dry_run:
                    print(f"  [{count}x imports] {rel}")
                    updated += 1
                else:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"  IMPORT FIXED [{count}x] {rel}")
                    updated += 1

    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Rebrand Hermes -> BlackHornet across codebase"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without applying")
    parser.add_argument("--files", action="store_true",
                        help="Only rename files, skip content")
    args = parser.parse_args()

    dry_run = args.dry_run
    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"═══ Rebrand: Hermes → BlackHornet [{mode}] ═══")

    total = 0

    if not args.files:
        print("\n--- Content replacements ---")
        total += apply_content_replacements(dry_run)

    print("\n--- File renames ---")
    total += rename_files(dry_run)

    if not args.files:
        print("\n--- Import updates ---")
        total += update_imports(dry_run)

    print(f"\n═══ Total changes: {total} [{mode}] ═══")
    if dry_run:
        print("Run without --dry-run to apply.")


if __name__ == "__main__":
    main()
