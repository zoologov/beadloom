# BDL-083 — the derived axes, undecided

> **Status:** Draft
> **Created:** 2026-10-18

Eight targets of slices S1 and S2, derived by the Explore role on 2026-10-18 at `0f1cb9a3` and re-rendered here verbatim by the same command. The `In scope` column is decided in the RFC, row by row, by the node's role in the change.

## `src/beadloom/services/commands/docsync.py`


> **Derived by:** `beadloom impact src/beadloom/services/commands/docsync.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 name-defined-more-than-once, 50 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | application | 1 — `src/beadloom/application/gate_document_pairs.py:147` | none | ? |  |
| branches | cli-commands | `sync_check`: 4 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_pair_label`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_unverified_why`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | cli-commands | `_stale_remedies`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_build_sync_report`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_hook_type_check`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `install_hooks`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `pre_commit_hook_body`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_write_hook`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `_remove_hooks`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `_bd_statuses_from_list`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_bd_epic_prefixes`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_query_bd_beads`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_query_bd_statuses`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_jsonl_is_tracked`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_export_jsonl`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_restage_within_this_commit`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_repo_relative`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `active_sync`: 3 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_has_active_table`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_active_sync_check`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_rebased`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | cli-commands | `_emit_active_sync`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_echo_unresolved`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_echo_named_by_an_unresolved_row`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_echo_unlisted`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_echo_staging`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_grounded_pairs`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_report_attestation`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_mark_synced_noninteractive`: 4 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_report_left_stale`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_why_left`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | cli-commands | `_resolve_scope`: 1 branch(es), 3 exit form(s) | none | ? |  |
| branches | cli-commands | `_named_pairs`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_reject_unknown`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `sync_update`: 4 branch(es), 8 exit form(s) | none | ? |  |
| branches | cli-commands | `rebase`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | application | `_document_pair_summary`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |


## `src/beadloom/graph/rules/liveness.py`


> **Derived by:** `beadloom impact src/beadloom/graph/rules/liveness.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 1 node-owns-unread-files, 36 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | graph | 1 — `src/beadloom/graph/linter.py:233` | none | ? |  |
| callers | rule-engine | 1 — `src/beadloom/graph/rules/__init__.py:248` | none | ? |  |
| callers | site-generation | 2 — `src/beadloom/application/site/generate.py:130` | none | ? |  |
| callers | tui | 16 — `src/beadloom/tui/app.py:69` | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | rule-engine | `_matcher_reason`: 2 branch(es), 6 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_reasons_for_matchers`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_deny_reasons`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_require_reasons`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_cycle_reasons`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_forbid_edge_reasons`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_layer_reasons`: 2 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_cardinality_reasons`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_unregistered_reasons`: 2 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_module_coverage_reasons`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_scenario_coverage_reasons`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_doc_area_reasons`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_summary_facts_reasons`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_suite_rule_reasons`: 5 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `_reasons_for_rule`: 14 branch(es), 14 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `inert_rules`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `inert_rule_names`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `evaluate_rule_liveness`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `__init__`: 1 branch(es), 0 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `is_empty`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `tags`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `all_tags`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `matched`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `sources`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `edge_kind_count`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `live_edges_of_kinds`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | rule-engine | `indexed_modules_under`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | site-generation | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | graph | `_evaluate`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | rule-engine | `evaluate_all`: 34 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 1 branch(es), 0 exit form(s), over every call, from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |


## `src/beadloom/application/gate_ownership.py`


