# PLAN: BDL-047 (F4.1) — AI tech-writer in CI

> **Status:** Approved
> **Created:** 2026-06-04
> **CONTEXT:** ./CONTEXT.md

---

## Beads (DAG)

Parent: `[epic] BDL-047 — F4.1 AI tech-writer in CI`

| Bead | Role | Title | Depends on |
|------|------|-------|-----------|
| BEAD-01 | dev | Non-interactive **mark-synced CLI** (wrap `mark_synced_by_ref`; closes UX #106) | — |
| BEAD-02 | dev | **Harness** `tools/ai_techwriter/` (platform-agnostic): scope (`sync-check --json`) → per-doc packet → invoke-Goose (abstracted, mockable) → mark-synced → fixpoint → `beadloom ci` → branch + PR/MR; retry/budget caps; PR-vs-flagged; **PR/MR platform adapter** (`gh` / `glab`\|GitLab API); **emits run-record** to `.beadloom/ai_techwriter_runs.json` (G9) | BEAD-01 |
| BEAD-03 | dev | **Goose recipe + Qwen3.7-Plus provider** config: instructions ported from `.claude/agents/tech-writer.md`, constrained tool allow-list (read-only code + git + beadloom read; write only `docs/**`), thinking enabled | BEAD-02 |
| BEAD-04 | dev | **Both CI wrappers** — `.github/workflows/ai-techwriter.yml` + `.gitlab-ci.yml` `ai-techwriter` job (dispatch/manual + schedule); same harness, per-platform trigger/secret/PR-MR; 0-stale → no-op | BEAD-02, BEAD-03 |
| BEAD-05 | dev | **`beadloom setup-ai-techwriter [--platform github\|gitlab]`** scaffold (setup-* family): templatize the chosen platform's wrapper + recipe + `docs/guides/ai-techwriter.md`; idempotent, config-check-friendly (G8) | BEAD-03, BEAD-04 |
| BEAD-06 | dev | **Dashboard widget (G9)**: `application/site_dashboard.py` + Vue component reading `.beadloom/ai_techwriter_runs.json` → "AI tech-writer activity" + token spend (tokens fact; $ labeled estimate; only real runs; reuses `TrendCharts`) | BEAD-02 |
| BEAD-07 | test | Tests: mark-synced CLI; setup command; **harness with Goose+model mocked** (scope, fixpoint incl. re-stale-siblings, gate decision, PR-vs-flagged, budget caps, run-record emission); widget data-builder | BEAD-01..06 |
| BEAD-08 | review | Code review (read-only): correctness, deterministic/agent boundary, safety (docs-only writes, no auto-merge, budget caps), honesty framing (tokens fact / $ estimate), mypy/ruff | BEAD-07 |
| BEAD-09 | dogfood | **G6 — real end-to-end run** (needs `QWEN_API_KEY`; run by main loop/owner): **GitHub** on Beadloom's own drift (#130/#131) → reviewable PR, `sync-check`→0 + `beadloom ci` green + run-record/widget populated; **GitLab** validated on the team's private GitLab repo | BEAD-08 |
| BEAD-10 | tech-writer | `docs/guides/ai-techwriter.md` (getting-started, 3-step) + CHANGELOG + ROADMAP status (F4.1) | BEAD-09 |

## Waves

```
W1 (dev):   BEAD-01  (mark-synced CLI — foundational)
W2 (dev):   BEAD-02  (harness + PR/MR adapter + run-record emission; Goose mocked)
W3 (dev):   BEAD-03  (Goose recipe + Qwen provider)
W4 (dev):   BEAD-04  (both CI wrappers: GitHub + GitLab)
W5 (dev):   BEAD-05  (setup-ai-techwriter scaffold)
W6 (dev):   BEAD-06  (dashboard widget — depends only on BEAD-02)
Test:       BEAD-07  (after all dev)
Review:     BEAD-08  (after test)  ── ISSUES → fix beads → re-run
Dogfood:    BEAD-09  (after review OK; real model run — owner/main-loop, needs key)
Docs:       BEAD-10  (after dogfood)
```

## Critical path

BEAD-01 → 02 → 03 → 04 → 05 → 07 → 08 → 09 → 10. BEAD-06 (widget) is **off the critical path** — it depends only on BEAD-02 (the emission), so it can run alongside W4/W5.

## Parallelism

- Largely sequential by design (the agentic loop is one thread — principle #1). The one independent branch is **BEAD-06 (widget)**: needs only BEAD-02's run-record, so it may run in parallel with BEAD-04/05. If run in parallel, isolate (worktree) or sequence to avoid the shared-tree pre-commit collision (UX #118).

## Acceptance (epic-level)

- [ ] G1 closed scoped loop (only sync-check-flagged docs; fixpoint to 0).
- [ ] G2 grounded by `sync-check --json` + `docs polish --json` + `ctx`/`why` + tool-use.
- [ ] G3 Goose + Qwen3.7-Plus (external), no local model, no tiering, **thinking enabled**.
- [ ] G4 honest+safe: proposal → gate (`sync-check`0 + `ci`) → PR; no auto-merge; budget caps; failure → flagged PR.
- [ ] G5 CI-runnable on **both** GitHub Actions and GitLab CI (one platform-agnostic harness + per-platform wrapper/adapter) + VPS runner.
- [ ] G6 dogfood: GitHub — real PR on Beadloom's own drift; GitLab — validated on the team's private repo.
- [ ] G7 docs + CHANGELOG + ROADMAP.
- [ ] G8 simple opt-in: `setup-ai-techwriter` + ≤3-step checklist.
- [ ] G9 activity + token tracking: harness emits the run-record; dashboard widget shows activity + token spend (tokens fact, $ labeled estimate).
- [ ] Gates green: pytest, ruff, mypy, `beadloom ci`; anonymization clean.

## Notes

- **Secrets:** the model call needs `QWEN_API_KEY`. Dev/test mock it. BEAD-08 (real run) is executed by the main loop / owner (subagents hold no secrets); the owner provides the VPS runner + key (or runs the loop locally with the key).
- `tools/ai_techwriter/` must be covered by ruff/mypy/pytest (extend scope beyond `src/` if needed).
- No DB migration; the mark-synced CLI only re-baselines existing `sync_state` rows.
- **Dual-platform (GitHub + GitLab) is first-class** (per team architecture doc `.claude/development/docs/BDL-AI-AGENTS-ARCHITECTURE.md`): one platform-agnostic harness, per-platform thin wrapper + PR/MR adapter. GitLab validated on the team's private repo.
- **Beads is NOT in the F4.1 runtime** (Goose + Beadloom + Qwen only); it remains the dev-flow tracker + a future agentic-stack component.
