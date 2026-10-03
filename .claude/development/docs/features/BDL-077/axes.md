# Axes: BDL-077 (Explore output, 2026-10-03)

> Raw output of the explore role (step 0.5). The `In scope` column is ruled in RFC.md, not here.

## Axes

> **Derived by:** `beadloom impact src/beadloom/application/site/architecture_view.py` over `src/beadloom`
> **Seed:** `each_graph_file` (effect `reads-a-yaml-directory`), `write_yaml_atomic` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 5 name-defined-more-than-once, 1 node-owns-unread-files, 16 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `src/beadloom/onboarding/scanner/bootstrap.py:52` | none | ? |  |
| co-writers | cli-commands | 4 — `src/beadloom/services/commands/index_ops.py:229` | none | ? |  |
| co-writers | doc-generator | 2 — `src/beadloom/onboarding/doc_generator.py:29` | none | ? |  |
| co-writers | graph-layout | 1 — `src/beadloom/onboarding/graph_layout.py:185` | none | ? |  |
| co-writers | graph-loader | 1 — `src/beadloom/graph/loader.py:297` | none | ? |  |
| co-writers | reindex | 1 — `src/beadloom/application/reindex/indexing.py:40` | none | ? |  |
| callers | ai-techwriter | 1 — `src/beadloom/ai_agents/ai_techwriter/runner.py:110` | 2 — `src/beadloom/ai_agents/ai_techwriter/provision-runner.sh` | ? |  |
| callers | scope-check | 1 — `src/beadloom/doc_sync/scope_check.py:262` | none | ? |  |
| callers | site-generation | 4 — `src/beadloom/application/site/generate.py:514` | none | ? |  |
| callers | wave-plan | 1 — `src/beadloom/application/waves/scope.py:127` | none | ? |  |
| branches | site-generation | 23 functions of `architecture_view.py` (`_arch_edges`, `_parent_map`, `build_architecture_view_data`, `serialize_architecture_view`, …) | none | ? |  |
| branches | ai-techwriter | `_branch_name`, from a caller's seat | 2 — `provision-runner.sh` | ? |  |
| branches | site-generation | `generate_site`, `_federated_landscape`, `render_landscape_md`, `render_landscape_view_md`, from a caller's seat | none | ? |  |
| branches | wave-plan | `parse_declaration`, from a caller's seat | none | ? |  |
| branches | scope-check | `_outside`, from a caller's seat | none | ? |  |

Not derivable: the seed rule reached two YAML sinks and not the write of the JSON data file (`src/beadloom/application/site/generate.py:582-586`, `public/architecture.data.json`), so no axis above is derived from that file's readers. The JavaScript and Vue viewer is not read by `beadloom impact`. The table names 10 distinct nodes.

## Supplement A — the viewer (JavaScript/Vue), not derived by `beadloom impact`

From reading the files and the `source:` paths in `.beadloom/_graph/site-*.yml` and `vitepress-site.yml`.

