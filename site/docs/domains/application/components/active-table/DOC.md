<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`active-table`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Active Table (component)

Internal building block of the application layer.

**Source:** `src/beadloom/application/active_table.py`

---

## Overview

Single source of truth for the **ACTIVE.md bead-status table** format used by the
packaged agentic flow. Extracted from the MCP S4 helpers (BDL-051) so the MCP
process-tools (`checkpoint` / `complete_bead`, in `services/mcp_server.py`) and
the `active-sync` command (BDL-053, in `services/cli.py`) share one tolerant,
fail-safe parser/updater rather than each carrying its own copy.

The module is deliberately **pure with respect to `bd`**: it never shells out to
the beads CLI. Callers query `bd` and inject the resulting status map; this layer
only parses and rewrites the markdown. That keeps it trivially testable and makes
the no-op contract (no `bd`, no ACTIVE table → nothing happens) the caller's
responsibility, not a hidden side effect here.

## The bead-status table format

The table is a markdown table whose header's first cell is `Bead`, directly
followed by a separator row (`| --- | --- | ... |`). Each data row carries a
bead-id in its first cell and a state token in its `Status` column. Both the
3-column `| Bead | Role | Status |` and 4-column
`| Bead | Role | Status | Depends |` shapes are supported — the `Status` column
is located by its header cell index (case-insensitive), not by position.

## Public surface

- **`split_table_row(line)`** / **`is_separator_cells(cells)`** — markdown table
  row primitives. `split_table_row` returns the stripped inner cells of a `| … |`
  line (or `None` if the line is not a table row); `is_separator_cells` is `True`
  for a header-separator row (cells are only `-`/`:`).
- **`set_active_table_status(active_path, bead_id, status)`** — flips one bead's
  Status cell (the row's **last** cell) by **whole-token** bead-id match in the
  first cell (so `…mukc.1` never collaterally matches `…mukc.10`). This is the
  extracted MCP S4 updater, byte-identical to the pre-extraction behaviour;
  `services/mcp_server.py` re-exports it for back-compat. Returns `True` on a
  write, `False` (file untouched) on a missing file / no table / no matching row.
- **`bd_status_to_cell(bd_status)`** — the documented `bd`-status → Status-cell
  map: `closed → "✓ done"`, `in_progress → "in progress"`, `blocked → "blocked"`,
  `open`/`ready → "ready"`. An unrecognised status returns `None` so the caller
  leaves the row untouched (never corrupt). The `"blocked"` token is injected by
  the caller for an `open` bead that has an open blocker.
- **`reconcile_active_tables(project_root, bd_statuses, *, epic=None)`** — the
  pure reconcile-from-`bd` core. Discovers the target ACTIVE.md files (just
  *epic*'s `.claude/development/docs/features/<epic>/ACTIVE.md` when given, else
  every `features/*/ACTIVE.md`), finds each file's bead-status table, and for
  every data row whose bead-id is present in `bd_statuses` rewrites the Status
  cell to the mapped state — **unless the existing cell already STARTS WITH that
  state token**, so a coordinator's richer note (`✓ done (PASS-WITH-FIXES)`) is
  preserved when the state agrees. Rows whose bead-id is absent, or whose `bd`
  status is unrecognised, are left untouched. Only files with a changed cell are
  rewritten; every other file is byte-preserved.
- **`ReconcileResult`** (dataclass) — the outcome: `changed_files` (paths
  rewritten) and `drifted_rows` (`(path, bead_id, old_cell, new_cell)` per
  corrected cell). `active-sync` uses `drifted_rows` to drive `--check` (nonzero
  exit when non-empty) vs the default fix mode.

Best-effort throughout: **never raises, never corrupts the file**. Prose,
headings, the Progress Log, and non-Status columns are always left untouched.

## Collaborators

- **`services/cli.py` — `active-sync` command (and helpers).** Queries `bd list
  --json` (via the mockable `services/bd_seam.run_bd` seam), maps it to a
  `{bead_id → status}` dict (`_bd_statuses_from_list`, which injects `"blocked"`
  for an `open` bead with an open `blocks` dependency on a non-closed target),
  then calls `reconcile_active_tables`. After a fix it best-effort runs
  `bd export -o .beads/issues.jsonl` (only when that file is git-tracked) so the
  tracker artifact stays honest across branch/squash-merge.
- **`services/mcp_server.py` — S4 process-tools.** `checkpoint` and
  `complete_bead` flip a single bead's row via the re-exported
  `set_active_table_status`.

See the [`active-sync` CLI reference](../../../../services/cli.md#beadloom-active-sync)
and the [Agentic Dev Flow guide](../../../../guides/agentic-flow.md) for the
user-facing command, the pre-commit "ACTIVE / tracker coherence" step, and the
no-op contract.

## Testing

The pure core is covered by `tests/test_active_table.py` and
`tests/test_active_table_hardening.py` (table primitives, the `bd`-status map,
and the reconcile core's drift / no-op / byte-preservation cases). The
`active-sync` command's check / fix / no-op paths are covered by
`tests/test_cli_active_sync.py` and `tests/test_cli_active_sync_hardening.py`,
the pre-commit hook wiring by `tests/test_cli_hooks.py`, and the re-exported S4
updater by `tests/test_mcp_process_tools.py`.
