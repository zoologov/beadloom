# PRD: BDL-053 — Tracker / ACTIVE coherence hook

> **Status:** Approved
> **Created:** 2026-06-14
> **Type:** feature
> **Roadmap:** do FIRST, before BDL-052 (AI tech-writer speed) — it removes process friction that slowed all of BDL-051.

---

## Problem

Across BDL-047..051 the durable bead/progress state **drifts from reality**, in two distinct ways the owner flagged twice:

1. **`ACTIVE.md` bead-status table goes stale.** The coordinator (main loop) edits the `| Bead | Role | Status |` table by hand and **keeps missing rows** — e.g. a bead is claimed/closed in `bd` but its ACTIVE row still says `blocked` / `in progress`. CLAUDE.md §0 ("update ACTIVE.md after each significant action") is being violated systematically. ACTIVE.md is a P0 session-start memory file — a stale one hides real progress and defeats its purpose.
2. **The `bd` tracker itself drifted.** `bd close` writes only the local embedded Dolt DB; the **tracked `.beads/issues.jsonl`** is not reliably synced across the feature-branch → squash-merge workflow. At BDL-051's end, almost every bead showed `in_progress` though all work was merged — the closes never reached the committed jsonl. (bd has `export`/`import` + an auto-sync / `dolt.auto-commit` policy, but it is not firing in our flow.)

Both are the same root failure: **durable state is maintained by manual discipline, and manual discipline keeps failing.** S4 of BDL-051 built a per-tool-call helper (`_set_active_table_status`) but it only fires when an MCP tool is called — the coordinator shelling `bd` + hand-editing docs bypasses it.

## Impact

Make tracker + ACTIVE coherence **correct by construction**, not a matter of vigilance: a deterministic *reconcile-from-truth* that regenerates the ACTIVE bead-status table from `bd` (the source of truth) and keeps the tracked jsonl synced — **wired into the pre-commit hook** so a commit physically cannot carry a stale ACTIVE table or an unsynced tracker. This is itself a dogfood of Beadloom's thesis (no drift between the artifact and reality), applied to the project's own process state.

Success criterion: a single `beadloom` command reconciles any epic's `ACTIVE.md` table from `bd` + ensures `.beads/issues.jsonl` reflects the DB; the pre-commit hook (`beadloom install-hooks`) runs it and **blocks/auto-fixes** a commit whose ACTIVE table or jsonl is out of sync; running the multi-agent flow no longer requires the coordinator to hand-edit ACTIVE rows.

## Goals

- [ ] **G1 — ACTIVE-table reconcile-from-bd.** A deterministic routine that, given an epic key (or auto-discovered from the staged ACTIVE.md files), regenerates the bead-status **table** in `.claude/development/docs/features/<KEY>/ACTIVE.md` from `bd` state: each row's Status cell set from the bead's real `bd` status (done / in progress / open / blocked). **Tolerant**: only the table is rewritten (preserve headings, prose, Progress Log, extra columns like `Depends`); keyed on the bead-id cell; never corrupts the file. Generalizes S4's `_set_active_table_status` into a from-truth reconcile.
- [ ] **G2 — Tracker jsonl sync.** Ensure `.beads/issues.jsonl` reflects the bd DB (via `bd export` or the right auto-sync/`dolt.auto-commit` config) so closes/claims persist across branch/squash-merge — no more "all in_progress though merged."
- [ ] **G3 — `beadloom` command.** Expose the reconcile as a CLI command (e.g. `beadloom active-sync` / `beadloom reconcile`) with a `--check` mode (exit non-zero if drift, like `sync-check`) and a default fix mode (rewrite + restage). JSON output option for tooling.
- [ ] **G4 — Pre-commit hook wiring.** `beadloom install-hooks` adds the reconcile to the pre-commit hook (alongside the existing lint + sync-check enforcement): a commit with a stale ACTIVE table or unsynced jsonl is fixed-and-restaged or blocked with a clear message. Safe-by-default, idempotent, fast.
- [ ] **G5 — Docs/CHANGELOG.** Document the command + hook behavior; CHANGELOG entry. (Update the CLAUDE.md flow note that ACTIVE is now reconciled by the hook, not by hand.)

## Non-goals (out of scope)

- **Orchestration / subagent changes** — unrelated; the coordinator still spawns roles in the main loop.
- **Re-designing `bd` or its Dolt internals** — we only ensure the tracked jsonl is synced via bd's own export/sync; we don't fork bd.
- **The AI tech-writer speed work** — that's BDL-052 (separate).
- **A general project-management dashboard** — scope is strictly the ACTIVE bead-status table + the jsonl sync.
- **Rewriting ACTIVE prose / Progress Log** — the reconcile touches only the status table; prose stays human/coordinator-authored.

## Open architecture questions (→ resolved in the RFC)

1. **bd as source of truth — read path.** `bd list --json` (or `bd export`) to get each bead's status? How to map a bd status → the ACTIVE Status cell vocabulary (✓ done / in progress / blocked / open)? Preserve a coordinator's richer status note (e.g. "✓ done (PASS-WITH-FIXES)")?
2. **Epic discovery.** Reconcile only the epic(s) whose ACTIVE.md is staged, all under `.claude/development/docs/features/*/`, or a passed `--epic`? How does the hook scope it to be fast?
3. **jsonl sync mechanism.** Is the fix `bd export` in the hook, or configuring `dolt.auto-commit`/auto-sync so it's always current? Which is robust + non-surprising in the trunk-based flow?
4. **Hook behavior on drift.** Auto-fix + `git add` the corrected ACTIVE/jsonl (convenient, but mutates the commit), or fail with a message telling the user to run `beadloom active-sync` (explicit)? Match the existing hook's lint/sync-check convention.
5. **Reuse vs extract.** Reuse `_set_active_table_status` from `mcp_server.py` directly, or extract the table parser/updater into a shared module (application/) that both the MCP tools and the new command call?

## User stories

### US-1: ACTIVE never lies
As the maintainer, when I open an epic's `ACTIVE.md` at session start, the bead-status table reflects the real `bd` state — because the hook reconciled it on the last commit — so I trust it without cross-checking `bd`.

### US-2: Closes persist
As the maintainer, when a bead is closed and the work is merged, the closed status is in the committed `.beads/issues.jsonl` on `main` — it does not silently revert to `in_progress` on the next branch/checkout.

### US-3: No vigilance tax
As the coordinator, I no longer hand-edit ACTIVE rows per wave (and miss some); I close beads in `bd` and the hook keeps ACTIVE + the jsonl honest by construction.

## Acceptance criteria

- `beadloom active-sync --check` exits non-zero when an epic's ACTIVE table disagrees with `bd`; the default (fix) mode rewrites the table from `bd` + leaves prose/Progress Log/columns intact.
- The tracked `.beads/issues.jsonl` reflects bd DB state after the hook runs (closes persist across branch/merge).
- `beadloom install-hooks` installs a pre-commit step that prevents committing a stale ACTIVE table or unsynced jsonl (fix-and-restage or block, matching the existing hook convention); idempotent; adds negligible commit latency.
- Reconcile is tolerant (3- and 4-column tables, prose, rich status notes) and never corrupts ACTIVE.md.
- Full `beadloom ci` green; the command + hook covered by tests.
