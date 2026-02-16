# PLAN: BDL-018 — Doc-Sync Honest Detection

> **Status:** Draft
> **Date:** 2026-02-16
> **Beads:** 5 (4 tasks + 1 E2E validation)
> **Waves:** 3

---

## DAG

```
Wave 1 (parallel — no dependencies):
├── BEAD-01 (P0): Preserve sync baseline across full reindex
│   Fix _snapshot_sync_baselines + pass to reindex()
│   Fix _compute_symbols_hash to include file_path
│   Fix old_symbols or None → if is not None
│
└── BEAD-02 (P0): Source-directory coverage check
    New check_source_coverage() in engine.py
    Detect untracked files via nodes.source

Wave 2 (depends on BEAD-01 + BEAD-02):
└── BEAD-03 (P1): Module-name coverage check + integration
    New check_doc_coverage() in engine.py
    Integrate all checks into check_sync()
    Enhance doctor with new checks
    Update CLI output

Wave 3 (depends on BEAD-03):
└── BEAD-04 (P1): E2E validation on beadloom itself
    Run fixed sync-check on beadloom → must detect >= 6 stale
    Acceptance test for the entire epic
```

---

## Bead Details

### BEAD-01: Preserve sync baseline + fix hash computation (P0)

**Type:** bug fix
**Files:** `reindex.py`, `engine.py`
**Effort:** M

**Tasks:**
1. Add `_snapshot_sync_baselines(conn)` helper in `reindex.py` — snapshots `{ref_id: symbols_hash}` from `sync_state` before `_drop_all_tables()`
2. Call it in `reindex()` BEFORE `_drop_all_tables()` (line 554)
3. Pass result to `_build_initial_sync_state(conn, preserved_symbols=snapshot)` (line 628)
4. Fix `old_symbols or None` → `old_symbols if old_symbols is not None else None` in incremental reindex (line 1082)
5. Update `_compute_symbols_hash()` in `engine.py` to include `file_path` in hash string: `"{file_path}:{symbol_name}:{kind}"`
6. Tests:
   - `_snapshot_sync_baselines` returns data, handles missing table
   - Full reindex preserves baseline → sync-check detects drift
   - `old_symbols = {}` does not trigger fresh baseline
   - Hash changes when new file added to same ref_id

### BEAD-02: Source-directory coverage check (P0)

**Type:** feature
**Files:** `engine.py`
**Effort:** M

**Tasks:**
1. New function `check_source_coverage(conn, project_root)` in `engine.py`
2. Query `nodes` for nodes with `source` ending in `/` (directories)
3. Scan actual `*.py` files on disk in each source dir (exclude `__init__.py`, `conftest.py`, `__main__.py`)
4. Query `sync_state` for `code_path` entries with matching `ref_id`
5. Report files on disk NOT in sync_state as "untracked"
6. Tests:
   - Node with source dir, all files tracked → empty result
   - Node with new untracked file → detected
   - Exclusions work (`__init__.py` ignored)
   - Node with file source (not dir) → skipped
   - No nodes → empty result

### BEAD-03: Module-name coverage + integration (P1)

**Type:** feature
**Files:** `engine.py`, `doctor.py`, `cli.py`
**Effort:** M
**Depends on:** BEAD-01, BEAD-02

**Tasks:**
1. New function `check_doc_coverage(conn, project_root)` in `engine.py`
   - For each node: get source dir, list `*.py` files (stems), read linked doc
   - Check if doc content contains each module name
   - Return `{ref_id, doc_path, missing_modules}`
2. Integrate into `check_sync()`:
   - After hash checks, run `check_source_coverage()` + `check_doc_coverage()`
   - Mark as stale if untracked files or missing modules detected
3. Add `_check_source_coverage()` to doctor checks
4. Enhance CLI sync-check output: show missing modules in detail
5. Tests:
   - Doc mentions all modules → ok
   - Doc missing module name → stale
   - Integration: full flow with all three check layers

### BEAD-04: E2E validation on beadloom (P1)

**Type:** test
**Files:** `tests/test_e2e_sync_honest.py`
**Effort:** S
**Depends on:** BEAD-03

**Tasks:**
1. E2E test: run `beadloom reindex && beadloom sync-check` on beadloom itself
2. Assert >= 6 stale docs detected (from BDL-017 audit)
3. Assert specific stale refs: `context-oracle`, `infrastructure`, `onboarding`, `mcp-server`
4. Assert existing "ok" docs (e.g., `doc-sync`) remain ok
5. Validate no regressions in existing test suite (1362+ tests)

---

## Wave Execution Plan

### Wave 1: BEAD-01 + BEAD-02 (parallel)
- Independent: BEAD-01 modifies `reindex.py` + `engine.py:_compute_symbols_hash`; BEAD-02 adds new function to `engine.py`
- No file conflicts: BEAD-01 changes existing function at top of file; BEAD-02 adds new function at bottom
- **Agents:** 2 parallel dev agents

### Wave 2: BEAD-03
- Depends on both BEAD-01 and BEAD-02 (integrates their outputs)
- Modifies `engine.py` (add `check_doc_coverage`, integrate into `check_sync`), `doctor.py`, `cli.py`
- **Agent:** 1 dev agent

### Wave 3: BEAD-04
- Depends on BEAD-03 (needs all fixes in place)
- Creates new test file, validates end-to-end
- **Agent:** 1 test agent

---

## Critical Path

```
BEAD-01 ─┐
          ├── BEAD-03 ── BEAD-04
BEAD-02 ─┘
```

**Estimated total:** 4 beads, 3 waves
