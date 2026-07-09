# 🖤 BLACKHORNET Daemon Audit — 2026-07-10

**Auditor:** Hermes (dhaherautobot) · **Scope:** `blackhornet.py` runtime viability
**Verdict:** ⛔ DAEMON WAS 100% DEAD ON ARRIVAL — now compiles + imports + runs past launch.

---

## FATAL BUGS FOUND (blocked all execution)

### BUG 1 — `IndentationError` — daemon never compiled
- **Location:** `blackhornet.py:239` `async def async_deploy_nest`
- **Cause:** method body was at `def`-indent level (not indented), and the method
  was orphaned *after* `deploy_nest()`'s `return True`. Python saw a function def
  with no body → `IndentationError: expected an indented block`.
- **Impact:** `python blackhornet.py` crashed at parse time. Nothing ran. Ever.
- **Fix:** Dedented `async_deploy_nest` to proper class-method level (method body
  indented 4 spaces). Now `python -m py_compile` passes.

### BUG 2 — `AttributeError: 'HyperGate' object has no attribute 'start'`
- **Location:** `main()` lines 594-602
- **Cause:** `main()` called `hypergate.start()` and `mnemosyne.start()` before
  argparse. Neither `HyperGate` nor `MnemosyneBridge` define `start()`
  (they use `complete()`/`status()`/`stop()`). Crashed on first line of `main()`.
- **Impact:** Even if Bug 1 were fixed, daemon died at `main()` entry before the
  nest loop ever started.
- **Fix:** Removed the bogus pre-argparse bridge init. `start_hornets()` already
  initializes HyperGate/MnemosyneBridge correctly inside the nest loop (with
  try/except guards).

---

## POST-FIX VERIFICATION (evidence)
```
$ python -m py_compile blackhornet.py        → exit 0 (compiles)
$ python -c "import blackhornet"             → no error (imports clean)
$ python blackhornet.py --sovereign          → past launch, into deploy_nest()
                                                  (clones repos, was network-bound)
$ hasattr(nest,'async_deploy_nest')          → True
$ hasattr(nest,'deploy_nest')                → True
```

---

## SECONDARY FINDINGS (not runtime-blocking, flagged)

| # | Finding | Severity | Note |
|---|---------|----------|------|
| 3 | `start_hornets()` subprocess.Popen to dead paths | MED | Launches `node index.js` (JeumpaLLM), `npm start` (mnemosyne), `blackhornet-doctor` — these depend on repos cloned into `~/blackhornet-nest`. If clone fails, services silently no-op (guarded by `if exists`). OK-by-design. |
| 4 | `deploy_nest` network-bound, no timeout on first clone of 7 repos | LOW | Each clone limited to 60s; slow mirrors cause long boot. Acceptable for daemon, not for CI. |
| 5 | `self_push` force-pushes to `codeberg`/`gitlab` `main` | MED | Immortal auto-push could clobber remote history. Review before enabling `--immortal` in prod. |
| 6 | Prior audit (AUDIT_SUMMARY.md) was cosmetic only | INFO | Fixed quoting/type-hints/bare-except but MISSED the two fatal parse/launch bugs above. |
| 7 | `bh-core/index.js` is a 7-line stub | INFO | Unrelated toy; not the real daemon. |

---

## RECOMMENDATION
1. ✅ Both fatal bugs fixed — daemon now viable.
2. Before `--immortal` in production: gate `self_push` behind a config flag (avoid
   force-push to main).
3. Add a CI smoke test: `python -m py_compile blackhornet.py && python blackhornet.py
   --status` so this class of "dead on arrival" regression can't recur silently.
4. `main()` should not do network I/O (clone) for `--status`/`--health` — those
   commands don't need the full nest. Split `deploy_nest()` out of the status path.
