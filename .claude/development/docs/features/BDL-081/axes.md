## Axes

> **Derived by:** `beadloom impact src/beadloom/__init__.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 no-seed, 1 node-owns-unread-files

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | — | no site found | — | ? |  |

## Axes

> **Derived by:** `beadloom impact get_actual_version` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 dynamic-dispatch, 1 no-seed, 9 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:94` | none | ? |  |
| callers | cli-commands | 1 — `src/beadloom/services/commands/index_ops.py:148` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site/dashboard/gate_metrics.py:109` | none | ? |  |
| branches | doctor | `_check_empty_summaries`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_unlinked_docs`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `_docs_absent_reason`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_nodes_without_docs`: 6 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_isolated_nodes`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_symbol_drift`: 4 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_stale_sync`: 2 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_source_coverage`: 2 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | doctor | `_extract_version_claim`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | doctor | `_extract_package_claims`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | doctor | `get_actual_version`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `_get_actual_cli_commands`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `_get_actual_mcp_tool_count`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_agent_instructions`: 18 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_stack_claim`: 3 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | doctor | `_check_test_framework_claim`: 3 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | doctor | `_declared_stack`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | doctor | `run_checks`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | ci-gate | `_run_doctor_checks`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `_doctor_metrics`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `doctor`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |

## Axes

> **Derived by:** `beadloom impact _beadloom_version` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 name-defined-more-than-once, 35 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:247` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/init_flow.py:47` | none | ? |  |
| callers | graph | 1 — `src/beadloom/graph/linter.py:151` | none | ? |  |
| callers | reindex | 1 — `src/beadloom/application/reindex/incremental.py:65` | none | ? |  |
| branches | reindex | `_beadloom_version`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | reindex | `_drop_all_tables`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | reindex | `reindex`: 3 branch(es), 1 exit form(s) | none | ? |  |
| branches | reindex | `incremental_reindex`: 7 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | graph | `lint`: 3 branch(es), 3 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `non_interactive_init`: 3 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `interactive_init`: 5 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |

## Axes

> **Derived by:** `beadloom impact read_version_surface` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 4 name-defined-more-than-once, 1 no-seed, 3 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | cli-commands | 1 — `src/beadloom/services/commands/version_surface.py:90` | none | ? |  |
| callers | doc-sync | 3 — `src/beadloom/doc_sync/version_subjects.py:219` | none | ? |  |
| callers | flow-suppression | 2 — `src/beadloom/onboarding/flow_suppression.py:168` | none | ? |  |
| callers | gate-ownership | 1 — `src/beadloom/application/gate_ownership.py:175` | none | ? |  |
| callers | rule-engine | 4 — `src/beadloom/graph/rules/doc_area.py:359` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site/raw_html.py:106` | none | ? |  |
| branches | version-surface | `read_version_surface`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_section`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_read_source_of_truth`: 4 branch(es), 9 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_each_file`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_normalise`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_sweep`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_lines_stating`: 2 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_attribute`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_build_instruments`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_packaging_holder`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_docs_audit_holder`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_graph_holder`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_rule_declaration`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_summary_lines`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_doctor_holder`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_flow_written`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_regions_of`: 3 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_test_suite_holder`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_declared_testpaths`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_assert_lines`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `unchecked`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `instrument`: 0 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | version-surface | `applies`: 0 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | version-surface | `covers`: 0 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `covers`: 0 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `covers`: 0 branch(es), 5 exit form(s), over every call | none | ? |  |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `covers`: 0 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `covers`: 0 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | version-surface | `covers`: 0 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | version-surface | `_under_testpaths`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | gate-ownership | `derive_gate_ownership`: 3 branch(es), 4 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `_opening_tag`: 4 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | doc-sync | `_project_names`: 5 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | doc-sync | `_configured_subjects`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | doc-sync | `_requirement_name`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_area_votes`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_read`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `area_of`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `layer_exemption_index_for`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | flow-suppression | `composed_headings`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | flow-suppression | `suppresses_nothing`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `version_surface`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |

## Axes

> **Derived by:** `beadloom impact _parse_version` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 13 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:108` | none | ? |  |
| callers | cli-commands | 2 — `src/beadloom/services/commands/docs.py:276` | none | ? |  |
| callers | flow-guards | 3 — `src/beadloom/application/guards/config.py:217` | none | ? |  |
| callers | mcp-server | 1 — `src/beadloom/services/mcp_server.py:695` | none | ? |  |
| callers | rule-engine | 10 — `src/beadloom/graph/rules/evaluators.py:187` | none | ? |  |
| callers | test-mapping | 2 — `src/beadloom/context_oracle/test_binding.py:357` | none | ? |  |
| branches | docs-audit | `_unreadable_table`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_foreign_surface_reason`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `parse_fail_condition`: 4 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `metric_value`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `fail_condition_triggered`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `compare_facts`: 6 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_values_match_with_tolerance`: 2 branch(es), 5 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_load_tolerances_from_config`: 3 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_load_ignore_from_config`: 3 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `run_audit`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `verified_facts`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `unverified_facts`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `matches`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `collect_set`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `collect`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_version`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_parse_version`: 10 branch(es), 5 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_db_counts`: 1 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_language_count`: 2 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_test_count`: 3 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_nodes_with_framework`: 3 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_rule_type_count`: 1 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_mcp_tool_count`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_cli_command_count`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_count_click_commands`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | docs-audit | `_collect_extra_facts`: 4 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | ci-gate | `_run_audit`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | flow-guards | `exclusion_for`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | flow-guards | `excluded_everywhere`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | flow-guards | `dead_exclusions`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | test-mapping | `union_over_descendants`: 2 branch(es), 3 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | test-mapping | `collect`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_first_matching_source`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `evaluate_require_rules`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `evaluate_forbid_edge_rules`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `evaluate_cardinality_rules`: 9 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `evaluate_unregistered_feature_candidate_rules`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `matched`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_matched_nodes`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `collect_claims`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `_facts_for`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `docs_audit`: 7 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `_docs_audit_json`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | mcp-server | `_active_rules_for_node`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |

