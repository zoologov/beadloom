# PRD: BDL-060 — Integration Map with Data

> **Status:** Approved
> **Created:** 2026-06-17
> **Type:** epic
> **Issue key:** BDL-060
> **North-star:** (b) team-of-solos / microservices — the federation & landscape use-case (ROADMAP P1)

---

## Problem

A team of solo engineers each runs the Beadloom solo-flow on their own service and federates into one product (north-star b). Today the federation layer can answer *"does a declared cross-service dependency resolve?"* (presence + lifecycle verdicts via `export`/`federate`), and it renders a **Mermaid** landscape. Three honest gaps block this from being the "integration map with data" the team actually needs:

1. **No data on what flows.** The landscape shows that service A talks to service B, but not *what* — the fields/types of the GraphQL operation, the body of the AMQP message. A presence-check can report `CONFIRMED` while the consumer reads a field the producer never exposes (the worst false-CONFIRMED). The team wants a **data-flow / interface map**: what data moves between services.
2. **The viz can't show it.** Mermaid is static — no clickable nodes/edges, no contract pop-up cards. Rich field/type pop-ups are technically impossible in Mermaid.
3. **Single-repo `ctx` is cross-repo-blind.** An agent working on service A, asking `beadloom ctx AUTH`, does **not** see `@repo-B:BILLING` — cross-repo identity lives only in `export`/`federate`, not in context bundles. This is a stated F1 honesty debt and directly undercuts the agentic-flow value for a federated team.

Secondary accuracy/safety gaps surfaced by the same use-case: real-but-**undeclared** integrations are invisible (the landscape under-reports reality); code-inferred nodes are treated as fact rather than `unverified`; verdict sources outside Beadloom (Pact/Buf/graphql-inspector) aren't unified; and graph YAML writes are non-atomic (a crash can corrupt the graph the whole flow depends on).

## Goals

- **G1 — Field-level contract data.** Extract and federate the *fields/types* of cross-service contracts: GraphQL **Tier A** (SDL → operations/fields/types/args) and AMQP **AsyncAPI / JSON-Schema** message bodies. The federated graph and verdicts carry the real interface surface, not just presence.
- **G2 — Interactive landscape with clickable contracts.** Replace Mermaid with an interactive viz (Cytoscape/D3) where nodes/edges are clickable and a **contract pop-up card** shows type/routing/protocol/verdict/producer↔consumer and the G1 field-level surface.
- **G3 — Live cross-repo `ctx`.** A context bundle for a node surfaces its cross-repo contract neighbours (`@repo-B:…`), so an agent on service A sees its real interface with service B. Closes the F1-metric honesty debt.
- **G4 — Landscape accuracy.** An automated sweep surfaces real-but-undeclared integrations; code-inferred nodes start `unverified` and conflicts are flagged, never silently decided (the anti-"MySQL-mistake" guard).
- **G5 — Verdict federation (PoC).** Unify at least one external contract-verdict source (Pact `can-i-deploy` / `buf breaking` / `graphql-inspector`) into Beadloom's `ContractVerdict`, proving the "one landscape, one gate" moat on one protocol.
- **G6 — Graph-write safety.** Graph YAML writes are atomic (temp + `os.replace`), so a crash mid-write cannot corrupt the source-of-truth graph.

## Non-goals

