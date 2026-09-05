# Active Table (component)

Internal building block of the application layer.

**Source:** `src/beadloom/application/active_table/`

---

## Overview

Single source of truth for the **ACTIVE.md bead-status table** format used by the
packaged agentic flow. Extracted from the MCP S4 helpers (BDL-051) so the MCP
process-tools (`checkpoint` / `complete_bead`, in `services/mcp_server.py`) and
the `active-sync` command (BDL-053, in `services/commands/docsync.py`) share one
tolerant, fail-safe parser/updater rather than each carrying its own copy.

The reconcile core is deliberately **pure with respect to `bd`**: it never shells
out to the beads CLI. Callers query `bd` and inject the resulting status map; this
layer only parses and rewrites the markdown. That keeps it trivially testable and
makes the no-op contract (no `bd`, no ACTIVE table → nothing happens) the caller's
responsibility, not a hidden side effect here.

### Five modules, one responsibility each

It was a single `active_table.py` until BDL-068 S5, and its own docstring already
needed an "and" to describe itself. The file moved with `git mv`, so the history
follows it, and `__init__.py` re-exports the whole public surface — no import path
outside the package changed.

| Module | Its one responsibility |
|--------|------------------------|
| `row_ids.py` | The bead id a row names, and what the row names when it names none |
| `table.py` | The markdown table: its rows, its Status column, one cell write |
| `statuses.py` | The state a Status cell states, and the `bd` status it comes from |
| `reconcile.py` | The reconcile core, pure with respect to `bd` |
| `staging.py` | What a reconcile may stage, which is never more than the commit already carries |

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

### And it is written inside whatever Markdown wraps it in

A cell is text in a document before it is a key in a lookup, so an author writes
`` `.10` `` or `**.10**` the way they write every other identifier in the same
file. `undecorate` reduces a link to its text and deletes every code-span and
emphasis character wherever it stands. Only two characters are stripped —
backtick and asterisk — because an underscore can appear in a tracker id, and
removing it to read `_.22_` would silently corrupt `proj_x.22`.