Not derivable: the four reader targets are `get_actual_version` (`src/beadloom/application/doctor.py:365`), `_beadloom_version` (`src/beadloom/application/reindex/full.py:68`), `read_version_surface` (`src/beadloom/doc_sync/version_surface.py:248`) and `_parse_version` (`src/beadloom/doc_sync/audit.py:768`), chosen from `grep __version__` because the BDL-079 RFC (`.claude/development/docs/features/BDL-079/RFC.md:65`) names no reader and its saved runs are not on disk; the places that state the version are documents, which `beadloom impact` does not read (they are listed under `## Version places`); the five sections name 19 distinct nodes (`ci-gate`, `cli-commands`, `site-generation`, `doctor`, `agent-prime`, `doc-generator`, `doc-sync`, `graph-layout`, `graph-loader`, `reindex`, `graph`, `version-surface`, `flow-suppression`, `gate-ownership`, `rule-engine`, `flow-guards`, `mcp-server`, `test-mapping`, `docs-audit`), and `beadloom lint` on `9f96ae52` reports no size finding and no boundary crossing on any of them.

## The measured diff, v8.0.0 → main (290507b2)

> **Room:** Darwin arm64, CPython 3.12.12, click 8.5.0, mcp 2.3.0, extra `languages`, in two
> scratch environments built for this run (not a `beadloom clean-room`). 8.0.0 is the PyPI
> artifact (`UV_NO_CACHE=1 uv pip install "beadloom[languages]==8.0.0"`). The tree is the
> wheel built from `9f96ae52`, whose `src/` and `tests/` equal `290507b2`
> (`git diff --stat 290507b2 HEAD -- src tests` is empty). A first pass with click 8.4.2 and CPython 3.13 beside
> click 8.5.0 and CPython 3.12 reported 58 default changes (`Sentinel.UNSET -> False`, a `Path.cwd`
> repr) that come from those versions, not from Beadloom. Matching the two removed them.
> **Projects measured:** this repository at `v8.0.0` (`git archive v8.0.0`, one commit), the
> fixtures `python`, `typescript`, `vue-fsd`, `rn-fsd` under `tests/fixtures/site/` after
> `init --yes`, and 28 small prototypes, each run under both versions on identical files.
> **Scripts and outputs:** `/private/tmp/claude-501/-Users-v-zoologov-beadloom/d9baf9b3-45de-4ce8-bce7-031fe744fc3f/scratchpad/explore-bdl081/`
> (`scripts/`, `out/8/`, `out/now/`, `proto/`), session scratch. `$X` below is that folder.

### 1. Commands, options and exit codes

