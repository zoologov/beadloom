# PRD: BDL-073 — The mutation duty becomes executable

> **Status:** Approved
> **Created:** 2026-09-20

---

## Problem

The mutation duty has produced an aggregate score **never**. BDL-072 fixed the guard that made every
nightly judge zero of 7187 mutants, and the chain now works — a local run of one declared target
printed `Score: 96.6% of 29 scored mutants`. What BDL-072 could not fix is that the job cannot
finish: two dispatched runs died at 93 and 100 minutes, both at the same queue position, and the
arithmetic says they never could have.

**The budget was always short, and nobody had done the sum.** Projected from the runner's own map
(`mutants/mutmut-stats.json`, mutant count × summed covering-test duration): the `graph/rules` slice
is **4479 mutants ≈ 28.3 h** of worst-case serial test time, against a budget of `timeout-minutes:
340` × 4 children ≈ **22.7 h** of worker time. The declared floors — 0.94 for the slice, 0.88 for
the scope — are therefore held against a measurement the pipeline cannot take.

**Most of that time is spent by luck rather than by necessity.** mutmut hands a mutant's covering
tests to pytest as an unordered `set` under `-x` (`mutmut/__main__.py:1443`), so which test kills a
mutant first is arbitrary. Measured over six mutants with identical verdicts under three orderings:

| Ordering of the same 827 covering tests | Mean time to kill |
|---|---|
| cheapest-first, by the durations mutmut already records | **4.2 s** |
| alphabetical (what the set happens to give today) | 21.8 s |
| most-expensive-first | 46.7 s |

**One function carries a fifth of the slice.** `graph/rules/loader.py::load_rules` is **333 mutants**
(19.7% of the worst case), covered by **827 tests across 67 files** — 7.6% of a 10 850-test suite
executing one function, 76% of them passing through it on the way to `init`, `lint` or an MCP tool
rather than asserting anything about rule loading. Half of its mutants (163 of 333) sit in a
twelve-branch `elif has_X:` dispatch.

**And the measurement that does run is not clean.** At `--max-children 4`, a mutant measured as
*killed* in 16 s survives when run serially in 49 s: the "kill" was an `IntegrityError` from the
shared live index (`beadloom-qq6m`). The nightly's kill counts contain an unknown number of these.

**What the surviving mutants say about the tests.** Sampling 30 of the 333 gives an 83.3% kill rate
and five survivors, each naming a gap: nothing pins the loader's `encoding="utf-8"` — the same class
of defect BDL-072 met in CI a day earlier; nothing asserts any of twelve error-message texts, so a
mutant that replaces a message with `None` still raises and passes; and no test loads a `rules.yml`
with no `rules:` key.

## Impact

The project's own claim about itself. `beadloom mutation` is the instrument that says whether this
suite can tell a defect from a correct program, and it has never answered for the declared scope. A
floor that cannot be reached is not a gate, and the nightly now announces its own silence (BDL-072),
so every night that passes adds a comment to an open issue rather than a number to a record.

Adopters are affected differently but really: the mutation duty is part of what this project ships
as a practice, and it ships with an unexamined assumption — that the runner's default ordering is
good enough — which measurement contradicts by a factor of eleven.

## Goals

- A dispatched `Mutation` run **completes** and both scoring steps print a score over a non-zero
  population, with the run's own numbers recorded against the two floors.
- Time-to-kill is decided by the durations mutmut already measured, not by set ordering. *(withdrawn 2026-09-25 — see Correction)*
- `load_rules` stops carrying a fifth of the slice: the twelve-branch dispatch becomes a table.
- The five gaps the survivors name are closed by tests, starting with the loader's codec.
- The kill count stops containing false kills produced by concurrency against the shared index.
- One `beadloom init` parses `rules.yml` once.

## Non-goals

- Raising or lowering the floors. They are re-derived from the first honest aggregate, not moved to
  fit it.
- A larger runner. It is a paid option for a public repository and changes nothing about the tests.
- Fixing the shared-index flake itself (`beadloom-qq6m`) — this work item only stops counting its
  effects as kills.
- Settling what kills the runner. That is `beadloom-5isv`'s instrumented run and stays open; this
  work item removes the reason the job runs long enough to meet it.

## User Stories

**As the maintainer**, I dispatch the nightly and read a score, so that the mutation floors stop
being a claim about a measurement nobody has taken.

**As the maintainer**, I read a kill count I can trust, so that "4001 killed" is not partly an
artefact of four workers sharing one index.

**As a reviewer of this repository**, I can see which lines of `load_rules` nothing asserts on,
because the survivors are named rather than lost in an aggregate.

**As an adopter following this project's mutation practice**, the runner I am told to use orders a
mutant's tests cheapest-first, so my own budget buys eleven times more verdicts.

## Acceptance Criteria (overall)

- A dispatched run of `Mutation` reaches both scoring steps and each prints a score over a non-zero
  population. The numbers are recorded on the bead against the floors; a breach is reported as a
  finding, never by moving the floor.
- The covering tests of each mutant are ordered by their recorded durations. Measured on the same
  six mutants as the baseline: identical verdicts, and a mean time-to-kill at or under 6 s against
  the 21.8 s baseline. *(withdrawn 2026-09-25 — see Correction)* Stock mutmut 3.7.0 already meets it: 1.16 s.
- `load_rules` carries at most 160 mutants (from 333), measured by counting
  `def x_load_rules__mutmut_N` in the generated tree, and the twelve authoring keys still round-trip
  — every test that pins the current dispatch keeps passing, named in the RFC.
- Five new tests, each seen red against the mutant it answers: the loader's codec, an error-message
  text, a `rules.yml` with no `rules:` key, and the two remaining survivors.
- `rules.yml` is parsed once per `beadloom init`, measured by a call counter over the same path, and
  the TUI's lint panel still sees a file edited while it is open.
- `beadloom ci` rc 0, the suite green on the tree, and the nine required checks green on the PR.

## Correction (2026-09-25) — the ordering premise was wrong

**Front 1 is withdrawn.** mutmut 3.7.0 already hands each mutant's covering tests to pytest
cheapest-first: `mutmut/__main__.py:1478-1479`, inside the forked child, reads `# Run fast tests
first` / `sorted_tests = sorted(tests, key=lambda test_name: mutmut.duration_by_test[test_name])`.
The fan-out analysis read `:1443`, where the set is fetched, and missed `:1479`, where it is sorted;
the coordinator had `:1479` in a grep result on 2026-09-19 and did not register it. Found by the B2
dev agent (`beadloom-7omx`) and verified in the installed source.

**What that withdraws from this document:** the 4.2 s / 21.8 s / 46.7 s table describes the explore
agent's own hand runs, not mutmut's behaviour — stock 3.7.0 killed the same six mutants in a mean of
**1.16 s**. And the "28.3 h against a 22.7 h budget" arithmetic is mutmut's
`estimated_worst_case_time`, which prices every mutant as a survivor running its whole covering set;
at an 83% kill rate with ordered tests, kills cost seconds and the real cost of the tail is its
**survivors** (~50 s each for `load_rules`). The slice was never shown to be unscorable by time.

**What stands:** the runner kill (eight runs, 73-102 min, far under `timeout-minutes: 340` — killed,
not timed out); `--max-children 2`, landed in `a3bf2e2d`; the gap tests, which now carry the most
weight, because each one that kills a survivor removes ~50 s from the tail; the table and the memo.
The owner chose to dispatch a real run after wave 1 rather than wait for the end of the plan.