Measured on this repository at `5846b20`, before the fix: 329 rows read, 211
resolved, 118 unresolved, and 27 of the 118 were BDL-067's own table, every row
of which writes its id as a code span. After: 238 resolved, 91 unresolved, and no
cell rewritten in either run — those rows already said what the tracker says.
A reconcile inert on the commonest way to write an id in Markdown does not prevent
hand-drift; it certifies it (BDL-UX #210).

### A row that did not resolve says which of five things it was

All 118 carried one sentence over four different facts with four different
remedies. `resolve_row_bead_id` returns a `RowId(bead_id, shape, reason)` and the
shape is one of `SHAPES`:

| Shape | The cell | What to do about it |
|-------|----------|---------------------|
| `no-bead-id` | `BEAD-01`, `01`, `b0xl` | Nothing — it names no bead |
| `bead-and-text` | `.7 review` | Move the title into a column of its own |
| `more-than-one-bead` | `.73`–`.76`, `proj-x.3..8` | Give each bead its own row |
| `unknown-to-tracker` | `.99` under an epic that has no `.99` | A finding about the tracker's answer |
| `ambiguous-number` | `.22`, with no known epic and two beads numbered `.22` | Write the full id |

A `bead-and-text` cell is deliberately **not** resolved to its head. The whole
cell is the row's id, and reading `.1 Contract model` as the bead `.1` would
resolve about fifty rows of this repository's finished epics and rewrite their
status cells inside an unrelated commit. The shape is reported so the next
decision is taken on a number rather than on a guess.

### A bead with no row, and a bead with a row this run could not read

These are two findings with two remedies, and they were one until BDL-068 S5's
review found the run contradicting itself over them. `seen` was filled only from
rows that RESOLVED, so every unresolved row handed its bead to "no row in their
epic's table" while the same run printed the row that names it under
`bead-and-text` or `more-than-one-bead`. Measured at `27db92b`: 79 beads reported
as carried by no row, 38 of which had a row whose first cell's head is exactly
that bead's id. A reader acting on the message adds a row that is already there.

The two offending shapes extract an id in order to write their message —
`_RANGE.group("first")` and `_ID_THEN_TEXT.group("id")` — and both used to throw
it away. `RowId.names` now carries it, resolved through the same code a whole
cell is resolved through, and the reconcile splits the bead-keyed report in two:

| List | The bead | The remedy |
|------|----------|------------|
| `beads_named_by_an_unresolved_row` (`(path, bead_id, cell)`) | a row names it and this run could not read that row | fix the cell; the shape in `unresolved_rows` says how |
| `unlisted_beads` (`(path, bead_id)`) | no row of the table names it | add a row |

Measured before and after on this repository, with `active-sync --check --json`:
79 carried by no row becomes 41 carried by no row and 38 named by a row this run
could not read. The row-keyed numbers do not move (329 read, 238 resolved, 91
unresolved, 0 rewritten), and 41 + 38 = 79: no bead left the report.

`RowId.names` is set only on a failure and only when the id it found is a bead
the tracker reported, because a head naming nothing the tracker holds has no bead
to subtract. **A range is not expanded.** `proj-x.3..8` names `proj-x.3`; the
numbers between the endpoints are ids the table does not write, and enumerating
them would be a guess. They stay in `unlisted_beads`, which is what the range's
own remedy — give each bead its own row — asks the author for.

Both lists are the other half of what BDL-062's reconcile missed, where three
closed beads read `blocked` and three more were not listed at all. Both are
reported and **never written**: inserting a row into somebody's document is the
same decision-for-an-agent as adding a path to their commit. Both are computed
only when the table's epic is known, because without a prefix there is no
population to subtract from. The human report prints neither on an `is_inert`
run — a run that resolved no row at all compared nothing, and a per-bead list
there restates that one fact once per bead — and `--json` carries both always.

## Public surface

- **`split_table_row(line)`** / **`is_separator_cells(cells)`** — markdown table
  row primitives. `split_table_row` returns the stripped inner cells of a `| … |`
  line (or `None` if the line is not a table row); `is_separator_cells` is `True`
  for a header-separator row (cells are only `-`/`:`).
- **`short_form(bead_id)`** / **`undecorate(cell)`** / **`resolve_row_bead_id(cell,
  bd_statuses, *, prefix=None)`** — the forms of a bead id, and the mapping between
  them. `short_form("proj-x.22")` is `".22"`; `undecorate` removes the Markdown a
  document wrapped an id in; `resolve_row_bead_id` returns a `RowId` carrying
  either a `bead_id` or a `shape` and a `reason`. On a failure `RowId.names`
  carries the bead the row NAMES without resolving to it, when its shape found
  one.
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
  corrected cell), `rows_read` / `rows_resolved`, `unresolved_rows` (a
  `UnresolvedRow(path, cell, shape, reason)` each), `unlisted_beads`
  (`(path, bead_id)`) and `beads_named_by_an_unresolved_row`
  (`(path, bead_id, cell)`). The counts exist because an empty `drifted_rows` had
  two meanings that read identically: every row agreed with the tracker, or no
  row was ever compared. `is_inert` is the second — rows read, none resolved —
  and `active-sync --check` exits 1 on it as well as on drift.
  `unresolved_by_shape` is the count a reader can act on: "118 unresolved" is a
  number nobody acts on, and "27 of them are a decoration we cannot read" is one
  somebody fixes in an hour.
- **`stageable(candidates, pending)`** / **`decide_staging(candidates,
  already_staged)`** / **`StagingDecision`** — what a reconcile may stage. See
  "Staging is the committer's decision" below.
- **`paths_this_commit_stages(root)`** / **`paths_the_index_has_not_taken(root)`**
  / **`stage_paths(root, paths)`** — the three git reads and the one git write,
  each a named collector at the module edge, so everything above them is a
  decision over a set somebody hands in.

## Staging is the committer's decision

