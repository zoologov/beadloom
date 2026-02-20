# BDL UX Feedback Log

> Collected during development and dogfooding.
> Format: `[DATE] [SEVERITY] Description — Context`

---

## Closed Issues

1. ~~[2026-02-13] [MEDIUM] `doctor` warns about auto-generated skeleton docs as "unlinked from graph"~~ **FIXED** — Root cause was `generate_skeletons()` writing to wrong paths (`docs/features/` instead of `docs/domains/{parent}/features/`). Fixed by using `docs:` paths from graph + correct convention fallback. Doctor now shows 0 warnings.

2. ~~[2026-02-13] [LOW] `lint` produces no output on success~~ **FIXED** — When formatter returns empty (porcelain with 0 violations), CLI now prints `"0 violations, N rules evaluated"` as confirmation.

3. ~~[2026-02-13] [LOW] `docs generate` creates skeleton files for services including the root~~ **FIXED** — Root detection changed from "empty source" to "no `part_of` edge as src". Root node is now correctly skipped regardless of source path.

4. ~~[2026-02-13] [INFO] MCP server description says "8 tools" / CLI "18 commands"~~ **FIXED** in BEAD-11 — services.yml updated to 20 commands, 9 tools.

5. ~~[2026-02-13] [HIGH] `doctor` shows 0% doc coverage on bootstrapped projects~~ **FIXED** in BDL-012 BEAD-01 — `generate_skeletons()` now writes `docs:` field back to `services.yml` via `_patch_docs_field()`. cdeep: 95% coverage, dreamteam: 83% coverage.

6. ~~[2026-02-13] [HIGH] `lint` false positives on hierarchical projects~~ **FIXED** in BDL-012 BEAD-02 — Rule engine now accepts empty `has_edge_to: {}` (matches any node). `domain-needs-parent` uses empty matcher. `service-needs-parent` removed. cdeep: 0 violations (was 33), dreamteam: 0 violations (was 1).

7. ~~[2026-02-13] [MEDIUM] Dependencies empty in polish data~~ **FIXED** in BDL-012 BEAD-03 — `generate_polish_data()` reads `depends_on` edges from SQLite via `_enrich_edges_from_sqlite()`. cdeep: 94 dependency edges visible in polish.

8. ~~[2026-02-13] [MEDIUM] `docs polish` text format = 1 line~~ **FIXED** in BDL-012 BEAD-03 — New `format_polish_text()` renders multi-line output with node details, symbols, deps, doc status.

9. ~~[2026-02-13] [LOW] Generic summaries~~ **FIXED** in BDL-012 BEAD-06 — `_detect_framework_summary()` detects Django apps, React components, Python packages, Dockerized services.

10. ~~[2026-02-13] [LOW] Parenthesized ref_ids from Expo router~~ **FIXED** in BDL-012 BEAD-06 — `_sanitize_ref_id()` strips parentheses: `(tabs)` → `tabs`.

11. ~~[2026-02-13] [MEDIUM] Missing language parsers — 0 symbols with no warning~~ **FIXED** in BDL-012 BEAD-05 — `check_parser_availability()` + `_warn_missing_parsers()` in CLI for both bootstrap and reindex commands.

12. ~~[2026-02-13] [LOW] `reindex` ignores new parser availability~~ **FIXED** in BDL-012 BEAD-06 — Parser fingerprint tracked in `file_index`. When `supported_extensions()` changes, full code reindex triggered.

13. ~~[2026-02-13] [INFO] Bootstrap skeleton count includes pre-existing files~~ **FIXED** in BDL-012 BEAD-06 — CLI output now shows "N skeletons created, M skipped (pre-existing)".

14. ~~[2026-02-13] [MEDIUM] Preset misclassifies mobile apps as microservices~~ **FIXED** in BDL-012 BEAD-04 — `detect_preset()` checks for React Native/Expo (`package.json` deps) and Flutter (`pubspec.yaml`) before `services/` heuristic.

---

## Open Issues

20. [2026-02-14] [LOW] `.beadloom/README.md` MCP tools list was stale after BDL-014 — Listed 8 tools, missing `get_status` and `prime`. The file is generated once by BDL-013 but never auto-updated. Unlike AGENTS.md which has `generate_agents_md()`, README.md has no regeneration mechanism. Low severity because `.beadloom/README.md` is a static guide, not agent-facing. **→ Not planned (low severity, manual)**

