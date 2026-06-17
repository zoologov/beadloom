# PLAN: BDL-060 — Integration Map with Data

> **Status:** Approved
> **Created:** 2026-06-17
> **Type:** epic
> **PRD/RFC/CONTEXT:** all Approved (RFC v2, refocused on GraphQL + AMQP)

---

## Shape

One epic, **6 dependency-ordered slices**, one PR each, sequential (principle 1 — one thread at a time). Each slice carries the mandatory 4-role bead structure: **dev → test → review → tech-writer**, TDD, behavior-preserving, `beadloom ci` rc0, dogfooded on the anonymized landscape fixture before "done". Heavy slices (S2/S4) may use worktree-isolated parallel dev if a slice splits into independent dev beads; integrate by file-checkout + 3-way on the shared seam.

Parent bead: `--type epic` (enables `bd swarm`), title `[BDL-060] Integration Map with Data`.

## Slices & acceptance

- **S1 (G6) — atomic YAML writes.** `write_yaml_atomic(path, data)` (temp in same dir + `os.replace`) used by every graph-YAML writer (graph loader/patchers + onboarding `services.yml` patchers). _Accept: regression test — simulated mid-write crash leaves the prior file intact; behavior-preserving (identical final bytes); ci rc0._
- **S2 (G1a) — GraphQL Tier-A (deep, incl. subscriptions).** Typed surface (queries/mutations/subscriptions; fields `{name,type+nullability+list,args}`; nested types) via `graphql-core` optional extra; native breaking verdict in `contracts.py`; export `contract.fields` (sorted/deduped). _Accept: on the dogfood fixture, a consumer referencing a dropped/retyped/nullability-broken field (incl. a subscription field) → `BREAKING` naming it; additive producer change → benign; absent the extra → honest name-level fallback; golden export/federate byte-parity; ci rc0._
- **S3 (G1b) — AMQP body (JSON-Schema + optional AsyncAPI ingestion).** `contract.body` (JSON-Schema) on the edge; body-field/type diff verdict; AsyncAPI ingestion adapter (source-only). _Accept: a consumer referencing a body field/type absent/changed vs the producer body schema → `BREAKING` naming it; AsyncAPI doc → extracted JSON-Schema body; honest degradation absent the adapter; golden parity; ci rc0._
- **S4 (G2) — interactive landscape (Cytoscape + ELK).** `landscape.data.json` (sorted nodes/edges/contracts + build-time ELK `preset` positions); Cytoscape view page; clickable contract pop-up showing protocol/routing/verdict/producer↔consumer + the S2/S3 field surface; theme config. _Accept: deterministic regeneration (byte-stable); pop-up shows REAL fields for ≥1 GraphQL + ≥1 AMQP contract on the fixture; honest "unknown" when data missing; no `ignoreDeadLinks`; ci rc0._
- **S5 (G3) — live cross-repo `ctx`.** `build_context` enriches a node bundle with resolved `@repo-B:…` contract neighbours (+ their field surface) from `federated.json` when available; cache etag folds in the federation artifact identity; single-repo bundles byte-identical when no federation. _Accept: `ctx <node-with-cross-repo-contract>` on the federated fixture shows the `@repo-B:…` neighbour + its fields; no federation → unchanged bundle; cache hit/miss correctness; ci rc0._
- **S6 (G4) — undeclared sweep + `unverified` lifecycle.** `unverified` added to the lifecycle set (reconciler = "needs review", not DRIFT); a sweep command emits code-inferred undeclared producer/consumer integrations as `unverified` entries; conflicts flagged for human review (never auto-activated). _Accept: the sweep finds the seeded undeclared integration in the fixture and writes it `unverified`; a conflicting inference is flagged, not applied; report/gate surface the "needs review" bucket; ci rc0._

## Bead DAG (created only after this PLAN is Approved)

```
beadloom-XXXX [epic] [BDL-060] Integration Map with Data
│
├─ S1 (G6 atomic YAML)
│   ├─ .1  [dev]         write_yaml_atomic + route all graph-YAML writers through it
│   ├─ .2  [test]        crash-mid-write regression + byte-parity      (dep .1)
│   ├─ .3  [review]      safety + behavior-preservation                (dep .2)
│   └─ .4  [tech-writer] infra DOC + any SPEC                          (dep .3)
│
├─ S2 (G1a GraphQL Tier-A)            (dep .4)
│   ├─ .5  [dev]         typed surface incl. subscriptions + native breaking verdict + export fields
│   ├─ .6  [test]        golden surface/verdict (incl. subscription break, nullability, args) (dep .5)
│   ├─ .7  [review]      data strictness + determinism + Hive-positioning honesty            (dep .6)
│   └─ .8  [tech-writer] federation SPEC + graph README                (dep .7)
│
├─ S3 (G1b AMQP body)                 (dep .4; sequenced after S2)
│   ├─ .9  [dev]         contract.body JSON-Schema + body-diff verdict + AsyncAPI ingestion adapter
│   ├─ .10 [test]        golden body diff + AsyncAPI extraction + degradation (dep .9)
│   ├─ .11 [review]      strictness + determinism                       (dep .10)
│   └─ .12 [tech-writer] federation SPEC + contract docs                (dep .11)
│
├─ S4 (G2 viz)                        (dep .8 + .12)
│   ├─ .13 [dev]         landscape.data.json + ELK build-time layout + Cytoscape view + pop-up + theme
│   ├─ .14 [test]        determinism (byte-stable) + pop-up data + dead-link guard (dep .13)
│   ├─ .15 [review]      readability/no-overlap + honest degradation + determinism (dep .14)
│   └─ .16 [tech-writer] site/viz guide + README portal note           (dep .15)
│
├─ S5 (G3 cross-repo ctx)             (dep .8 + .12)
│   ├─ .17 [dev]         build_context federated-neighbour enrichment + cache-etag fold-in
│   ├─ .18 [test]        cross-repo neighbour + no-federation parity + cache hit/miss (dep .17)
│   ├─ .19 [review]      F1-honesty + cache correctness                 (dep .18)
│   └─ .20 [tech-writer] ctx/context-oracle SPEC                        (dep .19)
│
└─ S6 (G4 sweep + unverified)         (dep .12; sequenced after S5)
    ├─ .21 [dev]         unverified lifecycle + sweep command + conflict-flagging
    ├─ .22 [test]        seeded undeclared → unverified + conflict-flag + reconciler bucket (dep .21)
    ├─ .23 [review]      anti-"MySQL-mistake" (no silent auto-activate) + lifecycle correctness (dep .22)
    └─ .24 [tech-writer] lifecycle + sweep docs                         (dep .23)
```

## Critical path

`S1 → S2 → S3 → S4 → S5 → S6` (sequential, one slice/PR at a time). Within each slice: dev → test → review → tech-writer (bead deps are the gates). S4/S5/S6 each hard-depend only on S2+S3 (S6 on S3), but run one-at-a-time per principle 1.

## Out (deferred, NOT beaded here)

External cross-protocol verdict federation (`buf`/protobuf, Pact, REST/OpenAPI), full AsyncAPI, live web hub, Backstage emit, model tiering — future epic(s).