> **Derived by:** `beadloom impact src/beadloom/application/gate_ownership.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 name-defined-more-than-once, 8 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:180` | none | ? |  |
| callers | cli-commands | 2 — `src/beadloom/services/commands/federation.py:545` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site/raw_html.py:106` | none | ? |  |
| callers | version-surface | 1 — `src/beadloom/doc_sync/version_surface.py:248` | none | ? |  |
| branches | gate-ownership | `derive_gate_ownership`: 1 branch(es), 4 exit form(s) | none | ? |  |
| branches | gate-ownership | `_attribute`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | gate-ownership | `_owner_of`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | gate-ownership | `_node_of`: 0 branch(es), 4 exit form(s) | none | ? |  |
| branches | gate-ownership | `_located_paths`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | gate-ownership | `_documented_nodes`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | gate-ownership | `gate_ownership_lines`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | gate-ownership | `_unowned_lines`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | gate-ownership | `_claimed_clause`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | gate-ownership | `_unread_lines`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | gate-ownership | `owned`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | gate-ownership | `unowned`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | gate-ownership | `unattributed`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | gate-ownership | `none_owned`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | gate-ownership | `by_bead`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `run_ci_gate`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `_opening_tag`: 0 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | version-surface | `read_version_surface`: 0 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `_gate_ownership_lines`: 0 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `_gate_ownership_notices`: 0 branch(es), 3 exit form(s), from a caller's seat | none | ? |  |


## `src/beadloom/application/declared_scope.py`


> **Derived by:** `beadloom impact src/beadloom/application/declared_scope.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 6 name-defined-more-than-once, 20 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | agent-prime | 1 — `src/beadloom/onboarding/scanner/alias_scan.py:207` | none | ? |  |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:933` | none | ? |  |
| callers | cli-commands | 5 — `src/beadloom/services/commands/docsync.py:78` | none | ? |  |
| callers | document-pairs | 3 — `src/beadloom/doc_sync/document_pairs.py:410` | none | ? |  |
| callers | flow-guards | 1 — `src/beadloom/application/guards/evaluation.py:86` | none | ? |  |
| callers | flow-suppression | 1 — `src/beadloom/onboarding/flow_suppression.py:130` | none | ? |  |
| callers | git-activity | 1 — `src/beadloom/infrastructure/git_activity.py:196` | none | ? |  |
| callers | graph-diff | 1 — `src/beadloom/graph/diff.py:510` | none | ? |  |
| callers | graph-loader | 2 — `src/beadloom/graph/loader.py:154` | none | ? |  |
| callers | review-brief | 1 — `src/beadloom/application/review_brief/reachability.py:222` | none | ? |  |
| callers | rule-engine | 3 — `src/beadloom/graph/rules/scenario_coverage.py:66` | none | ? |  |
| branches | declared-scope | `trunk_ref`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | declared-scope | `work_item_of_branch`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | declared-scope | `scope_of_branch`: 1 branch(es), 5 exit form(s) | none | ? |  |
| branches | declared-scope | `scope_check`: 1 branch(es), 3 exit form(s) | none | ? |  |
| branches | declared-scope | `_key`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | declared-scope | `_node_contexts`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | declared-scope | `_target_nodes`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | declared-scope | `work_item_axes`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | declared-scope | `_section_of`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | declared-scope | `_undecided`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | declared-scope | `_unattributed`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | declared-scope | `checked`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | declared-scope | `describe`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_scope_check`: 1 branch(es), 3 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-guards | `evaluate_guard`: 1 branch(es), 7 exit form(s), from a caller's seat | none | ? |  |
| branches | review-brief | `work_item_documents_channel`: 0 branch(es), 5 exit form(s), from a caller's seat | none | ? |  |
| branches | document-pairs | `_row_count_findings`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | document-pairs | `_kind_findings`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | document-pairs | `_unpaired`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | graph-diff | `_render_duplicates`: 0 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | graph-loader | `load_graph`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | graph-loader | `describe`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | graph-loader | `describe`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | rule-engine | `_matcher_description`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | rule-engine | `_node_leg`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | rule-engine | `_dead_reason`: 0 branch(es), 5 exit form(s), from a caller's seat | none | ? |  |
| branches | git-activity | `activity_history_note`: 0 branch(es), 3 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-suppression | `render_suppression_notice`: 0 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `_object_entries`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `sync_check`: 4 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `_surface_lines`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `scope_check`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `_emit_filter`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `waves`: 1 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |


## `src/beadloom/application/gate.py`


