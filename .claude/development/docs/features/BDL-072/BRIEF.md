# BRIEF: BDL-072 — The nightly mutation run judges nothing: a guard reads mutmut's own mutated copy

> **Status:** Approved
> **Type:** bug
> **Created:** 2026-09-18
> **Tracker:** `beadloom-ey4m` (P1, open since 2026-09-12) · **Log entry:** BDL-UX #289

---

## Problem

The `Mutation` workflow has reached a verdict on **0 of 7187 mutants for nine consecutive nights**
(2026-09-10 … 2026-09-18). The last green nightly is `e17c2258`, 2026-09-09. Five of the nine ran on
the same commit, `2f744c4a`, so nothing about recent work causes it.

**The mechanism, already established on the bead and re-confirmed today.** mutmut 3.7 builds a
`mutants/` tree, puts `mutants/src` on `sys.path` and runs the pool from inside it. Before scoring it
runs the selected tests once, and one of them fails:
`tests/test_two_readers_of_one_markdown_table.py::TestThePackageHasTwoReadersOfOneRow::test_every_pipe_split_in_the_package_is_declared`.
The guard derives its scan root from its own file (`_SRC`, line 49) and walks it (line 103), so inside
the run it reads mutmut's generated bodies — `x_cells_of__mutmut_2`, `x__bound__mutmut_3`,
`x_cells_of__mutmut_orig` — as undeclared pipe-splitting sites. mutmut stops at the first failure:
`1 failed, 4616 passed … failed to collect stats. runner returned 1`.

**The instrument did not lie.** Both scoring steps print `Counters: killed 0, mutants 7187`,
`Score: none`, the finding `mutation-run-zero-mutants` naming the empty denominator, and exit 1. What
failed is the run, not the verdict about it. What nobody had is a reason to look: a nightly that goes
red is visible only to whoever opens Actions, and for nine nights no one did.

**What the silence cost, measured:** the declared scope grew from 6544 mutants to 7187 while it was
dead, so 643 mutants have entered a scope that has never been judged.

## Axes

> **Derived by:** `beadloom impact` over `src/beadloom` on four seeds — `doc_sync/tables.py`,
> `application/mutation_scope/score.py`, `services/commands/mutation.py`,
> `application/active_table/table.py` (Explore, 2026-09-18).
> **Seed:** none — on all four seeds the derivation reported `no name the target reaches performs
> a declared effect under rule reaches-an-effect-sink`, so every axis it rendered is unresolved
> rather than empty, and the `co-writers` row below carries that verdict verbatim. Unresolved
> terminator names: 5 on the `mutation_scope/score.py` seed, 7 on `commands/mutation.py`, 1 on
> `active_table/table.py`, 0 on `doc_sync/tables.py`; `name-defined-more-than-once`: 2 on
> `commands/mutation.py`.
> **The derivation's own limit, and it decides the route:** `beadloom impact` reads `src/`, and every
> site of this defect is in `tests/` and `.github/`. No row below can name a file this change edits.
> **Kept nodes: 0.** The count is stated rather than rounded up to one: the simplified flow is taken
> because the change reaches no graph node at all, not because it reaches exactly one.

| Axis | Node | Sites | In scope | Why |
|---|---|---|---|---|
| co-writers | — (unresolved, no declared effect sink) | — | no | Unresolved on all four seeds. Nothing to rule, and the change writes no product code. |
| callers | markdown-tables | `doc_sync/tables.py` — the component the failing guard is about | no | The guard is wrong about this node; the node is not. Its code, its callers and its contract are untouched. |
| callers | axes-section | `doc_sync/axes_section.py:193` | no | Reads table cells. Not edited, not re-specified. |
| callers | doc-quality | `doc_sync/doc_quality.py:369` | no | Same: a reader of the row grammar, unaffected by a test's scan root. |
| callers | document-pairs | `doc_sync/document_pairs.py:329` | no | Same. |
| callers | work-item-routing | `application/work_item_routing.py:192` | no | Same. |
| callers | active-table | `active_table/table.py`, `reconcile.py:156` | no | The second reader the failing guard compares. The comparison stays as it is; only where the guard looks changes. |
| callers | mutation-scope | `application/mutation_scope/score.py` — owns `mutation-run-zero-mutants` (line 48) | no | It reported the dead run correctly and exits 1 already. Changing it would be changing the witness, not the defect. Re-examined if the fix cannot be verified without it. |
| callers | cli-commands | `services/commands/mutation.py:97`, `waves.py:363`, `docsync.py:1323` | no | The command surface prints the verdict; no flag or output shape changes. |
| callers | ignore-block | `onboarding/ignore_block.py:264` | no | Surfaced from the `commands/mutation.py` seed as a neighbour in one module; unrelated to the defect. |
| branches | markdown-tables, mutation-scope, active-table, cli-commands, doc-quality, document-pairs, axes-section, work-item-routing | every branch row of the four derivations | no | Branch rows say where a mutant could hide, not where this fix edits. Judging them is what the repaired run will do — they are the subject of the measurement, not of the change. |

