# PRD: BDL-038 — F2: Cross-Service Contract Graph

> **Status:** Approved
> **Created:** 2026-06-01

---

## Problem

F1 (BDL-037) shipped the federation *foundation* — cross-repo identity (`@repo:ref_id`), the `lifecycle` field, `beadloom export`, and `beadloom federate` with a three-valued intent-vs-reality `EdgeVerdict`. But it is a deliberately thin slice: **AMQP only**, contract metadata buried inside an edge's `extra` JSON, reconciliation matched purely on `message_type`, and Python-on-both-sides. It cannot yet answer the question that actually makes Beadloom defensible (STRATEGY-3 §2):

> *Does this contract match on both sides — across services, across paradigms, across languages — and is it about to break?*

The target landscape is polyglot and multi-paradigm: a backend that **produces** a GraphQL schema and AMQP messages, and frontend/mobile clients (TS/FSD, Swift/Kotlin bridges) that **consume** them. Today a TS client's `consumes @backend:GraphQLSchema` cannot be expressed or reconciled — contract identity is tied to a code symbol, not the contract *name*, so it cannot resolve across a language boundary. And a freshly bootstrapped FSD repo's `page/feature/entity/repository` nodes are untested through `export → federate`. F2 is where federation stops being "two Python repos sharing a message type" and becomes the **cross-service contract graph** — the differentiated killer feature.

## Impact

F2 is the phase the whole STRATEGY-3 thesis hinges on. The visual IT-landscape map (F4) renders the F2 contract graph; the CI enforcement (F3) gates on F2 verdicts; the README positioning rewrite (the next-release RELEASE GATE) can only lead with "federated architecture infrastructure with intent-vs-reality enforcement" once F2 makes that real and no longer over-promises. Without F2 the product stays a single-repo context-oracle with an experimental federation footnote.

The success criterion is concrete (STRATEGY-3 §"What done looks like"): **Beadloom detects a real contract mismatch between two of the maintainer's services before it ships** — and proves paradigm-agnosticism on a real FSD repo (Product-B), not on paper.

## Goals

- [ ] **G1 — Contract as a first-class object.** Promote the cross-service contract out of `edge.extra` into a first-class, protocol-agnostic model: `contract_key` (language-neutral identity), `protocol` (`amqp | graphql`), producer side, consumer side(s), `lifecycle`, source file, confirmed-both-sides status. The federated graph carries a `contracts` collection that is the unit of reconciliation.
- [ ] **G2 — GraphQL SDL contract source (U2).** Beyond AMQP: a backend `produces` a parsed `schema.graphql`; a frontend/mobile client declares `consumes @backend:<GraphQLSchema>`. Both-sides reconciliation works with a UI client as the consumer (first non-Python, non-backend consumer in federation).
- [ ] **G3 — Language-neutral `contract_key` / `FederatedRef` (U3).** Contracts resolve on the **contract name** (GraphQL operation/type, AMQP message type/exchange/queue), never on a language-specific code symbol — so a TS↔backend edge resolves across the language boundary.
- [ ] **G4 — AMQP contract enrichment.** Fold queue/exchange identity (deferred from F1, where matching was `message_type`-only) into the `contract_key`, so two services that share a message *name* but a different exchange/routing are not falsely confirmed.
- [ ] **G5 — Contract-level intent-vs-reality.** Verdicts computed at the contract level (not just per-edge): **DRIFT** (declared-active contract absent on a side), **ORPHANED_CONSUMER** (consumes a contract nobody produces), **UNDECLARED_PRODUCER** (produces a contract nobody declares consuming), and a **basic GraphQL breaking-shape check** (a consumer references an operation/type/field the producer's current SDL no longer exposes).
- [ ] **G6 — Paradigm-agnostic round-trip (U1).** `export`/`federate` carry arbitrary `kind` / `edge_kind` (FSD `page/feature/entity/repository` alongside DDD `domain/service`) with **zero loss or rejection**. A freshly bootstrapped FSD repo's nodes survive `export → federate` intact.
- [ ] **G7 — `external` / `unmapped` lifecycle (U4).** Present-but-not-indexed nodes (native Swift/Kotlin/ObjC++/C++ bridges in `modules/`) are tagged `external` / `unmapped`, **not** dropped into DRIFT/UNDECLARED noise. Extends Principle 8.
- [ ] **G8 — Nested landscapes (U5).** `federate` composes a single **product-landscape** *or* a **company-landscape** that aggregates several products. Cross-product contract edges appear only where integration is real; contract-less products/satellites never cross-pollute each other's verdicts.
- [ ] **G9 — Dogfood (the success criterion).** (a) Detect a real contract mismatch on the maintainer's live landscape before it ships; (b) run the U1 paradigm-agnostic round-trip on Product-B's real FSD mobile graph (anonymized). Capture friction in `BDL-UX-Issues.md`.
- [ ] **G10 — README positioning rewrite (RELEASE GATE).** The tech-writer wave leads `README.md` / `README.ru.md` with the §2 federation positioning + a proper federation headline section. Named deliverable; the next release does not ship without it.

## Non-goals (deferred to later F-phases)

- **REST / OpenAPI and gRPC contract sources** — REST is runtime-generated (no static SDL) and lowest priority per the F1 analysis; gRPC is not on the real landscape yet. F2 does AMQP + GraphQL.
- **Full schema-diff-over-time / semantic versioning of contracts** — F2's breaking-shape check is *presence-based* (does the consumed operation/type/field still exist in the producer's current SDL), not a historical version-delta engine.
- **CI/CD wiring** (auto-pull on push, registry artifacts, PR gates on verdicts) — F3.
- **VitePress visual landscape map / AI-tech-writer-in-CI / dashboard** — F4.
- **SaaS hub / satellite auto-bootstrap** — federation stays file-based + manual aggregation, as in F1.
- **Auto-deriving the producer GraphQL contract from running code** — the producer side declares `produces <schema.graphql>`; we parse the SDL file, not introspect a live server.

