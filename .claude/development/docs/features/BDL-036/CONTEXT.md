# CONTEXT: BDL-036 — Phase 0: Foundation / Honesty Gate

> **Status:** Approved
> **Created:** 2026-05-30
> **Last updated:** 2026-05-30

---

## Goal

Make Beadloom pass its own `doctor` / `lint --strict` / `sync-check` honestly (the STRATEGY-3 Phase 0 prerequisite). Decouple the `infrastructure` god-package into a canonical DDD **application** layer, restore architecture rules to `error`, and fix the diagnostic/silent-failure bugs. (Immutable after approval.)

## Key Constraints

- **Verify before fixing; `honest ≠ complete`** — if an issue (esp. #89/#90/#86) proves deeper than Phase 0 warrants, re-scope transparently in the docs with evidence; never fake green or silently drop.
- **Mechanical move for #91** — preserve module APIs; update import paths; run full pytest after. Serialize the landing with `bd merge-slot`.
- **Exit criterion is the acceptance test:** `beadloom doctor && beadloom lint --strict && beadloom sync-check` honestly green on Beadloom itself + clean fresh bootstrap.
- **RE-SCOPE (2026-05-30, honest≠complete):** `doctor` + `lint --strict` are honestly green and a fresh bootstrap lints clean. `sync-check` *mechanism* is now honest (#89/#90 fixed), BUT ~30 pre-existing stale doc pairs (accumulated content drift across graph/tui/onboarding/…, largely NOT from Phase 0) remain. Driving sync-check to zero = a repo-wide doc refresh = its own epic (BDL-UX #99). Phase 0 closes with lint+doctor green + sync-check mechanism honest + Phase-0-touched docs updated; full sync-check green deferred to #99. Faking green via baseline-reset was explicitly rejected (it is the exact dishonesty this epic exists to remove).
- First real-code dogfood of the BDL-035 process (agents/* subagents, swarm/gate/merge-slot).

## Code Standards

(from CLAUDE.md §0.1)

| Standard | Application |
|----------|-------------|
| Language/env | Python 3.10+ (`str \| None`), uv |
| TDD | Red → Green → Refactor |
| Linter/format | ruff |
| Typing | mypy --strict |
| Tests | pytest + pytest-cov, coverage ≥ 80% |

**Restrictions:** no `Any`/`# type: ignore` without reason; no `print()`/`breakpoint()`; no bare `except:` (the #94 fix embodies this); `pathlib` not `os.path`; parameterized SQL; `yaml.safe_load`.

**Commit format:** `[BDL-036] <type>: <description>`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-30 | #91 = Split into a new `application` layer (not invert, not reclassify-only) | Honestly reflects reality; cheapest *honest* option; reclassify-only would make the graph lie |
| 2026-05-30 | Layer name = `application` | Canonical DDD term for use-case orchestration services |
| 2026-05-30 | Layer order: `services → application → domains → infrastructure` | Restores DDD Dependency Rule; orchestrators legally depend on domains+infra |
| 2026-05-30 | Bounded contexts (4 domains) untouched | We only relocate application services out of infra; domains unchanged |
| 2026-05-30 | Cheap honesty fixes (Wave 1) land before the #91 move (Wave 2) | Fast honest doctor; isolates the risky refactor |
| 2026-05-30 | #96 scoped to modules the #91 move touches | Not a global 193-site test rewrite (anti-over-process) |

## DDD note (why `application` is correct, not a violation)

Canonical DDD has four layers: Interface (`services`/`tui`) → Application (use-case orchestration, no business rules) → Domain (bounded contexts) → Infrastructure (db/io). `reindex`/`doctor`/`debt_report` are application services currently misfiled in `infrastructure`, which is *why* infra imports domains (a Dependency-Rule violation). Extracting `application` **fixes** DDD; it does not break it. The 4 bounded contexts (`context_oracle`, `doc_sync`, `graph`, `onboarding`) are unchanged.

## Related Files

(discover via `beadloom ctx <ref-id>` / `beadloom why <ref-id>` — never hardcode)
- `src/beadloom/infrastructure/{reindex,doctor,debt_report}.py` → move to `src/beadloom/application/`
- `src/beadloom/infrastructure/{db,git_activity}.py` → stay (domain-agnostic)
- `src/beadloom/services/{cli,mcp_server}.py` → import updates
- `src/beadloom/graph/loader.py` (#86), `src/beadloom/doc_sync/engine.py` (#89/#90)
- `.beadloom/_graph/{services,rules}.yml` (layers + restore error)
- `BDL-UX-Issues.md` (close #91/#88/#92/#93/#94/#86/#89/#90/#71)

## Current Phase

- **Phase:** Planning
- **Current bead:** (none yet — created after PLAN approval)
- **Blockers:** none
