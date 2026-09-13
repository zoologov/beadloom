# CONTEXT: BDL-070 — The layer a node is in, answered once and reported over its population

> **Status:** Approved
> **Created:** 2026-09-12
> **Last updated:** 2026-09-12

---

## Goal

`architecture-layers` states the population it ran over on every run, and one function — reading the
declaration, climbing `part_of` — answers what layer a node is in for every instrument that asks.
The population is reported before the answer changes any verdict.

## Key Constraints

- **No adopter's Gate may change verdict on upgrade** (BDL-069 CONTEXT). This is why the work is two
  releases and why their order is fixed: everything that changes no verdict ships first.
- `architecture-layers` is `severity: error`. What it evaluates decides whether `main` — ours and
  every adopter's — is mergeable.
- **Release A must be provably verdict-neutral**, not argued to be. A test holds `lint --strict`'s
  findings identical across the change on this repository and on at least one fixture that is not.
- The same-layer predicate is decided and recorded (RFC Q1): legal when both ends share a tagged
  ancestor, a finding when they do not. It is not reopened without a new measurement.
- The shared lookup reads the rule's declared `layers`. **Nothing may hardcode a layer tag**, because
  Beadloom ships to projects whose layers are declared differently.
- The 16 peer crossings are triaged before the verdict changes. An exemption with a stated reason is
  an acceptable outcome; a silent allowance is not.

## Code Standards

### Language and Environment

- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Architecture:** DDD packages — `ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`,
  `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`

### Methodologies

| Methodology | Application |
|---|---|
| TDD | Red -> Green -> Refactor. A test that cannot fail is the defect this epic is about; assert the red. |
| Clean Code | SRP, DRY, KISS |
| Architecture | `services -> application -> domains -> infrastructure`, never the reverse. No domain depends on a peer domain — the rule this epic makes checkable. |

### Testing

- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Fixtures that are not this repository.** Every layer-shape claim is measured on at least one
  graph that is not ours — a nested-component graph and a graph with no `part_of` at all. This
  repository hides the shapes an adopter meets, which is how both BDL-069 blockers survived.

### Code Quality

- **Linter:** ruff (lint + format) — `uv run ruff check src/ tests/`
- **Typing:** mypy --strict — `uv run mypy src/`
- **Gate:** `beadloom ci` rc 0 before every push

### Restrictions

- No `Any` or `# type: ignore` without a stated reason
- No `print()` / `breakpoint()` — use logging
- No bare `except:` — name the exception
- No `os.path` — pathlib only; no f-strings in SQL — parameters `?`; no `yaml.load` — `safe_load`
- **Never pipe a command whose exit code is the answer.** `cmd | tail` returns tail's status, not
  cmd's. Redirect to a file and read `$?`. This cost BDL-069 two false "green" reports.
- **Never truncate a tool's output before reading it.** BDL-UX #285 was filed on a diagnosis drawn
  from output cut off above the line that named the cause.
- **Commit only your own files, by explicit path** — never `git add -A`. Take the landing lock as
  `bd merge-slot acquire --holder <bead-id>` and treat a non-zero exit as *you do not hold it*.
- **"Green in a clean room over N files" is a different claim from "green on the tree."** Say which.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-11 | P0, its own epic rather than a BDL-069 tail | Not a tail: it changes how the main architecture check decides, and it can turn an adopter's green Gate red. |
| 2026-09-12 | Widest scope — population, the three implementations, inheritance, and the declaration | Owner. Two of the three implementations already disagree on verdict; fixing one without the others leaves the disagreement. |
| 2026-09-12 | Same-layer edges: legal iff both ends share a tagged ancestor | Owner, on a measurement: 114 internal against 16 peer crossings. Neither existing predicate was right — one passed all 130, the other flagged all 130. |
| 2026-09-12 | `agent-prime -> reindex` resolved inside the epic, as its own bead, before inheritance | Owner. The alternative — an exemption in `rules.yml` — leaves a hole only the rules file knows about. |
| 2026-09-12 | The shipped role template `dev.md.txt:13` is in scope | Owner. It tells an adopter's dev agent to rely on a proof the rule does not provide. |
| 2026-09-12 | The population is emitted as a finding from inside the evaluator, following `scenario-coverage` | `tui/data_providers.py` and `debt_report/collect.py` call `evaluate_all` directly; a clause in the summary line cannot reach them. |
| 2026-09-12 | Two releases, A verdict-neutral and B verdict-changing | BDL-069 CONTEXT forbids a verdict change on upgrade without warning. A ships the visibility that makes B legible. |

## Related Files

Discover via `beadloom ctx <ref-id>` — never hardcode. The nodes this epic keeps in scope are
`rule-engine`, `graph`, `graph-loader`, `application`, `tui`, `mcp-server`, `ci-gate`, `agent-prime`,
`debt-report`, `cli-commands`, `guard-probes`, `onboarding`.

## What this epic knows it has not established

- **The reader set was found by name-matching**, not by an effect-reachability derivation, because
  `beadloom impact` found no seed for the target and said so. A reader that reaches
  `nodes.extra.tags` through an alias would not appear. The review bead re-derives the set by a
  different method.
- **The figures carried from `beadloom-rqma.4`** — the original 353/16/345 — were re-measured for
  this RFC at `aa4bfad4` and came out 362/16/354. The 16 agreed exactly; the growth is this
  repository's own new modules from BDL-069.
- **`tests/` was not enumerated**, so the number of tests Release B changes is not derived.
- **No clean room, no test run, no CI leg** backs any measurement in the planning documents. They
  were all read from the working tree on macOS.

## Current Phase

- **Phase:** Planning
- **Current bead:** none — beads are created after PLAN is approved
- **Blockers:** none