`active-sync --stage` used to `git add` every path the reconcile had written. In
BDL-062 an agent unstaged `.beads/issues.jsonl` on purpose, because it was another
agent's tracker export, and the pre-commit hook put it back and said so. This
project instructs every agent to *commit only your own files, by explicit path,
never `git add -A`* — and that instruction cannot survive a tool that stages after
the decision was taken (BDL-UX #207).

**The commit's own scope decides.** It is the set of paths whose index entry
differs from `HEAD`, which is what a commit actually contains: a path staged with
content identical to `HEAD` puts nothing in the commit, so correcting it and
staging it would add a change nobody asked for. `decide_staging` re-stages the
corrected content of a path inside that set and NAMES every correction outside it;
a scope that could not be read stages nothing and says so, because an unknown
scope is not an empty one.

**`stageable` drops what staging would not change.** A path whose working tree
already matches the index gains nothing from a `git add` and loses nothing from a
withholding, so no line is printed about it.

**The escape hatch works, once nothing stages behind it.** Measured on git 2.49.0
in two isolated rigs: `git commit -- <paths>` DOES exclude a path that is staged
and unnamed. It is not a defence against a hook, because a pathspec commit builds
a temporary index and a `git add` run from pre-commit writes into that one — the
hooked file landed in the commit and was left staged in the real index afterwards.
So the hook defeated the one instruction an agent could have followed.

**Why not `beadloom scope-check`.** It answers a different question — does this
commit leave the work item's approved axes — over a population that excludes
exactly these two files: its rule reports nothing about a path no graph node owns,
and neither an `ACTIVE.md` nor `.beads/issues.jsonl` is owned.

**What no hook can see.** A path already in the index looks the same whether the
committer put it there or another tool did. Commit `050d63ac` on `features/BDL-068`
carries a neighbouring bead's `git mv` for that reason, with no hook involved.

Best-effort throughout: **never raises, never corrupts the file**. Prose,
headings, the Progress Log, and non-Status columns are always left untouched.

## Collaborators

- **`services/commands/docsync.py` — `active-sync` command (and helpers).** The same
  module also carries the pre-commit and pre-push hook TEMPLATES, whose subject is
  `guard-hooks` rather than this component; the one line of them that belongs here is the
  coherence block, which runs `active-sync --stage` and prints the paths it withheld.
  The block runs no `git add` of its own, and it selects the withheld lines with
  `grep` rather than with the `sed -n 's/^# //p'` shape the two porcelain legs beside
  it use: that shape is this project's verdict/payload split and means something, and
  borrowing its spelling for an unrelated extraction gives one protocol a second
  meaning.
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
  The `--stage` flag (via `_restage_within_this_commit`) re-stages the corrected
  content of the paths the commit already carries and names the rest under a
  fixed `  withheld: ` line. It adds no path to a commit. Under `--stage`,
  `bd export` runs only when the commit already carries `.beads/issues.jsonl`:
  the export exists to keep the TRACKED artifact honest across a branch or
  squash-merge and achieves that only when the refresh is committed, so once the
  refresh can no longer be staged into somebody else's commit, running it anyway
  would dirty a shared working tree for nothing. That gate is measured rather
  than assumed — over the sixteen commits of `features/BDL-068`, `bd export`
  moved the file in sixteen, so without it the hook would print one line on every
  commit, and four of those sixteen are `chore: tracker export` and nothing else.
  The by-hand path (no `--stage`) exports exactly as before. The `--check` mode
  runs reconcile on a throwaway sandbox copy (`_active_sync_check`) so it never
  writes to the real tree, and `_rebased` maps the result's paths back to the real
  files — a finding that names a file the reader cannot open is a finding nobody
  acts on. It exits 1 on drift, 0 when clean.
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
and the reconcile core's drift / no-op / byte-preservation cases);
`tests/test_active_table_id_forms.py` covers the two forms of an id, and
`tests/test_active_reconcile.py` plus
`tests/acceptance/features/active_reconcile.feature` cover the decoration a
document wraps an id in, the five unresolved shapes, the unlisted beads and the
staging decision; `tests/test_active_row_named_beads.py` covers the split between
a bead no row names and a bead a row names and this run could not read. The
`active-sync` command's check / fix / no-op paths are covered by
`tests/test_cli_active_sync.py` and `tests/test_cli_active_sync_hardening.py`,
the pre-commit hook wiring by `tests/test_cli_hooks.py`, and the re-exported S4
updater by `tests/test_mcp_process_tools.py`.
