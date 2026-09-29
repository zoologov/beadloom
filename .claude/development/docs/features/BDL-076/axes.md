## Axes

> **Derived by:** `beadloom impact src/beadloom/application/site.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 name-defined-more-than-once, 1 node-owns-unread-files, 29 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 1 — `src/beadloom/onboarding/scanner/doc_classify.py:63` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:229` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | agentic-flow-setup | 2 — `src/beadloom/onboarding/agentic_flow_setup.py:236` | none | ? |  |
| callers | ai-techwriter-setup | 5 — `src/beadloom/onboarding/ai_techwriter_setup.py:68` | none | ? |  |
| callers | cli-commands | 1 — `src/beadloom/services/commands/docs.py:102` | none | ? |  |
| callers | role-adapters | 1 — `src/beadloom/onboarding/role_adapters.py:127` | none | ? |  |
| callers | tui | 16 — `src/beadloom/tui/app.py:69` | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | site-generation | `_count_kinds`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_compute_health`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_plural`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_top_level_diagram`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_lint_violation_refs`: 1 branch(es), 2 exit form(s) | none | ? |  |
| branches | site-generation | `_render_index`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_published_doc_slugs`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_render_about_page`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | site-generation | `_render_docs_overview`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_section_members`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_docs_section_sentence`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_extract_mermaid_blocks`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_guard_diagrams`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | site-generation | `_write`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | site-generation | `_to_int`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_to_float`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | site-generation | `_scalar_metrics`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `_record_metrics_point`: 1 branch(es), 0 exit form(s) | none | ? |  |
| branches | site-generation | `generate_site`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | site-generation | `__init__`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | agentic-flow-setup | `_scaffold_composed`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | agentic-flow-setup | `_scaffold_claude_md`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | ai-techwriter-setup | `_scaffold_github`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | ai-techwriter-setup | `_scaffold_gitlab`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | ai-techwriter-setup | `_scaffold_guide`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | ai-techwriter-setup | `_scaffold_recipe`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | ai-techwriter-setup | `_scaffold_provision_runner`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | role-adapters | `generate_adapters`: 0 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | cli-commands | `docs_site`: 1 branch(es), 1 exit form(s), from a caller's seat | none | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |
| branches | tui | `__init__`: 0 branch(es), 0 exit form(s), from a caller's seat | 4 — `src/beadloom/tui/styles/app.tcss` | ? |  |

Not derivable: the 22 committed files of node `vitepress-site` (source `site/`) and both site workflows — `beadloom impact` reads Python only; they are listed in Supplement A.

## Axes

> **Derived by:** `beadloom impact docs_site` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `flow_signature` (effect `serialises-yaml`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 33 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:37` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:229` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | doc-sync | 1 — `src/beadloom/doc_sync/surface.py:199` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:297` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | — | no site found | — | ? |  |
| branches | cli-commands | `docs`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `docs_generate`: 1 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `docs_polish`: 1 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `docs_site`: 1 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `docs_audit`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_scan_surface_json`: 0 branch(es), 4 exit form(s) | none | ? |  |
| branches | cli-commands | `_docs_audit_json`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `_format_tolerance`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_coverage_note`: 0 branch(es), 4 exit form(s) | none | ? |  |
| branches | cli-commands | `_print_coverage_summary`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `_print_attributed_versions`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_print_unjudged_versions`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_docs_audit_rich`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_echo_per_kind`: 0 branch(es), 0 exit form(s) | none | ? |  |
| branches | cli-commands | `docs_quality`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `epic_bead_statuses`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_bd_records`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `docs_spaces`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_spaces_json`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_spaces_rich`: 0 branch(es), 1 exit form(s) | none | ? |  |
| branches | cli-commands | `_rel`: 0 branch(es), 2 exit form(s) | none | ? |  |
| branches | cli-commands | `_rel_path`: 0 branch(es), 2 exit form(s) | none | ? |  |

Not derivable: `docs_site` writes no VitePress scaffold, and the non-Python files the command's output depends on are listed in Supplement A.

## Axes

