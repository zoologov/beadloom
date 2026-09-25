# RFC: BDL-073 — The mutation duty becomes executable

> **Status:** Approved
> **Created:** 2026-09-20

---

## Overview

Three fronts, in the order their measurements justify: make the runner spend its time on verdicts
rather than on ordering luck; take a fifth of the slice off the one function that carries it; close
the gaps the surviving mutants name. Each front is independently landable and each is measured
against a number taken before the change.

## Motivation

The PRD's arithmetic: 4479 mutants ≈ 28.3 h of worst-case serial test time against a 22.7 h budget,
so the declared floors have never been reachable. The three fronts move that number by different
mechanisms — ordering changes what a verdict costs (measured 11× spread), the table changes how many
mutants exist (333 → ~145 projected), and the tests change what the score means rather than what it
costs.

## Technical Context

**How mutmut spends the budget.** `mutmut/__main__.py:1441` sorts the mutant QUEUE cheapest-first by
`estimated_worst_case_time` (`:1300-1302`, the sum of the durations of the covering tests). Line
`:1443` then takes that mutant's covering tests as a `set` and hands them to pytest under `-x`. The
queue is ordered; the tests inside it are not.

**Why `load_rules` is the tail.** 827 tests execute it — measured with a plugin that wrapped the
function and recorded `traceback.extract_stack()` per call: 1581 calls, 797 distinct `rules.yml`
paths, two src-side callers (`application/reindex/rules_loader.py:225` `_load_rules_into_db`, 688
calls; `graph/linter.py:199` `lint`, 669 calls), and 630 of 827 tests (76.2%) reaching it through
`init`/`lint`/`ci`/`gate`/MCP without naming rule loading at all. One `beadloom init` parses
`rules.yml` twice: reindex ingests the rules into the `rules` table, and lint re-parses the same YAML
from disk.

**What the survivors say.** 83.3% kill rate over 30 sampled mutants; survivors 2, 15, 33, 41, 233.
Mutant 2 removes `encoding="utf-8"` from the `open` at `loader.py:883`; 15, 41 and 233 change or null
error-message texts (`raise ValueError(None)` still raises, so outcome assertions pass); 33 changes
`data.get("rules", [])` to a `None` default, which no test reaches because no test loads a
`rules.yml` without a `rules:` key.

**What pins today's shape**, so the rewrite knows what it must keep passing: `test_rule_engine.py`
`:289`, `:306`, `:3438`; `test_import_boundary_rule.py` `:433`, `:473`; `test_rule_engine.py`
`:3004`, `:3735`; `test_scenario_coverage_rule.py:697`; `test_tui.py::TestLintDataProvider::test_with_rules_file`.
The key set itself is pinned three ways: `test_rule_engine.py:3941` holds `AUTHORING_KEYS`
(`loader.py:347`) against the `Keyword` column of `docs/domains/graph/features/rule-engine/SPEC.md`,
`:3950` asserts the SPEC's literal `**Twelve** rule types exist`, and `test_onboarding.py:2801` holds
`AUTHORING_KEYS` against `onboarding/scanner/rules_gen.py:82` `_detect_rule_type` — a second,
independent twelve-key map that calls nothing in the loader.

**Seven of the twelve type-guard `raise`s are reached by no test** in the 1404-test population that
names `load_rules`: `loader.py:990`, `:996`, `:1010`, `:1018`, `:1050`, `:1058`, `:1066`.

## Axes

