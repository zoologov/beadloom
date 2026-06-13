# RFC: BDL-053 — Tracker / ACTIVE coherence hook

> **Status:** Approved
> **Created:** 2026-06-14
> **PRD:** ./PRD.md

---

## Summary

A deterministic **reconcile-from-truth** that keeps process state honest by construction, delivered so it **works out-of-the-box for every adopter of the packaged flow** (owner requirement):

1. **`beadloom active-sync`** — a new CLI command that, for each epic's `ACTIVE.md`, reads the bead-ids already listed in its **bead-status table**, queries `bd` for each bead's real status, and rewrites only that table's Status cells from `bd` (the source of truth). Tolerant (3/4-column tables, prose/Progress Log untouched, preserves a coordinator's richer note when the *state* agrees). Plus a tracker sync: `bd export` → the tracked `.beads/issues.jsonl` so closes persist across branch/squash-merge.
2. **Pre-commit hook wiring** — `beadloom install-hooks` adds an "ACTIVE/tracker coherence" step to both hook templates that runs `active-sync` (auto-fix + restage). Guarded so it is a **safe no-op** in any repo without `bd` or without ACTIVE files → ships universally, surprises no one.

One implementation of the table parser/updater (extracted from S4's `mcp_server._set_active_table_status`) is shared by the MCP tools and the new command — single source of truth for the table format.

## Decisions on the open questions

1. **bd → ACTIVE read path → drive from the table's own rows.** The ACTIVE bead-status table already lists the bead-ids (rows like `| beadloom-mukc.3 | review — S1 | ... |`). `active-sync` parses those ids, calls `bd` once (`bd list --json`, or `bd show <id> --json` per id via the seam) to get each bead's `status` (+ `dependency`/blocker info), and sets the row's Status cell. **No epic→children discovery needed** — the table is the authoritative row set; we only correct each row's *status*. Status map: `closed → "✓ done"`, `in_progress → "in progress"`, `open` with an open blocker → `"blocked"`, else `open → "ready"`. **Preserve rich notes:** if the existing cell already begins with the correct state token (e.g. `✓ done (PASS-WITH-FIXES)`) and `bd` agrees, leave it; only overwrite when the *state* disagrees (so coordinator annotations survive, drift is fixed).
2. **Epic discovery → scan the flow dir.** No args → reconcile every `.claude/development/docs/features/*/ACTIVE.md` that contains a bead-status table (detect by a header row whose first cell is `Bead` + a separator row). `--epic <KEY>` → just that one. The hook runs the no-arg form (cheap: a handful of files × one `bd list --json`).
3. **jsonl sync → explicit `bd export` in the hook.** `bd export -o .beads/issues.jsonl` (the canonical tracked path) regenerates the jsonl from the Dolt DB, then the hook `git add`s it. Chosen over relying on `dolt.auto-commit`/auto-sync because that demonstrably did **not** fire in our branch/merge flow; an explicit export is deterministic + visible. (Only export when `.beads/` + a prior tracked `issues.jsonl` exist, so non-bd repos are untouched.)
4. **Hook behavior on drift → auto-fix + restage (default).** Reconcile is a *mechanical, deterministic regeneration* (unlike a lint error, there's nothing for the developer to "decide"), so the hook runs `active-sync` in fix mode and `git add`s the corrected `ACTIVE.md`(s) + `issues.jsonl` into the commit → the commit always carries a coherent state ("correct by construction"). The command also offers `--check` (exit non-zero on drift, no writes) for CI / explicit use. This is a deliberate, documented deviation from the lint/sync-check "warn|block" convention — for this kind of state, silent-correct beats nag.
5. **Reuse vs extract → extract a shared module.** Move the table parser/updater (`_split_table_row`, `_is_separator_cells`, `_set_active_table_status`) out of `services/mcp_server.py` into a new **`application/active_table.py`** (or `doc_sync/active_table.py`); `mcp_server` (S4 tools) and the new `active-sync` command both import it. New code there: `reconcile_active_tables(project_root, bd_statuses, epic=None) -> ReconcileResult` (pure, testable) + a `--check`/fix wrapper. The `bd` query funnels through the existing **`services/bd_seam.run_bd`** (already mockable + raises `BdUnavailableError` when `bd` is absent — reused for the graceful no-op).

## The "works for every new user" requirement (owner)

This is a first-class design constraint, not an afterthought:

- **Ships via the existing channels.** The hook templates (`_HOOK_TEMPLATE_WARN`/`_BLOCK` in `cli.py`) already call `beadloom <cmd>`; adding the `active-sync` step means **`beadloom install-hooks` raises it in any adopter repo** automatically. The agentic-flow scaffold's `CLAUDE.md.txt` (and the setup guidance) already tell adopters to run `install-hooks` — update its "lint + sync-check enforcement" note to "+ ACTIVE/tracker coherence".
- **Safe no-op when the flow isn't used.** Hook step is guarded `if command -v bd >/dev/null 2>&1` AND the command itself exits 0 doing nothing when: `bd` is unavailable (`BdUnavailableError` → skip), there are no `ACTIVE.md` files with a bead table, or `.beads/issues.jsonl` isn't tracked. So a repo that installed beadloom for sync-check only (no bd, no agentic flow) sees **zero behavior change** — never a blocked or mutated commit.
- **No hardcoded Beadloom specifics.** Paths (`.claude/development/docs/features/*/ACTIVE.md`, `.beads/issues.jsonl`), the bead-id token, and the table shape are the flow's *conventions* (the same ones `task-init`/`checkpoint` scaffold) — not Beadloom-only. The reconcile derives everything from those conventions + `bd`, so it's correct for any adopter who uses the packaged flow. Tool-agnostic ([[project_vision]]).
- **Tested as an adopter would hit it.** Tests cover: a scaffolded-but-bd-less repo (no-op), a fresh epic with a 3-col table, a 4-col (`Depends`) table, rich-note preservation, and the hook end-to-end in a temp git repo.

## Component / file impact

| Component | Change |
|-----------|--------|
| `application/active_table.py` (NEW) | extracted table parser/updater (from `mcp_server`) + `reconcile_active_tables()` (bd-status → table) + epic discovery |
| `services/mcp_server.py` | import the shared module (S4 `_set_active_table_status` now delegates) — no behavior change |
| `services/cli.py` | new `active-sync` command (`--check` / `--epic` / `--json`); extend `_HOOK_TEMPLATE_WARN`+`_BLOCK` with the guarded coherence step (run `active-sync` + `bd export -o .beads/issues.jsonl` + `git add`) |
| `services/bd_seam.py` | (reuse) `run_bd` for `bd list --json` / `bd export`; `BdUnavailableError` → graceful skip |
| `onboarding/templates/agentic_flow/CLAUDE.md.txt` | install-hooks note → "+ ACTIVE/tracker coherence" (re-vendor; BDL-048 drift-guard) |
| graph (`services.yml`) | `active-sync` is part of the `doc-sync` or a small `active-table` feature node + SPEC (coverage-lint is ERROR now — must classify the new module) |
| docs/guides + CHANGELOG | document the command + hook + the no-op contract |

## Algorithm (active-sync, one epic)

```
load ACTIVE.md → find the bead-status table (header 'Bead' + separator)
parse each data row → bead_id (first cell), status_cell (the 'Status' column by header index)
ids = [bead_id for each row]
bd_status = { id: status } from `bd list --json` (filter to ids)   # one call
for each row:
    want = map(bd_status[id], has_open_blocker)                    # ✓ done / in progress / blocked / ready
    if cell already starts with want's state token: keep (preserve note)
    else: rewrite the Status cell = want
write back only if changed (tolerant: untouched prose/columns)
return ReconcileResult(changed_files, drifted_rows)               # --check: nonzero if drifted_rows
then (fix mode, if .beads/issues.jsonl tracked): bd export -o .beads/issues.jsonl
```

## Alternatives considered

- **Configure `dolt.auto-commit=on` instead of `bd export` in the hook.** Rejected as the sole fix: it's bd-internal, didn't fire reliably in our flow, and is invisible; explicit export in the hook is deterministic + reviewable. (We may *also* set it, but the hook export is the guarantee.)
- **Keep maintaining ACTIVE only via the MCP `checkpoint`/`complete_bead` tools (S4).** Rejected: that only fires when a tool is called; the coordinator shelling `bd` bypasses it (the exact failure mode). A commit-time reconcile catches every path.
- **Block-and-tell (don't auto-fix).** Rejected as default: the reconcile is deterministic with no human judgment — auto-fix+restage is smoother and matches "works like clockwork." `--check` covers the explicit/CI case.
- **Generate the whole ACTIVE.md from bd.** Rejected: prose/Progress Log/decisions are human-authored; we touch only the status table.
- **A git `post-commit`/`post-merge` hook.** Rejected: pre-commit keeps the committed artifact coherent (post-commit would leave the commit itself stale).

## Risks & mitigations

- **Hook mutates the commit (auto-`git add`).** → documented behavior; only touches ACTIVE.md tables + issues.jsonl; idempotent (no-op when already coherent → no surprise diffs). `--check` available for those who want fail-not-fix.
- **Breaking non-flow adopters.** → the guarded no-op (no bd / no ACTIVE / no tracked jsonl → exit 0, no writes); explicit adopter test. This is the owner's headline requirement — covered by AC + tests.
- **bd status vocabulary mismatch.** → centralize the status→cell map in one function; unit-test each bd status; unknown status → leave the cell + warn (never corrupt).
- **Table-format fragility.** → reuse S4's tolerant parser (keyed on bead-id cell, Status column by header index); 3/4-col + rich-note tests; never raise (best-effort, like S4).
- **`bd export` clobbering uncommitted bd work.** → export reflects the DB (the intent); only runs in fix mode; the exported jsonl is staged so it's reviewable in the commit.
- **Coverage-lint (now error) flags the new module.** → classify `active_table` as a node + SPEC in the same PR (lesson from BDL-051).

## Rollout

One feature branch `features/BDL-053`, one PR via `ci.yml` (gate + tests + site-build + ai-techwriter[skip]). Beads: extract+command (dev) → hook+jsonl+adopter-wiring (dev) → test → review → tech-writer. After merge: run `beadloom install-hooks` to refresh the local hook; the next epic's ACTIVE stays honest by construction. Verify on a throwaway temp repo (adopter no-op) + on this repo (real reconcile).