> **Derived by:** `beadloom impact src/beadloom/application/architecture_view.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 2 name-defined-more-than-once, 1 no-seed, 1 node-owns-unread-files, 10 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | ai-techwriter | 1 — `src/beadloom/ai_agents/ai_techwriter/runner.py:110` | 2 — `src/beadloom/ai_agents/ai_techwriter/provision-runner.sh` | ? |  |
| callers | application | 3 — `src/beadloom/application/landscape_view.py:341` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site.py:430` | none | ? |  |
| branches | application | `_declared_layer_rule`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | application | `_declared_layers`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | application | `_declared_exemptions`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | application | `_layer_view`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_symbol_count`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_doc_status`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | application | `_doc_slug`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_served_doc_link`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_doc_links`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_arch_edges`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_parent_map`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_node_dict`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `build_architecture_view_data`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `serialize_architecture_view`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_as_list`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `render_architecture_view_md`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `layers`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `token`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | application | `rank`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `flagged`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | ai-techwriter | `_branch_name`: 1 branch(es), 3 exit form(s), over every call, from a caller's seat | 2 — `src/beadloom/ai_agents/ai_techwriter/provision-runner.sh` | ? |  |
| branches | application | `render_landscape_view_md`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `generate_site`: 3 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_federated_landscape`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `render_landscape_md`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |

Not derivable: the reader of `architecture.data.json` — `site/.vitepress/theme/composables/useArchitectureData.js:28` and `site/.vitepress/theme/components/ArchitectureMap.vue` — is JavaScript and is not a caller this command can see.

## Axes

> **Derived by:** `beadloom impact src/beadloom/application/site_pages.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 4 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | application | 3 — `src/beadloom/application/site_dashboard/recommendations.py:59` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site.py:430` | none | ? |  |
| branches | application | `load_nodes`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_kind_dir`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_node_link`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_load_kinds`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_load_edges_for`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_incoming_link`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | application | `_load_incoming_for`: 5 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_load_symbols`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_load_docs`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_scoped_diagram`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_edges_section`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_symbols_section`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_published_doc_link`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_docs_section`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_diagram_section`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `render_node_page`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `render_all_pages`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | site-generation | `generate_site`: 3 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_lint_recommendations`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_debt_recommendations`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_stale_doc_recommendations`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |

Not derivable: the Mermaid enhancer that renders the node page's `## Diagram` block — `site/.vitepress/theme/components/DiagramViewer.vue` — is JavaScript.

## Axes

> **Derived by:** `beadloom impact src/beadloom/application/landscape_view.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 4 name-defined-more-than-once, 1 no-seed, 5 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | application | 5 — `src/beadloom/application/architecture_view.py:557` | none | ? |  |
| callers | contracts | 3 — `src/beadloom/graph/contracts.py:325` | none | ? |  |
| callers | federation | 1 — `src/beadloom/graph/federation/export.py:46` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site.py:430` | none | ? |  |
| branches | application | `_health_class`: 0 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | application | `_local_contracts`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_legacy_contracts`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_edge_contract`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | application | `_routing`: 1 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | application | `_contract_dict`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_edges_from_contracts`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_worse`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_node_dicts`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `build_landscape_view_data`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `serialize_landscape_view`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `_as_list`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `render_landscape_view_md`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | application | `render_architecture_view_md`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | site-generation | `generate_site`: 3 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_federated_landscape`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_node_health`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_edge_lines`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `render_landscape_md`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | contracts | `reconcile_contracts`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | contracts | `edge_group_key`: 1 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | contracts | `_cross_landscape_keys`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | federation | `_export_edge`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |

Not derivable: the reader of `landscape.data.json` — `site/.vitepress/theme/composables/useLandscapeData.js:28` and `site/.vitepress/theme/components/LandscapeMap.vue` — is JavaScript.

## Axes

