# ACTIVE: BDL-037 — F1: Federation Foundation

> **Last updated:** 2026-06-01
> **Phase:** Development

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

### Wave 1 (parallel dev — foundations)
- [ ] BEAD-01 (.1) — @repo:ref_id identity (owns loader.py + FederatedRef)
- [ ] BEAD-02 (.2) — lifecycle field (owns Node/Edge dataclass + db migration + rule_engine)

### Wave 2-7
- [ ] BEAD-03 (.3) export · BEAD-04 (.4) federate · BEAD-05 (.5) dogfood · BEAD-06 (.6) test · BEAD-07 (.7) review · BEAD-08 (.8) tech-writer

## Results

| Bead | Status |
|------|--------|
| beadloom-eeo.1 | Pending |
| beadloom-eeo.2 | Pending |
| beadloom-eeo.3..8 | Pending |

## Notes

- File-boundary discipline for parallel W1: BEAD-01 owns `graph/loader.py` + new `FederatedRef` parsing (foreign ref = `@repo:id` string in edge src/dst — NOT a new dataclass field). BEAD-02 owns the Node/Edge dataclass (`lifecycle` field) + `infrastructure/db.py` migration + `rule_engine.py`. If a subagent must touch the other's file, it records it in bead comments; coordinator serializes landing via merge-slot.
- Dogfooding feedback → `BDL-UX-Issues.md` throughout (exercising the BDL-035 multi-agent process per user request).
