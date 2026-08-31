# BRIEF: BDL-067 — A virgin `beadloom init` leaves the Gate red

> **Type:** bug
> **Status:** Approved
> **Created:** 2026-08-31

---

## Problem

`beadloom init --yes --mode bootstrap` exits 0 and then fails its own `beadloom ci`
on `domain-needs-parent` — a rule the same command wrote one step earlier.

Measured on the built 3.0.0 wheel against a scratch adopter project (a TypeScript
service with one file under `src/`), tracked as `beadloom-e8s4` / BDL-UX #192:

```
beadloom init --yes --mode bootstrap   ->  rc 0   Graph: 2 nodes, 0 edges
beadloom lint                          ->  rc 0
beadloom lint --strict                 ->  rc 1   domain-needs-parent:require:error:::src:
beadloom ci                            ->  rc 1
```

### The chain, traced

1. `detect_preset` returns MONOLITH for a project without `services/ cmd/ packages/ apps/`
   (`onboarding/presets.py:134-173`); `MONOLITH.default_kind = "domain"` (`presets.py:81`).
2. `_cluster_with_children` (`onboarding/scanner/project_scan.py:135-194`) yields only
   *subdirectories* of a source dir that contain code files. A flat `src/index.ts` yields `{}`.
3. That takes the fallback branch of `bootstrap_project`
   (`onboarding/scanner/bootstrap.py:133-145`): one node per source dir, `kind=domain`,
   **and no edge**. The root-attachment loop at `bootstrap.py:226-229` iterates `clusters`,
   which is empty here, so those nodes are never attached to the root either.
4. `services.yml` is written as `{"nodes": nodes}` and gains an `edges:` key only
   `if edges` (`bootstrap.py:232-235`) — so the file has no `edges:` key at all.
5. `generate_rules` (`onboarding/scanner/rules_gen.py:18-78`) reads only
   `kinds = {n["kind"] for n in nodes}` (`:29`) — `edges` is an accepted parameter it
   **never reads** — and emits `domain-needs-parent` because a domain exists (`:32-46`),
   with no `severity:` key, so the loader defaults it to `error`
   (`graph/rules/loader.py:884-895`).
6. `init --yes` prints `Graph: N nodes, M edges` and returns bare
   (`services/commands/setup.py:781-804`). It never lints. `non_interactive_init`
   (`onboarding/scanner/init_flow.py:40-117`) reindexes but never lints either.

### Why the existing guard does not cover it

`rules_gen.py` already carries this exact worry twice, and both times stopped one case short:

- `feature-needs-parent` (`:48-66`) was relaxed under BDL-UX #71 with an empty `has_edge_to`
  matcher, commented *"requiring a `domain` parent makes a clean bootstrap fail its own
  `lint --strict` gate out of the box"*.
- `service-needs-parent` was removed outright (`:68-71`), because *"the root service node has
  no parent by definition"*.

An empty `has_edge_to` relaxes **which** parent is acceptable, never **whether** there is one.
Confirmed at evaluation time: `_parse_node_matcher` accepts `{}` with `allow_empty=True`
(`graph/rules/loader.py:53-89, 133-173`) producing a matcher whose `matches` returns `True`
unconditionally (`graph/rules/types.py:130-146`); `evaluate_require_rules`
(`graph/rules/evaluators.py:214-303`) then reduces the rule to *"this node must have at least
one outgoing `part_of` edge to any existing node"*. A node with zero outgoing edges always
violates, and `liveness.py:253-261` will not mark the rule inert, because an empty matcher
selects every node. Only an edge can fix it.

### Two defects in the test suite that let this ship

Found while tracing, and part of this bug rather than separate debt:

- `tests/test_virgin_scaffold_is_green.py:22,28-38` runs the real end-to-end
  `init --yes --mode bootstrap` on exactly the fixture that reproduces this
  (`typescript_project`, `tests/adopter_project.py:60-78`, flat `src/index.ts`) and asserts
  only `exit_code == 0` plus `config-check`. **It never lints.** The suite runs the broken
  graph on every CI run and cannot see it.
