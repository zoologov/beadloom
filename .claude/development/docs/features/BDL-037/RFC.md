# RFC: BDL-037 — F1: Federation Foundation

> **Status:** Approved
> **Created:** 2026-06-01

---

## Overview

Add cross-repo federation to Beadloom as a thin live slice: cross-repo node identity (`@repo:ref_id`), a `beadloom export` artifact, and a hub that aggregates satellite exports into one federated graph with lifecycle-aware, three-valued intent-vs-reality and per-satellite staleness. First contract modeled: the real `core-monolith ↔ integration-service` RabbitMQ edge (AMQP).

## Motivation

### Problem
See PRD. Beadloom is single-repo; the microservices landscape's value is in cross-repo connections. No `@repo:node`, no export, no aggregation, no cross-service drift detection exist today.

### Solution
A small federation capability in the `graph` domain (which owns the Node/Edge model + loader) plus a hub aggregation command. Built thin, dogfooded on the real `core-monolith`/`integration-service` repos.

## Technical Context

### Constraints
- Python 3.10+, ruff + mypy --strict, pytest ≥ 80%, beadloom lint/doctor stay green.
- Existing model (from `graph` domain): `Node(ref_id, kind, summary, source, extra: dict)`, `Edge(src_ref_id, dst_ref_id, kind)`. YAML graph in `.beadloom/_graph/`. SQLite index via reindex.
- `beadloom export` does NOT exist yet (only `diff`, `snapshot`). Greenfield.
- Carries STRATEGY-3 Principle 8 (lifecycle status + three-valued intent-vs-reality + draft-then-review).

### Affected areas
`graph/` (model: lifecycle field, `@repo:ref_id` parsing in loader; new `graph/federation.py` for export + aggregate), `services/cli.py` (new `export` + `federate` commands), `services/mcp_server.py` (optional `export` tool later), `.beadloom/_graph/*.yml` schema (lifecycle field), docs.

## Proposed Solution

### 1. Cross-repo node identity `@repo:ref_id`
- Extend ref parsing in `graph/loader.py`: a ref of the form `@<repo>:<ref_id>` denotes a **foreign** reference. Local refs unchanged.
- New small value type `FederatedRef(repo: str | None, ref_id: str)`; `repo=None` = local. Parser validates the `@repo:id` shape; malformed → recorded in `result.errors` (never silently dropped — honesty).
- Edges may target a foreign ref: `depends_on: @integration-service:plans`. At single-repo reindex, a foreign edge is a **dangling/foreign** edge (target not local) — flagged, not an error (it resolves at the hub).

### 2. Lifecycle status (Principle 8)
- Add optional `lifecycle: active | planned | deprecated | dead` to Node and Edge (default `active`). Stored in YAML + carried in the model + SQLite column (additive migration).
- Rule engine / doctor learn the lifecycle: `planned`/`deprecated` edges are NOT treated as live for cycle/layer checks the same way (e.g. a `planned` edge to an unbuilt target is expected, not a violation).

### 3. `beadloom export` — satellite artifact
- New command `beadloom export [--out FILE] [--json]`. Produces a self-describing JSON:
  ```
  { "schema_version": 1, "repo": "<name>", "commit_sha": "<HEAD sha>",
    "exported_at": "<iso8601>", "generator": "beadloom <ver>",
    "nodes": [ {ref_id, kind, summary, lifecycle, source, ...} ],
    "edges": [ {src, dst, kind, lifecycle, contract?: {protocol, source_file, direction}} ] }
  ```
- Deterministic ordering (sorted) → reviewable diffs. `repo` name from config (`config.yml` `repo:` key or git remote basename).
- Contract metadata on edges (AMQP first): `protocol: amqp`, `source_file`, `direction: produces|consumes`, message `type`.

### 4. Hub aggregation — `beadloom federate`
- New command `beadloom federate <export1.json> <export2.json> ...` (or a hub `config.yml` listing satellite artifact paths). Runs in the hub repo.
- Composes one **federated graph**: union of satellite nodes (namespaced `@repo:ref_id`) + edges; **resolves** `@repo:node` foreign refs against the union.
- Computes **three-valued intent-vs-reality** per edge:
  - declared `active` + both sides present → OK
  - declared `active` + target/peer absent → **DRIFT**
  - declared `planned` + absent → expected
  - declared `deprecated` + present → cleanup candidate
  - **undeclared** but present (a satellite emits to a queue no one declares consuming) → **UNDECLARED**
