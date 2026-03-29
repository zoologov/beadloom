# ACTIVE: BDL-037 — F1: Federation Foundation

> **Last updated:** 2026-06-01
> **Phase:** Completed — ✅ F1 EPIC CLOSED (9/9 beads + parent). export/federate work; real AMQP both-sides confirmed; 4 dogfood bugs (#100-103) fixed; lint/doctor 0; 2707 tests / 90.5% cov. Subagent-blocked fallback used twice (BEAD-07 review session-limit, done inline).

---

## Epic

**Parent (epic):** `beadloom-eeo` · swarm `beadloom-x29` (max parallelism 2, 7 waves).
**Goal:** cross-repo federation thin slice — `@repo:ref_id` + lifecycle → export → federate → dogfood real AMQP.

## Bead-ID ↔ BEAD-NN (suffixes match this time)

| BEAD | bead-id | Role | Wave |
|------|---------|------|------|
| BEAD-01 | `beadloom-eeo.1` | dev | W1 (@repo identity) |
| BEAD-02 | `beadloom-eeo.2` | dev | W1 (lifecycle) |
| BEAD-03 | `beadloom-eeo.3` | dev | W2 (export) |
| BEAD-04 | `beadloom-eeo.4` | dev | W3 (federate) |
| BEAD-05 | `beadloom-eeo.5` | dev | W4 (dogfood) |
| BEAD-06 | `beadloom-eeo.6` | test | W5 |
| BEAD-07 | `beadloom-eeo.7` | review | W6 |
| BEAD-08 | `beadloom-eeo.8` | tech-writer | W7 |

## Progress

### Wave 1 (parallel dev — foundations) ✅ COMMITTED
- [x] BEAD-01 (.1) — @repo:ref_id identity ✅ (federation.py + loader; 21 tests)
- [x] BEAD-02 (.2) — lifecycle field ✅ (db migration + rule_engine; 28 tests)

### Wave 2-4
- [x] BEAD-03 (.3) export ✅ · BEAD-04 (.4) federate ✅ · BEAD-05 (.5) dogfood ✅

### Wave 5-7
- [ ] BEAD-06 (.6) test · BEAD-07 (.7) review · BEAD-08 (.8) tech-writer

### BEAD-05 dogfood result (2026-06-01)
- Proved F1 end-to-end on the REAL core-monolith ↔ integration-service RabbitMQ contract.
- Scratch slices under `.scratch-federation/` (gitignored). `beadloom export` ×2 → `beadloom federate`.
- ALL 4 message types **confirmed both-sides**: start_plan_version_upload + ensure_plans_folder_path
  (core produces → integration consumes); plan_version_upload_completed +
  ensure_plans_folder_path_completed (integration produces → core consumes, the reverse).
  16 edges all verdict OK, unresolved_refs [], staleness reported per satellite.
- Regression: `tests/test_federate_dogfood_amqp.py` (4 tests) captures both-sides as a durable fixture.
- Findings → BDL-UX-Issues #100–#104: (#100 HIGH export drops `@repo:` cross-repo edges;
  #101 HIGH edge-kind CHECK rejects produces/consumes; #102 MED UNIQUE(src,dst,kind) collapses
  multi-contract; #103 LOW commit_sha leaks host repo HEAD for nested dir; #104 SUCCESS note).

## Results

| Bead | Status |
|------|--------|
| beadloom-eeo.1 | Pending |
| beadloom-eeo.2 | Pending |
| beadloom-eeo.3..8 | Pending |

## Notes

- File-boundary discipline for parallel W1: BEAD-01 owns `graph/loader.py` + new `FederatedRef` parsing (foreign ref = `@repo:id` string in edge src/dst — NOT a new dataclass field). BEAD-02 owns the Node/Edge dataclass (`lifecycle` field) + `infrastructure/db.py` migration + `rule_engine.py`. If a subagent must touch the other's file, it records it in bead comments; coordinator serializes landing via merge-slot.
- Dogfooding feedback → `BDL-UX-Issues.md` throughout (exercising the BDL-035 multi-agent process per user request).
