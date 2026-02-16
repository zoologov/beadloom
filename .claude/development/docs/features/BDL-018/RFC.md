# RFC: BDL-018 — Doc-Sync Honest Detection

> **Status:** Approved
> **Date:** 2026-02-16
> **PRD:** BDL-018/PRD.md (Approved)

---

## 1. Architecture Decision

### Approach: Three-layer fix

Fix the existing mechanism at three levels rather than building a new system:

1. **Layer 1 (Bug fixes):** Preserve baseline across full reindex, fix `old_symbols or None`, include file paths in hash
2. **Layer 2 (Source-aware tracking):** Use node `source:` field from graph YAML to detect ALL files in a node's directory, not just annotated ones
3. **Layer 3 (Coverage check):** Verify doc content mentions module names from source directory

### Why NOT a new system

- The existing `sync_state` + `symbols_hash` infrastructure is sound
- `check_sync()` and `_check_symbol_drift()` algorithms are correct — they just receive broken baselines
- Fixing 5 specific bugs is cheaper and less risky than a rewrite

---

## 2. Technical Design

### Fix 1: Preserve baseline across full reindex

**File:** `src/beadloom/infrastructure/reindex.py`

**Current (broken):**
```python
# Line 554-555: drops ALL tables including sync_state
_drop_all_tables(conn)
create_schema(conn)
# ... reindex ...
# Line 628: fresh baseline (no preserved_symbols)
_build_initial_sync_state(conn)
```

**Proposed:**
```python
# BEFORE drop: snapshot symbols_hash from sync_state
old_symbols = _snapshot_sync_baselines(conn)

_drop_all_tables(conn)
create_schema(conn)
# ... reindex ...
# Pass snapshot to preserve baselines
_build_initial_sync_state(conn, preserved_symbols=old_symbols)
```

New helper:
```python
def _snapshot_sync_baselines(conn: sqlite3.Connection) -> dict[str, str]:
    """Snapshot symbols_hash from sync_state before table drop.

    Returns {ref_id: symbols_hash} for all entries with non-empty hash.
    Returns empty dict if sync_state doesn't exist yet.
    """
    try:
        rows = conn.execute(
            "SELECT ref_id, symbols_hash FROM sync_state "
            "WHERE symbols_hash IS NOT NULL AND symbols_hash != ''"
        ).fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception:  # Table doesn't exist on first run
        return {}
```

### Fix 2: Fix `old_symbols or None` bug

**File:** `src/beadloom/infrastructure/reindex.py`, line 1082

**Current (broken):**
```python
_build_initial_sync_state(conn, preserved_symbols=old_symbols or None)
```

**Proposed:**
```python
_build_initial_sync_state(
    conn,
    preserved_symbols=old_symbols if old_symbols is not None else None,
)
```

### Fix 3: Include file paths in symbols_hash

**File:** `src/beadloom/doc_sync/engine.py`, lines 18-32

**Current (incomplete):**
```python
data = "|".join(f"{r['symbol_name']}:{r['kind']}" for r in rows)
```

**Proposed:**
```python
data = "|".join(
    f"{r['file_path']}:{r['symbol_name']}:{r['kind']}" for r in rows
)
```

This ensures that adding a new file with new symbols in the same domain changes the hash, even if the symbol names happen to match existing ones.

### Fix 4: Source-directory-aware file tracking

**File:** `src/beadloom/doc_sync/engine.py`

New function to detect untracked code files:

```python
def check_source_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if all source files in a node's directory are tracked in sync_state.

    For each node with a `source` directory, compares actual Python files
    on disk against code_paths tracked in sync_state for that ref_id.

    Returns list of {ref_id, doc_path, untracked_files} for nodes with gaps.
    """
```

**Algorithm:**
1. Query `nodes` table for all nodes with `source` ending in `/` (directories)
2. For each node, scan actual `*.py` files on disk in that directory
3. Query `sync_state` for `code_path` entries with matching `ref_id`
4. Report files on disk NOT in sync_state as "untracked"
5. If untracked files exist → the doc is considered stale

**Integration into `check_sync()`:**
After existing hash-based checks, call `check_source_coverage()` and merge results — any node with untracked files gets status "stale".

### Fix 5: Module-name coverage check (Level 1 semantic)