| Change | SemVer kind | Evidence |
|---|---|---|
| Commands: 56 at 8.0.0, 56 on the tree; none added, removed or renamed | none | `$X/scripts/clitree.py` walks the click tree; `clidiff.py cli8.json clinow.json` prints `commands: 56 -> 56` |
| `init --preset` gains `fsd` | MINOR | `clidiff`: `CHANGED init preset choices ['monolith', 'microservices', 'monorepo'] -> [..., 'fsd']`; `diff -r help8 helpnow` differs only in `init.txt:7` |
| Every other option, default and `--help` text: byte-identical (55 of 56 help texts) | none | `diff -r $X/help8 $X/helpnow` |
| `lint --strict` and `ci` on a `kind: site` node under a `require` rule whose `for` is `kind: service`: exit 0 → 1 | MAJOR (row 3) | `$X/proto/sitekind-{8,now}`: 8.0.0 `service-needs-parent:rule_liveness:warn` ("matches none of the 2 nodes"), rc 0; tree `service-needs-parent:require:error:::portal:`, rc 1; `ci` rc 0 → 1 |
| `lint --strict` when a `.mjs` file's import crosses a `deny` rule: exit 0 → 1, edges 2 → 3 | MAJOR (row 3; 8.0.0 classed the same case Breaking, `CHANGELOG.md:429`) | `$X/scripts/jsvariant.sh mjs_importer`: tree `ui-not-store:deny:error:src/ui/a.mjs:1:ui:store` |
| `lint --strict` when an import read through tsconfig `paths` crosses a `deny` rule: exit 0 → 1 | MAJOR (row 3) | `jsvariant.sh tsconfig_paths`: tree `ui-not-store:deny:error:src/ui/a.ts:1:ui:store` |
| `lint --strict` when `../store/Button` names only `Button.ios.tsx`: exit 0 → 1 | MAJOR (row 3) | `jsvariant.sh rn_platform` |
| `lint --strict` through `imports.aliases`: exit 0 → 1 only once the block is written | MINOR (the input differs) | `jsvariant.sh vite_alias_cfg` |
| `config-check` on `imports: {foo: 1}` and on an alias naming nothing: exit 0 → 1 | MAJOR (row 3: accepted, now refused) | `$X/scripts/variant.sh imports_unknown`, `imports_badpath`; tree: "`foo:` is not a key of `imports:`", "`nowhere` names nothing in the project" |
| `lint --strict` on a `layers` rule carrying `scope:` (a node that does not hold the crossing, or no node): exit 1 → 0 | MAJOR (row 3, the direction 8.0.0 also counted, `CHANGELOG.md:443`) | `variant.sh upward_scope_lib`, `upward_scope_ghost`: 8.0.0 `layering:layer:error:::lib:ui`; tree `layering:rule_liveness:warn` |
| `lint --strict` on a `layers` rule with `title: ""`: exit 0 → 2 | MAJOR (row 3) | `variant.sh title_empty`: tree "'title' must be a non-empty string" |
| `lint --strict` on a matcher `{kind: component, tag_prefix: zzz}`: exit 1 → 0 | MAJOR (row 3) | `variant.sh kind_plus_prefix`: 8.0.0 two `needs:require:error`; tree `needs:rule_liveness:warn` |
| `config-check` and `ci` on this repository at `v8.0.0`, unedited: exit 0 → 1 | MAJOR by row 3, or an upgrade step (Open question 3) | `$X/out/{8,now}/repo800b/configcheck.rc`; `ci.out:11` `config-check FAIL: 4 drifted artifact(s)` — `.claude/agents/{dev,explore,review}.md`, `.claude/commands/coordinator.md`: "composed body is stale" |
| `init --yes` on the `vue-fsd` fixture: exit 0 (preset `monolith`) → 1 (preset `fsd`) | MAJOR by row 3, or a new preset's verdict (Open question 4) | `$X/out/now/vue-fsd/init.out`: "Error: your code does not pass the rules this command wrote alongside it. fsd-layers: features-apply-coupon; fsd-public-api: src/widgets/product-grid/ui/ProductGrid.vue:3" |
| `config-check` on a valid `site.logo`, `site.powered_by: false`, `site.repo_icon: gitlab`: exit 1 → 0 | MINOR (refused before, accepted now) | `variant.sh site_logo_ok`, `site_powered`, `site_repo_icon`; 8.0.0 "`logo:` is not a key of `site:`" |
| `docs site` built from an unpushed commit: exit 0 on both; the tree adds a stderr warning | none | `$X/out/now/repo800b/site.err` |
| `reindex`, `status`, `export`, `doctor`, `impact`, `sync-check`, `docs polish`, `debt-report`: exit codes equal | none | `$X/out/{8,now}/{repo800b,python,typescript,vue-fsd,rn-fsd}/*.rc` |
| Counts move on unedited projects: this repository at `v8.0.0` scans 478 → 482 files, 3952 → 3956 symbols, 1757 → 1759 imports resolved, 743 → 747 sync pairs; edges, lint and the debt score unchanged. `rn-fsd` and `vue-fsd` initialised by 8.0.0: edges 48 → 50 and 54 → 55 | Changed (the 8.0.0 precedent for counts) | `$X/out/*/repo800b/lintjson.out`, `status.out`, `ci.out:4`; `$X/proto/up-{rn-fsd,vue-fsd}` |
| A specifier must match each folder's case exactly (macOS) | not measured | `CHANGELOG.md:298-304`. Measured on Darwin only, with no case-mismatched fixture |