> **Derived by:** `beadloom impact` over `src/beadloom` on three seeds — `graph/rules/loader.py`,
> `application/reindex/rules_loader.py`, `graph/linter.py` (Explore, 2026-09-20).
> **Seed:** `none` on the first two — the derivation reported `no name the target reaches performs a
> declared effect under rule reaches-an-effect-sink`, so their axes are unresolved rather than empty;
> the `linter.py` seed resolved to `each_graph_file` (`reads-a-yaml-directory`) and `flow_signature`
> (`serialises-yaml`). Unresolved counts as rendered: 1 no-seed + 1 node-owns-unread-files + 28
> unresolved-terminator-name (loader), 1 no-seed + 15 (rules_loader), 3 name-defined-more-than-once +
> 18 (linter).
> **Kept nodes: 5 of 15** in the union. Branch rows are grouped per node below rather than listed one
> per function — the grouping is stated so it is not mistaken for a shorter derivation.

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved on two seeds, no commit point to ask through | — | no | Nothing to rule; the change writes no new sink. |
| callers + branches | rule-engine | `graph/rules/loader.py` (`load_rules` 33 branches, `validate_rules` 13, the twelve `_parse_*`), `graph/rules/liveness.py:433` | none | **yes** | The work site. The twelve-branch dispatch becomes a table and the loader gains its memo. |
| callers + branches | reindex | `application/reindex/rules_loader.py:216` `_load_rules_into_db`, `_serialize_rule`, `reindex` | none | **yes** | One half of the double parse: it ingests the rules the second reader then re-parses. |
| callers + branches | graph | `graph/linter.py:151` `lint` (4 branches, 3 exit forms) | none | **yes** | The other half: `lint` re-reads the YAML reindex already stored. The memo lands on its path. |
| callers + branches | tui | `tui/data_providers.py:158` `LintDataProvider.refresh` | 4 — `tui/styles/*.tcss` | **yes** | Not an edit site: the one caller in a long-lived process, and the reason the memo is keyed on `(path, st_mtime_ns, st_size)` rather than on the path. It is where the cache is proven not to blind anyone. The 4 unread files are Textual stylesheets — checked, no template and no YAML. |
| — (no row; not a caller) | onboarding | `onboarding/scanner/rules_gen.py:82` `_detect_rule_type` | — | **yes** | Ruled in although `beadloom impact` cannot show it: a second twelve-key map over the same authoring keys, held against the loader by `test_onboarding.py:2801`. A table in one place and a chain in the other is the duplication this work removes. |
| callers | cli-commands | `services/commands/review_brief.py:285`, `federation.py:278`, `index_ops.py:203` | none | no | Calls the loader; nothing about its call changes. Blast radius. |
| callers | mcp-server | `services/mcp_server.py:700`, `:399` | none | no | Same: a consumer of the parsed rules, unchanged by how they are parsed. |
| callers | debt-report | `application/debt_report/collect.py:226` | none | no | Same. |
| callers | ci-gate | `application/gate.py:266` | none | no | Reaches `lint`, not the loader's shape. |
| callers | site-generation, application, flow-guards, doc-generator, doc-sync, graph-layout, agent-prime | the `linter.py` seed's co-writer and caller rows | none | no | They surfaced under the `linter.py` seed because they write or read the graph directory, not because this change reaches them. |
| branches | rule-engine (`_reasons_for_rule`, `_coverage_leg`, `_suite_leg`, `_reference_leg`, `_declaration_leg`), graph (the 14 formatter/accessor rows), reindex (`_serialize_*`), mcp-server, cli-commands, tui (`refresh` ×7) | as rendered | none / 4 | no | Branch rows say where a mutant could hide, not where this change edits. They are the subject of the measurement this work item is trying to make possible. |

**Not derivable here:** `beadloom impact` sweeps `src/beadloom` for Python, so no row above can name
`tests/`, `.github/workflows/mutation.yml`, `pyproject.toml` or `.beadloom/flow.yml` — the tooling
and test fronts have no row in any table and are carried by the beads that name them.

## Proposed Solution

### Front 1 — the covering tests are ordered by the durations mutmut already recorded

`mutmut.__main__` line 1443 turns a `set` into pytest arguments. The fix is `sorted(tests,
key=lambda t: mutmut.duration_by_test.get(t, 0.0))`. Three ways to apply it, and this RFC picks the
third:

1. Patch the installed package in place — rejected: invisible, lost on the next `uv sync`.
2. Vendor a fork — rejected: a whole runner carried for three lines.
3. **A thin entry point in this repository** that imports mutmut, replaces that one expression, and
   then calls mutmut's own CLI. It is ~20 lines, it states what it patched and against which mutmut
   version, and it refuses to run if the line it patches is not where it expects — a patch that
   silently stops applying is worse than no patch.

`tests/package_under_test.py:9-12` and `tests/mutmut_copy.py:34-45` already pin mutmut 3.7.0
internals, so a version assertion has precedent and a home.

**What this moves in the workflow, and what that costs:** `.github/workflows/mutation.yml:254` and
`:265` stop reading `uv run mutmut run …` and read the entry point instead. `tests/test_mutation_ci_job.py:103`
asserts every `mutmut run` step carries `|| true`; that test moves with its reason restated — the
invariant is "no runner invocation decides the verdict", and it must keep holding for the new
spelling. `:117`, `:122` and `:148` are unaffected: the `--stats`, `--target` and `--min-score`
arguments of the scoring steps do not change.

Also on this front: `--max-children` 4 → 2. Nothing pins it (grep over `tests/` returns zero), and
4-way concurrency produced a measured false kill through the shared live index.

### Front 2 — the twelve-branch dispatch becomes a table