- `tests/test_integration_onboarding.py:129-136` (`test_lint_zero_violations_after_init`) is a
  **false green**: it invokes `lint` *without* `--strict` and asserts `exit_code == 0`, which
  `services/commands/federation.py:331-343` returns even when error-severity violations exist.
  The test's name states a claim its assertion cannot make.
- `tests/test_bootstrap_clean_lint.py:52-65` does assert `not result.has_errors` and
  `violations == []`, but its fixture (`:28-46`) is nested, so it never reaches the fallback
  branch. It is the right assertion pointed at the wrong shape.

## Solution

**Decision taken by the owner on 2026-08-31: option (a) — the bootstrap emits the edges.**
Option (b) (`generate_rules` omits the rule when no `part_of` edge exists) was rejected: it
ships every adopter one structural rule weaker than this project runs, with nothing that later
reminds a human to restore it — a gate quietly downgraded is the class of thing this project's
own thesis rejects.

The inference objection against (a) does not apply on the path that is actually broken: the
root node is created by the same command in the same act (`bootstrap.py:171-179`), there is
exactly one of it, and it is parentless by construction — which is precisely why
`service-needs-parent` was removed. A `part_of` edge from a classified top-level source dir to
the single root of the project it was classified in is a tautology of the preset, not a claim
about the code.

**Fixed as an invariant, not as a branch patch.** The defect is that one branch of
`bootstrap_project` forgets the edge; patching that branch alone leaves the next branch free to
forget it again. So the fix is a stated post-condition of `bootstrap_project`:

> Every node the bootstrap writes with `kind: domain` carries at least one outgoing `part_of`
> edge, to its classified parent where one exists and to the root service node otherwise.

The edge must use the root node's **actual** `ref_id` value as written, not a recomputed one:
cluster refs pass through `_sanitize_ref_id` (`bootstrap.py:227-228`,
`onboarding/scanner/constants.py:149-154`) while the root ref does not (`bootstrap.py:171-179`),
so recomputing the name is how the dst silently stops resolving for a project whose name
contains parentheses.

**And `init` stops reporting rc 0 over a graph that fails the rules it just wrote.** This is the
half that prevents the class rather than the instance: after writing the graph, `init` evaluates
it with the same semantics the Gate uses (`application/gate.py:217-233` — `passed = not
result.has_errors`) and either exits non-zero or names the incompleteness in the words the Gate
will use. The natural site is `services/commands/setup.py:793-798`, right after the
`Graph: N nodes, M edges` line, where the counts are already in hand; there is precedent for
naming a known-weak green at `services/commands/federation.py:333-343`.

## Beads

| ID | Name | Priority | Status |
|----|------|----------|--------|
| `beadloom-e8s4` | parent (bug) — BDL-UX #192 | P0 | Open |
| `.1` | dev — bootstrap post-condition: no domain is written without a `part_of` edge | P0 | Pending |
| `.2` | dev — `init` must not report success over a graph that fails its own rules | P0 | Pending |
| `.3` | test — the virgin-scaffold assertion that can actually fail; close the two false greens | P0 | Pending |
| `.4` | review — read-only verification | P0 | Pending |
| `.5` | tech-writer — doc refresh for the changed surfaces | P0 | Pending |

Dependencies: `.3` waits on `.1` and `.2`; `.4` waits on `.3`; `.5` waits on `.4`.
Wave shape between `.1` and `.2` is decided by `beadloom waves`, not asserted here.

## Acceptance Criteria

Behaviour-bearing; the scenarios live in
`tests/acceptance/features/bootstrap_self_consistency.feature` and that file is the source of
truth for their text.

- [ ] Scenario: `A flat single-source-dir project bootstraps into a graph that passes its own rules`
- [ ] Scenario: `Every domain the bootstrap writes carries a part_of edge`
- [ ] Scenario: `init does not report success over a graph that fails the rules it just wrote`

Measured, not asserted — the reproduction from BDL-UX #192 must be re-run end to end on a
project that is not us (`typescript_project`), and `beadloom ci` must return 0 where it
returns 1 today.