### 2. Keys of `.beadloom/config.yml`

| Change | SemVer kind | Evidence |
|---|---|---|
| `site.logo`, `site.powered_by`, `site.repo_icon` added; `site:` now reads 8 keys, 5 before | MINOR | 8.0.0: "the block reads `base:`, `description:`, `forges:`, `repo_url:`, `title:`"; tree: the same plus `logo:`, `powered_by:`, `repo_icon:` (`$X/proto/sitekeys`) |
| `imports.aliases` added; an `imports:` block 8.0.0 ignored is now refused when unusable | MINOR for the key, MAJOR for the refusal (section 1) | `variant.sh imports_ok` 0/0; `imports_unknown` 0 → 1. The guide claims "no accepted configuration is refused" (`docs/guides/public-api.md:45-47`). 8.0.0 accepted the block by ignoring it |
| `activity:` keys unchanged (`exclude:`) | none | `$X/proto/actkeys-{8,now}`: identical refusal text |
| Removed or renamed keys: none found | none | the refusal texts above |
| `preset: fsd` written by `init` | MINOR (a value added) | `$X/work/now/rn-fsd/.beadloom/config.yml`: `preset: fsd` (8.0.0 `monolith`) |

**Keys of `rules.yml`.** The guide names no list item for them. Item 6 covers `init`'s
`rules.yml` as a generated file, and the rule-engine SPEC is their reference.

| Change | SemVer kind | Evidence |
|---|---|---|
| Rule types `slice_public_api`, `slice_shape` added; 8.0.0 refuses both at load | MINOR | `variant.sh slice_api`, `slice_shape`: 8.0.0 `lint` rc 2 "must have exactly one of 'check', 'deny', …"; tree rc 0 |
| `tag_prefix:` on a matcher: alone, refused by 8.0.0 (rc 2) and read now | MINOR | `variant.sh tag_prefix` |
| `tag_prefix:` beside `kind`, `scope:` and `title:` on `layers`: 8.0.0 accepted and ignored them, the tree reads them | MAJOR (section 1, the rows on `scope:`, `title:` and `tag_prefix`) | `variant.sh layers_scope` 0/0, `layers_title` 0/0, `kind_plus_prefix`, `title_empty` |
| `kind: site` read as `service` through an alias | MAJOR (stated under Breaking) | `src/beadloom/graph/loader.py:76` `KIND_ALIASES = {"site": "service"}`; reindex prints `[info] Node 'portal' declares kind 'site', read as 'service' (an accepted alias)` |

### 3. JSON outputs

The guide declares `ctx --json`, `status --json`, the debt report and `export`
(`docs/guides/public-api.md:48-52`). `docs polish`, `lint --format json`, `impact --json` and
`mutation --json` are not on the list. They were measured anyway. Method: every key path and
every short string value, unioned over five projects (`$X/scripts/keys.py vals`).

| Output | Declared | Change | SemVer kind | Evidence |
|---|---|---|---|---|
| `ctx --json` | yes | no key added or removed; `focus.kind` and `graph.nodes[].kind`: value `site` no longer emitted (`service` instead) | MAJOR (a value removed; stated under Breaking) | `out/*/repo800b/ctx_site.out`: `VOCAB .focus.kind removed: ['site'] added: ['service']` |
| `status --json` | yes | `by_kind.site` absent for a project with a `kind: site` node; it is counted under `by_kind.service` | MAJOR (a key removed; Breaking names only the data file and `ctx --json`, `CHANGELOG.md:22-23`) | repo800b: 8.0.0 `{'component': 67, 'feature': 51, 'domain': 7, 'service': 4, 'site': 1}`, tree `{..., 'service': 5}` |
| Debt report | yes | keys and the `severity` vocabulary unchanged (`critical` already in 8.0.0, `src/beadloom/application/debt_report/scoring.py:39` at `v8.0.0`); the score is the same on this repository at `v8.0.0` (35.5) | none | `out/*/repo800b/debt.out` |
| `export` | yes | `nodes[].kind`: value `site` no longer emitted | MAJOR (unnamed by Breaking) | `out/*/repo800b/export.json` |
| `docs polish --format json` | no | `nodes[].kind`: value `site` no longer emitted | none (undeclared) | `out/*/repo800b/polish.out` |
| `lint --format json` | no | no key added or removed; `rule_type` values `slice_public_api`, `slice_shape` added | none (undeclared) | `out/*/{vue-fsd,rn-fsd}/lintjson.out` |
| `impact --json`, `mutation --json`, `sync-check --json` | no | no key or value change | none | `out/*/repo800b/{impact,impact2,mutation,synccheck}.out` |