> **Derived by:** `beadloom impact src/beadloom/application/gate.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 11 dynamic-dispatch, 4 name-defined-more-than-once, 75 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/jvm_layout.py:411` | none | ? |  |
| callers | axes-section | 1 — `src/beadloom/doc_sync/axes_section.py:247` | none | ? |  |
| callers | cli-commands | 3 — `src/beadloom/services/commands/federation.py:418` | none | ? |  |
| callers | flow-guards | 4 — `src/beadloom/application/guards/checks/bead_claimed.py:48` | none | ? |  |
| callers | mcp-server | 1 — `src/beadloom/services/mcp_server.py:889` | none | ? |  |
| callers | wave-plan | 1 — `src/beadloom/application/waves/media_checks.py:240` | none | ? |  |
| branches | ci-gate | `_run_doctor_checks`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_run_audit`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `run_ci_gate`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_reindex`: 1 branch(es), 3 exit form(s) | none | ? |  |
| branches | ci-gate | `lint_step`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_sync_check`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_sync_shape_finding`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_sync_summary`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_excused_clause`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_docs_audit`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_audit_summary`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_docs_quality`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_convention_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_issue_numbers`: 0 branch(es), 5 exit form(s) | none | ? |  |
| branches | ci-gate | `_issue_number_summary`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_issue_number_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_doc_spaces`: 1 branch(es), 3 exit form(s) | none | ? |  |
| branches | ci-gate | `_named`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_doc_space_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_doc_quality_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_scope_check`: 1 branch(es), 3 exit form(s) | none | ? |  |
| branches | ci-gate | `_scope_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_config_check`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_doctor`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_doctor_summary`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_federate`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | ci-gate | `_simple_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_sync_finding`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_pair_clause`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_sync_unverified_finding`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | ci-gate | `_surface_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_audit_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_config_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_site_config_findings`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_activity_setting_findings`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_import_alias_findings`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_config_block_findings`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_mutation_scope_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_doctor_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `_gate_failure_finding`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `ok`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | ci-gate | `findings`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | flow-guards | `check_bead_claimed`: 1 branch(es), 3 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-guards | `check_working_branch`: 1 branch(es), 3 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-guards | `_could_not_run`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-guards | `_error_verdict`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | wave-plan | `_graph_drift_detail`: 2 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | axes-section | `_row`: 1 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `_root_module_clusters`: 2 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `_module_cluster`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `ci`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `_lines`: 1 branch(es), 5 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `_verdict_on_the_generated_graph`: 2 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | mcp-server | `handle_complete_bead`: 2 branch(es), 4 exit form(s), from a caller's seat | none | ? |  |


## `src/beadloom/services/commands/issue_number.py`


> **Derived by:** `beadloom impact src/beadloom/services/commands/issue_number.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 4 name-defined-more-than-once, 7 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | agent-prime | 2 — `src/beadloom/onboarding/scanner/jvm_layout.py:411` | none | ? |  |
| callers | axes-section | 1 — `src/beadloom/doc_sync/axes_section.py:247` | none | ? |  |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:775` | none | ? |  |
| callers | cli-commands | 5 — `src/beadloom/services/commands/clean_room.py:315` | none | ? |  |
| callers | flow-guards | 3 — `src/beadloom/application/guards/evaluation.py:86` | none | ? |  |
| callers | site-generation | 7 — `src/beadloom/application/site/markdown_positions.py:266` | none | ? |  |
| callers | wave-plan | 1 — `src/beadloom/application/waves/media_checks.py:240` | none | ? |  |
| branches | cli-commands | `issue_number`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `allocate`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_refuse`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `check`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_exit_code`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_payload`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_named`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_refused_lines`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_refusal_lines`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_undetermined_lines`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_lines`: 1 branch(es), 5 exit form(s) | none | ? |  |
| branches | ci-gate | `_step_doc_spaces`: 1 branch(es), 3 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-guards | `evaluate_guard`: 1 branch(es), 7 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-guards | `_could_not_run`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | flow-guards | `_error_verdict`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `_locate_lines`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `_locate_html_block`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `_locate_definition`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `_code_block`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `_definition`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `_checked`: 1 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | site-generation | `read`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | wave-plan | `_graph_drift_detail`: 2 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | axes-section | `_row`: 1 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `_root_module_clusters`: 2 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | agent-prime | `_module_cluster`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `_finish`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `mutation`: 1 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `rooms`: 0 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `typed_surface`: 1 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `version_surface`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |


## `src/beadloom/application/rooms.py`


