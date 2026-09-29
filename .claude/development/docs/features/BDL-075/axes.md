## Axes

> **Derived by:** `beadloom impact src/beadloom/__init__.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 no-seed, 1 node-owns-unread-files

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | — | no site found | — | ? |  |

Not derivable: the symbol target is refused — `beadloom impact __version__ --section` exits 1 with
"no file and no symbol named '__version__' under src/beadloom". The `callers` axis reports no site
while ten lines in seven files under `src/` read `__version__`; they are listed in Supplement A under `readers`,
derived by `grep`. Which history lines `beadloom docs audit` reports stale after the bump is not
measured: the simulated bump in a scratch copy was not run.

### Supplement A — the version surface `impact` cannot read

> **Derived by:** `beadloom version-surface` on the working tree at `11b5ad0d` (branch `features/BDL-075`); readers by `grep -rn __version__ src/`; paired documents from `sync_state` in `.beadloom/beadloom.db`; pinning tests by `grep` under `tests/`
> **Seed:** none — a sweep for the literal `6.0.0`, not a reachability derivation
> **Unresolved:** a place that states a version other than `6.0.0` is invisible to the sweep; `.json` files are not read (26), `.beadloom/flow-manifest.json` among them; 79 of the 154 places "checked by nothing" are in 15 files under `mutants/`, a gitignored mutmut copy (`.gitignore:69`), and are not the project

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| current-version | beadloom | `src/beadloom/__init__.py:6` — checked by packaging-manifest | none | ? |  |
| current-version | — | `.beadloom/_graph/beadloom.yml:5` "(v6.0.0)" — checked by graph-summary-facts | — | ? |  |
| current-version | — | `.claude/CLAUDE.md:118` — checked by doctor; rendered from `__version__` by `src/beadloom/onboarding/scanner/claude_md.py:203`; `.beadloom/flow-manifest.json` records the file's hash | — | ? |  |
| current-version | beadloom | `docs/getting-started.md:45` — checked by docs-audit | none | ? |  |
| current-version | cli | `docs/services/cli.md:858` — checked by docs-audit; `docs/services/cli.md:857` — the audit attributes the token to `bd`, so nothing compares it | none | ? |  |
| current-version | docs-audit | `docs/domains/doc-sync/features/docs-audit/SPEC.md:112`, `:113` — checked by nothing | none | ? |  |
| current-version | — | `tests/test_integration_v1.py:27`, `:33` — checked by test-suite; `:17` docstring — checked by nothing | — | ? |  |
| current-version | — | `.claude/development/ROADMAP.md:3`, `:8` — checked by nothing | — | ? |  |
| pinning-test | — | `tests/self_check/config/test_version_surface.py:60`–`:80` — fails unless each of nine files states the current literal, `CHANGELOG.md`, `.claude/development/ROADMAP.md` and the docs-audit `SPEC.md` among them | — | ? |  |
| release-notes | — | `CHANGELOG.md:8` — `[6.0.0]` is the top section; no `[Unreleased]` section; 0 lines name BDL-072, BDL-073 or BDL-074 | — | ? |  |
| audit-config | — | `.beadloom/config.yml:120`–`:151` — three `docs_audit.ignore` triples for `4.0.0` (graph-loader `DOC.md`, onboarding `README.md`, `cli.md`); they name `4.0.0`, not `6.0.0` | — | ? |  |
| paired-docs | beadloom | `docs/architecture.md`, `docs/getting-started.md`, `docs/guides/ci-setup.md` — each paired with `src/beadloom/__init__.py` in `sync_state` | none | ? |  |
| readers | cli-commands | `src/beadloom/services/commands/_root.py:11`, `:51` (`--version`) | none | ? |  |
| readers | mcp-server | `src/beadloom/services/mcp_server.py:16`, `:1494` | none | ? |  |
| readers | doctor | `src/beadloom/application/doctor.py:378` | none | ? |  |
| readers | reindex | `src/beadloom/application/reindex/full.py:68` | none | ? |  |
| readers | wave-plan | `src/beadloom/application/waves/clean_room.py:645`, `:688` | none | ? |  |
| readers | docs-audit | `src/beadloom/doc_sync/audit.py:810` (regex read of the source file) | none | ? |  |
| readers | version-surface | `src/beadloom/doc_sync/version_surface.py:164` (regex read of the source file) | none | ? |  |
| history | — | `CHANGELOG.md:13`, `:140`, `:143`, `:149`; `.claude/development/ROADMAP.md:38`, `:358`; `.beadloom/config.yml:120`, `:147`; `.claude/development/BDL-UX-Issues.md:113`–`:115`, `:298` — checked by nothing | — | ? |  |
| history | — | `.claude/development/docs/features/BDL-071/` — 56 lines in `ACTIVE.md`, `CONTEXT.md`, `PLAN.md`, `PRD.md`, `RFC.md` — checked by nothing | — | ? |  |

Distinct nodes: 0 in the `impact` table; 3 in the current-version rows (`beadloom`, `cli`,
`docs-audit`); 9 across Supplement A.

### Supplement B — adopter-visible changes from 6.0.0 to `main`

> **Derived by:** `git diff v6.0.0..11b5ad0d --stat` (1021 files; 66 under `src/`), a targeted diff of each of the 66, and `git log -S unbound_tests v6.0.0..11b5ad0d`; `v6.0.0` resolves to `058ef59e`
> **Bar:** `.claude/development/docs/features/BDL-071/CONTEXT.md:80` — "a JSON value-set change (`declared` widened to `bool | null`) makes A major"
> **Unresolved:** no document read declares which Python import paths are public; `pyproject.toml` changes only a ruff per-file-ignore path and the mutmut test pool, with no dependency change

| Change | Sites | Node | Label | Reason |
|---|---|---|---|---|
| `mutation --json`: `unbound_tests` → `unplaced_tests` | `src/beadloom/application/mutation_scope/change.py:314` | mutation-scope | not adopter-visible | `unbound_tests` was added in `7cbc1874` and renamed in `45a3c2fc`, both after `v6.0.0`. `git grep` finds neither key in `v6.0.0:src`, so against 6.0.0 the key is part of the new `change` object. |
| `mutation --json`: new top-level keys `change`, `survivors_by_node`, `sample`, each `null` when unused | `src/beadloom/services/commands/mutation.py:283`–`:287`; `change` object at `src/beadloom/application/mutation_scope/change.py:292`–`:318` | cli-commands, mutation-scope | additive | Keys are added and none is removed from `_payload`. |
| `mutation`: options `--changed-since`, `--survivors`, `--sample-of`; exit 2 on an unreadable change, list or sample | `src/beadloom/services/commands/mutation.py:117`, `:126`, `:132`, `:173`, `:245`, `:260` | cli-commands | additive | Every new exit-2 cause needs a new flag. `--stats` without `--target` is newly accepted only with `--changed-since`. |
| `mutation --min-score` with `--sample-of` misses the floor only when the whole Wilson interval is under it | `src/beadloom/services/commands/mutation.py:306` | cli-commands | additive | The floor changes only on the new flag. Without it, `:308` keeps the 6.0.0 comparison. |
| Debt report: the untested count is withheld while any test file is unplaced, and counted from the test binding otherwise | `src/beadloom/application/debt_report/collect.py:196`, `:240`, `:257`; weight `models.py:31`; score `scoring.py:171` | debt-report | breaking (verdict) | 6.0.0 counted nodes whose estimate was `none`, which `v6.0.0:src/beadloom/context_oracle/test_mapper.py:468`–`:470` never returned once a framework was detected. It therefore scored 0 on any project with a test file. With every test file placed, each binding-covered node with no bound file now adds to `debt_score`, so `status --fail-if score>N` (`services/commands/status.py:79`) can flip on an unedited graph. |
| Debt JSON: new key `test_population` (`status --debt-report --json`, MCP `get_debt_report`) | `src/beadloom/application/debt_report/render.py:96` | debt-report | additive | A key is added and none is removed. |
| Debt report keeps `layer_populations` under MCP `get_debt_report` with `trend`, and under `status --category` | `src/beadloom/services/mcp_server.py:512`; `src/beadloom/services/commands/status.py:117` | mcp-server, cli-commands | fix | 6.0.0 rebuilt `DebtReport` by hand (`v6.0.0` `mcp_server.py:511`, `status.py:115`) and dropped the field. |
| `ctx --json` and MCP `get_context`: new keys `test_placements`, `test_unplaced`, `test_recognition` | `src/beadloom/context_oracle/builder.py:519`–`:521` | context-builder | additive | Keys are added and none is removed. |
| `ctx` bundle `extra.tests`: the four keys are kept and their values come from the binding | `src/beadloom/context_oracle/test_binding.py:86`, `:124`, `:436`–`:447`; `src/beadloom/application/reindex/test_index.py:382`, `:404` | test-mapping, reindex | breaking (value set) | `framework` can be a `+`-joined name such as `go_test+pytest`, where 6.0.0 held one name or `none`. `test_files` and `test_count` are the union over descendants, where 6.0.0 aggregated only for a parent with no direct file. |
| `ctx` human output: unplaced-share and recognition lines | `src/beadloom/services/commands/query.py:70`, `:76` | cli-commands | additive | Lines are added to human output only. |
| `reindex` human output: a `Tests:` line | `src/beadloom/services/commands/index_ops.py:119` | cli-commands | additive | A line is added to human output only. |
| The first incremental reindex over an index without the test tables runs a full reindex | `src/beadloom/application/reindex/incremental.py:124` | reindex | additive | The rebuild happens once per index and changes no output. |
| Index: new tables `test_files`, `test_imports`, `test_overrides` | `src/beadloom/infrastructure/db.py:274`, `:285`, `:296`; dropped on reindex at `src/beadloom/application/reindex/models.py:30`–`:32` | db | additive | No existing table or column changes. |
| New config block `tests:` with keys `roots`, `patterns`, `kinds`, `beside_code`, `mirrors` | `src/beadloom/context_oracle/test_layout.py:91`, `:102`, `:274`–`:281` | test-layout | additive | A project without the block reads the defaults at `:102`. |
| Node YAML `tests:` is read as a list of path prefixes that overrides the mirror | `src/beadloom/application/reindex/test_index.py:99`–`:122` | reindex | additive | A value that is not a list of paths now produces a reindex warning (`:111`–`:115`). |
| New rule kinds `test_binding`, `test_import_boundary`, `scenario_binding` | `src/beadloom/graph/rules/loader.py:1073`–`:1075` | rule-engine | additive | Each fires only when declared. `grep` finds none of the three under `src/beadloom/onboarding`, so `init` generates none. |
| The suite rules' population statement is advisory | `src/beadloom/graph/rules/advisories.py:67` | rule-engine | additive | The statement does not trip `--fail-on-warn`. |
| Removed module `beadloom.context_oracle.test_mapper` (629 lines) and the `_store_test_mappings` export of `beadloom.application.reindex` | `src/beadloom/context_oracle/test_mapper.py` (deleted); `src/beadloom/application/reindex/__init__.py` | test-mapping, reindex | breaking for Python importers only | No CLI command or MCP tool names either. Three documents still name the module: `docs/domains/context-oracle/README.md`, `docs/domains/context-oracle/features/test-mapping/SPEC.md`, `docs/domains/application/features/debt-report/SPEC.md`. |
| Composed role text: the tester's standards; the stack/overlay sentence in review, tech-writer and test | `src/beadloom/onboarding/templates/roles/core/test.md.txt:17`–`:49`; `.../stack/python/test.md.txt:4`–`:35`; `.../core/review.md.txt:8`; `.../core/tech-writer.md.txt:8` | onboarding | additive (text) | `setup-agentic-flow` rewrites the adopter's role files. The Python overlay replaces "Tests live in `tests/` (flat, no subdirs)" with the kind and mirror layout. No machine-read surface changes. |
| Rich-markup escaping of graph and document text | `src/beadloom/context_oracle/why.py:336`–`:360`; `src/beadloom/graph/diff.py:521`–`:582`; `src/beadloom/services/commands/docs.py:589`–`:614`; `src/beadloom/application/debt_report/render.py:207`–`:230`; `src/beadloom/onboarding/scanner/init_flow.py:209` | why, graph-diff, cli-commands, debt-report, agent-prime | fix | Bracketed text was read as markup: `--[part_of]--` printed `----`, `app/[slug]/` lost its folder, and a pattern holding `[/x]` raised `MarkupError`. The fix touches human output only. |