> **Derived by:** `beadloom impact src/beadloom/graph/c4.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 no-seed

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | ? |  |
| callers | application | 1 — `src/beadloom/application/site_pages.py:182` | none | ? |  |
| callers | cli-commands | 1 — `src/beadloom/services/commands/query.py:359` | none | ? |  |
| callers | site-generation | 1 — `src/beadloom/application/site.py:159` | none | ? |  |
| branches | c4-diagrams | `_compute_depths`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_depth_to_c4_level`: 0 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_load_nodes`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_load_edges`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_build_c4_node`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `map_to_c4`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_c4_element_name`: 0 branch(es), 3 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_mermaid_node_line`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_mermaid_grandchildren`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_mermaid_top_level_node`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_mermaid_orphan_boundaries`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `render_c4_mermaid`: 3 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_declared_node_ids`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_mermaid_rel_lines`: 2 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `filter_c4_nodes`: 4 branch(es), 4 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_filter_context`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_filter_container`: 0 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_filter_component`: 1 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_sanitize_id`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_node_macro`: 1 branch(es), 8 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_plantuml_top_level_node`: 2 branch(es), 2 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `_plantuml_orphan_boundaries`: 1 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | c4-diagrams | `render_c4_plantuml`: 4 branch(es), 1 exit form(s), over every call | none | ? |  |
| branches | site-generation | `_top_level_diagram`: 1 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | application | `_scoped_diagram`: 2 branch(es), 1 exit form(s), over every call, from a caller's seat | none | ? |  |
| branches | cli-commands | `graph`: 9 branch(es), 2 exit form(s), over every call, from a caller's seat | none | ? |  |

## Supplement A — non-Python files, by owning node

Distinct nodes per section above, counted from the tables: `site.py` 11, `docs_site` 7,
`architecture_view.py` 3, `site_pages.py` 2, `landscape_view.py` 4, `c4.py` 4. The node
`vitepress-site` appears in none of them.

**`vitepress-site`** (kind `site`, `source: site/`, `.beadloom/_graph/vitepress-site.yml:8-10`;
no document, by the `docs_absent` reason at `vitepress-site.yml:14-33`). Tracked files, line
counts measured with `wc -l`:

| File | Lines | Role |
|---|---|---|
| `site/package.json` | 27 | npm scripts `docs:dev`/`docs:build`/`docs:preview`/`dev-check` (lines 7-12); dependencies (13-21), devDependencies (22-26) |
| `site/package-lock.json` | — | lockfile read by `npm ci` |
| `site/.vitepress/config.mjs` | 56 | `withMermaid` shell, imports `config.generated.mjs` (21-28) |
| `site/.vitepress/theme/index.js` | 70 | registers every component (43-69); mounts `DiagramViewer` in `doc-footer-before` (38-42) |
| `site/.vitepress/theme/custom.css` | 77 | Mermaid pan/zoom frame and controls (`.bl-pz-*`) |
| `site/.vitepress/theme/architectureTheme.js` | 201 | Cytoscape palette, ELK options, lanes, edge legend, stylesheet |
| `site/.vitepress/theme/landscapeTheme.js` | 146 | same for the landscape map |
| `site/.vitepress/theme/components/ArchitectureMap.vue` | 590 | the architecture viewer |
| `site/.vitepress/theme/components/LandscapeMap.vue` | 496 | the landscape viewer |
| `site/.vitepress/theme/components/DiagramViewer.vue` | 268 | svg-pan-zoom enhancer for every Mermaid block (node-page mini-diagram) |
| `site/.vitepress/theme/composables/useArchitectureData.js` | 41 | fetches `/architecture.data.json` (28) |
| `site/.vitepress/theme/composables/useLandscapeData.js` | 41 | fetches `/landscape.data.json` (28) |
| `site/.vitepress/theme/composables/useDashboardData.js` | 41 | fetches `/dashboard.data.json` |
| `site/.vitepress/theme/composables/useEcharts.js` | 84 | ECharts registration for the dashboard |
| `site/.vitepress/theme/components/{AlertBanner,StatusCards,HealthGauges,CategoryChart,TrendCharts,Recommendations,AiTechwriterActivity}.vue` | 136/90/103/128/122/120/218 | dashboard widgets |
| `site/scripts/dev-optimize-check.mjs` | 28 | boots the VitePress dev server and closes it; referenced by no workflow and no test (grep over `.github/` and `tests/`) |

**No node owns these** (no `source:` in `.beadloom/_graph/*.yml` names `.github/`):

- `.github/workflows/deploy-site.yml` (86 lines): `uv sync --extra dev --extra languages` (48),
  `beadloom reindex` (51), `beadloom docs site --out site` (54), Node 22 (57-59), `npm ci` (62),
  `npm run docs:build` (66), upload `site/.vitepress/dist` (73-75), deploy (77-86). Triggers:
  push to `main` and `workflow_dispatch` (11-14).
