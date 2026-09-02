# CONTEXT: BDL-068 — The flow's rules are advice; make them instruments

> **Status:** Approved
> **Created:** 2026-09-02
> **Last updated:** 2026-09-02

---

## Goal

Convert this project's multi-agent flow from rules an agent is asked to follow into
instruments that report when it did not, in six ordered slices, the first of which builds the
instrument the other five are measured by.

## Key Constraints

- **The derivation is over a shape, never a spelling.** A check that asks for one way of
  writing something is a check five other spellings walk past — measured on BDL-067.
- **The unresolved population is part of every answer.** A derivation that omits what it could
  not parse hands an agent a clean list, and a clean list is trusted and stopped at.
- **Tool-agnosticism.** Nothing this epic adds may require an adopter to own a runner. Where a
  runner is needed, it is this repository's dev dependency and the shipped artifact is the
  scope and the report.
- **The coordinator cannot read source.** Any artifact describing source is produced by a role
  or a command, never by the orchestrating loop.
- **No check is added that cannot fail.** Each slice states, per check, the tree on which it
  goes red, and verifies it there before the check is called done.
- **Beads are created per slice, not for the epic.** See the architectural decision below.

## Code Standards

### Language and Environment

- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies

| Methodology | Application |
|-------------|-------------|
| TDD | Red -> Green -> Refactor; an assertion not verified red is declared, with its reason |
| Clean Code | SRP, DRY, KISS |
| Architecture | DDD — `services → application → domains → infrastructure`, never the reverse |

### Testing

- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Acceptance:** behaviour-bearing criteria are Gherkin scenarios in
  `tests/acceptance/features/`; the `.feature` file is the source of truth and the document
  references the scenario by name.

### Code Quality

- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict
- **Gate:** `beadloom ci` rc 0, measured in the foreground without a pipe.

### Restrictions

- No `Any` / `# type: ignore` without a stated reason
- No `print()` / `breakpoint()` — use logging
- No bare `except:` — name the exception
- No `os.path` — pathlib only; no f-strings in SQL; no `yaml.load` without a safe loader
- **No measurement reported without the room it was taken in.** "green in a clean room over N
  files", "green on the tree" and "green on Ubuntu" are three different claims.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-09-02 | Q1: the axes are DERIVED by `beadloom impact`; the document records the derivation's output and the human's scope decision; the bead's `refs:` is generated from the document. A disagreement between the three is a finding. | Two authored homes are two things that can disagree, which is the class this epic exists to remove. One computation, two renderings, one check. |
| 2026-09-02 | Q2: the commit-scope check compares against the WORK ITEM's axes, not the bead's. | The work item's axes are what the human approved; a bead may narrow freely inside them. A commit leaving the work item's axes means the approval no longer covers the change, which is exactly the re-plan trigger. |
| 2026-09-02 | Q4: External `bd` findings are answered by deriving our own call sites and asserting each one's behaviour, not by a wrapper. | A wrapper is a second thing to keep in step with upstream. A derived population of `bd` call sites is the same technique this epic applies everywhere else, and it fails on a call site added later. |
| 2026-09-02 | Q5: `Explore` becomes a role file composed by the same composer as the other four, not a mode of an existing role. | A mode has no protocol file, and that is precisely why the one `Explore` run in BDL-067 returned an excellent trace of the defect and nothing about axes. Composing it through `role-composer` is what stops it drifting independently (#191's shape). |
| 2026-09-02 | Beads are created per slice, when the preceding slice's review closes — not for the whole epic up front. | Writing 24 beads now means writing 20 of them before the first slice has taught anything. This is the re-plan rule expressed as structure rather than as discipline. |
| 2026-09-02 | Q3 stays open by design, with its decision rule stated: the mutation job runs per PR if it fits under the budget that withdrew `tests-windows` (~16-28 runner-minutes), and nightly otherwise. Measured in S3 before the job is added. | A cost decision taken before the cost is measured is the kind of claim this project rejects from everyone else. |

## Related Files

Discover through `beadloom ctx <ref-id>` — every node the RFC names resolves today:
`review-brief`, `wave-plan`, `guard-hooks`, `ci-gate`, `sync-check`, `doc-quality`,
`docs-audit`, `mutation-scope`, `scenario-binding`, `flow-config`, `flow-composer`,
`role-composer`, `role-adapters`, `flow-manifest`, `flow-suppression`,
`agentic-flow-setup`, `config-check`.

## Current Phase

- **Phase:** Planning
- **Current bead:** none — S1's beads are created when this PLAN is approved
- **Blockers:** PR #58 (`features/BDL-067`) is open and green but not merged; this branch is
  stacked on it because S1 lifts three derivations that live only there.