- **Market / adoption features** (marketplace publish, VS Code extension, marketing guides) — explicitly off-north-star (ROADMAP P3).
- **A live web app / SaaS hub.** The portal stays static + CI-generated; federation stays a pull-based CI pattern (ROADMAP "Won't do").
- **REST/OpenAPI, gRPC/proto contract sources** — the most-requested deferred source is REST, but it stays P2 (out of this epic's scope unless a slice has spare capacity).
- **Full bootstrap accuracy upfront** — G4 is a review-gated `unverified` layer, not an attempt to auto-derive a perfect graph.
- **Backstage replacement** — Beadloom *feeds* Backstage (emit `catalog-info.yaml`), it does not replace it.
- **Model tiering** — agentic features keep running on top-tier models (principle 10).

## Users / use-case

- **The team-of-solos** (primary): each member federates their service; they want to *see the product* and *what flows in it*, and to be warned when a contract they depend on breaks — across repos.
- **An AI dev agent on one service** (G3): needs the cross-repo contract context to build/maintain its service without blindly breaking a peer.
- **Beadloom itself** (dogfood acceptance): the anonymized multi-service landscape (`catalog-service` / `storefront-web` + the AMQP/GraphQL contracts already in the test corpus) is the acceptance fixture for every slice.

## Requirements (what "done" means, per goal)

- **R1 (G1):** `graphql-core` behind an optional extra parses SDL to a typed surface (operations, fields, types, args); AMQP edges carry an AsyncAPI/JSON-Schema body declaration. `federate` verdicts use the field surface (a consumer referencing a field absent from the producer surface → `BREAKING`, naming the field). Determinism preserved (byte-stable export/federate).
- **R2 (G2):** the generated site renders an interactive landscape (Cytoscape or D3) with clickable nodes/edges and a contract pop-up card; it degrades honestly when data is missing (no fake fields). Built by the existing `docs site` path; deterministic regeneration; no `ignoreDeadLinks`.
- **R3 (G3):** `beadloom ctx <ref>` includes resolved cross-repo contract neighbours from the federated graph (when a federation artifact is available); honest "unknown" when not federated. No change to single-repo bundles when there is no federation.
- **R4 (G4):** a command surfaces undeclared producer/consumer integrations found in code; inferred nodes are written with `lifecycle: unverified`; conflicts (e.g. an inferred node contradicting a declared one) are flagged for human review, not auto-applied.
- **R5 (G5):** one external verdict source maps into `ContractVerdict` and participates in the gate on a PoC contract; the mapping is documented and the source is optional.
- **R6 (G6):** every graph-YAML write goes through an atomic temp-file + `os.replace` helper; a regression test proves a mid-write crash leaves the prior file intact.
- **R-cross:** every slice keeps Beadloom green on its own `doctor / lint --strict / sync-check / docs audit / beadloom ci`; behavior-preserving where it touches existing surfaces; dogfooded on the anonymized landscape fixture before the slice is called done (principle 2: honest ≠ complete; dogfood = acceptance).

## Success metrics

- The anonymized dogfood landscape renders interactively with a working contract pop-up showing **real fields** for at least one GraphQL and one AMQP contract (G1+G2).
- A deliberately-introduced field-level break (consumer references a dropped field) is caught by `federate`/the gate, **naming the field** — on the dogfood fixture (G1).
- `beadloom ctx <node-with-a-cross-repo-contract>` shows the `@repo-B:…` neighbour on the federated dogfood (G3).
- The UNDECLARED sweep finds the seeded undeclared integration in the fixture and writes it `unverified` (G4).
- One external verdict (PoC) flips the gate on the fixture (G5).
- `beadloom ci` rc 0 on `main` after every slice; no version regression.

## Risks & mitigations

- **Scope is large (6 goals).** → Ship as **dependency-ordered slices, one shippable PR each** (see RFC/PLAN). One thread at a time (principle 1); each slice dogfooded before the next. The epic is "one epic" for coherence, not "one big-bang merge."
- **Tier-A semantic extraction is the spine** — viz pop-ups, better verdicts, and accuracy all depend on having real field data. → Sequence G1 first; G2/G5 consume it.
- **Determinism regressions** in export/federate (the byte-stable invariant). → Golden artifacts per slice; sort/dedupe field surfaces (as the existing GraphQL surface normalization already does).
- **Viz tech (Cytoscape vs D3) is a one-way-ish door.** → Decide in the RFC with a thin-slice spike; keep the data model viz-agnostic so the renderer is swappable.
- **Federation multiplies dishonesty by N repos** (principle 4). → Single-repo honesty (G1 extraction correct on one service) is a prerequisite gate before cross-repo depth (G3+).

## Open questions (to resolve in RFC)

- Cytoscape vs D3 for R2 (rich pop-ups, static-site-embeddable, deterministic).
- Which external verdict source for the G5 PoC (Pact `can-i-deploy` vs `buf breaking` vs `graphql-inspector`) — pick the one closest to the dogfood corpus (GraphQL → `graphql-inspector`).
- AsyncAPI vs a lighter JSON-Schema-only body declaration for AMQP (R1) — how much spec surface to adopt.
- Does G4 (`unverified` lifecycle + review-gated bootstrap) need a new graph node-state, or does the existing lifecycle set suffice?
