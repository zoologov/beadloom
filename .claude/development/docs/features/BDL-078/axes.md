# Axes: BDL-078 (Explore output, 2026-10-04)

> Output of the explore role (step 0.5), six `beadloom impact --section` runs. Branch rows are
> condensed to one line per node here (the full per-function lists are in the session's explore
> report); co-writer and caller rows are kept as derived. `In scope` is ruled in RFC.md.

## Seed `resolve_import_to_node` and `reindex_file_imports` (nh7h, jcng)

> **Derived by:** `beadloom impact resolve_import_to_node` / `reindex_file_imports` over `src/beadloom` (identical rows)
> **Seed:** none — no name the target reaches performs a declared effect under `reaches-an-effect-sink`; every axis is unresolved, not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 13 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no sink reached | — | ? |  |
| callers | agent-prime | 1 — `src/beadloom/onboarding/scanner/import_scan.py:82` | none | ? |  |
| callers | reindex | 4 — `src/beadloom/application/reindex/full.py:80` | none | ? |  |
| callers | site-generation | 2 — `src/beadloom/application/site/scaffold.py:210` | none | ? |  |
| branches | import-resolver | 45 functions of `graph/import_resolver.py` (`resolve_import_to_node`, `_find_node_for_file`, `resolve_go_import`, `resolve_swift_import`, `resolve_jvm_import`, `reindex_file_imports`, …) | none | ? |  |
| branches | reindex | `reindex`, `_refresh_imports`, `_memoised_resolver`, `resolve`, from a caller's seat | none | ? |  |
| branches | site-generation | `_walk`, `shipped_files`, from a caller's seat | none | ? |  |
| branches | agent-prime | `_quick_import_scan`, from a caller's seat | none | ? |  |

Not derivable: the input that makes `src/beadloom/tui/app.py:17` resolve to `graph-reads` here and to `application` in a fresh tree (Strategy 1 reads `code_symbols`, `file_index` at `graph/import_resolver.py:962-966`); the incremental caller `application/reindex/incremental.py:348` (function-local import at `:341`); the manifests read as inputs (`GoModules` / `SwiftPackages`, `import_resolver.py:1428-1429`).

## Seed `bootstrap_project` and `bind_test_file` (76mk)

> **Derived by:** `beadloom impact bootstrap_project` (seed `each_graph_file`, `write_yaml_atomic`) and `bind_test_file` (seed none)

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `onboarding/scanner/bootstrap.py:52` | none | ? |  |
| co-writers | cli-commands | 4 — `services/commands/index_ops.py:229` | none | ? |  |
| co-writers | doc-generator, graph-layout, graph-loader, reindex | 2 / 1 / 1 / 1 | none | ? |  |
| callers | agent-prime | 2 — `onboarding/scanner/init_flow.py:47` | none | ? |  |
| callers | cli-commands | 1 — `services/commands/setup.py:1533`; 1 — `services/commands/query.py:21` | none | ? |  |
| callers | context-builder | 1 — `context_oracle/builder.py:383` | none | ? |  |
| callers | debt-report | 1 — `application/debt_report/collect.py:196` | none | ? |  |
| callers | mutation-scope | 1 — `application/mutation_scope/change.py:243` | none | ? |  |
| callers | reindex | 3 — `application/reindex/test_index.py:204` | none | ? |  |
| callers | test-layout | 1 — `context_oracle/test_layout.py:264` | none | ? |  |
| branches | test-mapping | 18 functions (`bind_test_file`, `mirrored_code_path`, `tree_mirrored_code_path`, `_subject_stem`, `_module_stem`, …) | none | ? |  |
| branches | agent-prime | `bootstrap_project`, `non_interactive_init`, `interactive_init` | none | ? |  |

Not derivable: the default kind folders (`unit`, `integration`) a flat `tests/test_*.py` falls outside are constants at `context_oracle/test_layout.py:94-95`, `:145`; init writes only JVM and Swift mirrors (`onboarding/scanner/bootstrap.py:373-375`).

## Seed `analyze_git_activity` and `card_activity` (the activity metric)

