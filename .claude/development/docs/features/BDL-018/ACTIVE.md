# ACTIVE: BDL-018 — Doc-Sync Honest Detection

> **Last updated:** 2026-02-16
> **Phase:** COMPLETED

---

## Summary

All 4 beads completed across 3 waves. Doc-sync now honestly detects staleness.

## Results

| Wave | Beads | Status | New Tests |
|------|-------|--------|-----------|
| Wave 1 | BEAD-01 (baseline fix), BEAD-02 (source coverage) | **Done** | 23 |
| Wave 2 | BEAD-03 (module coverage + integration) | **Done** | 15 |
| Wave 3 | BEAD-04 (E2E validation) | **Done** | 5 |

**Total new tests:** 43 | **Full suite:** 1404 passed

## E2E Validation on Beadloom

- `beadloom sync-check`: **35 stale entries** detected (target: >= 6)
- `beadloom doctor`: Shows untracked source files (why.py, doctor.py, watcher.py, app.py)
- All key domains flagged: context-oracle, doc-sync, graph, infrastructure, onboarding, mcp-server

## Files Changed

| File | Changes |
|------|---------|
| `src/beadloom/doc_sync/engine.py` | Fixed `_compute_symbols_hash()`, added `check_source_coverage()`, `check_doc_coverage()`, integrated into `check_sync()` |
| `src/beadloom/infrastructure/reindex.py` | Added `_snapshot_sync_baselines()`, fixed baseline preservation, fixed `or None` bug |
| `src/beadloom/infrastructure/doctor.py` | Added `_check_source_coverage()` check |
| `src/beadloom/services/cli.py` | Enhanced sync-check output with reason/details |
| `tests/test_source_coverage.py` | 15 new tests |
| `tests/test_doc_coverage.py` | 11 new tests |
| `tests/test_e2e_sync_honest.py` | 5 new E2E tests |
| `tests/test_sync_engine.py` | 6 new tests (hash + integration) |
| `tests/test_reindex.py` | 5 new tests (baseline + snapshot) |
