# Active Table (component)

Internal building block of the application layer.

**Source:** `src/beadloom/application/active_table.py`

---

## Overview

Single source of truth for the **ACTIVE.md bead-status table** format used by the
packaged agentic flow. Extracted from the MCP S4 helpers (BDL-051) so the MCP
process-tools (`checkpoint` / `complete_bead`, in `services/mcp_server.py`) and
the `active-sync` command (BDL-053, in `services/commands/docsync.py`) share one
tolerant, fail-safe parser/updater rather than each carrying its own copy.

The module is deliberately **pure with respect to `bd`**: it never shells out to
the beads CLI. Callers query `bd` and inject the resulting status map; this layer
only parses and rewrites the markdown. That keeps it trivially testable and makes
the no-op contract (no `bd`, no ACTIVE table → nothing happens) the caller's
responsibility, not a hidden side effect here.

## The bead-status table format

The table is a markdown table whose header's first cell is `Bead`, directly
followed by a separator row (`| --- | --- | ... |`), AND carrying a `Status`
column. Each data row carries a bead-id in its first cell and a state token in
its `Status` column. Both the 3-column `| Bead | Role | Status |` and 4-column
`| Bead | Role | Status | Depends |` shapes are supported — the `Status` column
is located by its header cell index (case-insensitive), not by position. The
scan does not stop at the first `Bead`-headed table: a `Bead` table with no
`Status` column is not the bead-status table, and giving up at it made this
repository's own BDL-061 ACTIVE.md unreadable, since a deferral table headed
`| Bead | What it is | Why it was not done here |` sits 480 lines above the
status table (BDL-061.84).

### A bead id is written in two forms

The tracker allocates `beadloom-mr2l.22`; an ACTIVE table abbreviates it to
`.22`, because the prefix is the same for every row in the file. Comparing the
two as whole strings matches nothing, which is what this module did for the whole
of BDL-053's life: `active-sync --check` reported `already coherent` over a table
it had compared zero rows of. `resolve_row_bead_id(cell, bd_statuses, *,
prefix=None)` is the single place that maps one form onto the other, and both
lookups in this module use it.

A short id is read against `prefix` — the tracker id of the epic that table
belongs to — because the number alone is not unique across a tracker: this
repository holds eight beads numbered `.17` in eight epics. Without a prefix the
short id must be unique in the whole tracker; an ambiguity is reported, never
guessed. Every cell that resolves to no bead is returned with a stated reason.

## Public surface

- **`split_table_row(line)`** / **`is_separator_cells(cells)`** — markdown table
  row primitives. `split_table_row` returns the stripped inner cells of a `| … |`
  line (or `None` if the line is not a table row); `is_separator_cells` is `True`
  for a header-separator row (cells are only `-`/`:`).
- **`short_form(bead_id)`** / **`resolve_row_bead_id(cell, bd_statuses, *,
  prefix=None)`** — the two forms of a bead id, and the mapping between them.
  `short_form("proj-x.22")` is `".22"`; `resolve_row_bead_id` returns
  `(bead_id, None)` or `(None, reason)`.
- **`set_active_table_status(active_path, bead_id, status)`** — flips one bead's
  Status cell (the row's **last** cell) by **whole-token** match in the first
  cell, in either of the id's two forms (so `…mukc.1` never collaterally matches
  `…mukc.10`, and a full id finds the `.22` row a table really writes). This is
  the extracted MCP S4 updater;
  `services/mcp_server.py` re-exports it for back-compat. Returns `True` on a
  write, `False` (file untouched) on a missing file / no table / no matching row.
- **`bd_status_to_cell(bd_status)`** — the documented `bd`-status → Status-cell
  map: `closed → "✓ done"`, `in_progress → "in progress"`, `blocked → "blocked"`,
  `open`/`ready → "ready"`. An unrecognised status returns `None` so the caller
  leaves the row untouched (never corrupt). The `"blocked"` token is injected by
  the caller for an `open` bead that has an open blocker.
