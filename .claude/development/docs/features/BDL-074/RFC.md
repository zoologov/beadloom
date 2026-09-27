# RFC: BDL-074 — Tests that belong to the graph

> **Status:** Approved
> **Created:** 2026-09-28

---

## Overview

Make tests first-class citizens of the graph in four moves, each measured against the suite map
(`map/test-map.json`, 2026-09-27): isolate the suite from the repository's live state; lay tests out
by kind and then by the code they test, so the node a test belongs to follows from where it lives;
replace the heuristic test mapper with that binding and put lint rules over it; and run mutation per
pull request through the binding. The rule-engine domain is the pilot restructured in full.

## Motivation

The PRD's numbers: 55.5% integration tests, 133 mixed files, self-checks at 28% of suite time, 19 files
touching the live index and four writing it, and a `ctx` that reports 0 tests for the rule engine
while 442 of its 884 stored links point into `mutants/`. Each move below removes one of those.

## Technical Context

All measured on 2026-09-28 by the research agent unless marked inferred.

- **Ownership today.** A node declares code with one `source:` prefix (`graph/loader.py:62`); a
  trailing `/` makes it a directory. Resolution is two pure string functions — `covering_prefix` and
  `source_covers` (`infrastructure/repository.py:335-360`) — and SQL helpers that pick the most
  specific covering node (`:363-425`). The pure functions work on any path list; the SQL helpers are
  tied to `nodes.source` and `code_symbols`, which holds 0 files under `tests/`.
- **Unknown node keys are accepted and stored** in `nodes.extra` (`loader.py:474-478`; doctor says so
  at `doctor.py:80-83`). A `tests:` key would be accepted — and then **overwritten** on every full
  reindex, because the heuristic mapper replaces `extra["tests"]` wholesale
  (`application/reindex/enrichment.py:69-79`, called from `full.py:183`).
- **Tests are not indexed.** `scan_paths: [src]` (`.beadloom/config.yml:3-4`); 0 of 2 393
  `code_imports` rows are under `tests/`. `forbid_import` matches only indexed files
  (`evaluators.py:365-366,436-439`), so a rule over `tests/**` would report itself dead.
