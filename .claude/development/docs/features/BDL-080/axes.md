# Axes: BDL-080 (Explore output, 2026-10-08)

> Six `beadloom impact --section` runs; condensed to one row per node here, `In scope` ruled in RFC.md.
> The JavaScript side (`widgets/graph-viewer`, 43 files, one node) is not derivable by `beadloom impact` (Python only).

## Seed `architecture_view.py` / `_declared_layer_rule`, `source_url` (repository_link.py), `card_activity` (architecture_card.py)

| Axis | Node | Sites |
|---|---|---|
| co-writers | agent-prime, cli-commands, doc-generator, graph-layout, graph-loader, reindex | graph-file writers (`bootstrap.py:56`, `index_ops.py:243`, `doc_generator.py:29`, `graph_layout.py:185`, `loader.py:297`, `indexing.py:40`) |
| callers | ai-techwriter | `runner.py:110` (owns unread `provision-runner.sh`) |
| callers | scope-check, wave-plan | `scope_check.py:262`, `waves/scope.py:127` |
| callers | site-generation | `generate.py:514`; `architecture_card.py:128`; `architecture_view.py:516` |
| callers | cli-commands | `commands/docs.py:166` (`_warn_about_the_base`) |
| callers | reindex | `reindex/test_index.py:102` |
| branches | site-generation | `_declared_layer_rule`, `_declared_layers`, `_layer_view`, `_stratification`, `_node_dict`, `build_architecture_view_data`, `source_url`, `repository_of`, `card_fields`, `card_activity`, … |

## Seed `presets.py`, `rules_gen.py`

| Axis | Node | Sites |
|---|---|---|
| callers | agent-prime | `bootstrap.py:56`, `agents_md.py:215` |
| branches | onboarding | `detect_preset`, `classify_dir` (owns unread: 49 — `templates/agentic_flow/CLAUDE.md.txt`) |
| branches | agent-prime | `generate_rules`, `_detect_rule_type`, `_read_rules_data`, `bootstrap_project`, `prime_context` |

## Kind `site` — every reader

`.beadloom/_graph/vitepress-site.yml:15` (the only node); `graph/rules/types.py:21`, `loader.py:83` (`VALID_NODE_KINDS` has no `site`: a rule cannot match it); `application/site/node_pages.py:39,85` and `nav.py:28,64` (not in `_KIND_DIR` → `other/`, left out of nav); `architecture_view.py:529` (`group: other`); `landscape_view.py:326`; `onboarding/doc_generator.py:231-239,1127` (no skeleton); tests `test_site_landscape.py:68,362`, `test_the_sites_browser_tests_bind_to_the_site_node.py:7`.

## Readers of `layers` rules

loader `rules/loader.py:408-474`; lint `linter.py:271`, `evaluators.py:623`; `layer_reach.py`, `layer_crossings.py`, `layer_edges.py`, `layer_exemptions.py`, `layer_declaration.py`; index `reindex/rules_loader.py:99-123`; debt `debt_report/collect.py:330`; portal (`LIMIT 1`) `architecture_view.py:225,253`; prime `scanner/prime.py:39,56`; TUI `lint_panel.py:69,126`, `data_providers.py:182`; viewer `entities/layers/model/layers.js:65`, `GraphViewer.vue:133`, `modes.js:58`, `filterOptions.js:15`, `NodeCard.vue:39`; config-check: none; init: none.

## Owners of `widgets/graph-viewer/**`

43 files (`index.js`, `lib/` 23, `model/` 18, `ui/` 1), all `beadloom:component=site-graph-viewer` (`.beadloom/_graph/site-graph-viewer.yml`, `kind: component`, `tags: [fsd-widgets]`, `part_of vitepress-site`).
