# Mutation Scope (component)

Whether a declared mutation target could run a single mutant.

**Source:** `src/beadloom/application/mutation_scope.py`

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

## Where it is called

`beadloom config-check` prints the findings among its warnings, and the `config-check` gate step
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
