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

31. [2026-02-16] [LOW] `bd dep remove` says "✓ Removed" but dependency persists — Running `bd dep remove beadloom-3v0 beadloom-53o` reports success, but `bd show beadloom-3v0` still shows the dependency and `bd blocked` still lists it as blocked. Workaround: `bd update --status in_progress --claim` works regardless of blocks. **→ Beads CLI bug, not beadloom**

35. [2026-02-17] [MEDIUM] Init doesn't offer `docs generate` — doc coverage 0% after bootstrap — After `beadloom init`, doc coverage is 0/6 (0%). User must know to run `beadloom docs generate` + `beadloom reindex` as separate steps. The init flow could offer doc skeleton generation as a final step. **→ Fix: add "Generate doc skeletons? [yes/no]" step to init, or auto-generate**

36. [2026-02-17] [LOW] Existing docs not auto-linked to graph nodes — Target project had 20 existing docs in `docs/` (architecture docs, native module docs, feature docs). All reported as "unlinked from graph" by `doctor`. No auto-discovery mechanism to match existing docs to nodes by path or content similarity. Manual linking requires editing `services.yml`. **→ Future: fuzzy doc-to-node matching during init or `doctor --fix`**

37. [2026-02-17] [INFO] `beadloom init` bootstrap quality metrics — Before/after manual graph improvement: Nodes 6→17, Edges 8→49, Symbols 23→380, Doc Coverage 0%→94%. The auto-generated graph captured only 35% of the real architecture. One native module alone has 130+ symbols — correctly indexed after scan_paths fix. **→ Track: bootstrap quality ratio as a metric for future improvements**

---

## Dogfooding: External React Native + Expo Project

> Discovered 2026-02-17 during `beadloom init` on a real-world React Native project
> Stack: React Native, Expo 53, Gluestack UI v3, Mapbox GL, two C++/JNI native modules, BLE integration

32. [2026-02-17] [HIGH] `beadloom init` scan_paths incomplete for React Native projects — Bootstrap only detected `app/` and `services/` (6 nodes), completely missing `components/` (ui, features, layout, navigation), `hooks/`, `contexts/`, `modules/` (two native modules), `types/`, `constants/`, `utils/`. Had to manually add 9 scan_paths and rebuild the graph to get 17 nodes with 380 symbols. Root cause: `detect_source_dirs()` in `onboarding/bootstrapper.py` uses manifest-based heuristics (package.json → standard dirs) but React Native/Expo projects use flat top-level structure with many domain dirs. **→ Fix: scan all top-level dirs with code files, not just manifest-adjacent ones**

---

## Recently Fixed Issues (v1.9.0)

> Fixed in BDL-027 UX Issues Batch Fix (Phase 12.12)

26. ~~[2026-02-16] [MEDIUM] Test mapping shows "0 tests in 0 files (low coverage)" for domains despite 1408+ tests~~ **FIXED in v1.9.0 (BDL-027 BEAD-05)** — New `aggregate_parent_tests()` function in `test_mapper.py` rolls up child node test counts to parent domain nodes. Reindex pipeline calls aggregation after `map_tests()`.

29. ~~[2026-02-16] [HIGH] Route extraction false positives~~ **FIXED in v1.9.0 (BDL-027 BEAD-05)** — Self-exclusion added to `extract_routes()`: files named `route_extractor` are skipped. Route aggregation scoped to source file ownership.

30. ~~[2026-02-16] [MEDIUM] Routes displayed with poor formatting in polish text~~ **FIXED in v1.9.0 (BDL-027 BEAD-05)** — New `format_routes_for_display()` function separates HTTP routes from GraphQL routes with wider columns and distinct formatting.

32. ~~[2026-02-17] [HIGH] `beadloom init` scan_paths incomplete for React Native projects~~ **FIXED in v1.9.0 (BDL-027 BEAD-04)** — `detect_source_dirs()` now scans all top-level directories containing code files, not just manifest-adjacent ones.