## User Stories

### US-1: Express a cross-paradigm contract
**As** a frontend/mobile architect, **I want** my client's graph to declare `consumes @backend:GraphQLSchema`, **so that** a TS-client → backend-schema dependency is explicit and reconcilable across the language boundary.

**Acceptance criteria:**
- [ ] A consumer node in one repo can declare consumption of a GraphQL contract produced in another repo, resolved by contract name (not code symbol).
- [ ] The producer repo declares `produces` a parsed `schema.graphql`; both sides meet at the hub.

### US-2: Detect a contract mismatch before it ships
**As** the landscape maintainer, **I want** `federate` to flag a contract that does not match on both sides, **so that** I catch the break before deploy.

**Acceptance criteria:**
- [ ] DRIFT: a declared-active contract present on only one side is flagged.
- [ ] ORPHANED_CONSUMER: a consumer of a contract nobody produces is flagged.
- [ ] UNDECLARED_PRODUCER: a producer of a contract nobody consumes is flagged.
- [ ] GraphQL breaking-shape: a consumer referencing an operation/type/field absent from the producer's current SDL is flagged.

### US-3: Compose a multi-product company landscape
**As** the company-landscape maintainer, **I want** `federate` to aggregate several independent products, **so that** I see cross-product contracts where they exist without forcing standalone products into mutual drift noise.

**Acceptance criteria:**
- [ ] Two products that share no contract produce **zero** mutual DRIFT/UNDECLARED.
- [ ] A real cross-product contract edge appears with a both-sides verdict.
- [ ] Product-B is modeled as its own product-landscape (not a satellite of the core-monolith landscape).

### US-4: Survive a foreign paradigm intact
**As** an FSD-repo owner, **I want** my `page/feature/entity/repository` nodes (and native bridge nodes) to round-trip through `export → federate` with no loss, **so that** Beadloom is paradigm-agnostic, not DDD-only.

**Acceptance criteria:**
- [ ] Arbitrary `kind` / `edge_kind` survive `export → federate` byte-faithfully (no rejection, no coercion to DDD kinds).
- [ ] Non-indexed native nodes are tagged `external` / `unmapped`, not DRIFT.
