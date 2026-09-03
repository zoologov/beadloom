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

## The score, and the three states in which there is none

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
| `mutation-run-zero-mutants` | the run covered the target and produced no mutants | a ratio over an empty denominator, again |
| `mutation-counters-missing` | the counters carry no `killed` or no `survived` | a missing counter read as zero produces "0%", and a number is what gets pasted into a bead comment |

Three rules decide what the number means, and each of them prevents a specific way of
flattering the suite:

- **A missing counter is not zero.** An absence stays an absence, and no score is stated.
- **Timeouts count as killed; mutants no test covers do not.** A mutant that hung the suite was
  detected. A mutant nothing executes was not, and leaving that class out of the denominator is
  how a slice with no tests at all scores 100%.
- **A run that does not say what it covered is not a run.** `--stats` without `--target` exits 2
  rather than assuming the run covered everything declared.

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
Linux that it does not skip on macOS, and a mutation score is a ratio over whatever ran).

Exit codes: `0` clean or nothing declared, `1` findings or a score under `--min-score`, `2` the
invocation cannot be answered.

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
