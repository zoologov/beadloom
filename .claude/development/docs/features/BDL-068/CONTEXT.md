# CONTEXT: BDL-068 — The flow's rules are advice; make them instruments

> **Status:** Approved
> **Created:** 2026-09-02
> **Last updated:** 2026-09-05

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
| 2026-09-04 | `scenario-coverage` does not stay `warn` on this project for its DOCUMENT leg: a document that references a scenario name the suite does not carry becomes `error`, while the node-population leg stays `warn`. Neither moves today — the promotion carries a precondition and an implementation cost, and both are stated here. | The severity comment shipped in `rules.yml` is right about one leg only: "a finding about declared INTENT is not a finding about code, and `error` would turn every adopter's green project red on the upgrade that ships the rule". That holds for the node leg, which reports 29 feature nodes with no bound scenario. The document leg reports something else — a name a document states and the suite does not contain is wrong about a checkable fact — and it hid a broken promise through six waves and ten beads because a `warn` leaves `lint --strict` at rc 0. Precondition, measured on 2026-09-04: 34 document findings exist, 5 in this epic's PRD (S2's two and S3's one, each with a suite scenario carrying the behaviour under another name) and 26 in BDL-061's closed PRD, which is repaired or removed from `references:` with the exclusion stated. Cost: severity is per RULE, not per leg — `graph/rules/scenario_coverage.py` passes `rule.severity` to every finding — so this is a per-leg severity key and not a `rules.yml` edit. |
| 2026-09-04 | US-5's acceptance criterion moves to the name the suite carries (`The report names a write path the binding cannot see`); the scenario is not renamed to the PRD's text. | The PRD states the convention that decides this: "the suite holds their text and this list references them by name", so the suite is the source of truth and the reference is what moves. The suite's name is also the truer one — the scenario builds a binding and reports the tool it cannot see, and performs no write, so "a write through a path outside the guard's surface" described something the scenario does not do. A second and smaller reason: `beadloom-0mdo.43` is editing `tests/acceptance/features/guard_surface.feature` in the same working tree, and renaming a scenario there would have put two agents in one file. |
| 2026-09-04 | S2's and S3's axis rows are derived retroactively and added to the RFC, dated to the tree they were actually taken on rather than to the tree those slices began on. | The section is the scope an active check judges against, not a log, and an incomplete union gave a wrong verdict in the present: `beadloom waves` reported `mutation-scope: not_derived — no row of RFC.md names it` against `beadloom-0mdo.45`, whose entire declared scope is that node. Dating the sweep 2026-09-04 at `d0088ba` keeps "each slice's rows are derived when that slice begins" true for S5 and S6 and stops a sweep taken forty commits later being read as S2's or S3's own. |
| 2026-09-04 | An axis row is `yes` when this epic WRITES the node and `no` when it only READS it, measured from the paths the epic changes. This replaces S1's "nothing is excluded" for every row derived after S1's. | S1's blanket `yes` left `scope-check` unable to fail: it approved a node set wide enough that S4 edited seven nodes no row named while the check reported "36 staged path(s) a node owns, 65 no node owns" and zero findings. CONTEXT's own constraint is that no check is added that cannot fail. The decision is therefore measured — the 239 paths BDL-068 changes since `17eafb8^` resolve to thirty owning nodes — and a later slice that needs one of the fourteen `no` rows re-derives and moves it, which is the per-slice rule already in force. |
| 2026-09-04 | The mutation scope gains four of S4's five new domain cores — `guards/shell_targets.py` (146 mutants), `guards/surface.py` (136), `waves/derivation.py` (98) and `onboarding/role_duties.py` (324) — and not `application/typed_surface.py` (241). | CONTEXT's rule for this scope is pure domain cores, where a survivor is a gap in the tests rather than an untested I/O branch. Applied per file by WHERE the filesystem is touched rather than whether: the four confine it to named collectors at the module edge (`_read_matchers`, `_read_grants`, `_marked_files`, `_role_files_on_disk`), which is the shape of `doc_quality.py`, declared since S3 and reading one file at its outermost loop. In `typed_surface.py` the filesystem IS the derivation — `_resolve_path` decides its answer with `glob`, `is_dir`, `is_file` and `exists` interleaved with the logic — so a mutant swapping `is_dir()` for `is_file()` survives unless a fixture tree has exactly that shape, and that survivor says nothing about the tests. Its 241 mutants are recorded here so the exclusion can be revisited when the resolution half is lifted out of the derivation. |
| 2026-09-04 | A declared mutation target the runner cannot reach is a test failure rather than a backlog item: `[tool.mutmut] only_mutate` now covers every name in `mutation.targets`, the nightly job names every one of them with `--target` and passes no `--only`, and `tests/test_mutation_runner_scope.py` asserts both inclusions instead of one. | Two of the three targets declared in S3 had never reported a run, and the cause was configuration rather than the schedule. Three settings must agree for a target to be measured and two said no: `only_mutate` named `graph/rules/*` alone, so no run could produce a mutant in `doc_quality.py` or `doc_shape.py` however long it ran, and the job's `--only src/beadloom/graph/rules/` told the one command that reports the gap to print the other two as "not judged by this run" instead of as `mutation-target-unmeasured`. The Gate cannot see it either: `beadloom ci` calls `check_mutation_scope` (could a mutant run here) and never `report_mutation_score` (did one), because the tree carries no stats file. The existing test asserted runner ⊆ declared, which is the one direction that cannot see this. |
| 2026-09-04 | The pool that widening required is derived, and its two exclusions are measured in the room they fail in rather than reasoned about. | The union of the six file targets' covering tests is 64 files, 43 of them new. Run in a `git archive HEAD` room with no `.git`, 42 passed and one failed — `test_bead15_s3b_coverage.py`, already excluded by name for that reason. Run in the actual `mutants/` copy, a second file failed that the cheaper room had passed: `test_bead18_s5_relation.py` reads `.beads/issues.jsonl` and `also_copy` does not carry `.beads`, which is 263 MB holding an embedded database. A room that reproduces one property of another room answers about that property only, which is why the expensive run was made before the pool was called derived. |
| 2026-09-04 | The mutation floors are calibrated in the room the job runs in: the rules slice moves from 0.95 to 0.94, and the whole declared scope is judged at 0.88. The job's timeout moves from 180 to 240 minutes. | Measured on the first run this workflow has ever had on a GitHub runner (33851288658, dispatched by hand after the cron fired 4 h 40 m late): `graph/rules/` scores 95.56% on `ubuntu-latest` and 96.19% on the macOS machine S3 calibrated against — 3 811 killed and 177 survived, against 3 836 and 152, over the same mutants. S3 chose 0.95 to leave ~1.2 points of headroom and it left 0.56, which is 22 mutants, so the floor would trip on the handful of new survivors its own comment said it was there to tolerate. This is recalibration and not accommodation: the number moves because the room it was taken in was not the room it is applied in, and both numbers are recorded. The same run measured 1 h 29 min 18 s against 54 min 55 s, a factor of 1.63, which projects the widened scope at about 110 minutes and is why the timeout moved before the margin did. |
| 2026-09-04 | `application` stays RULED OUT of BDL-068's axes, and the three S5 declarations that named it are regenerated from the derived rows instead. | The declaration confused a layer with a node. Node `application` owns eighteen files and every one renders a view — `architecture_view.py`, `landscape_view.py`, `site_about.py`, `site_landscape.py`, `site_mermaid_guard.py` and the `site_dashboard/` package — and none of them reaches the tracker. Measured: `application` is not among the 31 nodes owning the 88 owned paths BDL-068 changes since `17eafb8^`. The application-layer files S5 touches are owned by nodes of their own (`active-table`, `flow-guards`, `ci-gate`, `doc-spaces`, `intent-reader`), so approving `application` would put eighteen view-rendering files inside the approval to buy a name no S5 surface needs. `beadloom waves` stated the remedy itself: widening the declaration is not the fix. |
| 2026-09-04 | The derived `bd` call-site population `beadloom-0mdo.51` builds is homed at node `bd-seam`, not in a new module under `application`. | `services/bd_seam.py` is the single place this project's code reaches `bd` — the population is a property of that seam, and the sweep confirms it: fourteen caller sites in five nodes all reach the tracker through it. A new module placed under a node the axes rule out would reproduce, one layer up, the finding `beadloom-0mdo.58` was opened to answer. |
| 2026-09-04 | This project keeps depending on `bd merge-slot`, in the call form that grants exclusion and in no other: `acquire --holder <bead-id>` read by exit code, and `release --holder <bead-id>`. The exclusion the flow relies on for FILES stays `beadloom waves`, and the instruction now says which guarantee is which. | Re-measured on bd 1.0.4 in an isolated rig with every exit code read without a pipe, because BDL-UX #194 and #237 both name the primitive as the broken thing. It is not: `acquire` refuses a held slot with exit 1, four rounds of eight simultaneous acquires produced exactly one winner each round, and `release --holder` is owner-checked. Every defect the two entries measured is a property of the call form this project instructs — no `--holder`, a bare `release`, and `--wait` under prose of ours that called it blocking. Withdrawing the primitive would discard a working mutex to answer a defect in our own prose; instructing it unchanged would keep telling every agent it holds a lock it does not hold. |
| 2026-09-04 | S5's axes are derived from thirteen Python targets, and the ~261 `bd` call sites that are prose are recorded as UNREACHABLE rather than absent. | `beadloom impact` sweeps Python source, and this project instructs `bd` far more often than it invokes it: 118 sites in its own harness, 133 in the templates it ships, 8 in hook bodies held as Python string literals, 2 in a provisioning shell script, and `.git/hooks/post-merge`, which `bd init` writes outside the repository and which `beadloom-l2f2`'s finding is about. Those counts come from a literal search for `bd <subcommand>`, so they are a lower bound and not a derivation. An unreachable region is unresolved, not empty — the same rule S4's axes state for `co-writers` — and deriving that population is exactly what `beadloom-0mdo.51` exists to do. |
| 2026-09-05 | A scaffolded bead DAG is created as ONE `bd create --graph` plan whose edges name plan-local keys, and the flat ids that path allocates are accepted in place of the `<parent>.<n>` shape `bd create --parent` gives. | The plan removes BDL-UX #171's root rather than guarding it: an edge names two keys the author chose, so no id is written down and there is none to get wrong. The id SHAPE is the cost, and it was measured rather than assumed — `bd create --graph` with `parent_id` sets the parent relation and allocates `rigB-p05`, while `bd create --parent` allocates `rigB-af8.1`, so a scaffolded bead loses the readable ordering its number carried. That ordering is what the convention wrote into titles in the first place, which is the defect; `bd dep tree` renders the DAG from the tracker, where the order is a fact rather than a copy. This changes nothing for the per-slice beads this epic creates with `bd create --parent`, whose remedy is `--json` and the title convention. |
| 2026-09-08 | The mutation scope KEEPS all seven pure cores S5 added — `bd_seam/assumptions.py` (183 mutants), `bd_seam/invocations.py` (181), `active_table/row_ids.py` (122), `bd_seam/answers.py` (107), `active_table/staging.py` (80), `bd_seam/creation.py` (62) and `waves/landing.py` (29) = 764, taking the declared scope to 6 464. None is excluded on cost. | Q3's yardstick is a cost, so the cost was measured rather than projected: the seven RUN in 36 min 35 s (six workers, 10-core Darwin arm64, CPython 3.13.7, mutmut 3.7.0, in a `git archive HEAD` room), scoring 83.64% — 639 killed, 125 survived, 0 unrun. Scaled by the 1.63 the `ubuntu-latest` runner measured against this machine, that is 60 min, taking the nightly from a projected 110 to 171 minutes against a cap raised to 340. The count alone would have decided this wrong in both directions: 764 mutants is 13.4% more mutants and eight times the cost per mutant, because these targets' covering tests are the derived-population ones that walk this repository's harness and template files — `invocations.py` and `assumptions.py` carry ten covering test files each where `creation.py` carries two. It is nonetheless affordable, because a nightly's only real cost is a cap that trips and reports nothing. Not excluded on purity either: none of the seven imports `subprocess` — only `bd_seam/client.py` does, and it stays undeclared — so CONTEXT's pure-core rule admits all seven on the same ground it admitted `doc_quality.py`. |
| 2026-09-08 | The aggregate floor is re-derived at the new scope and STAYS at 0.88; the job's timeout moves from 240 to 340 minutes. | The workflow states the rule itself — the floor "is a property of the scope and is re-derived whenever the scope changes" — and the pass that widened the scope to fourteen targets left both numbers where a scope of seven had put them. Re-derived: the seven score 83.64%, below the scope's mean, so the aggregate falls from 89.98% (5 129 of 5 700) to 89.23% (5 768 of 6 464) and 0.88 keeps 1.23 points of headroom where it had 2.00. That is 79 mutants, against the 62 at which the rules floor above was called adequate, and the floor survives its own worst case: two of its three components are macOS numbers enforced on `ubuntu-latest`, and dropping both by the 0.63 points the rules slice actually fell between those rooms still leaves 88.99%. The timeout moves because the projection did — 171 minutes by the same method that set 180 over 89 and 240 over 110, both about 2.0, and 171 x 2 is 342. It stops at 340 rather than 360 because 360 is GitHub's own six-hour ceiling for a hosted job, where a `timeout-minutes` equal to it can never be the thing that trips. |
| 2026-09-08 | A mutation target's cost is its mutant count multiplied by the cost of reaching a killing test, and this project will state both when it declares one. | Recorded because the count on its own was misleading here and because six earlier beads deferred on a reason that was true of the wrong half of the job. The COUNT needs no `mutants/` copy and no room — `mutate_file_contents` is static generation over a file's own text, and all fourteen targets count in 17.3 s in an ordinary working tree. The copy is required by a RUN. That distinction was available at every one of the six deferrals, and the obstacle to the second half was applied to the first. || 2026-09-08 | S6's axes are derived from nineteen Python targets, and the 862 `beadloom <subcommand>` instructions in the flow's own documents are recorded as `unresolved` rather than left out. | S6's subject is the flow's documents and roles, and `beadloom impact` parses Python: measured, the derivation reaches 0 of those 862 instruction sites and covers only the machine half each bead builds. S5's equivalent gap was 14 derivable call sites against about 261 in prose, so S6's is the wider one and saying so is what stops a `no` row being read as coverage of `.claude/CLAUDE.md` or the shipped templates. |
| 2026-09-08 | Node `onboarding` is IN SCOPE for BDL-068, which is the opposite decision to `application`. | It owns 24 of the 110 paths this epic changes, the largest share of any node, and it is the only node whose source covers the shipped `CLAUDE.md` template, the role cores and the vendored agent snapshots that `beadloom-0mdo.59` and `beadloom-iur5` rewrite. `application` was ruled out because its eighteen files are all view-rendering and none was touched; `onboarding`'s share is measured, so the same rule gives the opposite answer. The cost is stated: approving it approves 57 files, and no narrower node exists because no node's source names `templates/`. |
| 2026-09-08 | `beadloom-ec1a`'s scope is derived from its TITLE alone and is recorded as such, rather than being widened to cover work nobody has specified. | The bead has no description, only a title, and its own comment says so. The title names one command — `config-check` should flag orphaned tool adapters — which resolves to exactly one node. Widening it to `role-adapters` as well would author scope for a bead whose content is not yet derived, which is the failure `beadloom-0mdo.46` exists to prevent one level up. |


