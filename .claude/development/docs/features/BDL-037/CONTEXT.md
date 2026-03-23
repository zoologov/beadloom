# CONTEXT: BDL-037 — F1: Federation Foundation

> **Status:** Approved
> **Created:** 2026-06-01
> **Last updated:** 2026-06-01

---

## Goal

Give Beadloom cross-repo federation as a thin live slice: `@repo:ref_id` identity, `beadloom export` artifact, `beadloom federate` hub aggregation with lifecycle-aware three-valued intent-vs-reality + per-satellite staleness — dogfooded on the real `core-monolith ↔ integration-service` RabbitMQ contract. (Immutable after approval.)

## Key Constraints

- **Thin slice, hard non-goals:** AMQP contracts only; manual aggregation (no CI wiring); no VitePress/semantic layer; no monorepo workspaces; no satellite auto-bootstrap. Anything bigger → re-scope transparently (honest ≠ complete).
- **No regression:** existing single-repo behavior unchanged — refs without `@` stay local; nodes/edges without `lifecycle` default to `active`; beadloom lint/doctor stay green; additive SQLite migration.
- **Federation lives in the `graph` domain** (owns Node/Edge model + loader); hub is a `beadloom federate` command (local-first, no SaaS).
- **Dogfood without mutating the real repos first:** scratch/hand-curated slice (Principle 8 draft-then-review), then propose adding `.beadloom/` to them.
- Second real-code epic run through the BDL-035 multi-agent process (agents/* subagents, swarm/gate/merge-slot).

## Code Standards

(from CLAUDE.md §0.1)

| Standard | Application |
|----------|-------------|
| Language/env | Python 3.10+ (`str \| None`), uv |
| TDD | Red → Green → Refactor |
| Linter/format | ruff |
| Typing | mypy --strict |
| Tests | pytest + pytest-cov, coverage ≥ 80% |

**Restrictions:** no `Any`/`# type: ignore` without reason; `pathlib`; parameterized SQL; `yaml.safe_load`; no bare `except:`; frozen dataclasses for models.

**Commit format:** `[BDL-037] <type>: <description>`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-01 | Federation in `graph` domain (new `graph/federation.py`), not a new domain | graph owns Node/Edge + loader; separate domain duplicates model access |
| 2026-06-01 | Hub = `beadloom federate` command, artifacts pull-based | local-first / no SaaS; loose coupling; temporal-consistency tracking |
| 2026-06-01 | `lifecycle` = explicit first-class field on Node/Edge (not `extra`) | type-checked, SQL-queryable, visible to rule engine |
| 2026-06-01 | Q1 command name = `federate` | clear verb |
| 2026-06-01 | Q2 federated output = hub repo `.beadloom/federated.json` + text report | not in satellite DBs |
| 2026-06-01 | Q3 `repo` name = `config.yml` `repo:` key, fallback git remote basename | deterministic, overridable |
| 2026-06-01 | Q4 staleness = export `commit_sha` + `exported_at` age | hub can't know satellite HEAD; report age honestly |
| 2026-06-01 | Q5 dogfood = scratch/hand-curated slice, do NOT mutate real repos yet | safe; propose `.beadloom/` adoption after |

## Related Files

(discover via `beadloom ctx graph` / `beadloom why` — never hardcode)
- `src/beadloom/graph/loader.py` (@repo parsing, lifecycle load), graph model (lifecycle, FederatedRef, contract meta)
- NEW `src/beadloom/graph/federation.py` (export + aggregate + drift + staleness)
- `src/beadloom/graph/rule_engine.py` (lifecycle-aware)
- `src/beadloom/infrastructure/db.py` (lifecycle column migration)
- `src/beadloom/services/cli.py` (`export`, `federate` commands)
- `.beadloom/_graph/*.yml` (optional `lifecycle:`)
- `CHANGELOG.md`, `BDL-UX-Issues.md` (dogfooding feedback)

## Current Phase

- **Phase:** Planning
- **Current bead:** (none yet — created after PLAN approval)
- **Blockers:** none
