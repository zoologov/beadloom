# Mutation Scope (component)

Whether a declared mutation target could run a single mutant, and what a run over it
produced.

**Source:** `src/beadloom/application/mutation_scope/`

---

## Overview

BDL-061's CONTEXT settled question Q5: **the mutation tool is the project's choice.** Owning a
runner would break tool-agnosticism and put a Python-only dependency inside a product that indexes
eleven languages. What Beadloom ships is the role duty (the dev and test role templates state
it), the scope convention, and this check.

**The failure worth catching is a declared target that runs zero mutants.** A mutation score is a
ratio, and a target naming a moved package, a deleted module or a directory holding no source file
produces the strongest possible ratio over an empty denominator. That reads as evidence of test
strength and is evidence of nothing.

**The component has two halves and they shipped eleven weeks apart.** `scope.py` asks whether a
declared target COULD run a mutant. `score.py` (BDL-068 S3.1) asks what a run over it DID, and it
exists because until it shipped nothing here could tell a performed mutation check from a sentence
claiming one: four beads in BDL-067 each reported "mutation checking" by a different hand method,
every result prose in a bead comment, and one of them — sent to audit another — found a reported
"all twenty assertions red before the fix" was eleven guards that cannot fail.

BDL-074 D1 added a third question: **what a run covers when it covers less than the whole
scope.** A run over one change or over a random sample is scored like any other run, and
five modules state the part it covered — see
[A run over a change, or over a sample](#a-run-over-a-change-or-over-a-sample).

## The three findings

| Check | Condition | Why it matters |
|-------|-----------|----------------|
| `mutation-outside-source` | the target is under no configured `scan_paths` entry | whatever it mutates is not the code this project indexes |
| `mutation-target-missing` | the target is not on disk | zero mutants, and a score computed over nothing |
| `mutation-zero-mutants` | the target holds no file in a declared `languages` suffix | zero mutants, for a different reason worth telling apart |

All three are `warn`. A project that declares no `mutation:` block declares no targets and is
reported nothing: not opting in is not a violation.

## Configuration

```yaml
# .beadloom/flow.yml
mutation:
  targets:
    - src/beadloom/doc_sync/doc_quality.py
```

`scan_paths` and `languages` come from `.beadloom/config.yml`, so an adopter whose code lives in
`lib/` is judged against `lib/`.

## The score, and the states in which there is none

`beadloom mutation` reads the counters a run wrote and holds them against the declared scope.
The counter vocabulary is NAMES rather than a tool — `killed` and `survived` are required,
`timeout`, `no_tests`, `skipped`, `suspicious` are optional, and `total` is accepted as the
second spelling of `mutants` — so any runner that writes a JSON object of counts is read.

```bash
beadloom mutation --stats mutants/mutmut-cicd-stats.json \
  --target src/beadloom/graph/rules/ --tool "mutmut 3.7.0"
```

| Check | Condition | Why it matters |
|-------|-----------|----------------|
| `mutation-target-unmeasured` | a declared target no run covered | the duty is stated and no score answers it |
| `mutation-run-zero-mutants` | the run produced no mutants, OR produced them and reached a verdict on none | a ratio over an empty denominator, again |
| `mutation-counters-missing` | the counters carry no `killed` or no `survived` | a missing counter read as zero produces "0%", and a number is what gets pasted into a bead comment |

Five rules decide what the number means, and each of them prevents a specific way of
flattering the suite:

- **A missing counter is not zero.** An absence stays an absence, and no score is stated.
- **Timeouts count as killed; mutants no test covers do not.** A mutant that hung the suite was
  detected. A mutant nothing executes was not, and leaving that class out of the denominator is
  how a slice with no tests at all scores 100%.
- **A run that does not say what it covered is not a run.** `--stats` without `--target` exits 2
  rather than assuming the run covered everything declared.
- **A run that classified nothing is not a run either** (BDL-068 S3.3). Ten mutants with
  `killed: 0`, `survived: 0` and `skipped: 10` stated `Score: none — see the findings below.`
  with no findings below it, and exited 0. Both emptinesses now report under
  `mutation-run-zero-mutants`, with a different `why` each, because the repairs differ: a run
  that produced nothing is pointed at the wrong path, and a run that classified nothing usually
  could not start its suite in the runner's copied tree.
- **A counter that cannot be a count is not read** (BDL-068 S3.3). `killed: -5` beside
  `survived: 1` divided to `125.0% of -4 scored mutants`. A negative is refused for the same
  reason `true` is: it makes a percentage out of something that is not a count. A required
  counter written that way is MISSING; an optional one is absent.

### The scope half is asked as well

Until BDL-068 S3.3 it was not, and the two halves of this component never met. A target naming a
path the code had moved away from, a target outside `scan_paths`, and a target holding no source
file each scored **100.0% of 10 scored mutants at exit 0**, measured on the shipped console
script over three temporary projects. `config-check` and the Gate reported all three; the command
producing the NUMBER asked neither.

`report_mutation_score` now folds `check_mutation_scope` over the targets the run is answerable
for, so `mutation-outside-source`, `mutation-target-missing` and `mutation-zero-mutants` reach the
score as well as the configuration report. It is filtered by `--only` for the reason `--only`
exists: reporting a target the run never claimed is how a scheduled job becomes permanently red.

### A slice that does not claim the whole scope

A first slice measures one declared target of several, and both obvious answers are wrong.
Reporting the rest as findings makes a scheduled job permanently red, which is how a check stops
being read; dropping them from `mutation.targets` deletes the duty to make the job green.
`--only` takes the third answer, which is the one this project uses everywhere else: judge what
the run is answerable for, and NAME what was not judged.

```bash
beadloom mutation --stats … --target src/beadloom/graph/rules/ \
  --only src/beadloom/graph/rules/
# Not judged by this run: src/beadloom/doc_sync/doc_quality.py, …
```

`--only` narrows what is judged; it never excuses what it names. A target inside the slice that
the run did not cover is still reported.

The report carries the ROOM it was measured in — platform, machine, interpreter and cores —
derived rather than typed by the caller (BDL-UX #227: the same suite skips fifteen tests on
Linux that it does not skip on macOS, and a mutation score is a ratio over whatever ran). Since
BDL-068 S3.2 `describe_room` composes that sentence in the
[verdict-room component](../verdict-room/DOC.md), so a Gate verdict and a mutation score name
one room in one wording; `beadloom rooms` says which rooms the project declares and which of
them a run did not enter.

The room is printed on **every** report, not only on the ones carrying a run. A report over a
declared target that no run covered exits 1 — it is a verdict — and it printed no room at all
until BDL-068 S3.3, which is the shape BDL-067 produced nine times. The room is a property of the
process, so it is stated wherever the process states anything.

Exit codes: `0` clean or nothing declared, `1` findings or a score under `--min-score`, `2` the
invocation cannot be answered.

## A run over a change, or over a sample

BDL-074 D1. The whole declared scope did not fit a CI runner: this repository's nightly was
killed mid-queue on ten runs, and was retired on 2026-09-27. A run now covers either the
functions one change touched or a random sample of the whole scope, and each shape says what
it covered. The runner-specific half — turning a function into a runner's mutant names —
stays out of the product (CONTEXT Q5); this repository keeps it in its own repository tooling.

| Module | Answers | Public API |
|--------|---------|------------|
| `touched.py` | which new-side lines a unified diff touched, and which functions they fall in | `changed_lines(diff_text)`, `touched_functions(source, lines)`, `TouchedFunctions` |
| `change.py` | the population of a change: touched functions in the declared scope, each one's owning node, the tests the binding ties to that node, the acceptance step files selected by its tag, and the unplaced files as the fallback | `diff_since(project_root, base)`, `plan_change(project_root, conn, diff_text, *, base)`, `describe_change`, `change_payload`, `ChangePlan`, `ChangedFunction`, `NodeSelection`, `MutationChangeError` |
| `acceptance.py` | which acceptance step files run a node's scenarios, by the `@node:` tags of the features they load (BDL-074 G1) | `acceptance_files_by_node(project_root, step_files)` |
| `survivors.py` | the survivors of a run, under the node owning their file | `read_survivors(path)`, `survivors_by_node(conn, survivors)`, `describe_survivors`, `survivors_payload`, `Survivor` |
| `sample.py` | the interval a score measured on a random sample supports | `wilson_interval(successes, trials)`, `sample_interval(counters, *, population)`, `describe_sample`, `sample_payload`, `SampleInterval` |

`scope.lies_within(path, entries)` is the one rule for "is this path one of these entries or
under one". It was `score._is_covered` until D1 and now answers two questions: whether a
declared target lies inside what a run covered, and whether a changed file lies inside the
declared scope.

**A function is what a runner mutates as a unit.** `touched_functions` names top-level
functions and `Class.method` for methods of a top-level class. A nested function belongs to
the outer one, and a decorator belongs to the function it decorates. A touched line inside no
function — a module constant, a class attribute — is COUNTED as `outside` rather than
dropped, because no mutant of it exists. Only Python is read. A source that does not parse
raises `SyntaxError`, and `plan_change` lists the file under `unread` instead of guessing its
functions.

**The diff is taken against the merge base.** `diff_since` runs
`git diff --unified=0 --no-renames --relative <merge-base>` against the working tree, so CI
measures a pull request's own commits and a local run measures uncommitted edits as well.
Untracked files are not in a git diff. A missing `git` or a base that names no commit raises
`MutationChangeError`.

**Every part of the population says what it covered.** `ChangePlan` carries the number of
files the change touched, the ones inside the declared scope, the unread ones, the touched
functions, the lines outside any function, one `NodeSelection` per node reached, and the test
files the runner falls back to. Each kind of test file is selected by what it is (BDL-074 G1):

| Kind | Where the plan carries it | Selected when |
|------|---------------------------|---------------|
| bound | `NodeSelection.bound_tests` | the binding recorded the node for the file, whatever placement bound it (`mirror`, `beside_code`, `override`) |
| acceptance step | `NodeSelection.acceptance_tests` (default `()`) | a scenario the step file loads carries the node's `@node:` tag |
| unplaced | `ChangePlan.unplaced_tests` | always: the binding placed the file nowhere (placement `unplaced`), so it may exercise the node and the binding cannot say. This is the runner's fallback |
| self-check, unowned | nowhere | never: a self-check tests the repository's own files rather than the changed code, and an unowned file names code no node owns |

`unplaced_tests` replaced `unbound_tests` (every file bound to no node, whatever the reason) in
BDL-074 G1, because that list held the acceptance step files and self-checks, which can never
become bound, so the fallback could never empty. The test files are read through
`graph.rules.suite_tables.read_test_files`, which carries each file's recorded kind.

`acceptance_files_by_node` reads each step file as Python for the LITERAL paths it hands to
pytest-bdd: every positional argument of `scenarios(...)` and the first of `scenario(...)`. A
path is resolved from the step file's own folder, pytest-bdd's default, and a folder stands for
every `.feature` beneath it. The `@node:` tags of the scenarios in those features name the
nodes. A computed path, a `bdd_features_base_dir` setting, a step file that does not parse and
a feature that cannot be read select nothing, because following them would be a guess that
reads as a binding. A `scenario(...)` binding is credited with every tag of its feature, which
can select a step file a little more widely than the one scenario it runs, never less.

Since BDL-074 F1 the plan also carries `test_placements` (test files by placement) and
`other_kinds` (the `other_kind` files by recorded kind), both defaulting to empty, and what it
STATES about the files bound to no node is counted from those by reason. `describe_change`
prints a `Binding:` line built by `context_oracle.test_binding.describe_unbound`: the unplaced
sentence `ctx` and the debt report state, then the unowned files, then each kind by its own
count, so the three surfaces state one number for "unplaced". The line is printed only when
some test file is bound to no node. A node's line adds `, N acceptance step file(s) by tag`
when N is non-zero. `change_payload` carries `unplaced_tests`, each node's `bound_tests` and
`acceptance_tests`, plus `test_placements` and `other_kinds` as `{name: count}` objects. An
empty population is a statement too: a change touching no function of the declared scope has
nothing to mutate and no score.

Measured by `beadloom-2mj3.10` on 2026-09-28, on a one-line change to
`liveness._cycle_reasons` (rule-engine; Darwin arm64, CPython 3.13.7, mutmut 3.7.0): this
repository's runner selected 36 bound + 10 acceptance by tag + 60 fallback = 106 files, with
103 self-checks excluded, and its select step took 180 s. The selection before G1 was
36 bound + 134 fallback = 170 files, in 342 s.

**Survivors are placed by the graph's ownership rule.** The survivor list is a JSON list of
`{path, mutant}` objects — names, not a tool. `survivors_by_node` asks
`get_owning_ref_id` for each file, so a survivor lands under the node `ctx` shows its file
under, and a file no node owns is listed under `(no node)` rather than dropped. An empty list
is a run in which nothing survived. An absent file, non-JSON, or an entry without a string
`path` and `mutant` is no list at all, and `read_survivors` returns `None`.

**A sampled score carries its interval.** `sample_interval` reads the counters as a sample
of `population` mutants and returns the Wilson interval at 95%, with timeouts counted as
killed as in the score. Wilson because it stays inside [0, 1] at the edges where a kill rate
lives. No finite-population correction, because the correction only narrows the interval and
leaving it out errs wide. `None` when no mutant was scored. A sample larger than its
population raises `ValueError`. The randomness itself is the runner's claim, which this
module cannot check.

`beadloom mutation` exposes the three as `--changed-since REF`, `--survivors FILE` and
`--sample-of N`; the options, the floor held against the interval and the exit codes are in
the [CLI reference](../../../../services/cli.md#beadloom-mutation).

## Where it is called

`beadloom config-check` prints the scope findings among its warnings, and the `config-check` gate step
carries them with their own `rule` names — the remedy is to edit the declared scope, not to run
`--fix`, and a reader filtering the gate's JSON must be able to find them.

The check runs **before** the gate step's database guard: a declaration is checkable against the
tree whether or not the index was built, and dropping it on a missing database would make the
finding disappear exactly when it is least likely to be noticed.

## Layering

It lives in `application` rather than beside the rest of the flow configuration because it joins
two sources: `flow.yml`'s declaration and `config.yml`'s scan paths, the second read through the
infrastructure seam that `onboarding` may not import (`onboarding-no-direct-infra`). Reading
`flow.yml` directly here follows the precedent of `application.guards.config`, which owns the
`guards:` block the same way.

Since BDL-074 D1 the change and survivor halves also read the index: `change.py` and
`survivors.py` ask `infrastructure.repository` for a file's owning node, and `change.py` reads
the test files with their binding and recorded kind through
`graph.rules.suite_tables.read_test_files` and takes `describe_unbound` from
`context_oracle.test_binding`. `acceptance.py` reads step files and features from disk, parsing
a feature with `graph.scenarios.parse_feature`. `change.py` runs `git` as a subprocess;
nothing here imports a mutation runner.
