# CONTEXT: BDL-038 — F2: Cross-Service Contract Graph

> **Status:** Approved
> **Created:** 2026-06-01
> **Last updated:** 2026-06-01

---

## Goal

Turn F1's edge-buried AMQP contract into a **first-class, protocol-agnostic, language-neutral cross-service contract graph** computed at the hub: add GraphQL SDL alongside AMQP (UI/mobile client as consumer), compute contract-level intent-vs-reality verdicts (DRIFT / ORPHANED_CONSUMER / UNDECLARED_PRODUCER / BREAKING), survive arbitrary paradigms (FSD kinds) and external/native nodes, and scope reconciliation by landscape so unrelated products never cross-pollute. Dogfood = detect a real contract mismatch on the maintainer's live landscape before it ships, + a Product-B FSD round-trip. (Immutable after approval.)

## Key Constraints

- **Purely additive / no regression:** a v1 export must still federate; an AMQP-only landscape behaves exactly as F1; refs without `@` stay local; nodes/edges without `lifecycle` default to `active`; `beadloom lint --strict` / `doctor` / `sync-check` stay green. The three version bumps (EXPORT 1→2, FEDERATION 1→2, DB SCHEMA 3→4) all read older inputs.
- **Satellite stays dumb, hub stays smart:** satellites declare contracts on edges + parse local SDL at `reindex`/`export`; **all** cross-repo reconciliation happens at `federate`. The hub never reads a satellite's files.
- **Hard non-goals (→ F3/F4):** REST/OpenAPI + gRPC sources; historical schema-version diffing (F2 is presence-based only); CI wiring & PR gates; VitePress visual map; AI-tech-writer-in-CI; SaaS hub; live-server introspection. Anything bigger → re-scope transparently (honest ≠ complete).
- **Federation lives in the `graph` domain.** F2 splits new surface into `graph/contracts.py` + `graph/sdl.py` to keep the `graph` domain under `domain-size-limit` (federation.py is already 693 LOC).
- **No new runtime dependency** for SDL parsing — minimal in-house surface extractor (name-presence only); `graphql-core` documented as the future upgrade path, not used now.
- **Anonymization (binding):** Product-B is a private dogfood landscape — its real name and any domain-fingerprinting tech MUST be anonymized in every committed artifact (working tree, git history, commit messages). The microservices landscape is already role-anonymized (core-monolith / integration-service / file-service / desktop-companion). Always confirm before force-push.
- Third real-code epic run through the BDL-035 multi-agent process (agents/* subagents, swarm/gate/merge-slot).

## Code Standards

(from CLAUDE.md §0.1)

| Standard | Application |
|----------|-------------|
| Language/env | Python 3.10+ (`str \| None`), uv |
| TDD | Red → Green → Refactor |
| Linter/format | ruff |
| Typing | mypy --strict |
| Tests | pytest + pytest-cov, coverage ≥ 80% |

**Restrictions:** no `Any`/`# type: ignore` without reason; `pathlib`; parameterized SQL; `yaml.safe_load`; no bare `except:`; frozen/`@dataclass` models; deterministic serialization (sorted keys + sorted collections).

**Commit format:** `[BDL-038] <type>: <description>`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-01 | Contracts declared on edges (satellite, F1 wire kept); **projected** to first-class `Contract` at the hub | no satellite migration; F1 export compat; reconciliation is a hub concern |
| 2026-06-01 | New modules `graph/contracts.py` (model + reconcile + key) + `graph/sdl.py` (SDL surface) | keep `graph` domain under size-limit; clean separation |
| 2026-06-01 | `contract_key` = protocol-prefixed (`amqp:<exchange>/<routing>:<mt>`, `graphql:<schema>`) | G3 cross-language resolve by name; G4 exchange identity ends false confirms |
| 2026-06-01 | GraphQL SDL parsed **satellite-side** at reindex; surface folded into export | hub stays file-free (principle 4); deterministic export |
| 2026-06-01 | In-house minimal SDL extractor, no `graphql-core` dep | lean; presence-based check needs names only |
| 2026-06-01 | `BREAKING` = `references ⊄ exposed` (presence-based), not version-diff | tractable; the real "breaks before ship" signal; version-diff is F3+ |
| 2026-06-01 | `external` added to `VALID_LIFECYCLES`; `unmapped` is a hub verdict | U4: native bridges suppress DRIFT, honest unknowns |
| 2026-06-01 | `landscape` provenance field; implicit matching scoped by `(landscape, contract_key)`; cross-product only via explicit `@repo:` | U5: contract-less products produce zero mutual noise |
| 2026-06-01 (BEAD-06) | `build_export` emits `landscape` **only when explicitly configured** (omitted otherwise); "falls back to repo" applies at the hub (provenance display + grouping default), NOT in the wire shape | keeps F1 cross-repo implicit confirm byte-identical: a no-landscape run = one shared group. Emitting `landscape=repo` would split existing two-repo confirm fixtures, breaking the byte-identical regression. `resolve_landscape` still returns config-or-repo; CLI omits when ==repo |
| 2026-06-01 (BEAD-06) | Explicit cross-product key detection = edge whose namespaced `dst` repo ≠ its own `repo`; such keys promoted to a single landscape-agnostic group (`cross_landscape_keys` / `edge_group_key`); `_mark_undeclared` reuses the same `(landscape, key)` scope | a real `@otherrepo:` contract resolves cross-landscape; per-product UNDECLARED stays honest (not silenced by an unrelated product's coincidental consumer). No EXPORT/FEDERATION/DB version bump (landscape is additive within export v2) |
| 2026-06-01 | DB CHECK rebuilt (not ALTERed) to add `external` lifecycle | SQLite cannot ALTER a CHECK in place; table-rebuild, additive, idempotent |

## Related Files

(discover via `beadloom ctx graph` / `beadloom why graph` — never hardcode)
- `src/beadloom/graph/federation.py` (identity, export, `aggregate_exports` orchestration — delegates reconciliation)
- NEW `src/beadloom/graph/contracts.py` (`Contract`, `ContractVerdict`, `reconcile_contracts`, `contract_key`)
- NEW `src/beadloom/graph/sdl.py` (GraphQL SDL surface extractor)
- `src/beadloom/graph/loader.py` (`_contract_key` protocol-aware, SDL-surface folding, `external` lifecycle, `landscape`)
- `src/beadloom/infrastructure/db.py` (`lifecycle` CHECK rebuild migration, SCHEMA_VERSION 3→4)
- `src/beadloom/services/cli.py` (`export` `--landscape`, `federate` richer contract report)
- `docs/domains/graph/features/federation/SPEC.md` (extend with the contract graph)
- `README.md` / `README.ru.md` (positioning rewrite — RELEASE GATE)
- `CHANGELOG.md`, `BDL-UX-Issues.md` (dogfooding feedback)

## Current Phase

- **Phase:** Planning
- **Current bead:** (none yet — created after PLAN approval)
- **Blockers:** none
