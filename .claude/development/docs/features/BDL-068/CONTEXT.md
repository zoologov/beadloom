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
| 2026-09-03 | Q3 answered: the mutation job is NIGHTLY, and the first slice's score is 96.2% over 3 989 mutants. | Measured before the job was written, per the rule CONTEXT stated on 2026-09-02: 54 min 55 s wall clock with six workers on a 10-core Darwin arm64 machine (CPython 3.13.7), against the ~16-28 runner-minute budget that withdrew `tests-windows`. Two to three times the budget on hardware faster than the runner, so no CI measurement can move the answer. The job is scheduled and deliberately NOT a required status check: a scheduled workflow reports no check-run on a pull request, and requiring its context would make `main` unmergeable. |
| 2026-09-02 | S1.3's measurement: `impact` DERIVES its seed from the target and names it in the answer. No invocation may take the commit point as an argument and no literal may name it. | Measured at `af26750d`, the tree BDL-067's first dev bead started from: seeded with `write_yaml_atomic` the lifted derivations list both writers and four branches of `init`; seeded with `bootstrap_project`, the function that bead was changing, they list no writers and three branches. Three is the number the epic carried throughout. The answer is a property of the seed, so a hardcoded seed would satisfy S1.2's acceptance while being the authored list this epic exists to remove. |

## Related Files

Discover through `beadloom ctx <ref-id>` — every node the RFC names resolves today:
`review-brief`, `wave-plan`, `guard-hooks`, `ci-gate`, `sync-check`, `doc-quality`,
`docs-audit`, `mutation-scope`, `scenario-binding`, `flow-config`, `flow-composer`,
`role-composer`, `role-adapters`, `flow-manifest`, `flow-suppression`,
`agentic-flow-setup`, `config-check`.

## Current Phase

- **Phase:** Development — S1
- **Current bead:** `.3` closed; `.2` (`beadloom impact`) is next and runs against the
  acceptance S1.3 rewrote.
- **Blockers:** none. PR #58 landed on `main` as `a4738b7`, so the three lifted derivations are
  no longer stacked on an open branch.