26. [2026-02-16] [MEDIUM] Test mapping shows "0 tests in 0 files (low coverage)" for domains despite 1408+ tests — Dogfooding on beadloom itself: `beadloom ctx context-oracle` shows "Tests: pytest, 0 tests in 0 files (low coverage)" even though there are hundreds of tests covering context-oracle code. Root cause: `map_tests()` in test_mapper.py maps tests based on `test_<module>.py` → `<module>.py` naming convention, but doesn't aggregate tests at the domain level. Tests like `test_builder.py` map to `builder.py` source file but this mapping isn't rolled up to the `context-oracle` domain node. **→ Future: aggregate test mappings by domain source path prefix**

29. [2026-02-16] [HIGH] Route extraction false positives — `beadloom docs polish` shows `QUERY extract_routes -> extract_routes (graphql_python)` on ALL domains, including doc-sync and graph which have no API routes. Root cause: `route_extractor.py` contains GraphQL regex patterns in its own source code (for detecting GraphQL routes in user code), and these patterns match themselves during symbol indexing. Routes are also propagated to all parent nodes instead of being scoped to the source file that contains them. Two bugs: (1) self-matching in route_extractor.py, (2) route aggregation to parent nodes includes unrelated routes from child sources. **→ Future: add self-exclusion for extractor code + scope routes by source path**

30. [2026-02-16] [MEDIUM] Routes displayed with poor formatting in polish text — Route handler names are truncated/misaligned. The `{method:<5} {path:<20}` format doesn't handle long paths well. Also `QUERY` and `MUTATION` as methods for GraphQL is confusing — should show as separate section or different format. **→ Future: improve route rendering format**

38. [2026-02-19] [MEDIUM] `beadloom doctor` shows `[info]` not `[warn]` for nodes without docs — During BDL-023, the tech-writer agent updated domain README and CLI docs but did not create the required `SPEC.md` for the new `c4-diagrams` feature node. `beadloom doctor` reported `[info] Node 'c4-diagrams' has no doc linked.` which the agent treated as informational and ignored. If this were `[warn]` (or `[error]`), the agent would have acted on it. Convention: every feature node should have a `features/{name}/SPEC.md`. **→ Fix: promote "node has no doc" from `[info]` to `[warn]` in doctor, so agents and CI treat it as actionable**

39. [2026-02-20] [MEDIUM] Debt report "untracked: 8" — no way to see which files — `beadloom status --debt-report` shows 8 untracked files contributing 4 pts to doc_gaps, but neither human nor JSON output lists which nodes are untracked. Root cause: `_count_untracked()` counts nodes with `source` but no `sync_state` entry (feature nodes like `why`, `cache`, `rule-engine`, `debt-report` etc. that have SPEC.md docs but no doc-code sync tracking). Two issues: (1) the report should list untracked nodes for actionability, (2) feature-level SPEC.md docs are not tracked by sync-check — only domain-level READMEs are. **→ Fix: add untracked node list to report output + extend sync-check to cover feature SPEC.md docs**

40. [2026-02-20] [MEDIUM] Oversized false positive on root and parent nodes — `beadloom status --debt-report` shows "oversized: 1" (2 pts complexity). The flagged node is `beadloom` (root) with 427 symbols, but 427 is the sum of ALL symbols across ALL child domains — `_count_oversized()` uses `LIKE 'src/beadloom/%'` which matches every file in every subdirectory. Root node can't be "fixed" by splitting. Same bug will affect domain nodes (e.g. `graph` = 109 symbols includes `rule-engine`, `import-resolver`, `c4-diagrams` children) — when children grow past 200 the parent gets a false positive despite being properly decomposed. Root cause: symbol counting doesn't respect ownership boundaries — each node should only count symbols from files directly in its source directory, not from subdirectories that belong to child nodes. **→ Fix: in `_count_oversized()`, count only direct files (exclude paths claimed by child node source prefixes)**

