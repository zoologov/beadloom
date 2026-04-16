# CONTEXT: BDL-039 — F3: Tool-Agnostic Enforcement Everywhere

> **Status:** Approved
> **Created:** 2026-06-01
> **Last updated:** 2026-06-01

---

## Goal

Turn Beadloom's detection (F1 landscape, F2 contract graph) into **enforcement**: a federated landscape gate (`federate --fail-on`), agent-actionable violation output (remediation, not just detection), AgentConfigAsCode (sync-check for agent-config ↔ graph drift), a single `beadloom ci` gate, and a reusable tool-agnostic CI integration (composite GitHub Action + GitLab template) — dogfooded on Beadloom's own CI. Success = a CI gate blocks a boundary violation / cross-service break / drifted agent-config regardless of which tool or human wrote the code. (Immutable after approval.)

## Key Constraints

- **Purely additive / no regression:** no graph-format or schema-version changes (no EXPORT/FEDERATION/DB bump). `Violation.remediation` is an additive field; lint/gate JSON gains optional keys. Existing commands keep their behavior; the per-repo `beadloom-aac-lint.yml` is subsumed by `beadloom ci`, not broken. `beadloom lint --strict` / `doctor` / `sync-check` stay green.
- **No false gates (principle 3 — a noisy gate gets disabled):** the `--fail-on` set NEVER includes `external` / `expected` / `dead` / `unmapped` / `confirmed` / `ok` / `cleanup_candidate`; AgentConfigAsCode checks ONLY auto-managed regions (between `beadloom:auto-start`/`auto-end`), never user-authored prose (avoids the #73 false-positive class). Explicit "clean landscape → exit 0" tests.
- **CI is the only true enforcement point (principle 7):** local rules files are hints; the gate is identical for Cursor / Claude Code / human authors. Generated adapters are *verified-fresh* (principle 7 / #93), never hand-maintained.
- **No new infra:** F3 ships the gate + a *documented* pull-based hub pattern; it does NOT build a registry/MinIO/SaaS. Anything bigger → re-scope transparently (honest ≠ complete).
- **DRY generator:** AgentConfigAsCode (`onboarding/config_sync.py`) re-runs the SAME generation code as `setup-rules --refresh` and diffs — never a parallel reimplementation.
- **Honest gate:** `beadloom ci` reports which steps ran + their result; never a green that silently skipped a step (the Phase-0 lesson).
- **Anonymization (binding) for dogfood fixtures:** committed `tests/fixtures/` hub exports must be anonymized (no real private-project names); the real landscape stays in gitignored scratch. Confirm before any force-push.
- Fourth real-code epic through the BDL-035 multi-agent process (agents/* subagents, swarm/gate/merge-slot).

## Code Standards

(from CLAUDE.md §0.1)

| Standard | Application |
|----------|-------------|
| Language/env | Python 3.10+ (`str \| None`), uv |
| TDD | Red → Green → Refactor |
| Linter/format | ruff |
| Typing | mypy --strict |
| Tests | pytest + pytest-cov, coverage ≥ 80% |

**Restrictions:** no `Any`/`# type: ignore` without reason; `pathlib`; parameterized SQL; `yaml.safe_load`; no bare `except:`; frozen/`@dataclass` models; deterministic serialization (sorted findings).

**Commit format:** `[BDL-039] <type>: <description>`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-01 | `federate --fail-on <csv>` writes artifacts FIRST, then exits 1 on failures | the federated.json must always be available for inspection/CI upload even when the gate fails |
| 2026-06-01 | `gate_failures(fed, fail_on)` is a pure function in `federation.py` | testable without CLI; reused by `federate` and `beadloom ci` |
| 2026-06-01 | Safe-default fail-set = `breaking,drift,orphaned_consumer,undeclared_producer`; never `external/expected/dead/unmapped/cleanup_candidate` | principle 3 — no false gates |
| 2026-06-01 | Agent-actionable = `Violation.remediation` + per-rule deriver + `--format json`/`github` | "how to fix", in the agent's/CI's native channel (GitHub annotations) |
| 2026-06-01 | AgentConfigAsCode = regenerate-and-diff (new `onboarding/config_sync.py`), reusing the `setup-rules --refresh` generator | DRY; checks only auto-managed regions; verified-fresh adapters |
| 2026-06-01 | New `beadloom ci` orchestrator in `application/gate.py` composing reindex→lint→sync→config-check→federate-gate | principle 7 single convergence point; one exit code; uniform `--format` |
| 2026-06-01 | Reusable CI = thin composite GitHub Action invoking `beadloom ci`; all logic in the CLI | testable without CI; satellites reference it |
| 2026-06-01 | No schema/version bumps in F3 | F3 is CLI/CI + a freshness checker, not a graph-format change |

## Related Files

(discover via `beadloom ctx`/`why` — never hardcode)
- `src/beadloom/graph/federation.py` (`gate_failures`; EdgeVerdict/ContractVerdict already defined in F2)
- `src/beadloom/graph/contracts.py` (`ContractVerdict` — read for the gate)
- `src/beadloom/graph/rule_engine.py` (`Violation.remediation` + remediation deriver)
- `src/beadloom/graph/linter.py` (lint JSON/github formatting)
- NEW `src/beadloom/application/gate.py` (`beadloom ci` orchestrator + formatters)
- NEW `src/beadloom/onboarding/config_sync.py` (AgentConfigAsCode regenerate-and-diff)
- `src/beadloom/services/cli.py` (`federate --fail-on`, `ci`, `config-check`)
- `.github/workflows/beadloom-aac-lint.yml` (→ becomes `beadloom-gate.yml`, calls the Action)
- NEW `.github/actions/beadloom-gate/action.yml` (composite Action)
- `docs/guides/ci-setup.md` (landscape gate, Action, `--fail-on`, AgentConfigAsCode, pull-based hub pattern)
- NEW `tests/fixtures/` (anonymized hub export artifacts for the dogfood gate)
- `CHANGELOG.md`, `.claude/development/STRATEGY-3.md` (§F3 status), `BDL-UX-Issues.md`

## Current Phase

- **Phase:** Planning
- **Current bead:** (none yet — created after PLAN approval)
- **Blockers:** none
