# ACTIVE: BDL-060 — Integration Map with Data

> **Type:** epic
> **Parent bead:** beadloom-8qqp
> **Branch:** features/BDL-060
> **Updated:** 2026-06-17

---

## Current focus

**Docs Approved** (PRD/RFC v2/CONTEXT/PLAN). Epic `beadloom-8qqp` + 24 beads created, linear slice DAG (only S1 `.1` ready). **Next: start S1 (G6 atomic YAML writes)** — the foundational-safety warmup. Scope refocused (owner): GraphQL (incl. subscriptions) + AMQP done maximally; external cross-protocol verdict federation (protobuf/Pact/REST) deferred. Viz = Cytoscape + ELK. Standards: TDD + DDD + cohesion-driven + data-strictness, Gate-green + dogfood per slice.

## Slice status

| Slice | Beads | State |
|-------|-------|-------|
| S1 atomic YAML | .1–.4 | ready (.1 dev) |
| S2 GraphQL Tier-A | .5–.8 | blocked → S1 |
| S3 AMQP body | .9–.12 | .9 dev DONE (amqp_body + asyncapi + contract.body body-diff verdict; ci rc0; 3 seeds green); .10–.12 next |
| S4 viz (Cytoscape+ELK) | .13–.16 | blocked → S3 |
| S5 cross-repo ctx | .17–.20 | blocked → S4 |
| S6 sweep + unverified | .21–.24 | blocked → S5 |

## Plan notes

- One PR per slice on `features/BDL-060` (sequential; principle 1). Each slice: dev → test → review → tech-writer, TDD, behavior-preserving, `beadloom ci` rc0, dogfooded on the anonymized landscape fixture.
- Key decisions: Cytoscape+ELK (build-time preset, byte-stable); native deep GraphQL (incl. subscriptions, Hive-aware, no external tool); AMQP JSON-Schema body + optional AsyncAPI ingestion; `unverified` = new lifecycle value; G5 deferred.
- Seams confirmed against HEAD per slice (coordinator does NOT read raw source). Carry BDL-059 lessons: worktree integration via file-checkout + 3-way + #133 re-baseline; recompose without `--force`; verify under multiple seeds; `site/` gitignored.

## Progress log

- 2026-06-17 — PRD → RFC v2 (refocused GraphQL+AMQP, G5 deferred) → CONTEXT + PLAN all Approved. Epic beadloom-8qqp + 24 beads created, linear slice DAG. Branch features/BDL-060 off main (ecfd6a5, post-BDL-059 + currency #26). Ready to start S1.