**Owns unread:** `none` on every row of all four derivations, so no row carries a question a template
or a non-Python file could hide.

## Solution

**One place answers "where is the package under test, and which of its names are real code".** The
four selected tests that walk a `__file__`-derived root stop deriving it from their own location and
stop reading mutmut's generated names.

Measured population (AST over the 155 entries of `[tool.mutmut] pytest_add_cli_args_test_selection`,
`pyproject.toml:327-483`), correcting a looser grep that had said 19 and 12:

| File | Root | Walk | Asserts over it | Can trip today |
|---|---|---|---|---|
| `tests/test_two_readers_of_one_markdown_table.py` | `_SRC`:49 | `rglob("*.py")`:103 | `:142` | **yes — this is the failure** |
| `tests/test_guards_invocation.py` | `_SRC`:76 | `rglob`:600, 808, 844 | `:844-922` | not today: it keys on `record_firing(` and process terminators, and neither occurs in any mutated file |
| `tests/test_the_reference_docs_state_the_population_shapes.py` | `TEMPLATES_ROOT`:68 | `rglob("*.md.txt")`:175 | yes | no: mutmut copies `.md.txt`, it does not mutate it |
| `tests/test_s2_move_regression.py` | `_TPL`:57 | `glob("**/*.py.txt")`:225 | `:225` | no: same reason |

Two more build a `src/` path and read one named file each, so no mutant enters their population
(`test_the_exit_condition_vocabulary_lives_below_both_declarers.py:33`,
`test_the_layer_rule_states_the_population_it_judged.py:631`). Four others walk a `__file__`-derived
root that stays outside `src/` but inside the copied room — `also_copy`, `pyproject.toml:484-497` —
and read no mutated source (`test_cli_json_streams.py`, `test_bead14_s4_binding.py`,
`test_doc_quality.py`, `test_reference_leg_syntax.py`).

**Resolving the root from the imported package is necessary and NOT sufficient**, which is the fact
that shapes the fix. Measured in mutmut 3.7.0 itself (`__main__.py:262-276`, `:479`): the pool runs
under `change_cwd("mutants")` with `mutants/src` on `sys.path`, so `beadloom.__file__` resolves to
`mutants/src/beadloom` — the package genuinely under test, **with the mutant bodies in it**. So the
helper must do both: resolve the package under test through the imported module, and decline
mutmut's generated names (`x_*__mutmut_N`, `*__mutmut_orig`).

Copy-safe root idioms already exist and none of them filters those names:
`tests/acceptance/steps/test_audit_self_facts_steps.py:32`, `test_ignore_block_drift_steps.py:39`,
`test_package_description_steps.py:39`, `tests/test_rules_docstring_references.py:50`, and in the
product `onboarding/composer.py:48`.

**A route that is closed, recorded so it is not re-proposed:** dropping the failing test from the pool
fails `tests/test_mutation_runner_scope.py:174` — no test importing a declared target may sit outside
the pool, and this one imports `beadloom.doc_sync.tables`.

**And the second half of the defect: nine nights of silence.** A red nightly nobody opens is the same
class as a check that never reports. The fix makes a dead or failing nightly announce itself where it
will be seen, rather than only in the Actions tab.

## Beads

| Bead | Role | What |
|---|---|---|
| `beadloom-ey4m` (exists, P1) | dev | The helper in `tests/`, the four walking tests moved onto it, and a guard test that a new test cannot re-introduce the shape. |
| new | dev | The nightly announces a dead or red run where it is seen. `.github/workflows/mutation.yml`, checked against what `tests/test_mutation_ci_job.py` pins (`:89`, `:103`, `:117`, `:122`, `:148`). |
| new | test | The suite proves the helper: a test that fails if a `__mutmut_` name reaches a guard's population, and the pool tests still hold. |
| new | review | Read-only verdict before the run is trusted, including that nothing was merely skipped. |
| new | verify | Run `Mutation` by `workflow_dispatch` on the branch and read the real verdict. ~3 h; this is the only proof the bead accepts. |

## Acceptance Criteria

- A `mutmut run` reaches a verdict on a **non-zero** population, and both scoring steps print a score
  instead of `Score: none`. **Not met** if the guard is merely skipped under mutation, and not met by
  the one test passing on the tree.
- The first scored nightly's numbers are recorded on the bead against the floors the workflow holds
  (0.94 for the rules slice, 0.88 for the declared scope), and a floor breach is reported as a finding
  rather than silently lowered.
- The four walking tests resolve the package under test through the imported package and decline
  mutmut's generated names; a new test that derives a scan root from `__file__` is caught by a guard.
- A dead or red nightly is visible without opening the Actions tab, and that mechanism is itself
  measured once rather than assumed.
- `beadloom ci` rc 0, the suite green on the tree, and `tests/test_mutation_runner_scope.py` and
  `tests/test_mutation_ci_job.py` still pass.
