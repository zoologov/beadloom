# ACTIVE: BDL-038 — F2: Cross-Service Contract Graph

> **Last updated:** 2026-06-01

---

## Current Focus

- **Phase:** Wave 1 done; investigating subagent write-block before Wave 2
- **Epic bead:** `beadloom-9xk`
- **Next bead:** Wave 2 — `beadloom-9xk.2` (AMQP) ∥ `.3` (GraphQL) ∥ `.7` (U1) once subagent write-block is resolved
- **Blockers:** subagent write-block (Wave 1 done inline as fallback) — root-cause investigation in progress per owner request

## Bead Map (epic `beadloom-9xk`)

| Bead | Role | P | Status | Depends |
|------|------|---|--------|---------|
| .1 Contract model + protocol-aware contract_key | dev | P0 | **DONE** (inline fallback) | — |
| .2 AMQP exchange/routing enrichment | dev | P0 | open | .1 |
| .3 GraphQL SDL source | dev | P0 | open | .1 |
| .4 Contract-level verdicts | dev | P0 | open | .2, .3 |
| .5 external/unmapped lifecycle + CHECK rebuild | dev | P1 | open | .4 |
| .6 Nested landscapes | dev | P0 | open | .4 |
| .7 U1 paradigm round-trip hardening | dev | P1 | open | .1 |
| .8 Dogfood (live mismatch + Product-B FSD) | dev | P1 | open | .2–.7 |
| .9 Test suite + back-compat + coverage | test | P0 | open | .1–.8 |
| .10 Review | review | P0 | open | .9 |
| .11 Tech-writer (SPEC + README RELEASE GATE) | tech-writer | P1 | open | .10 |

## Waves

- **Wave 1 (solo dev):** .1 — foundation (Contract model).
- **Wave 2 (parallel dev):** .2, .3, .7 — independent, depend only on .1.
- **Wave 3 (dev):** .4 — verdicts (needs both protocols).
- **Wave 4 (parallel dev):** .5, .6 — independent, depend on .4.
- **Wave 5 (solo dev):** .8 — dogfood (anonymized; merge-slot to land).
- **Wave 6 (test):** .9.
- **Wave 7 (review):** .10 → fix cycle if ISSUES.
- **Wave 8 (tech-writer):** .11 — README RELEASE GATE.

## Progress Log

- 2026-06-01 — `/task-init` complete: PRD / RFC / CONTEXT / PLAN approved; epic `beadloom-9xk` + 11 sub-beads created; DAG wired; `bd ready` confirms .1 unblocked.
- 2026-06-01 — Wave 1 (BEAD-01) DONE: new `graph/contracts.py` (`Contract`/`ContractEndpoint`/`ContractVerdict` skeleton, protocol-aware `contract_key`, `reconcile_contracts`); `federation.py` `_reconcile_contracts` delegates + projects via `to_report_dict` (F1 byte-identical). 2723 tests pass; ruff/mypy/lint/doctor green; sync-check honest 0 (graph README documented contracts.py + `# beadloom:domain=graph` annotation added + re-attested to fixpoint — F4.1 invariant; surfaced UX #105/#106). Background dev subagent was **write-blocked** (3rd occurrence) → completed inline. Loader `_contract_key` unification + AMQP exchange deferred to BEAD-02 (avoids breaking `test_graph_loader.py:535`).

## Notes / Reminders

- **Anonymization (binding):** Product-B name + domain-fingerprinting tech NEVER committed (working tree, history, commit messages). Confirm before any force-push.
- **Backward-compat is a hard gate:** v1 export must federate; AMQP-only = F1; single-product = F1. EXPORT 1→2, FEDERATION 1→2, DB SCHEMA 3→4 all read older inputs.
- **README rewrite (.11) is a RELEASE GATE** — next release does not ship without the federation positioning headline.
- Re-run `sync-check` to fixpoint after `mark_synced` (F4.1 loop invariant — second-order `untracked_files` masking).
