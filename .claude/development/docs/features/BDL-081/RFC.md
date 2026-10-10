# RFC: BDL-081 — Release 9.0.0: the portal is a service, the viewer serves Feature-Sliced frontends

> **Status:** Approved
> **Created:** 2026-10-10

---

## Summary

A release by BDL-079's recipe: the bump in every place `version-surface` names, the `[9.0.0]`
change log with Breaking first and complete by the measurement, the documentation read against
the release, one product fix (the leftover `other/` page on upgrade), the harness extended to the
new surfaces and run on the downloaded wheel, publish, verify, close-out. The measured diff and
the version places are in `axes.md` (Explore, 2026-10-10); this document carries the decisions.

## Axes

> **Derived by:** `beadloom impact src/beadloom/__init__.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 no-seed, 1 node-owns-unread-files

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | — | no site found | — | no | blast radius: a reader of the version constant; the bump changes its input, not its code |

## Axes

> **Derived by:** `beadloom impact get_actual_version` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 dynamic-dispatch, 1 no-seed, 9 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:94` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | cli-commands | 1 — `src/beadloom/services/commands/index_ops.py:148` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | site-generation | 1 — `src/beadloom/application/site/dashboard/gate_metrics.py:109` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| branches | doctor | `_check_empty_summaries`: 2 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_unlinked_docs`: 2 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_docs_absent_reason`: 1 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_nodes_without_docs`: 6 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_isolated_nodes`: 2 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_symbol_drift`: 4 branch(es), 4 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_stale_sync`: 2 branch(es), 3 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_source_coverage`: 2 branch(es), 4 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_extract_version_claim`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_extract_package_claims`: 2 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `get_actual_version`: 1 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_get_actual_cli_commands`: 1 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_get_actual_mcp_tool_count`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_agent_instructions`: 18 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_stack_claim`: 3 branch(es), 4 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_check_test_framework_claim`: 3 branch(es), 4 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `_declared_stack`: 1 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | doctor | `run_checks`: 2 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | ci-gate | `_run_doctor_checks`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | site-generation | `_doctor_metrics`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | cli-commands | `doctor`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |

## Axes

> **Derived by:** `beadloom impact _beadloom_version` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 name-defined-more-than-once, 35 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:247` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/init_flow.py:47` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | graph | 1 — `src/beadloom/graph/linter.py:151` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | reindex | 1 — `src/beadloom/application/reindex/incremental.py:65` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| branches | reindex | `_beadloom_version`: 0 branch(es), 1 exit form(s) | none | no | a branch of a reader; nothing a release edits |
| branches | reindex | `_drop_all_tables`: 0 branch(es), 0 exit form(s) | none | no | a branch of a reader; nothing a release edits |
| branches | reindex | `reindex`: 3 branch(es), 1 exit form(s) | none | no | a branch of a reader; nothing a release edits |
| branches | reindex | `incremental_reindex`: 7 branch(es), 2 exit form(s), from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | graph | `lint`: 3 branch(es), 3 exit form(s), from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | agent-prime | `non_interactive_init`: 3 branch(es), 1 exit form(s), from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | agent-prime | `interactive_init`: 5 branch(es), 1 exit form(s), from a caller's seat | none | no | a branch of a reader; nothing a release edits |

## Axes

