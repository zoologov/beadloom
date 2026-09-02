# RFC: BDL-068 — The flow's rules are advice; make them instruments

> **Status:** Approved
> **Created:** 2026-09-02

---

## Overview

Six ordered slices, each independently shippable, that convert this project's multi-agent
flow from a set of rules an agent is asked to follow into a set of instruments that report
when it did not. The first slice builds the instrument the other five are measured by, so it
is inside this epic rather than beside it.

The unifying technique is already proven on this repository and is not new work: BDL-067
wrote three AST derivations that answer "who else writes this, who else calls this, how many
branches does this have" from the source rather than from a list. They live in the test suite
and are lifted into a command here.

## Motivation

### Problem

Every measured failure of the flow has one shape: a rule that is correct as written, and no
instrument that can tell a followed rule from a claimed one. The PRD carries the four proofs.
The technical statement of the same thing is narrower and more useful:

**Every existing flow check reads a channel it declares, and is read as answering a question
about all channels.** `review-brief` counts bead comments and reports `0 withheld`, which is
true of bead comments and false about what the reviewer can reach. The commit-scoped hook
judges the paths a commit stages, which is true of that commit and blind to a neighbour's hunk
inside a file it touched. `sync-check` verifies the pairs it has a baseline for. `mutation-scope`
reports a declared target outside the configured source paths — and no runner produces the
score the target was declared for.

### Solution

Two moves, applied six times.

**Derive the population, do not list it.** Wherever a check today asks "is X in this list", it
asks the source for the list instead, and the derivation is over a SHAPE rather than a
spelling. BDL-067 measured the difference: a reader detector asking for `glob("*.yml")` plus
`yaml.safe_load` by name missed five bodies that read the same directory with `iterdir`,
`listdir`, `scandir`, `walk`, or `yaml.load` with an explicit loader.

**Report the unresolved population as part of the answer.** A derivation that omits what it
could not parse produces a clean list, and a clean list is what an agent trusts and stops at.
Recall over precision: the failure mode we are moving toward is false confidence, which is
worse than the ignorance we have now.

## Technical Context

### Constraints

- Python >= 3.10, `mypy --strict`, `ruff`; the stack section of `CLAUDE.md` is authoritative.
- **Tool-agnosticism.** Beadloom must not require a runner an adopter cannot have. The
  mutation slice therefore ships the SCOPE and the report, and names `mutmut` as this
  repository's own dev dependency rather than as a shipped requirement.
- **The coordinator cannot read source.** Any artifact that describes source must be produced
  by a role or by a command, never by the orchestrating loop.
- **A check that cannot fail must not be added.** Each slice states, per check, the tree on
  which it goes red.

## Axes

Derived, never authored. An epic is not a single `impact` target: its axes are the UNION of its
slices' axes, and each slice's rows are derived when that slice begins. The rows below are S1's,
derived on 2026-09-02 after `c7591a8`. S2–S6 add theirs at their own start, which is the same rule
as beads being created per slice.

> **Derived by:** `beadloom impact` over `onboarding/role_composer.py`, `doc_sync/axes_section.py`
> and `services/commands/impact.py` — the three surfaces S1 changed
> **Seed:** `none`, under the rule `reaches-an-effect-sink`, on all three. Every axis below the
> seed is therefore unresolved and not empty — S1's surfaces are composition and rendering, and
> none of them reaches a declared effect sink.
> **Unresolved:** co-writers, on all three targets — no declared effect rule found a sink these
> targets reach, so there is no commit point to ask who else writes through. Measured on
> 2026-09-02 at `c7591a8`, macOS, `beadloom impact` in the foreground.

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | — | unresolved (no seed on any of the three targets) | no | Nothing can be taken into scope until a seed resolves, so the decision is `no` and not `n/a` — an undecided row is what the check reads as a derivation nobody acted on. When a later slice's target does reach a sink, this row is re-derived and decided then. It is recorded rather than dropped so the blank is not read as "nothing writes here" |
| callers | `config-check` | 2, first `_composed_corpus` (`onboarding/config_sync.py:808`) | yes | `.5` had to make the composed role visible to it, which is BDL-UX #191's shape |
| callers | `role-adapters` | 1, `generate_adapters` (`onboarding/role_adapters.py:107`) | yes | The fifth role file is written through it |
| callers | `ci-gate` | 1, `_step_doc_spaces` (`application/gate.py:590`) | yes | The `## Axes` checks report through the Gate step |
| callers | `flow-guards` | 3, first `_unanswerable` (`application/guards/invocation.py:473`) | yes | S4's slice is these guards; S1 already reaches them |
| callers | `planning-report` | 1, `planning_report` (`application/planning_report.py:136`) | yes | Where the section is read back |
| callers | `work-item-type` | 1, `_collect` (`doc_sync/work_item_type.py:121`) | yes | `.5` routes the type decision through it |
| callers | `impact` | 3, first `_rows` (`application/impact/section.py:92`) | yes | The command rendering its own section |
| callers | `cli-commands` | 1, `axes` (`services/commands/impact.py:88`) | yes | The command surface |

