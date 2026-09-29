# PRD: BDL-074 — Tests that belong to the graph

> **Status:** Approved
> **Created:** 2026-09-28

---

## Problem

Beadloom's code is organised by domain and bound to the graph; its tests are organised by history
and bound to nothing. A measured map of the suite (`map/test-map.json`, three full runs, 2026-09-27)
gives the shape:

| | measured |
|---|---|
| size | 457 files, 10 895 tests, 518 s for the whole suite |
| integration tests | 6 043 (55.5%) |
| unit tests | 3 795 (34.8%) |
| self-checks of this repository | 547 (5.0%) — **28% of the suite's time** |
| acceptance (Gherkin) | 510 (4.7%) |
| files mixing kinds | 133 of 457 |
| nodes a test file executes | median 5, mean 11.3, max 60 |
| files with no clear node | 201 execute several nodes with none primary; 29 execute no product code |

**The suite is not isolated from the repository it lives in.** 19 files (89 tests) touch the
repository's own index `.beadloom/beadloom.db`, and four of them write it; three run `bd` against the
live tracker; eleven run `git` against the repository's history; 32 more read repository files by
defaulting to the current directory (the product has 53 such `Path.cwd()` sites). This is the cause
of the shared-index failures that reddened required checks on five pull requests running
(`beadloom-qq6m`), and of the false kills measured under concurrent mutation runs (BDL-073).

**The link Beadloom already draws between tests and nodes is false.** `context_oracle/test_mapper.py`
guesses a node from import names, file names and directories, stores the guess at reindex, and
`beadloom ctx` prints it. Measured today: only 22 of 108 nodes have any test file; `ctx rule-engine`
reports **0 tests** for a node whose single function `load_rules` is executed by 855; 442 of the 884
stored links point into `mutants/`, mutmut's copy of the tree; the mapper counts itself as a test. The
Gherkin `@node:` tags are data, not a binding: they name the node a step file actually executes in 37
of 69 files, and a node the file never executes in 3.

**And the cost shows up elsewhere.** The most-executed code is infrastructure — `db.open_db` runs in
1 640 tests — because most tests enter through the CLI and a real index. A function in the rule
engine is covered by 550–855 tests. That fan-out is why whole-scope mutation took hours and was
retired on 2026-09-27, and why a pull request's CI takes 10-15 minutes.

## Impact

For this repository: CI that fails for reasons unrelated to the change, mutation numbers that cannot
be trusted or produced, and a `ctx` that misstates what is tested. For adopters: Beadloom holds code
and documentation to the graph and holds tests to nothing — and the one thing it does say about tests
is wrong. The owner's aim is a Beadloom that is strict end to end: **node → code → documentation →
tests → the strength of those tests**.

## Goals

- **G1 — Isolation.** No test reads or writes the repository's live index, tracker or git history
  implicitly. Tests that check this repository itself stay, as an explicit category that runs against
  an isolated copy.
- **G1b — Self-checks are sorted, deduplicated and cheap** (owner decision 2026-09-28). The 547
  tests in 76 files that assert on this repository itself are inventoried by what they guard. A check
  that repeats what a required Gate leg already enforces on the real repository leaves pytest — only
  with the Gate leg named and shown to check the same thing — and the checker keeps a product test on
  a synthetic fixture instead. A check the Gate does not make moves to `tests/self_check/<category>/`
  (architecture, docs, config, process) and runs against an isolated snapshot built once per session,
  or becomes a Gate leg where adopters would want it. Recorded findings (`xfail` with a BDL-UX
  reference) stay as they are.
- **G2 — A declared binding.** Every test file states the node or nodes it tests, as a fact the graph
  holds; `beadloom ctx <node>` shows the real tests; the heuristic mapper stops being the source.
- **G3 — Rules over the binding.** Lint reports a node with no bound tests, a test bound to no node,
  and a test of a domain node that reaches into infrastructure — each with its population stated and
  its severity configurable per node kind.
- **G4 — Mutation per change.** A pull request mutates the functions it changed and runs only the
  tests bound to their nodes, in minutes, and reports its survivors; a weekly random sample gives the
  trend with a confidence interval.
- **G5 — A restructured pilot, under invariants.** One domain — the rule engine, where mutation cost
  and fan-out are highest — is restructured: tests located by node, kinds separated, a fast unit layer
  beside the code. The number of tests, per-node coverage and the sampled kill rate must not fall.
- **G5a — Every test file with a clear node lives under that node** (owner decision 2026-09-28, after
  this PRD was approved). The 227 files the map gives a clear primary node are relocated mechanically
  into a layout that mirrors the code — their contents unchanged. The 201 files that touch several
  nodes with none primary need splitting, which is real work: the rule-engine ones go with the pilot,
  the rest to follow-up slices.
- **G5b — Acceptance scenarios follow the same rule** (owner decision 2026-09-28). The Gherkin suite
  (76 `.feature` files, 510 scenarios, 69 step files) is laid out by the graph's feature nodes,
  mirroring `docs/domains/<domain>/features/<feature>/`. Feature files whose `@node:` tag names the
  node their steps actually execute (37 of 69 step files today) move mechanically; a rule checks that
  a scenario's `@node:` tag, its folder and the code it executes agree. Rewriting the content — a
  shared step vocabulary per domain, `Rule:` and `Scenario Outline`, declarative steps over a driver
  layer — is done for the rule-engine pilot; the rest is follow-up slices.
- **G6 — Standards that are checked.** What a good test is here — one behaviour, arrange/act/assert,
  no shared state, named by behaviour — is written into the `test` role and checked where a check
  can be written.

## Non-goals