- **The heuristic's consumers** read `extra["tests"] = {framework, test_files, test_count,
  coverage_estimate}`: `context_oracle/builder.py:466,504`, `services/commands/query.py:48-54` (the
  `Tests:` line), `doc_sync/audit.py:941-975`, `onboarding/doc_generator.py:934-935,1036-1045`;
  `debt_report/collect.py:189-222` calls `map_tests` live. The mapper walks without skipping
  `mutants/` (`test_mapper.py:51-80,97-106`): 532 of 1 064 entries are mutmut copies. Node `beadloom`
  gets 882 files because every test imports the top-level package.
- **Adding a rule type** is a parser in `_MAPPING_PARSERS` (`graph/rules/loader.py:874-886`), a frozen
  dataclass in the `Rule` union (`types.py:486-499`), an evaluator, an arm in `evaluate_all`
  (`graph/rules/__init__.py:214-273`) and a liveness arm (`liveness.py:444-469`). Only the layer rule
  states its population structurally (`layer_reach.py:186-258`); other rules do it in message text.
- **mutmut 3.7.0.** `mutmut run [NAMES...]` takes exact names or fnmatch globs (`__main__.py:1241-1247,
  1360-1364`). Names are `<module>.x_<func>__mutmut_<N>` and `<module>.xǁ<Class>ǁ<method>__mutmut_<N>`
  (`utils/format_utils.py:61-67`, `mutation/trampoline_templates.py:17-24`). A glob ending in
  `__mutmut_*` matches no mangled function name in `tests_for_mutant_names` (`:1542-1551`), so the
  clean pre-run falls back to the whole static selection — exact names, read from the `.meta` files,
  avoid that. The covering tests can be restricted **only** through `pytest_add_cli_args_test_selection`
  (`configuration.py:109-114`); it is part of the config fingerprint, so changing it resets results —
  harmless for a CI run that starts from nothing.
- **Layout today.** `tests/` is a package; 457 `test_*.py`; 66 files import other test modules (14 of
  them import from `test_*.py` files; `tests.adopter_project` is imported 21 times); 97 files find the
  repository root from their own depth (`parents[1]` ×80) and would break when moved; 69 step files
  load scenarios by relative path; `pyproject.toml` names 157 test files in the mutation pool;
  `.beadloom/_graph/rules.yml:413` globs `tests/acceptance/features/**/*.feature`.
- **Live state.** `live_repo_reindexed` (`tests/conftest.py:89-106`) reindexes the shared
  `.beadloom/beadloom.db`, used by 12 files. `src/beadloom` has 52 `Path.cwd()` defaults in command
  entry points, the guard root and three rule evaluators; `bd` and `git` inherit that root. An autouse
  chdir into an empty directory is estimated to break 40-70 files, under 3% of test functions (inferred).
  Two stray index files already exist under `.beadloom/_graph/` — something once ran with the wrong root.

## Axes

> **Derived by:** `beadloom impact` over `src/beadloom` on six seeds — `context_oracle/test_mapper.py`,
> `graph/rules/scenario_coverage.py`, `graph/rules/evaluators.py`, `application/mutation_scope/score.py`,
> `services/commands/mutation.py`, `context_oracle/builder.py` (Explore, 2026-09-27).
> **Seed:** none — on all six seeds the derivation reported `no name the target reaches performs a
> declared effect under rule reaches-an-effect-sink`, so every axis is unresolved rather than empty.
> Unresolved counts as rendered: test_mapper 1 name-defined-more-than-once + 1 no-seed; scenario_coverage
> 1 + 1 + 8 unresolved-terminator-name; evaluators 1 no-seed + 29; score 1 + 5; commands/mutation 2 + 1 + 7;
> builder 1 + 1 + 1 node-owns-unread-files + 3.
> **Kept nodes: 9** — 8 of the 15 derived, ruled by the owner on 2026-09-28, plus `onboarding`, ruled
> `yes` with this RFC's approval (see the rows under the table). Branch rows are grouped per node below; the
> grouping is stated so it is not mistaken for a shorter derivation.

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved on all six seeds | — | no | No declared sink; nothing to rule. |
| branches | test-mapping | `test_mapper.py` — `map_tests`, `aggregate_parent_tests`, `_map_test_file_to_nodes`, the five `_find_*_test_files`, `_extract_*` | none | **yes** | The heuristic this work replaces with a declared binding. |
| callers + branches | context-builder | `builder.py:466,504`; `build_context`, `collect_chunks` | none | **yes** | `ctx` shows the node's tests from the binding. |
| callers + branches | rule-engine | `evaluators.py` (module_coverage at 1012-1112, forbid_import), `scenario_coverage.py`, `attribution.py:140`, `__init__.py:195` | none | **yes** | New rule types over the binding; the `@node:` agreement rule. |
| callers + branches | graph | `linter.py:483` `format_json`; the loader | none | **yes** | The node YAML carries the binding override; the linter reports the new rules. |
| callers + branches | reindex | `enrichment.py:27` `_store_test_mappings`; `full.py:183` | none | **yes** | Today it overwrites `extra["tests"]` with the guess; it will index test files and store the binding. |
| callers + branches | debt-report | `collect.py:189` `_count_untested` | none | **yes** | Counts "untested" nodes through the heuristic; must read the binding or it keeps misreporting. |
| branches | mutation-scope | `score.py` — `report_mutation_score`, `read_run_counters`, the counters | none | **yes** | Per-change and sampled runs report through it. |
| callers + branches | cli-commands | `commands/mutation.py:97` `mutation`, `_render`; `query.py:48-54` the `Tests:` line | none | **yes** | A per-change entry point; the `Tests:` line reads the binding. |
| callers | ci-gate | `gate.py:266` `lint_step` | none | no | Runs `lint`; the rules arrive through the engine, not through this call. |
| callers | mcp-server | `mcp_server.py:111`, `:399` | none | **yes** | First ruled no: it consumes the `ctx` bundle, whose `tests` shape is kept. C2 changed it: its hand-built copy of the debt report would have dropped the new `test_population` field, as it already dropped `layer_populations`; it now copies with `dataclasses.replace`. Ruled in by the owner after the pre-push scope warning. |
| callers | tui | `data_providers.py:360` | 4 — `tui/styles/*.tcss` | no | Consumes the bundle; the four unread files are stylesheets, checked. |
| callers | status, why, cache | `status.py:45`, `why.py:242`, `cache.py:289` | none | no | Consumers of `build_context`; shape kept. |
| callers | ignore-block | `ignore_block.py:264` | none | no | Surfaced through a shared `_render` name; unrelated. |
| — (not derived; G6) | onboarding | the shipped agentic-flow role templates the `test` role is composed from | — | **yes** | Ruled with the RFC's approval: G6 writes the test standards into the shipped `test` role. |
| — (not derived; consumers) | docs-audit, doc-generator | `doc_sync/audit.py:941-975`, `onboarding/doc_generator.py:934-1045` | — | no | Read `extra["tests"]`, whose four-key shape this RFC keeps. |
| — (not derived; C1) | db | `infrastructure/db.py` — the three test-file tables | — | **yes** | The test index needs its tables. Surfaced by PR #83's pre-push scope warning; ruled in by the owner on 2026-09-27. |
| — (not derived; C1, C2) | repository | `infrastructure/repository.py` — `most_specific_owner`, `count_test_files_by_placement` | — | **yes** | `ctx` reads the placement count from the repository rather than importing the reindex. Surfaced by the same warning; ruled in by the owner on 2026-09-27. |

**Not derivable, and to rule with this RFC's approval.** `beadloom impact` reads Python under `src/`,
so no row can name `tests/`, `.github/workflows/`, `pyproject.toml`, `.beadloom/*.yml` — every site of
isolation, relocation and the self-check triage lives there and is carried by the beads that name it.
Two product sites surfaced after the first ruling and were ruled with this RFC's approval — the
`onboarding` and consumers rows. Three more surfaced during phase A (`db`, `repository`, `mcp-server`)
and were ruled in by the owner on 2026-09-27, after PR #83's pre-push scope warning.

## Proposed Solution

### Move 1 — isolation (G1)

- An autouse fixture moves every test's working directory into an empty temporary directory. Any code
  that falls back to `Path.cwd()` then meets nothing instead of this repository. The 52 product
  defaults stay: defaulting to the current directory is correct CLI behaviour; the tests stop relying
  on it. The estimated 40-70 files that break are fixed by passing an explicit root.
- The existing tracked-write guard (`tests/tracked_write_guard`) is extended into a **contact guard**:
  outside the self-check category, a test fails if it opens the repository's `.beadloom/beadloom.db`,
  runs `bd` or `git` with the repository as its root. The guard states what it caught.
- Self-checks get a session-scoped **snapshot**: the tracked files copied once into a temporary
  directory and reindexed there. `live_repo_reindexed` is replaced by it. Nothing in the suite touches
  the live index afterwards.

### Move 1b — the self-check triage (G1b)

Each of the 547 self-checks is classified by what it guards. One that repeats a required Gate leg on
the real repository — `lint`, `sync-check`, `docs-audit`, `readme-pair`, `issue-log`, `config-check`,
`doctor`, `scope-check` — leaves pytest, with the leg named in the commit and a product test of the
checker on a synthetic fixture kept. The rest move to `tests/self_check/{architecture,docs,config,process}/`
under a `self_check` marker, against the snapshot. Recorded findings (`xfail` with a BDL-UX reference)
stay.

### Move 2 — layout, and the binding it gives (G2, G5a)

```
tests/
  unit/<path of the code under src/beadloom/>/test_*.py
  integration/<path of the code under src/beadloom/>/test_*.py
  acceptance/<domain>/<feature>.feature   + steps/<domain>/, steps/common/
  self_check/{architecture,docs,config,process}/
  support/                                 shared helpers (adopter_project, repo root, …)
```

- **Kind first, then the code.** It is the common Python layout, it lets CI select a kind by path, and
  the path under `unit/` or `integration/` mirrors the source path.
- **The binding follows from the mirror.** A test file under `tests/<kind>/graph/rules/` binds to
  the node whose `source:` covers `src/beadloom/graph/rules/` — the same `covering_prefix` rule
  ownership already uses, applied to the mirrored path. No per-file declaration.
- **Override, for what the mirror cannot say:** an optional `tests:` list in node YAML, resolved the
  same way, for tests that genuinely belong to a node their path does not mirror. The reindex stops
  overwriting it.
- **Relocation of the 227 clear-node files is mechanical:** `git mv` by the map's primary node; shared
  helpers first moved to `tests/support/`; the 97 files that find the repository root from their own
  depth switch to one helper that finds `pyproject.toml`; the mutation pool in `pyproject.toml` and
  `rules.yml:413` are regenerated. Proven by an identical collected-test set (ids modulo path) and an
  identical result before and after.

### Move 3 — the index, `ctx` and the rules (G2, G3)

- Reindex records test files — path, bound node, kind, test count, and their imports — in their own
  tables. Tests are **not** added to `scan_paths`: they must not become code (symbols, module coverage).
- `extra["tests"]` is produced from the binding in the **same four-key shape**, so every consumer
  keeps working: no `mutants/` entry (the walk skips it), no parent double-counting (a parent's count
  is the union of its children's files, not the sum), `coverage_estimate` derived from the bound files.
  `test_mapper`'s guessing is retired; `debt-report` reads the binding.
- New rule types, each stating its population:
  - `test_binding` — a node of a configured kind with no bound tests; a test file bound to no node
    (with an exemption list that carries a reason and an exit condition, like every stand-down here);
  - `test_import_boundary` — the `forbid_import` evaluator run over test imports: a unit test of a
    domain node that imports infrastructure;
  - `scenario_binding` — a scenario's `@node:` tag names the node of its folder and a node its steps
    execute.

### Move 4 — mutation per change, and a weekly sample (G4)

- **Per change.** A CI job on pull requests: `git diff` against the merge base → the functions changed
  in `only_mutate` files → their **exact** mutant names from the generated `.meta` files → a
  per-run `pytest_add_cli_args_test_selection` naming the tests bound to those functions' nodes (a
  fresh CI run has no cache, so the fingerprint reset costs nothing) → `mutmut run <names>` →
  `beadloom mutation` lists survivors by node. Budget: 10 minutes on `ubuntu-latest`.
- **Weekly sample.** A scheduled job runs N random mutant names from the declared scope with the
  default selection and reports a kill rate with its confidence interval. N is chosen to fit a budget,
  and stated.
- The retired nightly's file is replaced by these two jobs; the docs that describe it are rewritten.

### Move 5 — the pilot (G5, G5b) and the standards (G6)

- **Rule engine, in full:** its mixed files split by node; a unit layer beside the pure cores (the
  loader, layer reach, node tags); its acceptance features rewritten with `Rule:`, `Scenario Outline`
  and declarative steps over a driver layer and a shared step vocabulary. Invariants measured before
  and after: test count, per-node line coverage, kill rate on a fixed sample.
- **Standards:** the `test` role states what a test is here — one behaviour, arrange/act/assert, no
  shared state, named by behaviour, placed by the mirror — and the checkable parts become checks: no
  test module imports another test module (helpers live in `tests/support/`), no repository root from
  a file's depth, no bead or slice id in a test file's name.

## Alternatives Considered

- **A marker in every test file** (`@pytest.mark.node("rule-engine")`). Rejected as the primary: 457
  declarations that drift, where the mirror gives the same fact from where the file is. Kept as the
  override's spirit, in node YAML instead of in files.
- **Layout by node first** (`tests/<node>/{unit,integration}/`). Readable, but node ids are not paths,
  it breaks the mirror, and CI could no longer select a kind by one path.
- **Add `tests` to `scan_paths`.** One line, and it makes every test a code file — symbols, module
  coverage, ownership all shift. Rejected for separate tables.
- **Patch mutmut to accept a per-run test selection.** Rejected: BDL-073 showed how a patch of a
  third-party runner rests on a reading that can be wrong; the generated per-run config uses mutmut as
  it is.
- **Fix the 52 `Path.cwd()` defaults in the product.** Rejected: the defaults are right for a CLI; the
  defect is tests relying on them.

## Risks

- **Moving files loses coverage silently.** Mitigated by the invariant: identical collected ids
  (modulo path) and identical results, measured per relocation commit.
- **Removing self-checks loses a check.** Only with the replacing required Gate leg named and shown to
  check the same thing; otherwise the check moves instead of leaving.
- **The chdir guard breaks more than estimated.** The estimate (40-70 files) is static; the first bead
  measures it before committing to the fix.
- **Per-change mutation exceeds 10 minutes** when a change touches a function with many survivors.
  The job reports its population and time; the budget is revisited with numbers, not raised silently.
- **mutmut internals move** (names, `.meta` layout). The per-change job asserts the shapes it reads,
  in the precedent of `tests/mutmut_copy.py`.

## Open Questions

- Q1 | N for the weekly sample and its interval: decided by the bead that builds it, from a measured
  per-mutant cost.
- Q2 | Whether some self-checks deserve to become Gate legs for adopters, not only tests here: named
  by the triage, decided by the owner case by case.