`loader.py` lines ~954-1067 hold twelve `has_X = "x" in rule_data` flags, a `sum([...]) != 1` check
and twelve `elif has_X:` arms, each repeating `rule_data[key]` + `isinstance(..., dict)` + a
`_parse_X(...)` call. Replaced by one mapping from authoring key to `(parser, requires_mapping)` plus
one loop. `has_layers` (no `isinstance` guard, passes the whole `rule_data`) and the `forbid_cycles`
`else` arm stay explicit — they do not fit the table, and pretending they do is how a table hides a
special case.

`AUTHORING_KEYS` becomes the table's keys rather than a second list, which is what lets
`test_rule_engine.py:3941` and `test_onboarding.py:2801` keep their meaning. The SPEC's `**Twelve**
rule types exist` stays true: the count does not change, only the dispatch.

**Projected: 333 mutants → ~145**, removing ~188 mutants ≈ 3.2 h of the 28.3 h worst case. **Cost,
stated honestly:** twelve independently-mutatable `isinstance` guards become one, so mutation can no
longer distinguish them — today nothing asserts on seven of the twelve anyway, and the tests of
front 3 pin the behaviour the table must keep.

### Front 3 — the gaps, and one parse per init

Five tests, each written against the mutant it answers and seen red before green:

| Test | Mutant it kills | What it pins |
|---|---|---|
| the loader reads UTF-8 whatever the locale says | 2 | `encoding="utf-8"` at `loader.py:883` — the class BDL-072 met in CI |
| a rules file with no `rules:` key loads as empty | 33 | the `[]` default at `:900` |
| the top-level type error names what it rejected | 15 | the message text at `:887` |
| the `rules` type error names what it rejected | 41 | the message text at `:902` |
| a per-rule error names the rule and the key | 233 | the twelve `msg = f"Rule '{name}': …"` bodies |

And the memo: `load_rules` caches on `(path, st_mtime_ns, st_size)`. The returned list is shared,
which is safe — every rule type in `graph/rules/types.py` is a frozen dataclass and no caller mutates
the list. Measured effect: 783 of 1581 parses (49.5%) removed in one suite run. The key is not the
path alone, because a path-only memo breaks
`tests/test_bead14_s4_binding.py::TestTheConfiguredLocationCannotBuyASilentGreen::test_moving_the_location_through_the_real_lint_command_is_not_a_clean_run`
and blinds the TUI's lint panel to a `rules.yml` edited while it is open.

**The covering-test count does not move** — 797 distinct paths for 827 tests, so nearly every test
parses at least once regardless. The memo is runtime hygiene and the second half of "one parse per
init"; it is not a mutation-cost lever and is not counted as one.

## Alternatives Considered

**Narrow the mutation test pool to the 197 direct callers.** Measured: identical verdicts on all 20
mutants of the first sample at 16.2 s instead of 49.9 s. Rejected as the primary lever because the
pool is file-level in practice: the 27-file version measured 117.7 s — slower than the node-id list —
with four failures before any mutant is applied, and it leaves
`graph/rules/liveness._GraphFacts.edge_kind_count` (12 mutants) with no covering test at all.

**Split `loader.py`.** Rejected on measurement: `load_rules` is not an outlier in fan-out, only in
mutant count. `node_tags.node_tags` is covered by 695 tests, `NodeTags.__init__` by 697,
`layer_reach.part_of_parents` by 639 — they all ride the same `lint` path. Splitting moves mutants
between names and moves no tests.

**Drop `loader.py` from `only_mutate`.** Rejected: it buys 19.7% of the slice by declaring less, and
the remaining 22.7 h still does not fit 22.7 h of budget.

**Upstream the ordering patch to mutmut.** Worth doing and not a substitute: an upstream release
lands on someone else's schedule, and this repository's floors are red tonight.

## Risks

- **The table hides a special case.** Mitigated by keeping `has_layers` and `forbid_cycles` explicit
  and by front 3's tests, which pin the messages the table now produces from one place.
- **The patched entry point stops patching silently** after a mutmut upgrade. Mitigated by asserting
  the patched expression's shape and failing loudly; the same class this project files as
  "a check that reports green over a dead mechanism".
- **Fewer children lengthens the run** — 2 instead of 4 doubles serial wall time. Front 1's ordering
  is the offset: projected 11.8 s per mutant against mutmut's 60.5 s estimate.
- **The run still dies.** `beadloom-5isv` is unresolved, and a shorter job may simply meet the
  killer later. This work item does not claim to fix that; it claims to make the job small enough
  that the question can be answered by a run that finishes.

## Open Questions

- Q1 | Does the ordered entry point belong in `scripts/`, in `tools/`, or as a console entry point in
  `pyproject.toml`? Decided by the bead that writes it, recorded in its comment.
- Q2 | After fronts 1 and 2, is the slice inside the budget on the runner rather than on paper? Only
  a completed dispatched run answers it, which is the verify bead.

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