**File:** `src/beadloom/doc_sync/engine.py`

New function:

```python
def check_doc_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if documentation mentions module names from the node's source directory.

    Level 1: exact string match of module filename (without .py) in doc content.
    Level 2: check public symbol names (functions, classes) — reported as warnings.

    Returns list of {ref_id, doc_path, missing_modules, missing_symbols}.
    """
```

**Algorithm:**
1. For each node, get source directory from `nodes.source`
2. List `*.py` files (excluding `__init__.py`) in that directory
3. Read the linked doc content
4. Check if doc content contains each module name (stem without `.py`)
5. Missing modules → mark as stale
6. (Level 2) Check if public symbols (non-`_` prefixed) from `code_symbols` are mentioned → report as warnings in doctor

---

## 3. Integration Points

### sync-check CLI

No new flags needed. The existing `beadloom sync-check` will:
1. Run hash-based checks (existing)
2. Run source-coverage check (new — Fix 4)
3. Run doc-coverage check (new — Fix 5)
4. Report combined results

### doctor CLI

`_check_symbol_drift()` will work correctly because baselines are now preserved (Fix 1). Additionally:
- New check: `_check_source_coverage()` — warns about untracked files
- Enhanced `_check_symbol_drift()` output: shows which specific modules are missing

### mark_synced / sync-update

No changes needed. `mark_synced()` already recomputes symbols_hash with `_compute_symbols_hash()`. Fix 3 changes what's hashed, but the function signature is unchanged.

---

## 4. Data Flow (After Fix)

```
beadloom reindex (full)
  |-> _snapshot_sync_baselines(conn)   <-- NEW: save old hashes
  |-> _drop_all_tables()
  |-> load graph, index docs, index code
  |-> _build_initial_sync_state(conn, preserved_symbols=old_hashes)  <-- FIXED
       |-> build_sync_state()
       |-> INSERT sync_state with OLD symbols_hash  <-- drift detectable

beadloom sync-check
  |-> for each sync_state row:
       |-> file hash comparison (existing)
       |-> symbols_hash comparison (existing, now with file paths)
  |-> check_source_coverage()           <-- NEW: find untracked files
  |-> check_doc_coverage()              <-- NEW: module name mentions
  |-> combined results → stale if any check fails
```

---

## 5. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Fix 3 changes hash format → all existing sync_state entries become "stale" | Accept: first run after upgrade will flag drift. `beadloom sync-update` resets baseline. In practice this is correct — docs ARE stale. |
| Source coverage false positives on utility files | Exclude `__init__.py`, `conftest.py`, `__main__.py` from coverage check |
| Module-name check misses renamed modules | Level 1 is best-effort. Combined with hash-based checks, coverage is good enough |
| Performance of disk scanning in check_source_coverage | Only scans dirs listed in `nodes.source`. Beadloom projects have ~20 nodes. Negligible cost. |

---

## 6. Files to Modify

| File | Changes |
|------|---------|
| `src/beadloom/doc_sync/engine.py` | Fix 3 (hash), Fix 4 (`check_source_coverage`), Fix 5 (`check_doc_coverage`), integrate into `check_sync()` |
| `src/beadloom/infrastructure/reindex.py` | Fix 1 (`_snapshot_sync_baselines` + pass to full reindex), Fix 2 (`or None` → `if is not None`) |
| `src/beadloom/infrastructure/doctor.py` | New `_check_source_coverage` check, enhanced drift output |
| `src/beadloom/services/cli.py` | Enhanced sync-check output (show missing modules) |

---

## 7. Testing Strategy

| Test | What it validates |
|------|-------------------|
| Unit: `_snapshot_sync_baselines()` returns correct data, handles missing table | Fix 1 |
| Unit: full reindex preserves symbols_hash baseline | Fix 1 |
| Unit: `old_symbols = {}` preserves (not resets) baseline | Fix 2 |
| Unit: `_compute_symbols_hash()` includes file paths | Fix 3 |
| Unit: `check_source_coverage()` finds untracked files | Fix 4 |
| Unit: `check_doc_coverage()` finds missing module mentions | Fix 5 |
| Integration: add new file + reindex + sync-check → stale | Fixes 1-4 combined |
| E2E: run on beadloom itself → detect >= 6 stale docs | All fixes |