**The scope decision.** Every caller row is in scope for this epic because each is a surface a
later slice edits — S4 is the guards, S6 is the composer and `config-check`. Nothing is excluded,
which is a decision and not an omission: an epic that declared a narrower scope than its own
slices would make `.6` red on its second commit.

## Proposed Solution

### Approach

**S1 — `beadloom impact`, the `## Axes` artifact, and the `Explore` protocol.**

`beadloom impact <path|symbol>` answers four questions from the source: who else writes the
files this writes, who else calls what this calls, how many branches the enclosing command
has and how many ways it terminates, and which of those the derivation could not resolve. The
graph supplies the boundary — the domain each found site belongs to — so the answer says when
a change leaves its domain. The three BDL-067 derivations are lifted out of `tests/` into a
production package; they are the bulk of the logic and they already carry anti-vacuity cases.

`## Axes` becomes a section of the BRIEF and RFC core templates. `doc_templates.required_sections`
already derives a document's required sections from the composed template's literal `## `
headings, so adding the heading makes it required by the same act, and `doc-quality` reports its
absence exactly as `missing_sections` reports any other.

`Explore` gets a file in `.claude/agents/` with a fixed deliverable — the `## Axes` section,
paths and lines, no narrative — and runs inside `/task-init` before the type is chosen.

**S2 — the review's independence, reported rather than asserted.**

`review-brief` stops reporting what it withheld and starts reporting what is REACHABLE:
bead comments, the epic documents a prompt may name, and the commit bodies of the reviewed
range. The count changes from `0 withheld` to a per-channel statement, and a channel it
cannot inspect is named rather than omitted.

**S3 — what we measure with.** `mutmut` over `graph/rules/` as this repository's first slice,
scoped by `source_paths` / `do_not_mutate` / test selection, with the score produced in CI.
`mutation-scope` gains its missing half: a declared target inside the paths still scores, and a
run that produced no mutants is a finding rather than a zero. Two further measurement gaps join
this slice because they are the same defect: a clean-room verdict cannot see a cross-bead
interaction (#181), and a verdict that does not name its platform is not a verdict (`mr2l.61`,
and the ten-to-one failure at the end of BDL-067).