- `.github/workflows/ci.yml:313-344`, job `site-build`: the same steps without the deploy; a
  prerequisite of `ai-techwriter` (`needs: [gate, tests, site-build]`, `ci.yml:353`).

**Documents**: `docs/domains/application/features/site-generation/SPEC.md` (site-generation),
`docs/domains/graph/features/c4-diagrams/SPEC.md` (c4-diagrams), and
`docs/guides/vitepress-site.md`, which is linked to no node (`vitepress-site.yml:20-24`).

**Generated, gitignored** (`.gitignore:39-57`): `site/*.md`, `site/domains/`, `site/features/`,
`site/services/`, `site/other/`, `site/docs/`, `site/ru/`, `site/public/`,
`site/.vitepress/config.generated.mjs`, `site/.vitepress/dist/`, `site/.vitepress/cache/`,
`site/node_modules/`.

**Python modules the generator uses, and the node the index assigns them to**: `site.py` →
`site-generation`; `architecture_view.py`, `site_pages.py`, `landscape_view.py` → `application`
(per the `impact` rows above, although each file carries `# beadloom:feature=site-generation`
at line 2); `site_landscape.py`, `site_nav.py`, `site_about.py`, `site_published.py`,
`site_mermaid_guard.py`, `site_metrics_history.py`, `site_dashboard/` are not in any section
above; `graph/c4.py` → `c4-diagrams`.

## Supplement B — facts for the RFC

**The graph library**

- Cytoscape.js `3.34.1` with `cytoscape-elk` `2.3.0` over `elkjs` `0.12.0`
  (`site/package.json:14,15,17`; locked at `site/package-lock.json:2067-2068`, `:2089-2090`,
  `:2686-2687`). `web-worker` is the only range, `^1.5.0` (`package.json:20`), locked `1.5.0`
  (`package-lock.json:3808-3809`).
- Loaded by dynamic import at `ArchitectureMap.vue:131-135`; instance created at `:140-146`.
- Layout: ELK `layered`, `DOWN`, orthogonal, `INCLUDE_CHILDREN`, partitioning on
  (`architectureTheme.js:52-68`); `partition` = `layer_rank` (`ArchitectureMap.vue:104`).
- Mermaid diagrams: `mermaid` `11.17.0`, `vitepress-plugin-mermaid` `2.0.17`, enhanced by
  `svg-pan-zoom` `3.6.2` (`package.json:23,25,18`).

**Pan, drag and selection**

- The Cytoscape constructor passes only `container`, `elements`, `style`, `layout`,
  `wheelSensitivity: 0.2` (`ArchitectureMap.vue:140-146`). No `autoungrabify`,
  `boxSelectionEnabled`, `userPanningEnabled`, or per-element `grabbable`/`pannable` is set.
- Cytoscape's defaults at the locked version: `userPanningEnabled: true`,
  `boxSelectionEnabled: true`, `autoungrabify: false`
  (`site/node_modules/cytoscape/dist/cytoscape.esm.mjs:19926-19929`), so every node, including
  a compound parent, is grabbable. Element-level `pannable` exists
  (`cytoscape.esm.mjs:13818`).
- Compound parents are drawn as boxes around their children with `padding: 12px`
  (`architectureTheme.js:118-130`); a domain or service box covers the area of its children, so a
  pointer-down inside the box and outside a child lands on the parent node.
- Selection: `tap` on a node calls `selectNode` (`ArchitectureMap.vue:147`), which sets both
  the card and the focus (`:156-162`); `tap` on the background clears both (`:148-152`,
  `:166-169`). There is no hover, no double-click and no keyboard handler.

**Filters and their state**

- Five Vue `ref`s local to the component: `kindFilter`, `domainFilter`, `layerFilter`,
  `onlyViolations`, `focusNode` (`ArchitectureMap.vue:46-50`); nothing is kept in the URL or
  in storage. Applied by `applyFilters` (`:184-218`) on `watch` (`:247`).
- Filtering adds the class `hidden` (`display: none`, `architectureTheme.js:196-199`) per node
  (`ArchitectureMap.vue:187-202`). Cytoscape treats a node as not visible when any ancestor does
  not take up space (`cytoscape.esm.mjs:13639-13650`, `:13705-13708`), so a filter that hides
  a compound parent hides its children: `Kind = feature` hides every domain and with it every
  feature placed inside one.