| Node | Site | Code at the site | In scope |
|---|---|---|---|
| site-generation | `src/beadloom/application/site/architecture_view.py:76` | `ARCHITECTURE_SCHEMA_VERSION = 2`, emitted at `:613` | ? |
| site-generation | `src/beadloom/application/site/architecture_view.py:405` | `_arch_edges`: the drawn edges and the derived dependency lists | ? |
| site-generation | `src/beadloom/application/site/architecture_view.py:481` | `_parent_map`: `part_of` containment, which the viewer turns into compound parents | ? |
| site-generation | `src/beadloom/application/site/architecture_view.py:560` | `build_architecture_view_data`: the payload's top-level keys | ? |
| site-generation | `tests/integration/application/site/test_architecture_view.py`, `tests/integration/application/site/architecture_view/` | integration tests of the data file | ? |
| site-architecture-data | `site_scaffold/.vitepress/theme/entities/architecture-data/api/useArchitectureData.js:14` | `SUPPORTED_SCHEMA_VERSIONS = [1, 2]`, checked at `:17` | ? |
| site-shared | `site_scaffold/.vitepress/theme/shared/cytoscape/load.js:12` | `import("cytoscape-elk")`, `cytoscape.use(elk)` at `:14` | ? |
| site-shared | `site_scaffold/.vitepress/theme/shared/cytoscape/layout.js:21` | `LAYERED_LAYOUT`: `elk.edgeRouting: ORTHOGONAL` at `:26`, `INCLUDE_CHILDREN` at `:27`, partition at `:18` | ? |
| site-shared | `site_scaffold/.vitepress/theme/shared/cytoscape/index.js:4` | exports `loadCytoscape`, `LAYERED_LAYOUT` | ? |
| site-shared | `site_scaffold/.vitepress/theme/shared/theme-tokens/resolve.js:13` | `TOKEN_VARIABLES`: theme colours reaching Cytoscape | ? |
| site-graph-viewer | `widgets/graph-viewer/model/useGraphCanvas.js:13` | `runLayout` on the main thread (`:15`, `layoutstop` `:16`) | ? |
| site-graph-viewer | `widgets/graph-viewer/model/useGraphCanvas.js:64` | edge hover `is-hovered` (`:64`-`:65`, cleared `:44`) | ? |
| site-graph-viewer | `widgets/graph-viewer/model/useGraphCanvas.js:83` | `showOnly` (`is-hidden` `:85`, `:88`) | ? |
| site-graph-viewer | `widgets/graph-viewer/model/useGraphCanvas.js:92` | `markNode`: `in-walk`, `ring-*`, `is-risk` (`:97`-`:105`) | ? |
| site-graph-viewer | `widgets/graph-viewer/lib/stylesheet.js:49` | `CURVE_STYLE = "bezier"`, applied `:148` | ? |
| site-graph-viewer | `widgets/graph-viewer/lib/stylesheet.js:170` | hovered/selected edge label, ring selectors `:177`/`:181` | ? |
| site-graph-viewer | `widgets/graph-viewer/lib/elements.js:49` | `buildElements` (`parent` `:25`, `partition` `:24`, `edgeElement` `:29`) | ? |
| site-graph-viewer | `widgets/graph-viewer/ui/GraphViewer.vue:185` | `useGraphCanvas(...)`, walk `:123`-`:128`, fit `:213` | ? |
| site-graph-viewer | `widgets/graph-viewer/ui/GraphViewer.vue:243` | `applyArrangePolicy()`, `@arrange` `:324`, Arrange help `:374` | ? |
| site-graph-viewer | `widgets/graph-viewer/model/testHandle.js:151` | `exposeTestHandle` (`positions` `:52`, walk edges `:67`, edge readers `:97`-`:128`) | ? |
| site-graph-viewer | `widgets/graph-viewer/model/modes.js:46` | `MODES`: architecture and landscape | ? |
| site-navigate-graph | `features/navigate-graph/model/useGraphNavigation.js:20` | `autoungrabify: true`, `applyArrangePolicy` `:56`, `toggleArrange` `:110` | ? |
| site-navigate-graph | `features/navigate-graph/ui/NavigationControls.vue:21` | the Arrange button (`:8`, `:25`) | ? |
| site-select-neighbourhood | `features/select-neighbourhood/lib/neighbourhood.js:23` | `neighbourhoodOf` | ? |
| site-impact-view | `features/impact-view/lib/impact.js:27` | `impactOf`, `impactSummary` `:81` | ? |
| site-impact-view | `features/impact-view/model/rings.js:19` | `ringOf` | ? |
| site-filter-graph | `features/filter-graph/lib/visibleIds.js:40` | `visibleNodeIds` → `showOnly` | ? |
| site-url-state | `features/url-state/model/useUrlState.js:14` | `useUrlState` (focus, depth, dir, hide, view) | ? |
| site-graph-edge | `entities/graph-edge/model/edgeKinds.js:24` | `DRAWN_KINDS`, `EDGE_STYLES` `:35`, `styleKeyOf` `:125` | ? |
| site-graph-edge | `entities/graph-edge/model/adjacency.js:41` | `adjacencyOf`, `edgeGroupsOf` `:80` | ? |
| site-architecture-page | `pages/architecture/ui/ArchitectureMap.vue:27` | `<GraphViewer mode="architecture">` | ? |
| site-landscape-page | `pages/landscape/ui/LandscapeMap.vue:18` | `<GraphViewer mode="landscape">` | ? |
| vitepress-site | `site_scaffold/package.json:19` | `"cytoscape-elk": "2.3.0"`, `"elkjs": "0.12.0"` `:21` | ? |
| vitepress-site | `site_scaffold/package-lock.json:2121` | nested `cytoscape-elk/node_modules/elkjs` 0.9.3 (`beadloom-f2we`); top-level `elkjs` `:2706` | ? |
| vitepress-site | `site_scaffold/e2e/navigation.spec.js:73` | "dragging a node moves it only while Arrange is on" (`:93`), drag-pans `:51` | ? |
| vitepress-site | `site_scaffold/e2e/node-page.spec.js:193` | zoom/fit and Arrange on node pages (`:210`) | ? |
| vitepress-site | `site_scaffold/e2e/edges.spec.js:20` | legend, line styles `:32`, hover label `:60`, themes `:102` | ? |
| vitepress-site | `site_scaffold/e2e/neighbourhood.spec.js:55` | walk edges highlighted (`:72`, `:87`) | ? |
| vitepress-site | `site_scaffold/e2e/impact.spec.js:48` | impact boundary crossings | ? |
| vitepress-site | `site_scaffold/e2e/url-state.spec.js:13` | linked view state (`:43`, `:51`) | ? |
| vitepress-site | `site_scaffold/e2e/graph-viewer-instances.spec.js:13` | test-handle lifecycle | ? |
| vitepress-site | `site_scaffold/e2e/support/viewer.js:12` | opens the page and waits for the layout | ? |
| site-graph-viewer | `docs/services/vitepress-site/graph-viewer.md:34` | Arrange (`:34`), the `bezier` measurement (`:45`, `:65`-`:70`) | ? |
| site-navigate-graph | `docs/services/vitepress-site/navigate-graph.md:14` | Arrange and `toggleArrange` (`:26`-`:27`) | ? |
| vitepress-site | `docs/services/vitepress-site.md:57` | slice table row "Pan, zoom, fit, centre and Arrange" | ? |

Not derivable: the owning node of `tests/self_check/docs/test_site_viz_deps.py` (`_REQUIRED_VIZ_DEPS` at `:46` names `cytoscape-elk`; `:120`-`:124` assert on `layout.js`'s text), and of `docs/guides/vitepress-site.md:208` (Arrange). Supplement: 14 distinct nodes; with the table's 10, 23 in all.
