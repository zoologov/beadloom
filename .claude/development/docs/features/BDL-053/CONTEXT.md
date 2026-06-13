# CONTEXT: BDL-053 — Tracker / ACTIVE coherence hook

> **Status:** Approved
> **Created:** 2026-06-14
> **PRD/RFC:** ./PRD.md · ./RFC.md

---

## State

- **ACTIVE.md tables:** live at `.claude/development/docs/features/<KEY>/ACTIVE.md`; a `| Bead | Role | Status |` (sometimes `| ... | Depends |`) markdown table whose rows carry the bead-id in the first cell. Maintained by hand by the coordinator today → drifts (rows missed). This is a P0 session-start memory file.
- **S4 helper (BDL-051):** `services/mcp_server.py` has `_set_active_table_status(active_path, bead_id, status)` + `_split_table_row` / `_is_separator_cells` — tolerant, best-effort, never raises; sanitizes pipes + whitespace. Only fires when an MCP tool (`checkpoint`/`complete_bead`) is called → bypassed when the coordinator shells `bd`.
- **bd seam (BDL-051 S3b):** `services/bd_seam.py` — `run_bd(...)` funnels every `bd` call (mockable; `BdUnavailableError` when `bd` not on PATH). `bd list --json` returns `[{id,status,issue_type,dependency_count,...}]`; `bd export -o FILE` writes the JSONL.
- **bd jsonl drift:** `bd close` updates the local Dolt DB; the tracked `.beads/issues.jsonl` is not reliably synced across feature-branch/squash-merge ([[reference_bd_close_jsonl_drift]]) → closes don't persist. `bd export` regenerates the jsonl from the DB.
- **Pre-commit hook:** `services/cli.py` `install-hooks` writes `_HOOK_TEMPLATE_WARN` (default) / `_HOOK_TEMPLATE_BLOCK` to `.git/hooks/pre-commit` — POSIX sh, calls `uv run ruff`, `uv run mypy`, `beadloom sync-check --porcelain`, each guarded by `command -v`.
- **Adopter delivery:** `onboarding/templates/agentic_flow/CLAUDE.md.txt` (the scaffolded flow doc) tells adopters to run `beadloom install-hooks`. Coverage-lint is now **error** (BDL-051 S3b) — any new module must be a classified node + doc.

## Decisions (from PRD/RFC)

- `beadloom active-sync` (`--check` / `--epic` / `--json`); default = fix + restage. Drives off the ACTIVE table's own bead-id rows → one `bd list --json` → rewrite Status cells; **preserve rich notes when the state agrees**.
- jsonl sync = explicit `bd export -o .beads/issues.jsonl` in the hook (not relying on dolt auto-commit).
- Hook step = **auto-fix + `git add`** (correct by construction), guarded so it's a **safe no-op** without `bd` / ACTIVE / tracked jsonl.
- Extract the table parser/updater into shared **`application/active_table.py`**; `mcp_server` + the command both use it; `bd` via `bd_seam.run_bd`.
- **Owner requirement (headline):** must work out-of-the-box for every adopter of the packaged flow — ships via `install-hooks` + agentic-flow scaffold; no Beadloom-only hardcoding; zero behavior change for non-flow repos.

## Code standards (from CLAUDE.md §0.1)

- Python 3.10+, SQLite, Click, Rich, tree-sitter. pytest (≥80% changed). ruff. mypy --strict (no `Any`/`# type: ignore` w/o reason). DDD boundaries (`lint --strict`). No bare except, no `import *`, no mutable defaults. Shell cmds use `-f`.
- New `application/active_table.py` respects DDD direction (application orchestrates; reads docs + the bd seam; not imported by lower layers improperly).
- The reconcile + hook step are **best-effort + fail-safe**: never corrupt ACTIVE.md, never block a commit in a non-flow repo.

## Constraints / invariants

- **Single PR on the consolidated `ci.yml`** (gate + tests 3.10–3.13 + site-build + ai-techwriter[skip per slice policy]); main green by construction.
- **No-op contract:** no `bd` (`BdUnavailableError`) OR no ACTIVE-with-table OR no tracked `.beads/issues.jsonl` → exit 0, zero writes. Tested explicitly (adopter-without-bd).
- **Tolerant + non-destructive:** only the bead-status table's Status cells change; headings, prose, Progress Log, extra columns untouched; reuse S4's parser; never raise.
- **Shared parser stays single-source:** after extraction, `mcp_server` behavior is byte-identical (S4 tests stay green).
- **Coverage-lint (error):** classify the new `active_table` module as a node + SPEC in this PR.
- Anonymize third-party project names in committed artifacts.

## Definition of done

`beadloom active-sync --check` flags drift (nonzero) and the fix mode rewrites only the table from `bd`; `bd export` keeps `.beads/issues.jsonl` honest; `install-hooks` ships the guarded coherence step (auto-fix+restage) that is a verified no-op in a bd-less/flow-less repo and corrects drift in a flow repo; the shared parser is extracted (S4 green); the new module is graph-classified; docs/CHANGELOG updated; full `beadloom ci` + `ci.yml` green.