- The domain filter keeps the domain and its DIRECT children only (`n.parent !== domain`,
  `ArchitectureMap.vue:193-198`).
- Focus = `closedNeighborhood()` of the node (`:208`): depth 1, both directions, every drawn
  edge kind, no depth or direction control. Everything else gets `dimmed` (`:209`).
- The data composable holds `data`/`error` as module-level singletons with a `started` latch
  (`useArchitectureData.js:14-16,22-26`), one fetch of one URL per page load.
- Landscape filters: `protocolFilter`, `verdictFilter`, `hideHealthy`, `focusNode`
  (`LandscapeMap.vue:36-39`).

**Edge styling and edge kinds**

- Index edge kinds (measured on this repository's `.beadloom/beadloom.db`): `depends_on` 379,
  `part_of` 110, `touches_code` 106, `uses` 22, `consumes` 1, `produces` 1.
- The data file carries only `part_of`, `depends_on`, `uses` (`architecture_view.py:396-400`).
  The viewer draws only `depends_on` and `uses` (`ArchitectureMap.vue:118`). `part_of` is
  rendered as compound nesting (`:108`), yet the legend lists "part of (containment)" as a line
  style (`architectureTheme.js:85`).
- Styles: base edge width 1.8, triangle arrow, `curve-style: taxi` vertical
  (`architectureTheme.js:145-154`); `violation` red dashed (`:156-166`); `runtime` (`uses`)
  dotted with `vee` arrow (`:168-181`); `impact` for the focused node's edges (`:183-191`).
- Colours given as `var(--vp-…)` are rejected by Cytoscape: its colour parser accepts names,
  hex, rgb and hsl only (`cytoscape.esm.mjs:475-477`). Measured in a headless Cytoscape
  3.34.1: `line-color: var(--vp-c-text-3)` logs "The style property … is invalid" and the edge
  resolves to `rgb(153,153,153)`. The `var(...)` colour values are at
  `architectureTheme.js:103,110,138,148,149,176,177,186,187` and `landscapeTheme.js:93,100,109,128`.
  The `impact` recolour at `:186-187` is one of them.
- A `depends_on` edge carries `violation` only when both ends have a rank
  (`architecture_view.py:410-414`); the verdict is the layer rule's (`:148-150`).

**Node metadata: in the data file versus in the index**

- In the file, per node (`architecture_view.py:460-483`): `id`, `label` (= `ref_id`), `kind`,
  `summary`, `layer` (own tag), `layer_rank` (inherited), `group`, `symbols` (a count),
  `doc_status` (`fresh`/`stale`/`none`), `doc_links`, `url`, `parent`, `depends_on`,
  `depended_on_by`, `uses`, `used_by`, and `lint_clean` only when lint ran (`:482-483`).
  Top level: `schema_version: 1` (`:55`), `scope`, `nodes`, `edges` (`:540-545`).
- Lint is reduced to a boolean: `site.py:166-180` keeps only the set of `from_ref_id`; the rule
  name and message are dropped.
- In the index and absent from the file:
  - `source`: read at `architecture_view.py:519` and passed as a parameter at `:447` that
    `_node_dict` never uses.
  - `lifecycle`: the `nodes.lifecycle` column (all 110 nodes `active`, measured).
  - `nodes.extra` keys `activity`, `tests`, `tags`, `docs_absent` (measured, `json_each` over
    `nodes.extra`). `activity` is written by `_store_git_activity`
    (`application/reindex/enrichment.py:131`) and `tests` is rebuilt from the BDL-074 binding
    (`application/reindex/full.py:206`).
  - Bound test files: table `test_files(path, kind, ref_id, placement, test_count, …)`, with 287
    of 633 rows bound to a node (measured).
  - Per-pair doc freshness: `sync_state` (`doc_path`, `code_path`, `status` in
    `ok`/`stale`/`missing`/`unverified`, `synced_at`). The file carries one aggregate per node
    (`architecture_view.py:289-305`).
  - Public symbol names: the node page lists them (`site_pages.py:158-171`), and the file
    carries a count.
  - Per-node debt: `compute_top_offenders` (`application/debt_report/scoring.py:53`) and
    `NodeDebt` (`models.py:79`), which the dashboard uses and the viewer does not.
  - Edge kinds `touches_code`, `consumes`, `produces` (above).
- `url` is set only for kinds `domain`/`service`/`feature` (`site_landscape.py:228-246`, from
  `site_pages._KIND_DIR` at `site_pages.py:27-31`). In the index that is 62 of 110 nodes; the
  47 `component` nodes and 1 `site` node get a page under `other/` (`site_pages.py:71-73`) and
  no `url` in the card.
- The copy at `site/public/architecture.data.json` in this working tree is from an earlier
  generation: 84 nodes and 346 edges, against 110 nodes and 511 edges of those three kinds in
  the index (measured).

**Full-screen today**

- The architecture viewer calls `requestFullscreen` on `stage` (`ArchitectureMap.vue:222-239`),
  and falls back to the CSS class `bl-arch-fullscreen` (`:501-508`) when the API is missing or
  rejects. `stage` (`:331-402`) holds the canvas and the card only. The controls (`:274-312`)
  and the legend (`:314-329`) are siblings outside it, so they are not in the full-screen
  element.
- It re-fits after 60 ms (`:238`, `:244`).
- `LandscapeMap.vue` has no full-screen (no match for `fullscreen`).
- The Mermaid enhancer requests full screen on the `.mermaid` container
  (`DiagramViewer.vue:104-112`, `:162-176`), styled at `custom.css:33-40`.

**How a node page embeds the mini-diagram**

- `render_node_page` appends `## Diagram` with a fenced `mermaid` block (`site_pages.py:267-268`,
  `:297`). The block is a C4 component view scoped to the node, falling back to the container view
  (`site_pages.py:182-196`, via `graph/c4.py` `map_to_c4`/`filter_c4_nodes`/`render_c4_mermaid`).
- `vitepress-plugin-mermaid` renders it. `DiagramViewer` is mounted on every page
  (`index.js:38-42`) and wraps each `.mermaid` SVG in svg-pan-zoom (`DiagramViewer.vue:114-178`).
- Base-path rewriting covers `/services/`, `/domains/`, `/features/`, `/docs/`
  (`DiagramViewer.vue:26`) and does not cover `/other/`.
- Example: `site/features/ai-techwriter.md:79-83` (generated).

**How the architecture page embeds the viewer**

- `render_architecture_view_md` writes `<ClientOnly><ArchitectureMap /></ClientOnly>` plus a static
  count line (`architecture_view.py:585-592`). The page text hard-codes
  "service → application → domain → infra" (`:579`).
- `generate_site` writes `public/architecture.data.json`, `architecture.md`, and the Mermaid
  fallback `architecture-diagram.md` (`site.py:472-486`).
- The component takes no props: no initial focus, depth or filter can be passed from a page.

**Landscape**

- `landscape.md` mounts `<LandscapeMap />` in `<ClientOnly>` (`landscape_view.py:375-377`).
  The data is `public/landscape.data.json` (`site.py:524-535`), and the Mermaid fallback
  `landscape-diagram.md` comes from `site_landscape.py:376` (`render_landscape_md`), which
  takes `--federated` (`site.py:536-541`).
- `LandscapeMap.vue:120-126` constructs Cytoscape with the same five options as the
  architecture viewer.

**`c4-diagrams`**

- `.beadloom/_graph/c4-diagrams.yml:3-11`, source `src/beadloom/graph/c4.py` (662 lines).
- Consumers: `site.py:159-163` (top-level container diagram on `architecture-diagram.md`),
  `site_pages.py:182-196` (node pages), `services/commands/query.py:359` (`beadloom graph`).
- Bound test: `tests/integration/graph/c4/test_c4.py` (135 `def test_`).

**Generation for an adopter**

- `beadloom docs site` (`services/commands/docs.py:82-127`) requires
  `.beadloom/beadloom.db` (`:119-122`) and calls `generate_site` (`:126`). It writes content only:
  Markdown, `public/*.json`, and `.vitepress/config.generated.mjs` (`site.py:430-564`).
- No command writes `site/package.json`, `site/.vitepress/config.mjs` or the theme. None of
  them is in the wheel: `pyproject.toml:112-119` packages `src/beadloom` plus two
  `ai_techwriter` files, and no module under `src/beadloom` contains `withMermaid` or a
  `.vue` file. No command scaffolds `deploy-site.yml` (no match for `deploy-site` under
  `src/beadloom`).
- Measured in a temporary TypeScript project (3 `.ts` files, `package.json`, no Python), under
  the installed `beadloom 7.0.0` at `~/.local/bin/beadloom`:
  - `init --yes --mode bootstrap` gave 4 nodes, 3 edges and 0 symbols. The installed tool
    carries `tree_sitter_python` and no other grammar, so the 0 is a fact about that install,
    not about the `languages` extra.
  - `docs site` exited 0 and wrote 19 files, none of them `package.json`, `config.mjs` or a
    theme.
  - With this repository's scaffold copied in by hand and `node_modules` linked, `vitepress
    build` completed in 14.49 s on Node 18.20.8 (local). CI uses Node 22 (`deploy-site.yml:59`,
    `ci.yml:336`).
- Pins: all npm dependencies are exact except `web-worker` (`package.json:13-26`). There is no
  `engines` field. Node is pinned only in the workflows (major 22). VitePress is `1.6.4` and
  Vue is locked at `3.5.35` (`package-lock.json:3721-3722`, `:3777-3778`).

**Specific to this repository in the generated site**

- `site.py:86`: `_REPO_URL = "https://github.com/zoologov/beadloom"`, used to rebase README
  links on the About page (`:255`).
- `site/.vitepress/config.mjs`: `title: "Beadloom"` (31), description (32-33),
  `base: "/beadloom/"` (39), GitHub social link to `zoologov/beadloom` (48-51). The adopter
  build above rendered `<title>Architecture | Beadloom</title>`, `/beadloom/` asset paths, and
  the `github.com/zoologov/beadloom` link (measured in its `dist/`).
- The layer palette and lanes are keyed by four tokens, `service`, `application`, `domain`,
  `infra` (`architectureTheme.js:16-22`, `:72-77`). The legend always lists those four
  (`ArchitectureMap.vue:39`, `:319-323`). A project whose layer tags differ renders grey
  (`architecture_view.py:57-63`).
- The dashboard always mounts `<AiTechwriterActivity />` (`site_dashboard/assemble.py:118`),
  which reads `.beadloom/ai_techwriter_runs.json` (`site_dashboard/ai_activity.py:60`).
- `deploy-site.yml` targets `https://zoologov.github.io/beadloom/` (line 5) and exists only in
  this repository.

**Tests covering the site today** (`def test_` counts by `grep`; `ref_id` from `test_files`)

- Bound to `application`:
  - `tests/integration/application/test_architecture_view.py` (24)
  - `.../architecture_view/test_the_view_ranks_nodes_by_the_declared_layers.py` (9)
  - `.../test_the_view_flags_what_the_rule_finds.py` (6)
  - `.../test_site_landscape.py` (18)
  - `.../test_site_metrics_history.py` (16)
  - `.../test_site_nav.py` (36)
  - `tests/unit/application/test_site_about.py` (43)
  - `tests/unit/application/test_site_mermaid_guard.py` (15)
- Bound to `c4-diagrams`: `tests/integration/graph/c4/test_c4.py` (135).
- Bound to no node:
  - `tests/test_site_generator.py` (26)
  - `tests/test_site_dashboard.py` (54)
  - `tests/test_site_coverage_edges.py` (22)
  - `tests/test_site_published_docs.py` (13)
  - `tests/test_site_viz_data_guards.py` (10)
  - `tests/test_landscape_view.py` (13)
  - `tests/test_s4_decomposition.py` (6)
  - `tests/self_check/docs/test_site_viz_deps.py` (11)
  - `tests/self_check/docs/test_docs_vitepress_safe.py` (1)
  - `tests/self_check/config/test_ci_consolidated.py` (19)
- Acceptance: `tests/acceptance/application/site-generation/layer_view_verdict.feature` with
  steps at `tests/acceptance/steps/application/site-generation/test_layer_view_verdict_steps.py`.
- `beadloom ctx site-generation` reports 0 tests in 0 files bound to `site-generation`.
- No test executes the JavaScript. `test_site_viz_deps.py:44-177` reads the `.vue`/`.js`
  sources as text. The only JavaScript execution in CI is `npm run docs:build` in `site-build`
  and `deploy-site`, which proves a bundle is produced and nothing about interaction. No test
  covers the adopter path (no scaffold exists to test).