- **`reconcile_active_tables(project_root, bd_statuses, *, epic=None,
  epic_prefixes=None)`** — the
  pure reconcile-from-`bd` core. Discovers the target ACTIVE.md files (just
  *epic*'s `.claude/development/docs/features/<epic>/ACTIVE.md` when given, else
  every `features/*/ACTIVE.md`), finds each file's bead-status table, and for
  every data row that resolves to a bead in `bd_statuses` rewrites the Status
  cell to the mapped state — **unless the existing cell already STATES that
  state**, so a coordinator's richer note (`✓ done (PASS-WITH-FIXES)`) is
  preserved when the state agrees. The comparison strips leading
  non-alphanumerics and case-folds, so `Done`, `✓ done` and `**DONE** (a1b2c3d)`
  are one state in three spellings; without that, the first working run on this
  repository would have rewritten 78 rows of one file to add a checkmark. Rows
  whose bead is absent, or whose `bd` status is unrecognised, are left untouched.
  `epic_prefixes` maps an epic DIRECTORY name onto the tracker id of its epic
  bead (`{"BDL-061": "beadloom-mr2l"}`). Only files with a changed cell are
  rewritten; every other file is byte-preserved.
- **`ReconcileResult`** (dataclass) — the outcome: `changed_files` (paths
  rewritten), `drifted_rows` (`(path, bead_id, old_cell, new_cell)` per
  corrected cell), `rows_read` / `rows_resolved`, and `unresolved_rows`
  (`(path, cell, reason)`). The counts exist because an empty `drifted_rows` had
  two meanings that read identically: every row agreed with the tracker, or no
  row was ever compared. `is_inert` is the second — rows read, none resolved —
  and `active-sync --check` exits 1 on it as well as on drift.

Best-effort throughout: **never raises, never corrupts the file**. Prose,
headings, the Progress Log, and non-Status columns are always left untouched.

## Collaborators

- **`services/commands/docsync.py` — `active-sync` command (and helpers).** The same
  module also carries the pre-commit and pre-push hook TEMPLATES, whose subject is
  `guard-hooks` rather than this component; the one line of them that belongs here is the
  coherence block, which runs `active-sync --stage` so the commit is coherent by
  construction and names the paths it added.
  Queries `bd list --all --json -n 0` (via the mockable
  `services/bd_seam.run_bd` seam) — `--all` and the lifted row cap are load-
  bearing: `bd list` defaults to open beads capped at 50 rows, which on this
  repository is 41 of 709 beads with every closed one missing, so the reconcile
  could never write `✓ done`. It maps the payload to a `{bead_id → status}` dict
  (`_bd_statuses_from_list`, which injects
  `"blocked"` for an `open` bead with an open `blocks` dependency on a
  non-closed target) and to an epic-prefix map (`_bd_epic_prefixes`, reading the
  `[KEY]` of each `epic`-typed bead's title), then calls
  `reconcile_active_tables`. Every output form states how many rows it resolved
  out of how many it read. After a fix it
  best-effort runs `bd export -o .beads/issues.jsonl` (only when that file is
  git-tracked) so the tracker artifact stays honest across branch/squash-merge.
  The module also hosts the `sync-check` command, which since BDL-061 S4b
  resolves the project's required document sections and passes them into
  `check_sync` — the two `sync-update` paths in the same module deliberately do
  not, because re-baselining a pair cannot fix a missing section. Its renderers
  own the verdict vocabulary a reader sees: `_STATUS_MARKER` carries one word
  per verdict (`[exempt]` among them since `beadloom-mr2l.76`, where an excused
  pair printed `[ok]`), and the `--json` summary counts every verdict so they
  sum to the total.
  The `--stage` flag runs `git add` on EXACTLY the reconciled ACTIVE.md paths
  plus the exported jsonl (via `_stage_reconciled`), never staging unrelated
  files. It nonetheless ADDS paths to a commit that is already in flight, and a
  commit made with an explicit pathspec does not exclude them — measured on
  BDL-061.22's own commit, which named one file and landed two. Since
  BDL-061.80 the installed pre-commit hook lists what this step added, because
  the hook's unjudged count states the remainder and nothing stated the
  addition. The `--check` mode runs reconcile on a throwaway sandbox copy
  (`_active_sync_check`) so it never writes to the real tree; it exits 1 on
  drift, 0 when clean.
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