41. [2026-02-20] [HIGH] C4 diagram: all elements render as `System()` — no Container/Component differentiation — `beadloom graph --format=c4-plantuml` renders every node as `System(...)`. Domains (depth 1) should be `Container`, features (depth 2) should be `Component`. Root cause: self-referencing `part_of` edge `beadloom → beadloom` in `services.yml` makes `_compute_depths()` find zero roots (`roots = all_ref_ids - set(parent_of.keys())` — beadloom is in `parent_of` so it's excluded). BFS never starts, all nodes fall through to depth=0 fallback (line 92 in c4.py), all become System. Same bug affects `--format=c4` (Mermaid). **→ Fix: in `_compute_depths()`, filter out self-referencing edges (`if child != par`) before computing roots**

42. [2026-02-20] [MEDIUM] C4 diagram: label and description are identical — Every C4 element shows the full summary twice: `System(agent_prime, "Cross-IDE context injection via...", "Cross-IDE context injection via...")`. Root cause: `_build_c4_node()` sets both `label=summary` and `description=summary`. Label should be a short human-readable name derived from ref_id (e.g. `context-oracle` → "Context Oracle"), while description should be the full summary. **→ Fix: generate label from ref_id via title-casing + hyphen-to-space, keep summary as description**

43. [2026-02-20] [MEDIUM] C4 diagram: root node appears inside its own boundary — Output shows `System_Boundary(beadloom_boundary, ...) { System(beadloom, ...) ... }` — the root is simultaneously the boundary group AND an element inside it. Root cause: self-referencing `part_of` edge makes `parent_of["beadloom"] = "beadloom"`, so beadloom gets `boundary=beadloom` and is added as a child of its own boundary. In C4, a System_Boundary is a visual grouping — the system itself should not appear as a child element inside. **→ Fix: skip self-referencing entries in `_load_edges()` part_of handling, or filter in renderer**

44. [2026-02-20] [LOW] C4 diagram: boundary ordering is non-semantic — `onboarding` boundary renders before `beadloom` boundary. Root cause: since `top_level_nodes` is empty (all nodes have a boundary due to bug #41), everything goes through `_plantuml_orphan_boundaries` in dict insertion order. `agent-prime` is alphabetically first, its parent `onboarding` gets rendered first. Even after fixing bug #41, orphan boundary ordering should be deterministic and semantic (e.g. root-first, then alphabetical). **→ Fix: sort orphan boundaries by node kind/depth, or render root system first**

45. [2026-02-20] [LOW] C4 diagram: `!include` always uses `C4_Container.puml` — PlantUML renderer always includes `C4_Container.puml` regardless of the C4 level. When `--level=component` is used, should include `C4_Component.puml` instead. When `--level=context`, should include `C4_Context.puml`. **→ Fix: select include based on the `--level` flag passed to `filter_c4_nodes()`**

52. [2026-02-20] [HIGH] `docs audit` high false positive rate (~86%) on real project — Dogfooding on beadloom: 107 "stale" mentions reported, but only ~15 are genuine (mcp_tool_count 13→14, cli_command_count 22→29, rule_type_count). Root causes: (1) small numbers (2, 3, 5) in SPEC.md examples match too aggressively against node_count/edge_count, (2) step numbers in CONTRIBUTING.md match test_count, (3) percentage "80" in "80% coverage" matches test_count keyword. PRD target was <20% FP rate. **→ Fix: increase minimum matchable number threshold (skip <10 for count facts), add "percentage" false positive filter, consider excluding SPEC.md/CONTRIBUTING.md by default**

53. [2026-02-20] [MEDIUM] `docs audit` year "2026" matched as mcp_tool_count — Line `README.md:66` matches "2026" near "tool" keyword and reports it as stale mcp_tool_count. Root cause: date filter catches `YYYY-MM-DD` and month patterns but not standalone 4-digit years (2020-2030 range). **→ Fix: add standalone year regex `\b20[0-9]{2}\b` to false positive filters**

54. [2026-02-20] [MEDIUM] `docs audit` SPEC.md files dominate false positives — 40+ of 107 stale mentions come from `.beadloom/_graph/features/*/SPEC.md` files which contain example numbers, thresholds, and architectural descriptions (e.g., "2 nodes", "5 edges", "100 nodes"). These are documentation about the system's behavior, not claims about current state. **→ Fix: exclude `_graph/features/*/SPEC.md` from default scan paths, or add a `docs_audit.exclude_paths` config option**

55. [2020-02-20] [LOW] `docs audit` test_count ground truth seems inflated — Reports `test_count: 3039` which is the count of `kind='test'` symbols in code_symbols table. This likely includes parameterized test IDs and non-test symbols. Actual pytest count is 2389. **→ Fix: consider using `uv run pytest --collect-only -q | tail -1` for more accurate test count, or document that this counts test symbols not test cases**

56. [2026-02-20] [LOW] `docs audit` Rich output lacks file path context — Stale mentions show bare filenames like `SPEC.md:44` without the full relative path. When multiple SPEC.md files exist across different feature directories, it's impossible to tell which file is referenced. **→ Fix: show relative path from project root (e.g., `docs/domains/graph/features/c4-diagrams/SPEC.md:44`)**

31. [2026-02-16] [LOW] `bd dep remove` says "✓ Removed" but dependency persists — Running `bd dep remove beadloom-3v0 beadloom-53o` reports success, but `bd show beadloom-3v0` still shows the dependency and `bd blocked` still lists it as blocked. Workaround: `bd update --status in_progress --claim` works regardless of blocks. **→ Beads CLI bug, not beadloom**

---

## Dogfooding: External React Native + Expo Project

> Discovered 2026-02-17 during `beadloom init` on a real-world React Native project
> Stack: React Native, Expo 53, Gluestack UI v3, Mapbox GL, two C++/JNI native modules, BLE integration

32. [2026-02-17] [HIGH] `beadloom init` scan_paths incomplete for React Native projects — Bootstrap only detected `app/` and `services/` (6 nodes), completely missing `components/` (ui, features, layout, navigation), `hooks/`, `contexts/`, `modules/` (two native modules), `types/`, `constants/`, `utils/`. Had to manually add 9 scan_paths and rebuild the graph to get 17 nodes with 380 symbols. Root cause: `detect_source_dirs()` in `onboarding/bootstrapper.py` uses manifest-based heuristics (package.json → standard dirs) but React Native/Expo projects use flat top-level structure with many domain dirs. **→ Fix: scan all top-level dirs with code files, not just manifest-adjacent ones**

33. [2026-02-17] [MEDIUM] `beadloom init` is interactive-only — no CLI flags for automation — The `init` command requires 3 interactive prompts: overwrite confirmation, mode selection (bootstrap/import/both), graph confirmation (yes/edit/cancel). No `--mode bootstrap --yes --force` flags available. Makes it unusable in CI pipelines, scripts, and awkward for AI agents (had to pipe `printf` answers). **→ Fix: add `--mode`, `--yes`/`--non-interactive`, `--force` flags**

34. [2026-02-17] [MEDIUM] Auto-generated `rules.yml` includes `service-needs-parent` that always fails on root — `beadloom init` generates `service-needs-parent` rule requiring every service node to have a `part_of` edge. Root service has no parent by definition → lint always fails. Had to manually remove the rule. Root cause: `_generate_default_rules()` doesn't account for root nodes. **→ Fix: either don't generate this rule, or add `exclude_root: true` option to rule engine**

35. [2026-02-17] [MEDIUM] Init doesn't offer `docs generate` — doc coverage 0% after bootstrap — After `beadloom init`, doc coverage is 0/6 (0%). User must know to run `beadloom docs generate` + `beadloom reindex` as separate steps. The init flow could offer doc skeleton generation as a final step. **→ Fix: add "Generate doc skeletons? [yes/no]" step to init, or auto-generate**

36. [2026-02-17] [LOW] Existing docs not auto-linked to graph nodes — Target project had 20 existing docs in `docs/` (architecture docs, native module docs, feature docs). All reported as "unlinked from graph" by `doctor`. No auto-discovery mechanism to match existing docs to nodes by path or content similarity. Manual linking requires editing `services.yml`. **→ Future: fuzzy doc-to-node matching during init or `doctor --fix`**

37. [2026-02-17] [INFO] `beadloom init` bootstrap quality metrics — Before/after manual graph improvement: Nodes 6→17, Edges 8→49, Symbols 23→380, Doc Coverage 0%→94%. The auto-generated graph captured only 35% of the real architecture. One native module alone has 130+ symbols — correctly indexed after scan_paths fix. **→ Track: bootstrap quality ratio as a metric for future improvements**

---

## Recently Fixed Issues (v1.8.0)

> Discovered during TUI dogfooding (BDL-025 Phase 12.10)

46. ~~[2026-02-20] [HIGH] TUI: Graph tree empty — only "Architecture" label visible~~ **FIXED in v1.8.0 (BDL-025)** — Self-referencing `part_of` edge (`beadloom → beadloom`) in `services.yml` caused `get_hierarchy()` to include `beadloom` as its own child. All nodes became children, leaving `root_level` empty. Fix: added `if child != parent` filter in `GraphDataProvider.get_hierarchy()`. Commit: `8e18fa8`.

47. ~~[2026-02-20] [HIGH] TUI: Activity widget shows 0% for all domains~~ **FIXED in v1.8.0 (BDL-025)** — `ActivityWidget._activity_level()` checked for nonexistent `commit_count` attribute on `GitActivity` dataclass. The actual attribute is `commits_30d`. Fix: changed to `commits_30d` with normalization formula `min(commits_30d * 2, 100)` (50 commits = 100%). Commit: `8e18fa8`.

48. ~~[2026-02-20] [MEDIUM] TUI: Enter on tree node only expands — doesn't navigate to Explorer~~ **FIXED in v1.8.0 (BDL-025)** — Textual Tree widget's Enter key only toggles expand/collapse. Leaf nodes (features, services without children) should open Explorer screen. Fix: added leaf-node detection in `DashboardScreen.on_node_selected()` — if `event.ref_id not in hierarchy`, calls `app.open_explorer(event.ref_id)`. Commit: `73b9306`.

49. ~~[2026-02-20] [HIGH] TUI: Doc Status screen shows "–" for all Doc Path and Reason columns~~ **FIXED in v1.8.0 (BDL-025)** — DB opened with `mode=ro` (read-only), but `check_sync()` writes updated hashes. `SyncDataProvider.refresh()` threw `sqlite3.OperationalError` (not caught), leaving `sync_lookup` empty — all nodes fell through to `doc_ref_ids` path with empty `doc_path`. Fix: removed `mode=ro`, opened DB in WAL mode (read-write); added `sqlite3.OperationalError` to catch clause. Commit: `b07931b`.

50. ~~[2026-02-20] [MEDIUM] TUI: Explorer shows self-referencing edges as duplicates~~ **FIXED in v1.8.0 (BDL-025)** — 15 self-referencing `touches_code` edges in DB (e.g. `search --touches_code--> search`). `NodeDetailPanel._render_node_detail()` matched them as both outgoing AND incoming, showing duplicates. Fix: added `e["dst"] != ref_id` / `e["src"] != ref_id` filter to edge lists. Commit: `88a2a1a`.

51. ~~[2026-02-20] [MEDIUM] TUI: Explorer defaults to "Downstream Dependents" — empty for leaf nodes~~ **FIXED in v1.8.0 (BDL-025)** — Leaf/feature nodes have no downstream dependents, so the default right panel was always "No dependencies found". Fix: changed default mode from `MODE_DOWNSTREAM` to `MODE_UPSTREAM` — upstream dependencies are more useful for navigation. User can press `d` to switch to downstream. Commit: `88a2a1a`.

---

## Recently Fixed Issues (v1.6.0)

16. ~~[2026-02-13] [MEDIUM] After BDL-012 bug-fixes, beadloom's own docs are outdated~~ **FIXED in v1.6.0 (BDL-019)** — All 13 domain/service docs refreshed by 4 parallel tech-writer agents. `symbols_changed` reduced from 35 to 0.

27. ~~[2026-02-16] [LOW] `docs polish` text format doesn't include routes/activity/tests data~~ **FIXED in v1.6.0 (BDL-017 BEAD-14)** — Smart `docs polish` now includes routes, activity level, test mappings, and deep config data.

28. ~~[2026-02-16] [INFO] `beadloom status` Context Metrics section working well~~ **CLOSED** — Confirmed working. No action needed.

---

## Recently Fixed Issues (v1.5.0)

15. ~~[2026-02-13] [HIGH] `doctor` 100% coverage + `Stale docs: 0` is misleading after major code changes~~ **FIXED in v1.5.0 (BDL-015 BEAD-08, BEAD-09) + BDL-016** — Symbol-level drift detection via `_compute_symbols_hash()` + `_check_symbol_drift()` in doctor. BDL-016 fixed E2E baseline preservation.

17. ~~[2026-02-14] [LOW] `setup-rules` auto-detect doesn't work for Windsurf and Cline~~ **FIXED in v1.5.0 (BDL-015 BEAD-12)** — Content-based detection instead of file presence.

18. ~~[2026-02-14] [HIGH] `sync-check` reports "31/31 OK" despite massive semantic drift~~ **FIXED in v1.5.0 (BDL-015 BEAD-08) + BDL-016** — Symbol-level drift detection works end-to-end.

19. ~~[2026-02-14] [MEDIUM] `.beadloom/AGENTS.md` not auto-generated during bootstrap~~ **FIXED in v1.5.0 (BDL-015 BEAD-06)**.

21. ~~[2026-02-14] [HIGH] Incremental reindex returns Nodes: 0 after YAML edit~~ **FIXED in v1.5.0 (BDL-015 BEAD-11)**.

22. ~~[2026-02-15] [HIGH] `.claude/CLAUDE.md` references obsolete project phases~~ **FIXED** — Updated phases, docs references.

23. ~~[2026-02-15] [HIGH] `/templates` has wrong project structure~~ **FIXED** — Fully rewritten with stabilized format.

24. ~~[2026-02-15] [HIGH] `/test` has wrong import paths~~ **FIXED** — Updated all paths and patterns.

25. ~~[2026-02-15] [MEDIUM] `/review` references old architecture layers~~ **FIXED** — Updated layer names.