- For a bidirectional contract (core↔integration), checks "confirmed both-sides?" — both a `produces` and a matching `consumes` exist.
- **Temporal consistency:** records each satellite's `commit_sha` + `exported_at`; output flags staleness ("integration-service export age 5d / unknown HEAD"). Hub never claims freshness it can't verify (honest≠complete).
- Output: a federated graph file (JSON) + a human report (text). Rendering to VitePress/Mermaid is F4 — out of scope.

### 5. Dogfood
- Add minimal `@repo:` cross-edges + lifecycle to the real `core-monolith` and `integration-service` `.beadloom/` graphs (or, if they have none yet, a tiny hand-curated slice), `beadloom export` each, `beadloom federate` them in a scratch hub dir, and verify the RabbitMQ contract edge shows confirmed-both-sides. Capture friction in `BDL-UX-Issues.md`.

### Changes

| File / Area | Change |
|-------------|--------|
| `graph/loader.py` | parse `@repo:ref_id` → `FederatedRef`; lifecycle field load; foreign-edge handling |
| `graph/models` | `lifecycle` on Node/Edge; `FederatedRef` type; contract metadata on Edge |
| NEW `graph/federation.py` | export serialization + hub aggregation + three-valued drift + staleness |
| `infrastructure/db.py` | additive `lifecycle` column (schema migration) |
| `services/cli.py` | `beadloom export`, `beadloom federate` commands |
| `graph/rule_engine.py` | lifecycle-aware (planned/deprecated not live violations) |
| `.beadloom/_graph/*.yml` | optional `lifecycle:` on nodes/edges (default active) |
| docs + CHANGELOG | federation docs |

### API Changes
New: `FederatedRef`, `lifecycle` field, `beadloom export`/`federate` commands, export JSON schema v1. Additive (existing graphs without lifecycle default to `active`; refs without `@` stay local). Log as API CHANGE for /review + /tech-writer.

## Alternatives Considered

- **New `federation` domain** vs putting it in `graph`: chose `graph` — it owns the Node/Edge model + loader; a separate domain would duplicate model access and add a cross-domain edge. Revisit if federation grows large (could extract later).
- **Hub as a separate tool/service** vs a `beadloom federate` command: chose a command — keeps "no SaaS, local-first, deterministic" (Strategy principle); the hub repo just runs beadloom. CI automation is a later follow-up.
- **Lifecycle in `extra` dict** vs explicit field: chose explicit field — first-class, type-checked, queryable in SQL; `extra` would hide it from the rule engine.
- **Hub clones satellites** vs artifact exchange: chose artifacts (pull-based, loose coupling, temporal-consistency tracking) per owner decision.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep (F1 balloons into full F2) | High | High | Hard non-goals: AMQP only, manual aggregation, no VitePress/CI. Thin slice. |
| Satellite repos have no `.beadloom/` graph yet | High | Med | Dogfood with a tiny hand-curated slice per Principle 8 draft-then-review; don't block on full bootstrap. |
| `lifecycle` semantics leak into rule engine incorrectly | Med | Med | Tests for each lifecycle×reality case; keep default `active` = current behavior (no regression). |
| Schema migration breaks existing index | Low | Med | Additive column + migration test; existing graphs reindex clean. |
| Export schema churn | Med | Low | `schema_version` from day 1; hub tolerates/﻿reports version mismatch. |

## Open Questions

| # | Question | Proposal (decide in CONTEXT) |
|---|----------|------------------------------|
| Q1 | `beadloom federate` command name | `federate` (vs `hub`/`aggregate`) |
| Q2 | Where federated output lives | hub repo's own `.beadloom/federated.json` + report; not in satellite DBs |
| Q3 | `repo` name source | `config.yml` `repo:` key, fallback git remote basename |
| Q4 | Staleness without hub knowing satellite HEAD | report export age + commit_sha; "freshness" = how recently exported (satellites export on push in the CI follow-up) |
| Q5 | Do we touch the real satellite repos' `.beadloom/` for dogfood, or use a scratch copy? | scratch/hand-curated slice first (don't mutate their repos), then propose adding `.beadloom/` to them |