> **Derived by:** `beadloom impact src/beadloom/application/rooms.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 1 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | ci-gate | 1 — `src/beadloom/application/gate.py:180` | none | ? |  |
| callers | cli-commands | 4 — `src/beadloom/services/commands/federation.py:499` | none | ? |  |
| callers | gate-coverage | 1 — `src/beadloom/application/gate_coverage.py:225` | none | ? |  |
| callers | mcp-server | 1 — `src/beadloom/services/mcp_server.py:836` | none | ? |  |
| callers | mutation-scope | 1 — `src/beadloom/application/mutation_scope/score.py:125` | none | ? |  |
| callers | source-derivation | 2 — `src/beadloom/application/source_derivation/call_graph.py:95` | none | ? |  |
| callers | wave-plan | 2 — `src/beadloom/application/waves/clean_room.py:309` | none | ? |  |
| branches | verdict-room | `codec_in_force`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `requested_locale_name`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `codec_of_locale_name`: 1 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `locale_dimensions`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `current_room`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `room_line`: 4 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_locale_clause`: 0 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `derive_declared_rooms`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_read_packaging`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_floor_clause`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `project_distribution`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `canonical_distribution`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_installed_distributions`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_distributions`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_find_distribution`: 2 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_declared_requirements`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_record_requirement`: 7 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_closure`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `extras_satisfied_by`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `installed_extras`: 6 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_leg_extras`: 4 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `typed_extras_of_job`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `declared_extra_names`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `leg_installs`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_extras_of_command`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_uv_sync_extras`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_pip_project_extras`: 2 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_read_workflows`: 3 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `load_jobs`: 1 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_rooms_of_job`: 3 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_runs_on_of`: 3 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_matrix_os_key`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_matrix_of`: 3 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_canonical`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_combinations`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_resolve_runs_on`: 3 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `take_census`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_room_with_extras`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_compare`: 11 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_no_codec_note`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_locale_difference`: 2 branch(es), 5 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_extras_difference`: 3 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `_platform_of`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `label`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `label`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `entered`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | verdict-room | `not_entered`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | ci-gate | `run_ci_gate`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | gate-coverage | `_read_pipeline`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | mutation-scope | `describe_room`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | source-derivation | `names_that_reach`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | source-derivation | `names_reached_from`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | wave-plan | `build_room`: 3 branch(es), 4 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | wave-plan | `extras_a_room_installs`: 4 branch(es), 3 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `_gate_room_lines`: 3 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `_format_gate_github`: 3 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `rooms`: 2 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `_human`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | mcp-server | `_verdict_room`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |


## `src/beadloom/application/waves/clean_room.py`


> **Derived by:** `beadloom impact src/beadloom/application/waves/clean_room.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 1 dynamic-dispatch, 6 name-defined-more-than-once, 9 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:65` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:249` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:323` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | application | 1 — `src/beadloom/application/import_aliases.py:106` | none | ? |  |
| callers | cli-commands | 2 — `src/beadloom/services/commands/clean_room.py:233` | none | ? |  |
| callers | flow-guards | 1 — `src/beadloom/application/guards/invocation.py:282` | none | ? |  |
| callers | graph | 3 — `src/beadloom/graph/go_modules.py:128` | none | ? |  |
| callers | role-map | 2 — `src/beadloom/onboarding/role_map.py:350` | none | ? |  |
| branches | wave-plan | `room_path`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | wave-plan | `room_owner`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | wave-plan | `room_request`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | wave-plan | `_record`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | wave-plan | `_names`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | wave-plan | `room_invocation`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | wave-plan | `_interpreter`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | wave-plan | `build_room`: 1 branch(es), 4 exit form(s) | none | ? |  |
| branches | wave-plan | `_remembering`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | wave-plan | `_environment`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | wave-plan | `_refuse_the_room`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | wave-plan | `_refuse_the_request`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | wave-plan | `_refuse_carried`: 0 branch(es), 4 exit form(s) | none | ? |  |
| branches | wave-plan | `_occupied`: 0 branch(es), 3 exit form(s) | none | ? |  |
| branches | wave-plan | `_refused`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | wave-plan | `_head_commit`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | wave-plan | `_archive_head`: 1 branch(es), 0 exit form(s) | none | ? |  |
| branches | wave-plan | `_within`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | wave-plan | `_carry`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | wave-plan | `_write_marker`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | flow-guards | `run_invocation`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | application | `_entry`: 0 branch(es), 4 exit form(s), from a caller's seat | none | ? |  |
| branches | graph | `_local_replacements`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | graph | `_workspaces`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | graph | `_directory`: 0 branch(es), 4 exit form(s), from a caller's seat | none | ? |  |
| branches | role-map | `_designations`: 0 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | role-map | `_inferred_rosters`: 0 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `clean_room`: 1 branch(es), 0 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `waves`: 1 branch(es), 2 exit form(s), from a caller's seat | none | ? |  |