### 4. MCP tools

| Change | SemVer kind | Evidence |
|---|---|---|
| 18 tools at both versions; names, input schemas and descriptions identical; `src/beadloom/services/mcp_server.py` unchanged since `v8.0.0` | none | `$X/scripts/mcptools.py` over `mcp_server._TOOLS`; `git diff --stat v8.0.0 290507b2 -- src/beadloom/services/mcp_server.py` empty |
| `get_context` returns `kind: service` for a node declared `kind: site` | MAJOR (Breaking names `ctx --json` only) | `get_context` calls `build_context` (`src/beadloom/services/mcp_server.py:132`), the builder `ctx` uses |
| `docs/services/mcp.md` changed in 2 lines (the `config_check` and `init` entries) | none | `git diff v8.0.0 290507b2 -- docs/services/mcp.md` |

### 5. Portal data files

The guide declares `architecture.data.json` only. It says `dashboard.data.json` "is not this
file and is not on this list … carry no promise" (`docs/guides/public-api.md:74-76`), and it
names no `landscape.data.json`.

| File | Change | SemVer kind | Evidence |
|---|---|---|---|
| `architecture.data.json` | `schema_version` stays 2 | none | `out/*/repo800b/site/public/architecture.data.json` |
| `architecture.data.json` | top-level `layer_rules[]` (`name`, `title`, `scope`, `edge_kind`, `layers[]` of `name`, `rank`, `tag`, `token`) added | MINOR | `keys.py`: `ADDED .layer_rules[]…` |
| `architecture.data.json` | `nodes[].layer_rule`, `nodes[].layer_rule_rank` added | MINOR | same |
| `architecture.data.json` | top-level `lint` (`errors`, `warnings`, `nodes_with_findings`, `nodeless[]` of `rule`, `severity`, `message`, `file`, `line`) added | MINOR | same |
| `architecture.data.json` | `nodes[].debt.inside` (`nodes`, `score`, `by_reason`) added | MINOR | same |
| `architecture.data.json` | top-level `source_ref` (`commit`, `linked`, `pushed`) added | MINOR | same |
| `architecture.data.json` | `nodes[].kind`: value `site` no longer emitted | MAJOR (stated under Breaking) | `VOCAB .nodes[].kind removed: ['site']` |
| `architecture.data.json` | no key removed | none | no `REMOVED` line over five projects |
| `dashboard.data.json` | `lint.nodes_with_findings`, `lint.nodeless[]`, top-level `pages` (`count`, `sections[]`, `languages[]`) added; no key removed | none (undeclared) | `keys.py`: `ADDED .pages.*`, `ADDED .lint.nodeless[]…` |
| `landscape.data.json` | a `kind: site` node moves from group `other` to the services group; `nodes[].kind` value `site` no longer emitted | none (undeclared) | `VOCAB .nodes[].group removed: ['other']`, `.nodes[].kind removed: ['site']` |

### 6. Files generated for an adopter

