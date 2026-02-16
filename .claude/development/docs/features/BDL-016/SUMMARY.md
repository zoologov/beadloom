# BDL-016: Symbol Drift Detection E2E Fix

> **Status:** COMPLETE
> **Version:** 1.5.0 (post-release bugfix)
> **Date:** 2026-02-16
> **Bead:** beadloom-8j9 (closed)
> **UX Issues fixed:** #15, #18

---

## Problem

Symbol-level drift detection (added in BDL-015 BEAD-08) did not work end-to-end.
After adding a function with `# beadloom:domain=doc-sync`, `beadloom reindex && beadloom sync-check`
still reported all pairs as `[ok]`.

### Root cause

`incremental_reindex()` deleted `sync_state` and rebuilt it from scratch via
`_build_initial_sync_state()`, which always computed fresh `symbols_hash`.
Result: stored hash == computed hash → always "ok", drift never detected.

## Fix (3 changes)

1. **`_build_initial_sync_state()`** — accepts `preserved_symbols` parameter to keep old baselines
2. **`incremental_reindex()`** — snapshots `symbols_hash` BEFORE processing changed files, passes to rebuild
3. **`mark_synced()` / `mark_synced_by_ref()`** — recompute `symbols_hash` to reset baseline after doc update

## Files changed
- `src/beadloom/infrastructure/reindex.py` — `_build_initial_sync_state()` + `incremental_reindex()`
- `src/beadloom/doc_sync/engine.py` — `mark_synced()` + `mark_synced_by_ref()`
- `tests/test_symbol_drift.py` — 5 new tests (14 total)
- `README.md` / `README.ru.md` — Known Issues updated

## Tests
- 5 new tests added (1153 → 1158 total)
- E2E verified on beadloom itself: add function → reindex → sync-check shows `[stale]`

## Key commit

```
44f10c4 [BDL-016] fix: symbol drift detection now works end-to-end
```