> **Derived by:** `beadloom impact analyze_git_activity` / `card_activity` (seed `each_graph_file`, `write_yaml_atomic`)

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime, cli-commands, doc-generator, graph-layout, graph-loader, reindex | as above | none | ? |  |
| callers | debt-report | 1 — `application/debt_report/collect.py:159` | none | ? |  |
| callers | reindex | 1 — `application/reindex/enrichment.py:131`; 2 — `application/reindex/test_index.py:99` | none | ? |  |
| callers | tui | 1 — `tui/data_providers.py:297` | 4 — `tui/styles/app.tcss` | ? |  |
| callers | site-generation | 2 — `application/site/architecture_view.py:516` | none | ? |  |
| branches | git-activity | `_classify_activity`, `_map_file_to_node`, `_parse_git_log`, `_is_within_days`, `analyze_git_activity` | none | ? |  |
| branches | site-generation | `card_activity`, `card_fields`, `_node_dict`, … | none | ? |  |

Activity chain: `infrastructure/git_activity.py:213` (git log over 90 days; thresholds `:35`, 1–4 commits in 30 days → `cold`; file → node `:57`) → `application/reindex/enrichment.py:131`, `:171-176` → `application/site/architecture_card.py:147`, `:250` → `widgets/node-card/ui/NodeCard.vue:87-90`; publishing checkout `.github/workflows/deploy-site.yml:49` (`actions/checkout@v5`, no `fetch-depth`), reindex at `:61`.

Measured on this checkout's index: 1/cold 51 nodes, 2/cold 21, 0/cold 17, 0/dormant 16, 3/cold 8, 4/cold 5, 5/warm 6, 6, 7 and 9/warm 1 each; `git log --since="30 days ago"`: 69 commits.

Not derivable: the git history depth the computation runs over (set by the publishing run's checkout).

## Supplement A — JavaScript-side slices (`src/beadloom/site_scaffold/`), located by search

| Item | Site | Node | In scope |
|---|---|---|---|
| stcx: mermaid plugin load | `.vitepress/config.mjs:14`, `:23`, `:37`; no `optimizeDeps` | vitepress-site | ? |
| stcx: pins | `package.json:26` (`mermaid` 11.17.0), `:28` (`vitepress-plugin-mermaid` 2.0.17); lock `:2769` (`fastdom` 1.0.12) | vitepress-site | ? |
| stcx: dev check boots and closes only | `scripts/dev-optimize-check.mjs:22-27` | vitepress-site | ? |
| stcx: mermaid consumers | `theme/app/index.js:27`, `:50`; `widgets/diagram-viewer/ui/DiagramViewer.vue:202` | site-app; site-diagram-viewer | ? |
| ytcg: id-keyed plain objects (write) | `entities/graph-node/model/node.js:60-62` (`parentMapOf`); `shared/elk/geometry.js:45-50` | site-graph-node; site-shared | ? |
| ytcg: reads | `node.js:106`; `shared/lib/tree.js:7`, `:19`; `widgets/graph-viewer/lib/elements.js:30`; `GraphViewer.vue:119`; `model/canvasLayout.js`, `canvasMap.js`, `lib/bundleDrawing.js`, `joins.js`, `buses.js`, `trunks.js`, `levels.js` | site-graph-node; site-shared; site-graph-viewer | ? |
| polish: aggregated-edge width | `widgets/graph-viewer/lib/mapMarks.js:19-27`, `:33-36`; `lib/stylesheet.js:292`, `:315` | site-graph-viewer | ? |
| polish: aggregated weight and route | `model/canvasMap.js:124-156`, `:181-183`; `lib/aggregateRoutes.js:117`, `:145`, `:169` | site-graph-viewer | ? |
| polish: arrowheads after a bend | `lib/stylesheet.js:184-190`, `:69`, `:205-207`, `:218`, `:229-238`, `:273`, `:287`, `:323-324` | site-graph-viewer | ? |
| polish: bridges | `lib/bridges.js`, `lib/bridgePaint.js:25`, `:70`; `model/bridgeOverlay.js` | site-graph-viewer | ? |
| polish: junction dots | `lib/junctions.js:55`, `:110`, `:132`; `model/bundleOverlay.js:23`, `:53`, `:60`, `:73`; `lib/bundleDrawing.js:34`, `:59`; `lib/trunks.js:138` | site-graph-viewer | ? |
| activity on the card | `widgets/node-card/ui/NodeCard.vue:87-90` | site-node-card | ? |
