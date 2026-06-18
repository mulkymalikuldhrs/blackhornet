# Agent B05: Short-Term Memory (STM) Audit

## Files Audited
- `src/memory/short_term.py` — ShortTermMemory (ring buffer + TTL)
- `src/memory/long_term.py` — LongTermMemory (SQLite+FTS5)
- `src/memory/semantic.py` — SemanticMemory (n-gram+FTS5)
- `src/memory/episodic.py` — EpisodicMemory (timeline+parent chains)
- `src/memory/consolidation.py` — MemoryConsolidator (STM→LTM→Semantic pipeline)
- `src/memory/forgetting.py` — ForgettingMechanism (decay-based forgetting)
- `src/memory/system.py` — MemorySystem (unified service)
- `src/memory/cli.py` — MemoryCLI
- `src/memory/tests.py` — Existing test suite
- `src/memory/__init__.py` — Barrel exports

## Verifications

### 1. Ring buffer eviction — **BUG FOUND**
- **Issue:** `ShortTermMemory.add()` evicted the oldest entry **before** checking if the given key already existed. When updating an existing key on a full buffer, a valid entry was unnecessarily evicted.
- **Fix:** Moved the duplicate-key removal *before* the capacity check in `add()`. Now when a key exists, it is removed first, so the eviction only fires when truly needed.

### 2. TTL expiration accuracy — **PASS (edge case hardened)**
- `is_expired` uses `time.time() > created_at + ttl_seconds` — correct monotonic comparison.
- `_purge_expired` uses the same logic — consistent.
- Added `test_ttl_precision_does_not_expire_prematurely` to verify fresh entries with long TTLs are not falsely expired.

### 3. STM→LTM consolidation — **PASS (verified)**
- `MemoryConsolidator.consolidate_stm_to_ltm()` correctly filters entries older than 30 min, searches LTM for near-duplicates via FTS5, and merges or inserts accordingly.
- Added `test_stm_to_ltm_consolidation` that creates an STM entry, ages it past the 30-min cutoff, runs consolidation, and verifies the entry is in LTM and removed from STM.

### 4. Decay-based forgetting — **PASS (verified)**
- Formula: `access_count / hours_since_access * exp(-0.01 * hours_since_access)` — monotonic decay.
- Added `test_decay_score_decreases_with_age` (older entries get lower scores).
- Added `test_unused_entry_decays_to_zero` (entries with `access_count=0` decay to 0.0).
- Added `test_find_decayed_entries` (verifies `find_decayed_entries` discovers aged, unused entries below threshold).

### 5. Thread safety — **FIXED**
- **Issue:** `ShortTermMemory` had no lock; `OrderedDict` operations could race under concurrent access.
- **Fix:** Added `threading.RLock()` and wrapped all public methods and `_purge_expired` in `with self._lock:`.
- Uses `RLock` (reentrant) because `_purge_expired` is called from within other locked methods.
- Added `test_thread_safety` — 4 concurrent writer threads + 4 concurrent reader threads, verifies zero exceptions.

### 6. CLI stats keys mismatch — **FIXED**
- **Issue:** `cli.py` used `stm_stats.get('entry_count', 0)` but `ShortTermMemory.stats()` outputs `'current_entries'`.
- `cli.py` used `epi_stats.get('total_entries', 0)` but `EpisodicMemory.stats()` outputs `'total_episodes'`.
- Also TTL key mismatch: `'default_ttl'` vs `'default_ttl_seconds'`.
- **Fix:** Updated `cli.py` stats display to use correct keys.

## Changes Summary

| File | Change |
|------|--------|
| `src/memory/short_term.py` | Added `threading.RLock()`; wrapped all methods; reordered add() to check duplicate key before eviction |
| `src/memory/cli.py` | Fixed stats display keys for STM (`entry_count`→`current_entries`, `default_ttl`→`default_ttl_seconds`) and Episodic (`total_entries`→`total_episodes`) |
| `src/memory/tests.py` | Added 8 new tests: `test_update_without_unnecessary_eviction`, `test_ttl_precision_does_not_expire_prematurely`, `test_thread_safety`, `test_stm_to_ltm_consolidation`, `test_decay_score_decreases_with_age`, `test_unused_entry_decays_to_zero`, `test_find_decayed_entries` |

## Test Results
**58/58 tests passing** (was 51/51 before changes — all legacy tests untouched and passing).