- Rewriting all 10 895 tests in this epic. The epic delivers the mechanism, the rules, one
  restructured domain and the mechanical relocation of every file with a clear node; splitting the
  remaining mixed files is follow-up slices that the rules then measure.
- Removing the self-check tests. They are how this project dogfoods its own gates; they become an
  isolated, named category rather than a hidden side effect.
- Settling what killed the whole-scope nightly's runner. That question was closed as superseded.
- **Binding a test by a guess** (owner, 2026-09-28, after the second review; `beadloom-2mj3.15`
  enumerated 32 conventions of the retired mapper, proved 23 no worse than main and ruled out 9).
  A test binds by the mirror, by its place beside the code, or through `tests:` — nothing else:
  - *NG2* — an Xcode sibling test target (`ShopTests/` beside `Shop/`) is not paired by default,
    because the pairing depends on the project's own name; one line of `tests.mirrors` restores
    main's figures.
  - *NG3* — a test is not bound by what it imports, nor by a folder named after a node: an import
    names fixtures, helpers and collaborators as well as the subject. Such a file is read and counted
    unplaced, and the untested count is withheld, so the debt score does not move.
  - *NG4* — a framework is not named from a marker file without a test file (`conftest.py`,
    `jest.config.*`, an empty test folder). A project with no test says so and scores that.
  - NG1 was **not** accepted as a non-goal: `test/`, `spec/` and `__tests__/` join `tests/` as default
    roots, read only when present, so a flat test folder is read (unplaced) without a declaration.
    NG1 named all three places; the coordinator's question to the owner named only `test/` and
    `spec/`, and `__tests__/` was added under the same ruling in `beadloom-2mj3.17` after the third
    review found it unread.

## User Stories

**As the maintainer**, I open `beadloom ctx rule-engine` and see which tests bind to it and how
strong they are, instead of "0 tests".

**As the maintainer**, a pull request that changes one function in the rule engine tells me, within
minutes, which mutants of that function its tests let survive.

**As a reviewer**, a CI failure means the change broke something — not that two tests raced for the
repository's own index.

**As an adopter**, `beadloom lint` tells me which features have no tests and which tests belong to
nothing, the same way it tells me which features have no documentation.

## Acceptance Criteria (overall)

- The tracer that built the map finds **0** implicit contacts with the live index, tracker or git
  history outside the self-check category, and the self-check category runs against an isolated copy.
- `beadloom ctx <node>` reports tests from the declared binding: no entry under `mutants/`, no test
  counted twice through a parent, and `rule-engine` reports the tests bound to it.
- Every test file is bound to at least one node, or named in an exemption that carries a reason and
  an exit condition. The lint rules report their populations.
- A pull request that changes one rule-engine function completes its per-change mutation job on
  `ubuntu-latest` in **10 minutes or less** and lists the survivors by node; the weekly sample job
  completes and prints a kill rate with its interval.
- The rule-engine pilot is restructured and the three invariants hold, measured before and after:
  test count, per-node line coverage, and the kill rate on a fixed sample.
- The 227 clear-node files sit under their nodes' folders with their contents unchanged, proven by an
  identical collected-test set (node ids modulo path) and an identical pass/fail result before and
  after the move.
- Every `@node:` tag names a node the scenario executes and matches its folder, or is listed as an
  exemption with a reason; the three tags that name a node never executed are resolved.
- Every self-check is either removed with the Gate leg that replaces it named, moved under
  `tests/self_check/<category>/` against the isolated snapshot, or kept as a recorded finding; the
  self-check share of suite time (145.5 s, 28%, measured 2026-09-27) is re-measured and reported.
- `beadloom ci` rc 0 and the nine required checks green on every pull request of the epic.

### Corrections (2026-09-28, after T measured every criterion — `beadloom-75pl`)

T found 10 criteria met, 4 not met, 2 not measurable before PR 3. The owner ruled on each:

- **Every test file bound or exempt.** The 101 self-check files bind to no node and are named in no
  exemption; the rule reported them under a phrase that was not true. Fixed in this epic:
  `beadloom-2mj3.6` makes the self-check and acceptance kinds outcomes the rule names by kind and
  count, corrects six false exemption reasons, and gives `ctx` and `beadloom mutation` one unplaced
  count.
- **The 227 clear-node files.** 216 sit in their node's folder. The other 11 are accounted for: one
  was retired with its module (C2), one became mixed, and nine acceptance step files follow the
  folder of the node their `@node:` tag names — the owner's layout ruling of 2026-09-28 — rather than
  the map's node. The criterion is read as "placed by the rule in force", not as 227 literally.
- **Every `@node:` tag names a node the scenario executes.** The folder half holds. The execution half
  is **not delivered by this epic**: a static stand-in found 59 of 81 executed pairs, too weak to be a
  rule. It moves to `beadloom-o9rl` (a coverage run of the acceptance suite). The three tags that
  name never-executed nodes are resolved here, in `beadloom-2mj3.8`.
- **Every self-check in one of three outcomes, against the snapshot.** The 36 marked self-checks and
  7 scenarios kept outside the three outcomes are placed in `beadloom-2mj3.8`. "Against the isolated
  snapshot" is read as **no contact with the live index, tracker or history**; 66 self-check files
  read files of the working tree, which the snapshot copies unchanged, and are not moved.
- **Also in this epic:** `reindex` and `test-mapping`, two of the nine kept nodes, had 0 bound tests;
  `beadloom-2mj3.7` splits their mixed files.
- **Not measurable before PR 3:** the per-change job's time on `ubuntu-latest` (locally 394 s, about
  642 s projected before setup — at risk) and the checks on PR 3 are V's (`beadloom-paze`).
