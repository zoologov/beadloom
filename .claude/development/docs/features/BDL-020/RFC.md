# RFC: BDL-020 — Source Coverage Hierarchy Fix

> **Status:** APPROVED
> **Date:** 2026-02-17

---

## Problem Statement

`check_source_coverage()` flags files as "untracked" when they are annotated to a child feature node rather than the parent domain node. This produces 12 false-positive stale entries.

### Current state (4 mismatches)

| File | Current annotation | Expected parent | Graph edge |
|------|-------------------|-----------------|------------|
| `context_oracle/why.py` | `domain=impact-analysis` | `context-oracle` | `why --part_of--> context-oracle` |
| `infrastructure/doctor.py` | `domain=doctor` | `infrastructure` | `doctor --part_of--> infrastructure` |
| `infrastructure/watcher.py` | `domain=watcher` | `infrastructure` | `watcher --part_of--> infrastructure` |
| `tui/app.py` | *(none)* | `tui` | *(tui is a service node)* |

### Root cause in logic

`check_source_coverage()` at line 404-409 checks if a file's annotations LIKE `%"ref_id"%` for the **parent** ref_id only. It doesn't consider that a file annotated to `doctor` (a child feature) is implicitly tracked under `infrastructure` (the parent domain) via the `part_of` edge.

---

## Solution: Two Paths

### Path 1: Fix annotations (4 files)

Fix the immediate mismatches:

1. **`why.py`** — Change `# beadloom:domain=impact-analysis` to `# beadloom:domain=context-oracle`. The `why` feature node already exists in the graph with its own `source: src/beadloom/context_oracle/why.py`, so it's tracked at feature level via that node. The annotation just needs to match the domain for sync-state tracking.

2. **`doctor.py`** — Change `# beadloom:domain=doctor` to `# beadloom:domain=infrastructure`. Same logic — `doctor` feature node has explicit `source` field.

3. **`watcher.py`** — Change `# beadloom:domain=watcher` to `# beadloom:domain=infrastructure`. Same as above.

4. **`tui/app.py`** — Add `# beadloom:service=tui` as first line.

### Path 2: Hierarchy-aware `check_source_coverage` (engine.py)

Modify the tracked-files query to include files annotated to any **child** ref_id (nodes with `part_of` edge pointing to the current ref_id).

#### Current logic (lines 394-409):

```python
# 5. Collect tracked code_paths from sync_state for this ref_id
tracked: set[str] = set()
sync_rows = conn.execute(
    "SELECT code_path FROM sync_state WHERE ref_id = ?",
    (ref_id,),
).fetchall()
for row in sync_rows:
    tracked.add(row["code_path"])

# 6. Also collect file_paths from code_symbols annotated with this ref_id
sym_rows = conn.execute(
    "SELECT file_path FROM code_symbols WHERE annotations LIKE ?",
    (f'%"{ref_id}"%',),
).fetchall()
for row in sym_rows:
    tracked.add(row["file_path"])
```

#### New logic (add step 5b and expand step 6):

```python
# 5. Collect tracked code_paths from sync_state for this ref_id
tracked: set[str] = set()
sync_rows = conn.execute(
    "SELECT code_path FROM sync_state WHERE ref_id = ?",
    (ref_id,),
).fetchall()
for row in sync_rows:
    tracked.add(row["code_path"])

# 5b. Also include sync_state entries for child nodes (part_of this ref_id)
child_rows = conn.execute(
    "SELECT src_ref_id FROM edges WHERE dst_ref_id = ? AND kind = 'part_of'",
    (ref_id,),
).fetchall()
child_ref_ids = [row["src_ref_id"] for row in child_rows]

for child_id in child_ref_ids:
    child_sync = conn.execute(
        "SELECT code_path FROM sync_state WHERE ref_id = ?",
        (child_id,),
    ).fetchall()
    for row in child_sync:
        tracked.add(row["code_path"])

# 6. Also collect file_paths from code_symbols annotated with this ref_id
#    or any child ref_id
all_ref_ids = [ref_id] + child_ref_ids
for rid in all_ref_ids:
    sym_rows = conn.execute(
        "SELECT file_path FROM code_symbols WHERE annotations LIKE ?",
        (f'%"{rid}"%',),
    ).fetchall()
    for row in sym_rows:
        tracked.add(row["file_path"])
```

This uses one extra query to `edges` table per directory-based node. Performance impact is negligible — the edges table is small and the query is indexed.

---

## Testing Strategy

### Path 1 tests
- Verify annotations by running `beadloom sync-check` after changes → 0 stale

### Path 2 tests (new unit tests)
- `test_hierarchy_child_tracked` — file annotated to child feature is not flagged as untracked for parent domain
- `test_hierarchy_no_false_negatives` — file NOT annotated to any child is still flagged
- `test_hierarchy_no_children` — node with no child features works as before
- `test_hierarchy_multiple_children` — multiple child features all counted

### E2E
- `beadloom sync-check` on beadloom itself → 0 stale entries

---

## File Changes

| File | Change |
|------|--------|
| `src/beadloom/context_oracle/why.py` | Fix annotation |
| `src/beadloom/infrastructure/doctor.py` | Fix annotation |
| `src/beadloom/infrastructure/watcher.py` | Fix annotation |
| `src/beadloom/tui/app.py` | Add annotation |
| `src/beadloom/doc_sync/engine.py` | Add hierarchy logic to `check_source_coverage()` |
| `tests/test_source_coverage.py` | Add 4+ hierarchy tests |

---

## Risks

- **Low risk:** Annotation changes are 1-line edits in 4 files
- **Low risk:** Logic change is additive (extra query), no existing behavior modified
- **Edge case:** Deeply nested hierarchies (feature → sub-feature → domain). Mitigated: only direct `part_of` children queried (1 level). Multi-level not needed for beadloom's current graph.
