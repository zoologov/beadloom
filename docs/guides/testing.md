# Testing: Tests That Belong to the Graph

<!-- beadloom:watches=cli,graph,flow.yml -->

How a test is written, where it lives, how it binds to a graph node, what `lint` judges about
the suite, and how mutation measures the strength of the tests a change runs.

This guide is for two readers. An adopter wants Beadloom to hold tests to the graph the way it
holds code and documents. A contributor to this repository needs to know where a new test goes
and which check will fail if it goes elsewhere. The first half applies to every project. The
sections that name `tests/self_check/`, the snapshot or `.github/workflows/mutation.yml` describe
this repository only.

The reference material lives elsewhere and is not repeated here. The binding and every
configuration key are in the [Test Mapping SPEC](../domains/context-oracle/features/test-mapping/SPEC.md),
the rule types in the [rule-engine SPEC](../domains/graph/features/rule-engine/SPEC.md), and
`beadloom mutation` with every flag in the [CLI reference](../services/cli.md#beadloom-mutation).

Every number below was measured on this repository on 2026-09-29, on `features/BDL-074` at
`067df32a` (Darwin arm64, CPython 3.13.7), unless it is marked as an example.

---

## What a test is here

The standards are written once, in the `test` role that `beadloom setup-agentic-flow` composes
into `.claude/agents/test.md` (and `.cursor/agents/test.md`), from the shipped core
`src/beadloom/onboarding/templates/roles/core/test.md.txt` and the stack overlay. Read them
there. In one line each:

1. **One behaviour per test.** When only the data varies, write one parameterised test.
2. **Arrange, act, assert.** An assertion before the action is a second test.
3. **No shared mutable state.** A test builds what it reads, and never reads or writes the
   project's live index, tracker or working tree.
4. **Named by the behaviour**, never by the bead, slice or epic that wrote it.
5. **Placed by the mirror**, kind first and then the path of the code it tests.
6. **Shared helpers in one support package.** A test module is never imported by another.
7. **The repository root is found one way**, by one helper that walks up to the manifest.
8. **Explicit roots, never the working directory.** Every call into the code under test
   receives the directory it works on.

The role states the reason beside each rule. A standard that code can check is checked in the
suite, so it fails on the next file written the wrong way. In this repository these checks run
with every test:

- `tests/self_check/architecture/test_the_suite_shares_helpers_through_support.py` fails on an
  import of a test module and on a file that counts its own parent directories;
- `tests/self_check/architecture/test_a_test_file_is_named_by_its_behaviour.py` fails on a
  work-item id in a test file's name;
- `tests/conftest.py` starts every test in its own empty directory, so a test that leaves its
  root to the `Path.cwd()` default fails instead of passing by accident. Its contact guard fails
  a test that opens this checkout's `.beadloom/beadloom.db` or runs `bd` or `git` against it.

## The layout: kind first, then the mirrored path

```
tests/
  unit/<path under src/beadloom/>/test_<module>.py
  integration/<path under src/beadloom/>/test_<module>.py
  acceptance/<domain>/<node>/*.feature        # spelled as docs/domains/<domain>/features/<node>/
  acceptance/steps/<domain>/<node>/, steps/common/
  self_check/{architecture,config,docs,process}/
  support/                                    # shared helpers, never collected as tests
```

**The kind comes first** because it is the common Python layout and because CI can then select
a kind by one path: `uv run pytest tests/unit` runs the unit layer alone. **The code's path comes
second** because the binding follows from it: a file under `tests/unit/graph/rules/` binds to the
node whose `source:` covers `src/beadloom/graph/rules/`. The layout by node first
(`tests/<node>/unit/`) was rejected when the layout was decided: a node id is not a path, so the
mirror would break, and a kind could no longer be selected by one path.

**An acceptance scenario lives in the folder of its node.** `tests/acceptance/graph/rule-engine/`
holds the rule engine's `.feature` files, mirroring `docs/domains/graph/features/rule-engine/`,
and the rule `scenarios-live-in-their-node-folder` checks that each scenario's `@node:` tag names
that folder's node.

The shape of this repository's suite, as `beadloom reindex` prints it:

```
Tests:   623 files (278 bound to a node, 167 unplaced, 75 acceptance step, 103 self-check)
```

The 167 unplaced files are the ones still at the top of `tests/`. Each tests several nodes with
none primary, so no single mirrored path can hold it until it is split by node.

## How a test binds: three ways, and nothing guessed

A test file binds to a node in one of three ways, and a declaration wins over the other two:

1. **Through `tests:` in the node's graph YAML.** A node lists path prefixes, resolved like
   `source:` (a trailing `/` is a directory), to claim tests its path does not mirror. A prefix
   that covers no test file is a reindex warning.

   ```yaml
   tests:
   - tests/integration/contracts/
   ```

2. **By the mirror of its path.** A file under `<root>/unit/` or `<root>/integration/` names the
   code its path mirrors, and the node that owns that code binds it. A build tool's test tree
   mirrors the code tree beside it: `src/test/java/shop/BillingTest.java` names
   `src/main/java/shop/Billing.java` (an example path).
3. **Beside the code.** A test inside a node's source, outside every root, binds to that node:
   `billing_test.go` beside `billing.go` (an example). This repository switches it off with
   `beside_code: false`, because five of its modules are named like tests.

**Nothing else binds a test, and the reason is a measurement.** The mapper this replaced guessed
a node from import names, file names and folders. Measured on 2026-09-27, before the binding
landed, it reported 0 tests for `rule-engine`, though its `load_rules` runs under 855 of them,
and 442 of the 884 links it stored pointed into `mutants/`, the mutation runner's copy of the
tree. An import
names fixtures, helpers and collaborators as well as the subject. A folder named after a node is
a name. So a file under a root that none of the three ways reaches is **unplaced**: it is read,
counted, and bound to nothing, and every surface says how many there are.

`beadloom ctx <ref-id>` prints the tests bound to the node and states the rest:

```
$ beadloom ctx rule-engine
…
Tests: pytest, 755 tests in 37 files (high coverage)
  167 of 623 test file(s) are unplaced (not under tests/integration/ or tests/unit/) and bind to no node, so the count above can be short
  A test file is read when its path matches a pattern of pytest (test_*.py, *_test.py) under the root tests
```

The last line always states which files are tests, so a count of test files is a count of the
files those patterns matched. The debt report withholds its untested count while any file is
unplaced, because an unplaced file may test a node that looks untested.

## Configuration: `tests:` in `.beadloom/config.yml`

Every key is optional, and a project that declares nothing is read by the defaults.

| Key | Default | A declared value |
|-----|---------|------------------|
| `tests.roots` | `[tests, test, spec, __tests__]`, each read only where a folder of exactly that spelling exists | replaces the list |
| `tests.kinds` | `unit`, `integration`, `acceptance`, `self_check`, each in a folder of its own name | replaces the folder of that one kind |
| `tests.patterns` | the five framework groups below | replaces all five groups |
| `tests.mirrors` | `src/test/java: src/main/java`, `src/test/kotlin: src/main/kotlin`, `Tests: Sources` | replaces all three trees |
| `tests.beside_code` | `true` | `true` or `false` |

The default patterns, per language:

| Language | Framework group | Default patterns |
|----------|-----------------|------------------|
| Python | `pytest` | `test_*.py`, `*_test.py` |
| Go | `go_test` | `*_test.go` |
| JavaScript, TypeScript | `jest` | `*.test.*`, `*.spec.*`, `__tests__/**/*.[jt]s`, `__tests__/**/*.[jt]sx` |
| Java, Kotlin | `junit` | `*Test.java`, `*Tests.java`, `*TestCase.java`, `*IT.java`, `*ITCase.java`, `*Test.kt`, `*Tests.kt`, `src/test/**/*.java`, `src/test/**/*.kt` |
| Swift | `xctest` | `*Tests.swift`, `*Tests/**/*.swift` |

A pattern without a `/` matches the file name. A pattern with a `/` matches the end of the path,
folder by folder, and `**` stands for any number of folders. Declaring `patterns` states which
frameworks the project has, so the other groups are dropped. A key that cannot be used is a
reindex warning, and its default stands. This repository declares:

```yaml
tests:
  roots: [tests]
  beside_code: false
  kinds:
    unit: unit
    integration: integration
    acceptance: acceptance
    self_check: self_check
  patterns:
    pytest: ["test_*.py", "*_test.py"]
```

What is deliberately not bound, and the declaration that binds it, is listed in
[Getting Started](../getting-started.md#tests--where-your-tests-are): an Xcode test target, a
folder named after a node, and a marker file without a test file.

## The suite rules and their population lines

Four rules in `.beadloom/_graph/rules.yml` judge this repository's suite, over three rule types.
Each prints a **population line**, a finding of type `suite_population` that states what the
rule judged and what it did not. The line is what lets a count of findings be read as a fraction
of something: without it, zero findings over zero judged files reads as a clean suite.

| Rule | Type | Severity here | Population line, measured |
|------|------|---------------|---------------------------|
| `test-files-bind-to-a-node` | `test_binding`, `files` leg | `error` | `judged 445 of 623 indexed test file(s) matching tests/**: 278 bound to a node, 167 bound to none — 167 excused by 4 exemption(s), 0 reported` |
| `features-have-bound-tests` | `test_binding`, `for` leg | `warn` | `judged 51 node(s) (kind=feature): 34 with a bound test file, 17 without — 0 excused by an exemption, 17 reported` |
| `domain-unit-tests-import-no-infrastructure` | `test_import_boundary` | `error` | `judged 47 of 623 test file(s) with recorded imports (243 import(s), 8 crossing(s) excused by an exemption)` |
| `scenarios-live-in-their-node-folder` | `scenario_binding` | `error` | `judged 528 scenario(s) in 82 file(s) under tests/acceptance: 367 agree with their folder, 161 do not — 161 in 29 file(s) excused by an exemption, 0 reported` |

The lines are abridged at `;`. Read them with `beadloom lint --format json`, where each is a
`suite_population` entry with its full message. Three things in them are easy to misread:

- **The files the first rule does not judge are named by kind.** Its line goes on: 75 acceptance
  step files are not judged by path, because their scenarios bind through `@node:` tags, and 103
  self-check files bind to no node by design. Each kind states the folder it was recognised by,
  and that the folder is trusted rather than verified: a unit test dropped into
  `tests/self_check/` counts as a self-check.
- **"Without a bound test" is not "untested".** The node leg is `warn` here. Every finding of
  that leg says how many test files bind to no node, and any one of those 167 files might be the
  one that exercises the node in question.
- **The scenario rule checks the folder, not the execution.** Whether a scenario's steps execute
  the node its tag names needs a runtime trace, and the line says it was not judged.

The rule-engine SPEC has the authoring keys, including the `files` and `for` legs and the
`from`, `to` and `of` of the import rule.

## Exemptions: a reason and an exit

A rule over the suite can excuse a file, a node or an import crossing, and never silently. Every
entry carries two mandatory keys: `reason`, why the subject cannot meet the rule yet, and
`until`, the deadline (`YYYY-MM-DD`) or the event that retires the entry.

```yaml
    test_binding:
      files: "tests/**"
      exempt:
        - files: ["tests/test_mixed.py"]            # an example path
          reason: >-
            Measured as exercising several nodes, so no single mirrored path can hold it.
          until: >-
            the file is split by node and each part placed by the mirror
```

The exit is enforced from both sides:

- **An entry that excuses nothing is reported by name**, with "delete it". Each entry is judged
  on its own, so a file listed as not yet split is reported the run after it moves to its node's
  folder. The lists only shrink.
- **An entry past the date its `until` leads with is reported once, with its count.** Expiry is a
  finding and not a time bomb: nothing turns into an `error` because a day passed.

The self-checks in this repository that keep exemption lists of their own follow the same
contract, and an entry that no longer matches fails the test.

## Self-checks, against a snapshot

A **self-check** asserts on this repository's own files: its graph, its rules, its CI workflows,
its documents, its roles. It is not a test of a node's behaviour, so it binds to no node, and it
lives in one of four folders:

| Folder | What it checks | Files |
|--------|----------------|-------|
| `tests/self_check/architecture/` | the graph, the lint configuration and the code structure | 25 |
| `tests/self_check/config/` | the manifest, the CI workflows and the declared configuration | 32 |
| `tests/self_check/docs/` | the documents and the published site | 23 |
| `tests/self_check/process/` | the roles, commands, hooks, the tracker and the suite's discipline | 23 |

Every test under those folders carries the `self_check` marker, and so does every test that reads
the snapshot. The marker selects 711 of the 11 616 items that
`uv run pytest --collect-only -q -m self_check` collects, so `-m "not self_check"` runs the
product tests alone.

**A self-check never reads the live index.** One that needs a built index takes the session
fixture `self_check_snapshot`: the working tree, copied once per session with its git history
into a temporary directory and reindexed there (`tests/support/self_check_snapshot.py`). The
live `.beadloom/beadloom.db` is shared with every other writer on the machine, a hook, a
concurrent `lint`, another test, and reading it was the cause of the shared-index failures that
reddened required checks on five pull requests. Each run prints the snapshot's population and
cost in its summary:

```
$ uv run pytest tests/self_check/docs -q
…
self-check snapshot: 1954 file(s) of the working tree copied with its git history in 0.7 s and indexed in 5.0 s, at /private/var/folders/…/self-check-snapshot0/beadloom; the copy is the one reader of the live tree, and the contact guard is suspended while it runs
70 passed in 15.70s
```

The copy is taken at test time, so a concurrent edit to the working tree is what the self-checks
judge. A check that repeats a required Gate leg on the real repository does not belong here: the
Gate leg is the check, and a product test of the checker on a synthetic fixture stays.

## Mutation: per change and weekly

Coverage says a line ran. Mutation says whether an assertion would have noticed the line being
wrong. Beadloom ships no mutation runner: the tool is the project's choice. `beadloom mutation`
states the population a run covers and scores the counters the runner wrote.

**Per change.** `--changed-since REF` states what a change asks a runner to mutate: the functions
it touched inside `mutation.targets` (declared in `.beadloom/flow.yml`), the node owning each, and
the test files bound to that node. Measured on this branch against `main`:

```
$ beadloom mutation --changed-since main
Change since main: 792 file(s) changed, 12 of them in the declared scope
Population: 57 function(s) in 11 file(s) of the declared scope, over 1 node(s): rule-engine
  rule-engine: _remediation_for, evaluate_all, … ; 37 test file(s) bound, 10 acceptance step file(s) by tag
620 changed line(s) in the declared scope lie outside any function, where no mutant exists
Binding: 167 of 623 test file(s) are unplaced … — so the tests bound to a node can be short of the tests that exercise it
…
No run was reported: the population above is what a runner is given.
```

In this repository the `mutation-per-change` job of `.github/workflows/mutation.yml` runs this on
every pull request, hands mutmut the exact mutant names of those functions with the bound tests
as the selection, and scores the run with `--survivors`, which lists each survivor under its node.
The selection also takes the acceptance step files by tag, falls back to the unplaced files of
the mutation pool in `pyproject.toml` because they may exercise the node, and excludes every
self-check. Its budget is 10 minutes on `ubuntu-latest`.
<!-- TODO: verify the per-change job's time on the runner once `beadloom-paze` has read one run -->

**Weekly.** The `mutation-sample` job runs on Monday at 03:17 UTC and by hand. It draws 150
mutants at random from the whole declared scope, seeded by the ISO week so a week's sample can be
reproduced, and scores them with `--sample-of`, which prints the interval the sample supports.

**Reading the score and the interval.** The score is killed plus timed-out mutants over every
mutant a verdict was reached about, survivors and mutants no test covered included. A counter
the runner did not write is reported, never read as zero. On a sample, the 95% Wilson interval
is the claim, and the floor is missed only when the whole interval lies under it. With example
counters of 130 killed and 20 survived, read as a sample drawn from a population of 6 992:

```
$ beadloom mutation --stats counters.json --target src/beadloom/graph/rules/ \
    --only src/beadloom/graph/rules/ --sample-of 6992 --tool 'mutmut 3.7' --min-score 0.88
…
Score: 86.7% of 150 scored mutants
Sample: a random sample of 150 of 6992 mutants; 95% interval 80.3% to 91.2% (Wilson)
Floor: 0.88 — the sample's interval reaches it.
```

The point estimate is under the floor and the interval is not, so the command exits 0. A floor
held against the point estimate would fail about a third of the weekly samples drawn from a
scope that truly scores 0.89, which makes it a coin rather than a check. The per-change run has
no interval: it runs every mutant of the touched functions, so its score is the population's,
and its survivors are the finding.

A survivor is fixed with a stronger assertion, never by deleting the mutant.