> **Derived by:** `beadloom impact read_version_surface` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 4 name-defined-more-than-once, 1 no-seed, 3 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | cli-commands | 1 — `src/beadloom/services/commands/version_surface.py:90` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | doc-sync | 3 — `src/beadloom/doc_sync/version_subjects.py:219` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | flow-suppression | 2 — `src/beadloom/onboarding/flow_suppression.py:168` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | gate-ownership | 1 — `src/beadloom/application/gate_ownership.py:175` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | rule-engine | 4 — `src/beadloom/graph/rules/doc_area.py:359` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | site-generation | 1 — `src/beadloom/application/site/raw_html.py:106` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| branches | version-surface | `read_version_surface`: 2 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_section`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_read_source_of_truth`: 4 branch(es), 9 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_each_file`: 3 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_normalise`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_sweep`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_lines_stating`: 2 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_attribute`: 3 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_build_instruments`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_packaging_holder`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_docs_audit_holder`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_graph_holder`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_rule_declaration`: 2 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_summary_lines`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_doctor_holder`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_flow_written`: 1 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_regions_of`: 3 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_test_suite_holder`: 2 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_declared_testpaths`: 1 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_assert_lines`: 2 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `unchecked`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `instrument`: 0 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `applies`: 0 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `covers`: 0 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `covers`: 0 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `covers`: 0 branch(es), 5 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `covers`: 0 branch(es), 3 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `covers`: 0 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `applies`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `covers`: 0 branch(es), 3 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | version-surface | `_under_testpaths`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | gate-ownership | `derive_gate_ownership`: 3 branch(es), 4 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | site-generation | `_opening_tag`: 4 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | doc-sync | `_project_names`: 5 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | doc-sync | `_configured_subjects`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | doc-sync | `_requirement_name`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `_area_votes`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `_read`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `area_of`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `layer_exemption_index_for`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | flow-suppression | `composed_headings`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | flow-suppression | `suppresses_nothing`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | cli-commands | `version_surface`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |

## Axes

> **Derived by:** `beadloom impact _parse_version` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 13 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:108` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | cli-commands | 2 — `src/beadloom/services/commands/docs.py:276` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | flow-guards | 3 — `src/beadloom/application/guards/config.py:217` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | mcp-server | 1 — `src/beadloom/services/mcp_server.py:695` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | rule-engine | 10 — `src/beadloom/graph/rules/evaluators.py:187` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| callers | test-mapping | 2 — `src/beadloom/context_oracle/test_binding.py:357` | none | no | blast radius: a reader of the version constant; the bump changes its input, not its code |
| branches | docs-audit | `_unreadable_table`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_foreign_surface_reason`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `parse_fail_condition`: 4 branch(es), 4 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `metric_value`: 0 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `fail_condition_triggered`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `compare_facts`: 6 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_values_match_with_tolerance`: 2 branch(es), 5 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_load_tolerances_from_config`: 3 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_load_ignore_from_config`: 3 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `run_audit`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `verified_facts`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `unverified_facts`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `matches`: 1 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `collect_set`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `collect`: 1 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_version`: 2 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_parse_version`: 10 branch(es), 5 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_db_counts`: 1 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_language_count`: 2 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_test_count`: 3 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_nodes_with_framework`: 3 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_rule_type_count`: 1 branch(es), 0 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_mcp_tool_count`: 2 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_cli_command_count`: 3 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_count_click_commands`: 2 branch(es), 2 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | docs-audit | `_collect_extra_facts`: 4 branch(es), 1 exit form(s), over every call | none | no | a branch of a reader; nothing a release edits |
| branches | ci-gate | `_run_audit`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | flow-guards | `exclusion_for`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | flow-guards | `excluded_everywhere`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | flow-guards | `dead_exclusions`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | test-mapping | `union_over_descendants`: 2 branch(es), 3 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | test-mapping | `collect`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `_first_matching_source`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `evaluate_require_rules`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `evaluate_forbid_edge_rules`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `evaluate_cardinality_rules`: 9 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `evaluate_unregistered_feature_candidate_rules`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `matched`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `_matched_nodes`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `collect_claims`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | rule-engine | `_facts_for`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | cli-commands | `docs_audit`: 7 branch(es), 1 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | cli-commands | `_docs_audit_json`: 2 branch(es), 0 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |
| branches | mcp-server | `_active_rules_for_node`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | no | a branch of a reader; nothing a release edits |

Not derivable: the four reader targets are `get_actual_version` (`src/beadloom/application/doctor.py:365`), `_beadloom_version` (`src/beadloom/application/reindex/full.py:68`), `read_version_surface` (`src/beadloom/doc_sync/version_surface.py:248`) and `_parse_version` (`src/beadloom/doc_sync/audit.py:768`), chosen from `grep __version__` because the BDL-079 RFC (`.claude/development/docs/features/BDL-079/RFC.md:65`) names no reader and its saved runs are not on disk; the places that state the version are documents, which `beadloom impact` does not read (they are listed under `## Version places`); the five sections name 19 distinct nodes (`ci-gate`, `cli-commands`, `site-generation`, `doctor`, `agent-prime`, `doc-generator`, `doc-sync`, `graph-layout`, `graph-loader`, `reindex`, `graph`, `version-surface`, `flow-suppression`, `gate-ownership`, `rule-engine`, `flow-guards`, `mcp-server`, `test-mapping`, `docs-audit`), and `beadloom lint` on `9f96ae52` reports no size finding and no boundary crossing on any of them.

Ruled in by the owner's goals rather than by a derived row: `doc-sync` (the version surface,
`docs audit`, the README pair), `cli-commands` (the root node's summary, `--version`, the
composed CLAUDE.md through `setup-agentic-flow`), `site-generation` (the leftover page on
upgrade, D4), `vitepress-site` (the scaffold the harness checks), the release harness under
`tests/release/` (bound to no node; `test-mapping` reads it). The derivation reaches no code
because a release changes a constant and documents; the readers surface as callers and are not
edited.

## The measured diff, v8.0.0 → main (290507b2)

The per-surface tables are in `axes.md` sections 1–8 (commands and exit codes; `config.yml`
keys; JSON outputs; MCP tools; the portal data files; generated files; Python paths; the change
log against the measurement). Under the PRD's rulings (owner, 2026-10-10) the Breaking section
of `[9.0.0]` names, in this order:

1. A `kind: site` node is read as `service`: `lint --strict` and `ci` exit 0 → 1 on an unedited
   project with such a node; `ctx --json`, `status --json` (`by_kind.site` is gone), `export`,
   the data file, `landscape.data.json` and MCP `get_context` say `service`; the node's page
   moves from `other/` to `services/`.