**S4 — the guards' surface.** Each guard's enforcement surface is derived from its own matcher
and compared against the write paths that exist, so a file written through `Bash` where the
guard watches `Edit|Write` is reported (#170). The commit gate learns to see a neighbour's hunk
inside a file the committer touched (`mr2l.81`).

**S5 — the tracker adapters.** Every External finding is answered by our behaviour in the face
of it: never read `bd list --json` as complete (#187), never trust `merge-slot` as exclusion
between agents that share one identity (#194), never write an id into a title a concurrent
create can shift (#171).

**S6 — the flow's own documents and roles.** `ROADMAP.md` and `BDL-UX-Issues.md` become
document KINDS whose counts the tool computes (`mr2l.72`), which is also what makes a duplicate
issue number impossible (`mr2l.91`, and the near-duplicate #211 this session produced).
`setup-agentic-flow` stops recomposing a hand-edited role adapter without `--force` (#191), and
the vendored-agents snapshot loop is closed in the remaining direction (`beadloom-iur5`).

### Changes

| File / Module | Change |
|---------------|--------|
| new package under `application/` | the three AST derivations, lifted from `tests/`, plus the unresolved-population report |
| `services/commands/` | `beadloom impact` |
| `onboarding/doc_templates.py` + core templates | `## Axes` heading, hence required by derivation |
| `.claude/agents/explore.md` | new role file with a fixed deliverable |
| `application/` — `review_brief` | reachability report replaces the withheld count |
| `pyproject.toml`, `ci.yml` | `mutmut` dev dependency and the scoped CI job |
| `graph/rules/` — `mutation_scope` | the half that reports a target that produced no mutants |
| `guard-hooks` | surface derivation and the unwatched-path finding |
| `doc_sync/` — document kinds | `ROADMAP` / issue-log kinds with computed counts |

### API Changes

`beadloom impact` is new. `review-brief`'s output shape changes: consumers reading the
`withheld` count must read the reachability block instead. No graph schema change is planned;
if the impact node needs one, PLAN states it before S1 begins.

## Alternatives Considered

### Option A: build `impact` as a graph walk over `part_of` / `depends_on`

Rejected, and the reason is the whole risk of this epic. Not one axis BDL-067 needed is a fact
of the graph — the writers of `.beadloom/_graph/`, the branches of `init`, its exit forms, the
modes, the renderers, the YAML readers and their policies all live INSIDE one node. A graph walk
would answer confidently and miss all of them: a green describing the checker's ignorance,
shipped as a feature. The graph supplies the boundary and nothing else.

### Option B: keep the rules as prompt text and rely on role discipline

Rejected on three measurements. The mutation duty shipped into every role core with no runner;
the review's withholding was defeated through `ACTIVE.md` and then through commit bodies. Each
rule was correct as written and none of them held.

### Option C: one monolithic work item covering all 24 findings

Rejected on this project's own measurement. BDL-067 was one bug that became 28 beads and nine
review passes whose finding count did not decay, and the retro named the cause: nothing
re-plans a work item whose type stops being true. Twenty-four findings taken at once starts in
the state BDL-067 reached at its fourth cycle.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `impact` under-reports and agents trust it, inverting ignorance into false confidence | High | High | The unresolved population is part of the answer, not an omission; S1 ships no check that consumes the axes until the report names what it could not resolve |
| The axes declaration lives in two places — the document and the bead's `refs:` that `waves` already reads — and they disagree | High | Medium | Open question Q1; one home is chosen in PLAN, and the other derives from it |
| The mutation slice costs more CI minutes than the project accepted for `tests-windows` | Medium | Medium | Scoped to `graph/rules/` with per-mutant test selection; measured before the CI job is added, and the job is nightly if the PR budget cannot hold it |
| Lifting the derivations out of `tests/` weakens the tests that currently hold them | Medium | High | The tests keep their assertions and import the lifted code; a derivation with no test that fails on a fifth body is not lifted |
| Six slices become nine, the way nine review passes became nine cycles | Medium | High | The re-plan rule is armed from S1: a second ISSUES verdict on one slice re-plans rather than cycles, and the stop rule is written into each review bead |
| An External `bd` behaviour changes upstream and our adapter's workaround becomes the wrong shape | Low | Medium | S5 states the upstream issue beside each workaround so the workaround can be withdrawn deliberately |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Does the `## Axes` declaration live in the document, or in the bead notes where `waves` already reads `refs:`? Two homes are two things that can disagree. | Pending — decided in PLAN |
| Q2 | Does the commit-scope check compare against the axes of the claimed bead, or against the axes of the work item? A bead is narrower; a work item is what the human approved. | Pending |
| Q3 | Does the mutation job run per PR or nightly? `tests-windows` was withdrawn at ~16-28 runner-minutes per PR, which is the budget this must fit under. | Pending — measured in S3 before the job is added |
| Q4 | For the External `bd` findings, is the deliverable a wrapper this project owns, or documented avoidance in every caller? | Pending |
| Q5 | Is `Explore` a fourth role subagent, or a mode of an existing one? A fifth role file is a fifth thing that can drift out of `setup-agentic-flow`. | Pending |
