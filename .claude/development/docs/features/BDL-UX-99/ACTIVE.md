# ACTIVE: BDL-UX#99 — Repo-wide Doc Refresh

> **Last updated:** 2026-06-01
> **Phase:** ✅ COMPLETED — sync-check honest 0; lint 0; doctor clean; gate green WITHOUT --no-verify; 5 beads + parent closed (`288e5eb`).

---

## Goal

`beadloom sync-check` → **honest 0** so the pre-commit gate passes without `--no-verify`, giving F2 a trustworthy baseline. 37 stale pairs / 15 docs.

## Execution model (race-safe)

- **Edit wave (parallel subagents):** each tech-writer batch edits ONLY its docs (distinct files). **No `reindex` / `mark_synced`** (those write the shared SQLite → race). For `symbols_changed`, update the doc's documented signatures/prose to match current code; for `hash_changed`, verify prose still accurate (edit only if drifted).
- **Verify wave (main loop, BEAD-05):** single `beadloom reindex` → `mark_synced_by_ref` per touched ref_id (attest current baseline AFTER prose is correct) → `sync-check` == 0 → fix residuals inline → `lint --strict` + `doctor` → commit WITHOUT `--no-verify`.
- Subagent-blocked fallback (BDL-036/037 lesson): any blocked batch → main loop completes it inline.

## Batches ↔ beads

| Bead | Batch | Docs (under `docs/`) | stale |
|------|-------|----------------------|-------|
| `beadloom-mbb.1` | A graph | `domains/graph/README.md` (7 symbols + cli hash), `domains/graph/features/graph-diff/SPEC.md` (cli hash) | 9 |
| `beadloom-mbb.2` | B infra | `domains/infrastructure/README.md` (db hash + git_activity/health symbols), `doctor`/`reindex`/`watcher` SPECs (cli hash) | 6 |
| `beadloom-mbb.3` | C app+svc | `domains/application/README.md` (debt_report/doctor/reindex/watcher symbols), `services/cli.md` (cli symbols), `services/mcp.md` (cli+mcp_server hash), `services/tui.md` (cli+app+data_providers+file_watcher hash) | 11 |
| `beadloom-mbb.4` | D independent | `domains/onboarding/README.md` (4 symbols + cli hash), `domains/doc-sync/README.md` (doc_indexer symbols + engine/cli hash), `doc-sync/features/docs-audit/SPEC.md` (cli hash), `domains/context-oracle/README.md` (cli hash), `context-oracle/features/search/SPEC.md` (cli hash) | 11 |
| `beadloom-mbb.5` | verify | reindex + mark_synced + sync-check==0 + lint + doctor | — |

## Progress

- [x] BEAD-01 graph (README edited) · [x] BEAD-02 infra (README edited) · [x] BEAD-03 app+svc (cli.md edited) · [x] BEAD-04 independent (re-attest only)
- [x] BEAD-05 verify — sync-check honest 0, lint 0, doctor clean, 288 tests, gate green without --no-verify

### Result
- 3 docs edited + 1 annotation fix (mcp_tools.py untracked gap); 12 docs re-attest-only.
- 60+4 pairs attested via `mark_synced_by_ref` after content review.
- Committed `288e5eb` WITHOUT `--no-verify` — gate restored.
- F4.1-loop friction note: `untracked_files` only surfaces once hash/symbols staleness clears (masked beneath higher-priority reasons) — the future `docs ai-refresh` must re-run sync-check after attest to catch second-order gaps.

## Notes

- ~13 graph/cli/infra relations will be re-staled by F2 → re-closed by F2's tech-writer wave (expected).
- Dogfood of the F4.1 loop: `docs polish --ref-id X --json` is the structured input agents use; capture friction.