2. The new import readings — `.mjs/.cjs` importers, tsconfig `paths`/`baseUrl`, React Native
   platform files — resolve imports 8.0.0 dropped, so `lint --strict` can exit 1 on an unedited
   JavaScript project (ruling 2).
3. Role files composed by 8.0.0 drift against 9.0.0's templates (the `cohesion` duty): `config-check`
   and `ci` exit 0 → 1 until `setup-agentic-flow` runs (ruling 3).
4. `init` detects the `fsd` preset on a tree 8.0.0 read as `monolith`: a different graph, nine
   rules, exit 1 when the code fails them, 21 fewer document skeletons (ruling 4).
5. Configuration 8.0.0 ignored is read or refused: an `imports:` block (refused when unusable),
   `scope:` and `title:` on a `layers` rule, `tag_prefix` beside `kind` (ruling 8).

Changed, not Breaking: the scaffold theme's 42 renamed or moved files (ruling 1: the promise
covers `docs site`'s entry files — `package.json`, the data files, the pages — and the guide's
item 6 says so), the `fsd` overlay's annotation vocabulary `feature=` → `component=` (ruling 5).
Undeclared, named in the guide beside `dashboard.data.json`: `landscape.data.json` (ruling 7).

## Decisions

### D1 — the bump and the change log (R1)

`src/beadloom/__init__.py` → `9.0.0`; `setup-agentic-flow` recomposes CLAUDE.md; the graph
summary `(v9.0.0)`; `docs/getting-started.md:52`; `docs/services/cli.md:959-960`; the public-API
guide's seven "since 8.0.0" lines → "since 9.0.0" where they describe this release (`:35` is
history and stays); `tests/test_integration_v1.py:27,33`,
`tests/self_check/process/test_the_release_harness_reports_what_ran.py` asserts and docstrings,
`tests/release/verify_the_release.py` `DEFAULT_RELEASE`; `ROADMAP.md:3`; the docs-audit SPEC's
examples. `CHANGELOG.md`: `[Unreleased]` becomes `[9.0.0] - <date>` with the sections in this
order: Breaking (the five above), Upgrading (`beadloom reindex`; `lint --strict` and read the
`kind: site` and the JavaScript findings; `beadloom setup-agentic-flow` for composed roles;
`beadloom config-check` for an `imports:` block; `docs site` over an 8.0.0 portal retires the
old files and the leftover page), Added, Changed, Fixed, Known limitations (CommonJS; the
`origin`-only stand-in; the Steiger rule off). The false line "nothing is removed or renamed" is
replaced by the measured counts.

### D2 — the documentation read (D1 bead)

`docs/guides/public-api.md`: item 6 states what "files generated for an adopter" covers (entry
files, not the theme's internal paths); items 3 and 5 name `landscape.data.json` as undeclared;
the sentence at `:45-47` becomes "a key 8.0.0 ignored silently may be read or refused by the
next MAJOR, and was"; the "since" lines. `CONTRIBUTING.md` *Public API* unchanged unless the
list changes. The README pair's Gate paragraph (`:111-138`) rerun at the release. Every
surface-drift reference document read, not re-baselined blind (BDL-079's rule).

### D3 — the harness (V1)

`tests/release/verify_the_release.py`: installs with the `languages` extra; adds checks that
fail on 8.0.0 and pass on 9.0.0 — `init` on a synthetic FSD tree writes the nine rules and
`lint --strict` judges a planted cross-import; `steiger.config.js` and `lint:fsd` written by
`docs site`; `public/brand/beadloom-icon.svg` and the favicons in the built portal; the footer
widget present; a `kind: site` node read as `service` in `ctx --json`; the exit-code vocabulary
0/2/3/4 kept; its report names what it ran. `DEFAULT_RELEASE = "9.0.0"`.

### D4 — the leftover page on upgrade (R2)

`docs site` over a portal written by 8.0.0 retires `other/<ref>.md` when the same node's page
is now written under `services/` (the retire step that already handles moved scaffold files
covers the node pages' old section); the scaffold line counts it; a case with an 8.0.0 portal
fixture. Measured today: `67 written, 51 updated, 91 unchanged, 42 retired, 9 empty folders
retired` and the old page left behind.

### D5 — the release itself (P)

PR from `features/BDL-081` on green CI (read the advisory legs); squash; `gh release create
v9.0.0 --target main --title v9.0.0 --notes-file`; watch `pypi-publish.yml`;
`UV_NO_CACHE=1 python3 tests/release/verify_the_release.py beadloom==9.0.0 --release 9.0.0
--node-bin … --record-json …` on the downloaded wheel (expect CDN lag ~3 min); the published
portal shows the brand and the site as a service; ROADMAP's version line; close-out by the
template.

## Public API

Nothing new is declared by this release beyond what BDL-080 added and the guide already lists;
the guide's wording changes (D2) narrow what item 6 promises and name two undeclared files.
