# PRD: BDL-037 — F1: Federation Foundation (thinnest live slice)

> **Status:** Approved
> **Created:** 2026-06-01

---

## Problem

Beadloom today is **single-repo**: each `.beadloom/` graph describes one repository in isolation. But the target reality (per `project-vision`) is a **microservices landscape** — multiple repos whose real value lives in the *connections between them*: who calls whom, through which contract, and whether the contract matches on both sides. A per-repo graph cannot express `@other-repo:NODE`, cannot aggregate a system-wide picture, and cannot detect cross-service drift. This is the #1 priority of the project's vision and STRATEGY-3 Phase F1.

The F1 landscape discovery (`.claude/development/F1-landscape-analysis.md`) confirmed the shape on real systems: 4 repos, one cleanly bidirectional contract (`core-monolith ↔ integration-service` over RabbitMQ), plus `planned`/`deprecated`/`undeclared` edges that a naive single-repo view cannot represent.

## Impact

Without federation, the whole STRATEGY-3 thesis (one honest source of truth for the whole landscape; intent-vs-reality at the system level; a VitePress IT-landscape map) cannot exist. F1 is the foundation every later phase (F2 contract graph, F3 CI enforcement, F4 living docs) builds on. We deliberately scope F1 to the **thinnest end-to-end thread** (ship + dogfood on the real landscape) rather than the full federation surface — to learn the hard problems on a live system before broadening.

## Goals

- [ ] **Cross-repo node identity:** a graph node can reference a node in another repo as `@<repo>:<ref_id>` (e.g. `@integration-service:plans`), resolvable to a real target when that repo's export is available.
- [ ] **`beadloom export`:** a repo can emit its graph + contract edges as a versioned, self-describing artifact (JSON), stamped with its commit SHA, for external consumption.
- [ ] **Hub aggregation:** a central hub can ingest N satellite exports and compose a single federated graph (landscape) spanning repos, with cross-repo edges resolved.
- [ ] **Lifecycle status (Principle 8):** nodes and edges carry `active | planned | deprecated | dead`; the federated view computes three-valued intent-vs-reality (active+absent = DRIFT, planned+absent = expected, undeclared+present = UNDECLARED).
- [ ] **Cross-service contract edge (AMQP first):** model the `core-monolith ↔ integration-service` RabbitMQ contract as a federated edge with protocol + contract-source + "confirmed both-sides?" status.
- [ ] **Temporal consistency:** the hub records how stale each satellite view is (e.g. "integration-service export is N commits / T behind") so the federated picture never silently lies.
- [ ] **Dogfood:** prove the slice on the real `core-monolith` + `integration-service` repos + their RabbitMQ edge; capture friction in `BDL-UX-Issues.md`.

## Non-goals (deferred to later F-phases)

- Full F2 contract graph for ALL protocols (GraphQL/REST/gRPC) — F1 does AMQP only, as a foundation.
- Monorepo workspaces / multiple `_graph/` roots in one repo (STRATEGY-2 task 13.4) — not needed by the 4-repo landscape.
- CI/CD wiring of the hub (auto pull on push, GitLab registry artifacts) — F1 defines the artifact format + manual aggregation; CI automation is a follow-up.
- VitePress landscape rendering (F4) and semantic search (F5).
- Auto-building satellite graphs (bootstrap accuracy) — satellites are hand-curated per Principle 8 draft-then-review.

## User Stories

### US-1: Reference another repo's node
**As** an architect, **I want** to declare `depends_on: @integration-service:plans` in `core-monolith`'s graph, **so that** a cross-service dependency is explicit and resolvable.

**Acceptance criteria:**
- [ ] `@repo:ref_id` parses and validates; unresolved refs are reported, not silently dropped.
- [ ] `beadloom` distinguishes a local node from a cross-repo reference.

### US-2: Export a repo for federation
**As** a satellite repo owner, **I want** `beadloom export` to produce a versioned artifact, **so that** the hub can consume my graph + contracts without cloning my repo.

**Acceptance criteria:**
- [ ] Export is JSON with schema version + source commit SHA + nodes + edges (incl. lifecycle status + contract metadata).
- [ ] Export is deterministic and reviewable.

### US-3: Compose the landscape at the hub
**As** the hub maintainer, **I want** to aggregate satellite exports into one federated graph, **so that** I can see the whole landscape and cross-repo edges in one place.

**Acceptance criteria:**
- [ ] Hub ingests ≥2 exports, resolves `@repo:node` edges across them.
- [ ] Cross-service contract edge (core-monolith ↔ integration-service AMQP) appears with both-sides status.
- [ ] Three-valued intent-vs-reality computed (active/planned/deprecated/undeclared).
- [ ] Each satellite's staleness is shown.

### US-4: Honest about what's missing
**As** anyone reading the federated view, **I want** unresolved refs, stale satellites, and `planned`/`undeclared` edges clearly flagged, **so that** the landscape never silently lies (the project's core value).

**Acceptance criteria:**
- [ ] Unresolved `@repo:node`, stale exports, and lifecycle mismatches are surfaced explicitly.

## Acceptance Criteria (overall)

- [ ] `@repo:ref_id` identity works end-to-end (declare → export → resolve at hub).
- [ ] `beadloom export` artifact format defined + implemented + tested.
- [ ] Hub aggregates ≥2 satellite exports into a federated graph with cross-repo edges + lifecycle + staleness.
- [ ] The real `core-monolith ↔ integration-service` RabbitMQ contract edge is represented with both-sides status, on the actual repos (dogfood).
- [ ] `beadloom lint --strict` / `doctor` stay green on Beadloom itself; tests pass; coverage ≥ 80%.
- [ ] `honest ≠ complete`: anything that proves bigger than the thin slice is re-scoped transparently, never faked.