33. ~~[2026-02-17] [MEDIUM] `beadloom init` is interactive-only — no CLI flags for automation~~ **FIXED in v1.9.0 (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

34. ~~[2026-02-17] [MEDIUM] Auto-generated `rules.yml` includes `service-needs-parent` that always fails on root~~ **FIXED in v1.9.0 (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

38. ~~[2026-02-19] [MEDIUM] `beadloom doctor` shows `[info]` not `[warn]` for nodes without docs~~ **FIXED in v1.9.0 (BDL-027 BEAD-03)** — `doctor.py` promoted "node has no doc linked" from `[info]` to `[warn]` severity, making it actionable for agents and CI.

39. ~~[2026-02-20] [MEDIUM] Debt report "untracked: 8" — no way to see which files~~ **FIXED in v1.9.0 (BDL-027 BEAD-03)** — `debt_report.py` now lists untracked node names in both human and JSON output.

40. ~~[2026-02-20] [MEDIUM] Oversized false positive on root and parent nodes~~ **FIXED in v1.9.0 (BDL-027 BEAD-03)** — `_count_oversized()` now counts only direct files, excluding subdirectories claimed by child node source prefixes.

41. ~~[2026-02-20] [HIGH] C4 diagram: all elements render as `System()` — no Container/Component differentiation~~ **FIXED in v1.9.0 (BDL-027 BEAD-01)** — `_compute_depths()` now filters self-referencing `part_of` edges. BFS correctly computes depths, producing System/Container/Component differentiation.

42. ~~[2026-02-20] [MEDIUM] C4 diagram: label and description are identical~~ **FIXED in v1.9.0 (BDL-027 BEAD-01)** — `_build_c4_node()` now generates label from ref_id via title-casing + hyphen-to-space; summary used as description only.

43. ~~[2026-02-20] [MEDIUM] C4 diagram: root node appears inside its own boundary~~ **FIXED in v1.9.0 (BDL-027 BEAD-01)** — `_load_edges()` skips self-referencing `part_of` entries; root node rendered at top level, not inside its own boundary.

44. ~~[2026-02-20] [LOW] C4 diagram: boundary ordering is non-semantic~~ **FIXED in v1.9.0 (BDL-027 BEAD-01)** — Orphan boundaries sorted by node kind/depth; root rendered first, then alphabetical.

45. ~~[2026-02-20] [LOW] C4 diagram: `!include` always uses `C4_Container.puml`~~ **FIXED in v1.9.0 (BDL-027 BEAD-01)** — PlantUML `!include` now selects `C4_Context.puml`, `C4_Container.puml`, or `C4_Component.puml` based on the `--level` flag.

52. ~~[2026-02-20] [HIGH] `docs audit` high false positive rate (~86%) on real project~~ **FIXED in v1.9.0 (BDL-027 BEAD-02)** — Minimum matchable number threshold increased (skip <10 for count facts), percentage false positive filter added, SPEC.md/CONTRIBUTING.md excluded from default scan paths.

53. ~~[2026-02-20] [MEDIUM] `docs audit` year "2026" matched as mcp_tool_count~~ **FIXED in v1.9.0 (BDL-027 BEAD-02)** — Standalone year regex `\b20[0-9]{2}\b` added to false positive filters.

54. ~~[2026-02-20] [MEDIUM] `docs audit` SPEC.md files dominate false positives~~ **FIXED in v1.9.0 (BDL-027 BEAD-02)** — `_graph/features/*/SPEC.md` excluded from default scan paths.

55. ~~[2020-02-20] [LOW] `docs audit` test_count ground truth seems inflated~~ **FIXED in v1.9.0 (BDL-027 BEAD-02)** — `test_count` now labeled as symbol count in output; documented distinction between test symbols and test cases.

56. ~~[2026-02-20] [LOW] `docs audit` Rich output lacks file path context~~ **FIXED in v1.9.0 (BDL-027 BEAD-02)** — Stale mentions now show full relative path from project root.

57. ~~[2026-02-20] [MEDIUM] `docs audit` version fact not collected for dynamic versioning~~ **FIXED in v1.9.0 (BDL-027 BEAD-02)** — `FactRegistry` now detects `dynamic = ["version"]` + `[tool.hatch.version]` and falls back to `importlib.metadata.version()` for installed packages.

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
