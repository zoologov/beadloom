# PRD: BDL-068 — The flow's rules are advice; make them instruments

> **Status:** Approved
> **Created:** 2026-09-02

---

## Problem

This project's multi-agent flow is a set of rules that are correct as written and that
nothing enforces. Every measured failure of the flow in the last three weeks has the same
shape: **a rule an agent is told to follow, with no instrument that can tell a followed rule
from a claimed one.**

Four proofs, each measured rather than argued:

- **A duty shipped without a runner.** BDL-061 S4 put mutation testing into every composed
  role core on the stated ground that owning a runner would break tool-agnosticism. Four
  beads in BDL-067 then reported "mutation checking" by four different hand methods, and
  every result exists only as prose in a bead comment. One of those beads, sent to audit
  another, found a reported "all 20 assertions red before the fix" was eleven guards that
  cannot fail.
- **The review's independence, defeated twice by the playbook itself.** `review-brief`
  withholds bead comments and reports `0 withheld`. On BDL-067 the author's account reached
  the reviewer through `ACTIVE.md`, which the launch prompt names as required reading
  (#212), and then through commit bodies, which the review protocol tells the reviewer to
  read (#219). Both leaks were found by the reviewers declaring them, unprompted. Nothing in
  the tooling could have reported either.
- **A guard narrower than its promise.** A flow guard bound to `Edit|Write` does not see a
  file written through `Bash` (#170); the commit gate cannot see a neighbour's hunk inside a
  file the committer touched (`mr2l.81`); on Windows the guard refuses every edit and states
  a false reason for it (`mr2l.60`).
- **A measurement true of one platform.** BDL-067 reported "green on the tree" nine times.
  All nine ran on macOS; the CI legs are Ubuntu, and the tenth measurement — CI — was red on
  all six. The failure was a path hard-wrapped mid-token at a width that only the runner's
  path length produces. `mr2l.61` already recorded the same skew from the other direction.

The pattern is not that the rules are wrong. It is that **an instrument which measures its
own scope reads as answering the question**, and this project has no way to see the
difference from inside.

## Impact

**Who is affected.** The owner, running a fleet of agents alone, is the only reader of every
verdict this flow produces — and cannot currently tell a verdict from an assertion without
re-measuring it by hand. During BDL-067 the coordinator re-measured every subagent claim and
found three that were overstated; nothing but that habit caught them.

**What it costs, measured.** BDL-067 was one bug — a domain written with no `part_of` edge.
It became 28 beads, 37 commits, nine review passes and +12 227 lines. Majors per review pass
ran 2, 1, 1, 3, 4, 3, 5, 2, 2: the count did not decay. Eight of the defects those passes
found were one sentence true of one shape while a neighbouring shape existed. The flow did
not cause the defects, but it could not see their class, could not re-plan when the work item
stopped being a bug, and could not tell the owner how large the change actually was.

**What happens if this is not done.** The same flow composes into every adopter's repository
through `setup-agentic-flow`. Rules that hold only when the agent chooses to follow them are
shipped as governance, which is the product's own definition of a published lie.

## Goals

- [ ] A work item cannot reach its first dev bead without a machine-derived `## Axes` section
      the Gate can see missing.
- [ ] A change that touches a call site outside the declared axes is a Gate finding, not a
      prompt input.
- [ ] `review-brief` reports what is REACHABLE by the reviewer, not what it happens to
      withhold — bead comments, epic documents and commit bodies counted alike.
- [ ] A mutation score is produced by a command in CI over a declared scope, rather than
      asserted in a bead comment.
- [ ] Every flow guard's enforcement surface is derived from the source and reported, so a
      write path the guard cannot see is a finding rather than a silence.
- [ ] A second ISSUES verdict on one work item forces a recorded re-plan rather than another
      fix cycle.

## Non-goals

- **`init` and Gate defects surfaced during BDL-067** — #214, #215, #216, #217, #218, #220,
  #221, #222. They are product bugs on their own beads and are not flow work.
- **The `docs audit` classifier family** — #173, #180, #205, #206, #209. A separate thread
  with its own root cause (English-keyword proximity, not agent behaviour).
- **BDL-066, agent behaviour observability.** It has its own drafted documents and answers a
  different question: this epic is about HOLDING a rule, BDL-066 is about SEEING what an
  agent was told. Ranked beside this epic, not inside it.
- **Fixing `bd` upstream.** Where a finding is External (steveyegge/beads — #187, #194,
  #165), the deliverable is our adapter's behaviour in the face of it, not a patch to that
  project.

## User Stories

### US-1: The owner learns how large a change is before agreeing to it

**As** the owner starting a work item, **I want** the axes a change ranges over derived from
the source before the type is chosen, **so that** I am not told a bug is one missing edge
when it is six instances of a class across four entry points.

**Acceptance criteria** (each references a scenario in `tests/acceptance/features/`):
- [x] Scenario: `A work item without an Axes section is reported before its first dev bead`
- [x] Scenario: `The axes name the population the derivation could not resolve`

### US-2: A commit that leaves the declared scope is caught by the Gate, not by a reviewer

**As** the owner, **I want** a change touching a call site outside the declared axes to be a
finding, **so that** the axes are an instrument rather than a paragraph an agent may skim.

**Acceptance criteria**:
- [x] Scenario: `A commit touching a call site outside the declared axes is reported`

### US-3: The reviewer is told what it can reach, not what was withheld

**As** the owner reading a verdict, **I want** `review-brief` to count every channel that
carries the author's account, **so that** "0 withheld" stops being true about its own scope
and false about the question.

**Acceptance criteria**:
- [x] Scenario: `The commit bodies of the reviewed range are stated with the range they were read over`
- [x] Scenario: `A document a composed role prompt names is reported as reachable, with the prompt that names it`

### US-4: A claimed mutation check is distinguishable from a performed one

**As** the owner, **I want** a mutation score produced by a command over a declared scope,
**so that** a suite that cannot fail is detected by the Gate rather than by a person reading
bead comments.

**Acceptance criteria**:
- [x] Scenario: `a target outside the configured source paths is reported`
- [x] Scenario: `a mutation run reports a score for the slice it was scoped to`

### US-5: A guard reports the write paths it cannot see

**As** the owner, **I want** each flow guard's enforcement surface derived and reported,
**so that** a file written through a path the guard does not watch is a finding rather than a
silence.

**Acceptance criteria**:
- [x] Scenario: `The report names a write path the binding cannot see`

## Acceptance Criteria (overall)

Behaviour-bearing criteria are scenarios; the suite holds their text and this list references
them by name. `beadloom lint` reports a referenced scenario the suite does not contain.

Every scenario box below is ticked on a measurement, not on a slice being declared done:
`uv run pytest tests/acceptance` on `features/BDL-068` at S4's end passed 232 of 232 scenarios
in 36 files, measured in Darwin arm64 / CPython 3.13.7 and in 0 of the 21 rooms this project
declares, so it is a claim about this machine and about no CI leg. Three references were
repointed at the same time, because they named scenarios the suite does not hold and `doctor`
reported all five occurrences: the two US-3 criteria now name the reachability scenarios S2
shipped, and the US-4 criterion now names `mutation_scope.feature`'s own spelling. The
non-behavioural boxes stay open — S5 and S6 have not shipped.

- [x] Scenario: `A work item without an Axes section is reported before its first dev bead`
- [x] Scenario: `The axes name the population the derivation could not resolve`
- [x] Scenario: `A commit touching a call site outside the declared axes is reported`
- [x] Scenario: `The commit bodies of the reviewed range are stated with the range they were read over`
- [x] Scenario: `a target outside the configured source paths is reported`
- [x] Scenario: `The report names a write path the binding cannot see`

**Non-behavioural criteria** stay checkboxes and are labelled, so the absence of a scenario is
a stated decision rather than a gap:

- [ ] The six slices are ordered and each is independently shippable — non-behavioural: a
      sequencing decision produces no observable change in the product.
- [ ] Every External (`bd`) finding is answered by our adapter's behaviour and the upstream
      issue is linked rather than patched — non-behavioural for this repository: the observable
      change belongs to the adapter scenarios of the slice that carries it.