## Related Files

Discover through `beadloom ctx <ref-id>` — every node the RFC names resolves today:
`review-brief`, `wave-plan`, `guard-hooks`, `ci-gate`, `sync-check`, `doc-quality`,
`docs-audit`, `mutation-scope`, `scenario-binding`, `flow-config`, `flow-composer`,
`role-composer`, `role-adapters`, `flow-manifest`, `flow-suppression`,
`agentic-flow-setup`, `config-check`.

## Current Phase

- **Phase:** Development — S5 is complete on the branch; S6 has started with its axes bead.
- **Current bead:** `beadloom-0mdo.72`, S6's axes, derived before any S6 wave launches.
  `beadloom waves` over S6's fifteen beads went from 10 findings to 5: 6 `unresolved_scope` and
  4 `not_derived` cleared, and the 5 that remain are 1 working-tree medium naming this bead's
  own uncommitted files and 4 `unguarded_axis`, which is BDL-UX #245 and is `beadloom-0mdo.46`'s
  subject. Before S6, `beadloom-0mdo.57` closed S5's documentation pass and `.13`, the slice
  bead, closes with it; `.62` and `.61` closed the two fix beads S5's review
  produced on its first pass, and the review passed on its second at 0 critical and 0 major.
  The slice's dev beads were `.39` (the landing lock, BDL-UX #194 and #237), `.51` (the derived
  `bd` call-site population), `.52` (#187 and #97), `.53` (#171 and #165) and `.54` (#207 and
  #210), over five waves, with `.58` deriving S5's axes before the first of them and `.55`
  cross-checking the six instruments against each other afterwards.
- **Next:** S6 (`beadloom-0mdo.14`), fifteen beads plus test, review and tech-writer. The
  owner decided on 2026-09-08 that it runs in full, declining an offer to cut it into the two
  entries that bite today and a follow-up epic. The decision and the offer are both recorded on
  `.14` and in ACTIVE.md.
- **Blockers:** none. S1 landed on `main` as `17eafb8` (PR #59) and S2+S3 as `97e0504`
  (PR #60). S4 and S5 are on `features/BDL-068` and not yet in a pull request.
