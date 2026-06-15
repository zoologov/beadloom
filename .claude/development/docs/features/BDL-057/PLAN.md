# PLAN: BDL-057 — Freshness for reference / overview documentation

> **Status:** Approved
> **Created:** 2026-06-15
> **Type:** feature
> **PRD:** ./PRD.md · **RFC:** ./RFC.md · **CONTEXT:** ./CONTEXT.md

---

## Beads (created only after this PLAN is Approved)

Parent: **BDL-057 [feature]** — Freshness for reference / overview documentation.

| Bead | Role | Scope | Depends on |
|------|------|-------|-----------|
| **.1** | dev | **Layer 1 — fact freshness in the Gate.** Drop `[experimental]` from `docs audit` (docstring + banner). Add `_step_docs_audit` `GateStep` to `run_ci_gate` (after `sync-check`), failing on `stale>0`; map audit findings to the shared finding shape. Thin gate-friendly entry in `doc_sync/audit.py` if needed. Annotations + tests (TDD). | — |
| **.2** | dev | **Layer 2 — surface-drift mechanism.** New `doc_sync/surface.py`: parse `<!-- beadloom:watches=... -->`; compute `cli`/`graph`/`flow.yml` signatures + aggregate hash. New `reference_state` table (`infrastructure/db.py`, created on reindex). Wire into `engine.py`: discover watched docs, baseline on reindex, emit `surface_drift` (severity=warning) on drift without touching symbol-pair logic. `sync-update <doc>` recomputes the baseline. `sync-check` rich/JSON renders the warning. Annotations + tests (TDD). | — |
| **.3** | test | Cross-cutting coverage: Layer 1 blocking on `stale>0` + safe when clean; Layer 2 baseline/drift/clear for each surface (`cli`/`graph`/`flow.yml`) + aggregate; warn-not-block in the Gate; no regression to symbol-pair sync-check + reason-masking; backward-compat no-op when no annotations. Coverage ≥ 80%. | .1, .2 |
| **.4** | review | Correctness, architecture boundaries (`doc_sync` stays clean; no `application`→infra leak), security, no overclaim, dogfood verdict. Read-only; posts findings. | .3 |
| **.5** | tech-writer | **G4 + feature docs.** Fill the 11 skeleton SPECs with code-accurate 2.0.0 prose (draft source: `archive/BDL-051-docs`); make Beadloom's own docs `docs audit`-clean. Declare `<!-- beadloom:watches=... -->` on README.md, README.ru.md, docs/getting-started.md, docs/architecture.md. Document the feature: `docs/services/cli.md` (`docs audit` stable + `sync-check` surface drift), getting-started, the agentic/CI guide as needed. Reindex + sync-check clean. | .4 |

11 skeleton SPECs to fill (.5): `context-oracle/features/{route-extraction,code-indexer,test-mapping}/SPEC.md`, `graph/features/snapshot/SPEC.md`, `application/features/{ci-gate,site-generation}/SPEC.md`, `doc-sync/features/sync-check/SPEC.md`, `onboarding/features/{agentic-flow-setup,ai-techwriter-setup,branch-protection,config-check}/SPEC.md`.

## Dependencies / DAG

```
.1 (dev: Layer 1) ─┐
.2 (dev: Layer 2) ─┴─> .3 (test) ─> .4 (review) ─> .5 (tech-writer)
```

## Waves

- **Wave 1 (parallel):** `.1` ∥ `.2` — independent dev units (worktree isolation; integrate by file-checkout). `.1` touches `cli.py`/`gate.py`/`audit.py`; `.2` touches `doc_sync/surface.py`/`engine.py`/`db.py`/`cli.py` (sync-update). Light `cli.py` overlap — coordinate the merge (one merge-slot).
- **Wave 2:** `.3` test (after both dev).
- **Wave 3:** `.4` review.
- **Wave 4:** `.5` tech-writer (fills skeletons, declares watches, makes docs audit-clean) → final `beadloom ci` green (Layer 1 blocking now satisfied).

## Critical path

`.2 (Layer 2 mechanism)` → `.3` → `.4` → `.5`. (`.1` is smaller and parallel.)

## Notes

- One branch `features/BDL-057`, commit per wave, ONE PR to `main`.
- Dogfood gate: Layer 1 is wired in `.1` but the repo only goes green once `.5` makes the docs audit-clean — expected; the final Gate (post-`.5`) is the authority.
- After merge: delete the `archive/BDL-051-docs` tag; release prep (likely **2.1.0**, additive) follows BDL-057 per owner's plan.