| Generator | Change | SemVer kind | Evidence |
|---|---|---|---|
| `docs site` scaffold | 189 → 217 files outside the page folders; 70 added, 42 removed or renamed | MAJOR by row 1, if the theme's internal paths are in the promise (Open question 1); the change log lists them under Changed (`CHANGELOG.md:232-241`) | `$X/scaffold_diff.txt` |
| `docs site` scaffold | renamed: `entities/graph-edge/*` → `entities/graph-edges/*` (5 files), `entities/graph-node/*` → `graph-nodes/*` (3), `entities/layer/*` → `layers/*` (3); 31 files of `widgets/graph-viewer/{lib,model}/` moved into `shared/{bundling,geometry,grid-routing,map-levels,canvas-marks}`, `features/{edge-pills,follow-edge,overview-map}`, `entities/graph-edges/lib` | as above | same |
| `docs site` scaffold | added: `steiger.config.js`, `public/brand/beadloom-{icon.svg,favicon.svg,favicon.png,favicon-dark.png}`, `widgets/powered-by/*`, `app/styles/nav-logo.css`, `widgets/dashboard/ui/{PageMap,RuleFindings}.vue`, `e2e/{brand,dashboard,layer-boxes}.spec.js`, `e2e/support/{fonts,layers}.js` | MINOR | same |
| `docs site` `package.json` | `scripts."lint:fsd": "steiger .vitepress/theme"`, devDependencies `steiger 0.7.0`, `@feature-sliced/steiger-plugin 0.8.0` added | MINOR | `diff out/8/*/site/package.json out/now/*/site/package.json`, identical on all five projects |
| `docs site` pages | the page of a `kind: site` node moves from `other/<ref>.md` to `services/<ref>.md` | MAJOR (a generated file renamed; unnamed by Breaking) | `$X/pages_8.txt`, `$X/pages_now.txt`: `< ./other/vitepress-site.md`, `> ./services/vitepress-site.md` |
| `docs site` upgrade in place | an 8.0.0 portal rewritten by the tree: `67 written, 51 updated, 91 unchanged, 42 retired, 9 empty folders retired`; `other/vitepress-site.md` stays beside the new `services/vitepress-site.md` | Changed; the leftover page is a measured fact (Open question 6) | `$X/upgrade_site/` |
| `docs site` footer | on by default, so an unedited portal gains `widgets/powered-by` | MINOR (a generated file added) | `CHANGELOG.md:245-247`; the scaffold diff above |
| `init` (Python, TypeScript fixtures) | `.beadloom/config.yml`, `_graph/rules.yml`, `_graph/services.yml`, `.beadloom/AGENTS.md`, `.gitignore`: byte-identical | none | `diff $X/work/8/{python,typescript}/… $X/work/now/…` |
| `init` (FSD fixtures) | preset `monolith` → `fsd`; nine rules written (`fsd-layers` with `title: "FSD architecture"` and `scope:`, `fsd-public-api` error, `fsd-slice-shape` warn, six `fsd-cohesion-*` warn); `imports.aliases` written (`'@': src`, `'@modules': modules` on `rn-fsd`); `package.json` gains `"lint:fsd": "steiger ./src"` on `rn-fsd` and is kept on `vue-fsd` | MINOR (new preset) | `$X/work/now/rn-fsd/.beadloom/_graph/rules.yml:17-100`; `git diff HEAD~1 -- package.json` in that folder |
| `init` (FSD fixtures) | 21 files 8.0.0 wrote for the same tree (`docs/domains/*/README.md`, `docs/services/shared*.md`) are not written | MAJOR by row 1, or a different preset's output (Open question 4) | `diff $X/init8_vue-fsd.txt $X/initnow_vue-fsd.txt` (and `rn-fsd`) |
| `.beadloom/AGENTS.md` | identical on Python and TypeScript; on FSD it lists the nine `fsd-*` rules in place of `domain-needs-parent`, `feature-needs-parent` | follows the preset | `diff …/rn-fsd/.beadloom/AGENTS.md` |
| `setup-agentic-flow` (`ddd`, `python`) | same 18 files; `dev` 13, `explore` 6, `review` 4, `coordinator` 4 lines changed: the `cohesion` duty (`<!-- beadloom:duty=cohesion roles=dev,explore,review -->`) and its carriers | MINOR by text; it makes `config-check` exit 1 on files composed by 8.0.0 (section 1) | `$X/flow/ddd-{8,now}` |
| `setup-agentic-flow` (`fsd`) | `dev` 44, `review` 14, `explore` 10, `tech-writer` 4, `coordinator` 4 lines changed; the annotation vocabulary moves from `beadloom:domain=<layer>`, `feature=<slice>`, `component=<segment>` to `component=<slice-ref>`; the `processes` layer is dropped from the chain | MAJOR by row 2 (a generated file's meaning changed), or MINOR (Open question 5) | `diff $X/flow/fsd-8/.claude/agents/dev.md $X/flow/fsd-now/.claude/agents/dev.md` |
| Role templates between earlier releases | `git diff --stat v7.0.0 v8.0.0 -- src/beadloom/onboarding/templates/roles` is empty; `v8.0.0..290507b2` changes 8 files | — | precedent: this is the first release since the declaration whose upgrade drifts composed roles |

### 7. Python import paths (not public)

19 modules added, 43 modified, 0 removed or renamed under `src/beadloom/`
(`git diff --name-status -M v8.0.0 290507b2 -- 'src/beadloom/**/*.py'`). Runtime dependencies are
unchanged: the `pyproject.toml` diff touches only the mutation test selection list.

### 8. CHANGELOG `[Unreleased]` against the measurement

| Claim or gap | Measured | Evidence |
|---|---|---|
| Breaking: a `kind: site` node is judged as a `service`; `lint --strict` can exit 1 where it exited 0 (`CHANGELOG.md:18-25`) | holds: exit 0 → 1, `ci` 0 → 1 | section 1 |
| "the data file and `ctx --json` show the node's `kind` as `service`" (`:22-23`) | holds. `status --json` (`by_kind.site`), `export`, MCP `get_context` and the page path `other/` → `services/` move too and are not named | sections 3, 4, 6 |
| "nothing is removed or renamed" (`:13`) | contradicted: 42 scaffold files removed or renamed; one generated page renamed; `by_kind.site` absent | section 6 |
| "the data file stays schema 2" (`:13`) | holds | section 5 |
| "`kind: site` stays accepted" (`:14`) | holds: the reindex prints the `[info]` alias line | section 2 |
| `.mjs`/`.cjs`, tsconfig `paths`, React Native platform files under Added (`:162-187`) | each moves `lint --strict` 0 → 1 on an unedited project. 8.0.0 put the same class under Breaking (`:429-446`) | section 1 |
| `imports.aliases` refusals (`:174-176`) under Added | an `imports:` block that 8.0.0 accepted is refused (exit 0 → 1). 8.0.0 put the same class under Breaking (`:460-463`) | section 1 |
| `scope:`, `title:`, `tag_prefix:` under Added (`:47-55`, `:66-71`) | 8.0.0 ignored `scope:`, `title:` and `tag_prefix` beside `kind`, and the tree reads them: exit 1 → 0, 0 → 2, 1 → 0 | section 1 |
| Upgrading (`:27-33`) names reindex and a `kind: site` lint | omits re-running `setup-agentic-flow` (`config-check` exit 0 → 1), `lint --strict` after the new import readings, and `config-check` for an `imports:` block | section 1 |
| `init` writes nine rules (`:193-198`) | holds: 9 rules on `rn-fsd` | section 6 |
| `init` exits 1 when the code fails its rules (`:197-198`) | holds on `vue-fsd`; on the same tree 8.0.0 exited 0 | section 1 |
| `docs site` retires empty folders and the scaffold line gains the count (`:275-280`) | holds: `42 retired, 9 empty folders retired` | section 6 |
| `dashboard.data.json` keys carry no promise (`:109-110`) | agrees with the guide (`docs/guides/public-api.md:74-76`) | section 5 |
| Footer on upgrade (`:245-247`) | holds: `widgets/powered-by/*` written | section 6 |
| CI runs `npm run lint:fsd` (`:240-241`) | holds: `.github/workflows/ci.yml:356` | — |
| `architecture-layers` judges 425 of 434 (`:25`) | not re-measured: a figure of an earlier commit; `beadloom prime` on `9f96ae52` reports 461 of 470 | — |

## Version places

`beadloom version-surface` on `9f96ae52`: source of truth `src/beadloom/__init__.py:6`
(`8.0.0`). It reports 18 checked places in 10 files and 71 unchecked places in 19 files.

| Place | Instrument | Bump |
|---|---|---|
| `src/beadloom/__init__.py:6` | packaging-manifest | `9.0.0` |
| `.beadloom/_graph/beadloom.yml:5` (`(v8.0.0)`) | graph-summary-facts | `(v9.0.0)` |
| `.claude/CLAUDE.md:118` | doctor | `9.0.0` |
| `README.md:111`, `README.ru.md:111` (the Gate output "at the 8.0.0 release, on 8 October 2026", block `:113-138`) | docs-audit | the paragraph and the block rerun at release |
| `docs/getting-started.md:52` | docs-audit | `9.0.0` |
| `docs/guides/public-api.md:23,29,35,39,58,68,80` ("since 8.0.0 (MINOR, …)") | docs-audit | `:35` is history ("as it has since 8.0.0"); the other six say "since 8.0.0 (MINOR, …)" of additions 9.0.0 ships |
| `docs/services/cli.md:960` (`beadloom 8.0.0 asks`) | docs-audit | `9.0.0` |
| `tests/test_integration_v1.py:27,33` (asserts), `:17` (docstring, unchecked) | test-suite | `9.0.0` |
| `tests/self_check/process/test_the_release_harness_reports_what_ran.py:48,57` (asserts), `:34,52,68,123,128,163,168,229,241` (unchecked) | test-suite | `9.0.0` |
| `tests/release/verify_the_release.py:6,72` (`DEFAULT_RELEASE = "8.0.0"`) | unchecked | `9.0.0` |
| `.claude/development/ROADMAP.md:3` | unchecked | `9.0.0` |
| `docs/domains/doc-sync/features/docs-audit/SPEC.md:112-113` | unchecked (excluded SPEC) | examples of the current release: `9.0.0` |
| `docs/services/cli.md:959` | unchecked (attributed to `bd`) | `9.0.0` |
| History, not to bump: `CHANGELOG.md:276,314,361-520`; `docs/domains/application/features/site-generation/SPEC.md:225`; `tests/acceptance/application/site-generation/portal_scaffold.feature:76`; `tests/acceptance/steps/application/site-generation/test_portal_scaffold_steps.py:133,143`; `tests/unit/services/commands/test_the_scaffold_line_names_the_folders_it_retired.py:4`; `src/beadloom/site_scaffold/e2e/levels.spec.js:331` | — | none |
| `CONTRIBUTING.md:244-264` (*Public API*) | — | no version literal. It holds the six-item list and does not carry the guide's "added since" lines |

## The harness and the publish workflow

| Item | Measured | Evidence |
|---|---|---|
| `tests/release/verify_the_release.py` | unchanged since `v8.0.0` | `git diff --stat v8.0.0 290507b2 -- tests/release/` empty |
| What it checks | version (CLI, `__version__`, metadata, wheel name); `init` and `reindex` exit 0; activity levels from `ctx --json`; the shallow-history line; `docs site --out` writes `package.json`, `.vitepress/`, `e2e/`; `npm ci` + `npm run docs:build`; `--pages-workflow` | `tests/release/verify_the_release.py:16-34`, `:586-620` |
| FSD `init`, `imports.aliases`, Steiger, `lint:fsd`, `steiger.config.js`, `public/brand/*`, the footer, the `kind: site` alias | not checked: no `fsd`, `steiger`, `brand`, `favicon`, `logo` or `alias` in the file | `grep -n -i "fsd\|brand\|steiger\|favicon\|logo\|aliases" tests/release/verify_the_release.py` prints nothing |
| Install form | `uv pip install --refresh <artifact>` without the `languages` extra, so a TypeScript or Vue project would not be parsed | `tests/release/verify_the_release.py:702-712` |
| `public/brand/beadloom-icon.svg` and `steiger.config.js` in the built package | present in the wheel built from the tree; the three favicons are written by `docs site` | `$X/venvnow/lib/python3.12/site-packages/beadloom/site_scaffold/` |
| FSD fixtures in CI | `site-adopters (vue-fsd)`, `site-adopters (rn-fsd)` legs, not required checks | `CHANGELOG.md:215-223`, `.github/workflows/site-adopters.yml` |
| `.github/workflows/pypi-publish.yml` | unchanged: no diff and no commit in `v8.0.0..290507b2` | `git diff --stat` and `git log` over the file print nothing |

## Open questions for the owner

1. **Are the scaffold theme's internal paths "files generated for an adopter"?** Yes: the 42
   removals and renames (`entities/graph-edge` → `graph-edges`, `widgets/graph-viewer/lib/*`
   moved) are MAJOR by row 1 and belong under Breaking. No: the promise covers `docs site`'s
   entry files (`package.json`, the data files, the pages), and the guide should say so. The
   guide's item 6 names `docs site` without that distinction.
2. **Do the new import readings go under Breaking?** `.mjs` importers, tsconfig `paths` and
   platform files each move `lint --strict` from 0 to 1 on an unedited project, measured. 8.0.0
   listed the same class under Breaking. `[Unreleased]` lists them under Added. Either the
   Breaking section names them, or the guide records why this release treats them differently.
3. **Is a composed-role drift an exit-code change?** Role files composed by 8.0.0 make
   `config-check` and `ci` exit 1 on 9.0.0 until `setup-agentic-flow` runs. Classed as row 3, it
   is Breaking. Classed as an upgrade step, it belongs in *Upgrading*, which does not name it
   now. This is the first release since the declaration whose role templates changed.
4. **Is `init`'s auto-detection on an FSD tree a same-input change?** The `vue-fsd` tree gets
   preset `fsd` instead of `monolith`, exit 1 instead of 0, and 21 fewer document files. Read as
   the same input, it is MAJOR by rows 1 and 3. Read as a new preset's first output, it is MINOR.
5. **Does the `fsd` overlay's new annotation vocabulary change a generated file's meaning?**
   An adopter following the 8.0.0 `dev.md` writes `beadloom:feature=<slice>`, and the tree's
   says `beadloom:component=<slice-ref>`. Row 2 makes that MAJOR. The overlay was written for a
   graph `init` did not produce before this release, which argues for MINOR.
6. **The page of a `kind: site` node after an in-place upgrade:** `other/<ref>.md` stays beside
   `services/<ref>.md`. The choice is a fix before the release or a line under *Known
   limitations*.
7. **Is `landscape.data.json` part of "the portal data file"?** The guide names
   `architecture.data.json` and excludes `dashboard.data.json`, and says nothing of the
   landscape file. That file's `group` and `kind` move for a `kind: site` node.
8. **Configuration that 8.0.0 ignored and the tree reads.** These are an `imports:` block,
   `scope:` and `title:` on a `layers` rule, and `tag_prefix` beside `kind`. Each changes an
   exit code, measured. `docs/guides/public-api.md:45-47` says no accepted configuration is
   refused, and the measurement shows 8.0.0 accepted an `imports:` block by ignoring it. 8.0.0
   put the same class (`site:`, `activity:`) under Breaking.

None of the measurements contradicts the MAJOR verdict. Questions 1 to 5 and 8 each add a
candidate to *Breaking*.
