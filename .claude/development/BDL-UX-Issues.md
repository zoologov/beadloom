# BDL UX Feedback Log

> Collected during development and dogfooding.
> Total: 69 issues | Open: 3 | Improvements: 2 | Excluded: 5 | Closed: 59
> Last reviewed: BDL-032 (Enhanced Architecture Rules)

---

## Open Issues

> Issues awaiting code fixes in Beadloom.

67. [2026-02-21] [MEDIUM] `_load_rules_into_db` silently drops v3 rule types — `reindex.py:_load_rules_into_db()` only handles `DenyRule` and `RequireRule` instances (line 327: `else: continue`). The 5 new v3 rule types (`ForbidCyclesRule`, `LayerRule`, `CardinalityRule`, `ForbidImportRule`, `ForbidEdgeRule`) are silently skipped. The `rules` DB table stays at 4 rows instead of 9. This makes `docs audit` report `rule_type_count: 4` instead of `9`, and any tool querying the `rules` table gets stale data.
    > **Impact:** `docs audit` ground truth is wrong. Any MCP tool or TUI widget querying the `rules` table sees only 4 rules.
    > **Fix:** Add `isinstance` branches for all 7 rule types in `_load_rules_into_db`, or use a generic serialization approach (e.g., `rule.to_dict()` method on the base `Rule` class).

68. [2026-02-21] [LOW] `_build_rules_section` and `_read_rules_data` use simplistic rule type detection — Both functions in `scanner.py` (lines 985, 1042) use `"require" if "require" in rule else "deny"` to determine rule type from YAML. This maps `forbid_cycles`, `layers`, `check` (cardinality), and `forbid_import` rules all to type "deny". The type label in AGENTS.md and `beadloom prime` output is inaccurate for 5 of 9 rules.
    > **Impact:** Cosmetic. The rule descriptions are correct, only the type label in parentheses is wrong.
    > **Fix:** Check for all YAML keys: `require`, `deny`, `forbid_cycles`, `layers`, `check`, `forbid_import`, `forbid_edge`.

69. [2026-02-21] [LOW] `generate_agents_md` Custom section preservation corrupts file on regeneration — When the old AGENTS.md has content after `## Custom` that itself contains a `## Custom` marker (e.g., from a prior duplication), the preservation logic at `scanner.py:1006-1011` captures everything after the first `## Custom` marker and appends it again, causing content duplication. In BDL-032, regeneration duplicated the entire file body because old content (from a prior manual edit) was stored below `## Custom`.
    > **Impact:** Regenerated AGENTS.md is garbled until manually cleaned.
    > **Fix:** Use a more robust marker, e.g., `<!-- beadloom:custom-start -->`, or only preserve content after the *last* `## Custom` marker.

---

## Improvements

> Enhancement proposals for existing features. Not bugs — current behavior works but can be better.

65. [2026-02-21] [MEDIUM] `docs audit` still has ~60% false positive rate on beadloom itself — 47 stale mentions reported, but most are false positives: threshold numbers (`>= 80%`), capability descriptions (`supports 12 languages`), example values in SPEC.md files, and years (`2026`). BDL-027 BEAD-02 fixed the worst cases (SPEC.md exclusion, year filter, skip numbers <10), but the matcher still lacks context awareness.
    > **Recommended approach (3 layers):**
    > 1. **Blocklist modifiers** — skip matches near `>=`, `up to`, `supports`, `limit`, `%`, `maximum`. Fastest win, cuts ~40% of FPs.
    > 2. **Proximity scoring** — weight match by distance to fact-type keyword (e.g., number `13` near `MCP` = likely mcp_tool_count; `80` near `coverage` + `%` = threshold, not test_count).
    > 3. **File-type heuristics** — lower confidence for SPEC.md, CONTRIBUTING.md, examples/; higher for README.md, AGENTS.md, CLAUDE.md.
    > Pure semantic (LLM-based) analysis is overkill for a CLI tool. Pattern + proximity + file heuristics should achieve ~90% precision without architectural changes.

66. [2026-02-21] [LOW] `graph_snapshots` lacks diff/compare capability — table stores immutable point-in-time graph captures (nodes_json, edges_json, symbols_count, label), but there's no CLI command to compare two snapshots. Users can only view individual snapshots, not see what changed between them (added/removed/changed nodes and edges).
    > **Recommended approach:**
    > 1. **`beadloom snapshots list`** — show all saved snapshots with labels, dates, node/edge counts.
    > 2. **`beadloom snapshots diff <label-a> <label-b>`** — compute and display added/removed/changed nodes and edges between two snapshots. Output as Rich table + optional `--json` for automation.
    > 3. **`beadloom snapshots save --label "v1.8.0"`** — explicit named snapshot creation (currently snapshots are auto-created during reindex).
    > Stays within existing SQLite + Python stack. No external dependencies (Dolt, etc.) needed — the current `graph_snapshots` schema already contains all necessary data for diffing.

---

## Excluded Issues

> Issues excluded from the backlog with justification. Not planned for implementation.

20. [2026-02-14] [LOW] `.beadloom/README.md` MCP tools list stale after BDL-014 — Listed 8 tools, missing `get_status` and `prime`. The file is generated once by BDL-013 but never auto-updated. Unlike AGENTS.md which has `generate_agents_md()`, README.md has no regeneration mechanism.
    > **Won't fix.** Static guide, not agent-facing. Low severity, manual update sufficient.

31. [2026-02-16] [LOW] `bd dep remove` reports success but dependency persists — Running `bd dep remove beadloom-3v0 beadloom-53o` reports success, but `bd show beadloom-3v0` still shows the dependency. Workaround: `bd update --status in_progress --claim` ignores blocks.
    > **External.** Bug in `steveyegge/beads` CLI, not in beadloom.

35. [2026-02-17] [MEDIUM] Init doesn't offer `docs generate` — doc coverage 0% after bootstrap — After `beadloom init`, user must run `beadloom docs generate` + `beadloom reindex` separately. The init flow could offer doc skeleton generation as a final step.
    > **Deferred.** Enhancement to onboarding workflow. Current workaround exists. Planned for future init improvements.

36. [2026-02-17] [LOW] Existing docs not auto-linked to graph nodes — Target project had 20 existing docs in `docs/`. All reported as "unlinked from graph" by `doctor`. No auto-discovery mechanism to match existing docs to nodes by path or content similarity.
    > **Deferred.** Requires fuzzy doc-to-node matching — a standalone feature. Deferred to Phase 14+ (semantic analysis).

37. [2026-02-17] [INFO] `beadloom init` bootstrap quality metrics — Auto-generated graph captures ~35% of real architecture (Nodes 6→17, Edges 8→49, Symbols 23→380, Doc Coverage 0%→94% after manual improvement).
    > **Tracking.** Observation, not a bug. Baseline metric for future onboarding quality improvements.

---

## Closed Issues

### v1.8.0 — BDL-028 (TUI Bug Fixes)

> Phase 12.13. TUI stabilization round 3 — threading, Explorer dependencies, screen state.

58. ~~[2026-02-20] [MEDIUM] TUI: File watcher thread doesn't stop cleanly on exit~~ **FIXED (BDL-028 BEAD-01)** — Added `threading.Event` as `stop_event` passed to `watchfiles.watch(stop_event=...)`. On unmount, `stop_event.set()` is called, which makes `watchfiles.watch()` exit its blocking loop immediately.

59. ~~[2026-02-20] [MEDIUM] TUI: Domain nodes in graph tree not navigable to Explorer~~ **RECLASSIFIED (BDL-028 BEAD-02)** — UX navigation issue, not a code bug. Domain nodes (nodes with children) only expand/collapse on Enter — no way to open them in Explorer. Recognized as a feature request, now tracked as BEAD-01 in BDL-029 (see #61).

60. ~~[2026-02-20] [HIGH] TUI: Static widgets not updating after screen switch~~ **FIXED (BDL-028 BEAD-03)** — Changed `_push_content()` in `ContextPreviewWidget`, `NodeDetailPanel`, and `DependencyPathWidget` to use `update(self._build_text())` instead of `refresh()`. `Static.refresh()` only triggers a re-render of existing content, while `update()` actually replaces the widget's content with new Rich Text.

### v1.8.0 — BDL-029 (TUI UX Improvements)

> Phase 12.14. TUI usability improvements — domain navigation, tree icons, edge labels, screen switching.

61. ~~[2026-02-21] [MEDIUM] TUI: Explorer — no way to open domain nodes directly~~ **FIXED (BDL-029 BEAD-01)** — Domain nodes in graph tree only expand/collapse on Enter. Added `e` keybinding to Dashboard that opens Explorer for any highlighted node, including domain nodes with children.

62. ~~[2026-02-21] [MEDIUM] TUI: Triangle icon shown for childless nodes at cold start~~ **FIXED (BDL-029 BEAD-02)** — Some nodes (e.g. "tui") show expandable triangle icon but have no children at cold start. Root cause: `_build_tree` checked `ref_id in hierarchy` but hierarchy dict could contain entries with empty children lists `{"tui": []}`. Changed condition to `hierarchy.get(ref_id)` which is falsy for empty lists.

63. ~~[2026-02-21] [MEDIUM] TUI: Edge count `[N]` has no legend~~ **FIXED (BDL-029 BEAD-03)** — `[N]` numbers next to tree nodes have no explanation. Changed label format to `[N edges]` (plural), `[1 edge]` (singular), omit badge for 0.

64. ~~[2026-02-21] [HIGH] TUI: Esc (Back) from Explorer/DocStatus crashes with ScreenStackError~~ **FIXED (BDL-029 BEAD-04)** — Pressing Esc from Explorer or DocStatus after navigating via `switch_screen` (keys 1/2/3) crashes with `ScreenStackError: Can't pop screen`. Root cause: `action_go_back()` called `pop_screen()` but `switch_screen` navigation keeps only 1 screen on the stack. Fixed in both ExplorerScreen and DocStatusScreen by using `_safe_switch_screen("dashboard")`.

### v1.8.0 — BDL-025 (TUI), BDL-026 (Docs Audit), BDL-027 (UX Batch Fix)

> Phases 12.10–12.12. Dogfooding on beadloom itself and an external React Native + Expo project.

26. ~~[2026-02-16] [MEDIUM] Test mapping shows "0 tests in 0 files" for domains despite 1408+ tests~~ **FIXED (BDL-027 BEAD-05)** — `aggregate_parent_tests()` rolls up child node test counts to parent domain nodes.

29. ~~[2026-02-16] [HIGH] Route extraction false positives~~ **FIXED (BDL-027 BEAD-05)** — Self-exclusion added: files named `route_extractor` are skipped. Route aggregation scoped to source file ownership.

30. ~~[2026-02-16] [MEDIUM] Routes displayed with poor formatting in polish text~~ **FIXED (BDL-027 BEAD-05)** — `format_routes_for_display()` separates HTTP routes from GraphQL routes with wider columns.

32. ~~[2026-02-17] [HIGH] `beadloom init` scan_paths incomplete for React Native projects~~ **FIXED (BDL-027 BEAD-04)** — `detect_source_dirs()` now scans all top-level directories containing code files, not just manifest-adjacent ones.

33. ~~[2026-02-17] [MEDIUM] `beadloom init` is interactive-only — no CLI flags for automation~~ **FIXED (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

34. ~~[2026-02-17] [MEDIUM] Auto-generated `rules.yml` includes `service-needs-parent` that always fails on root~~ **FIXED (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

38. ~~[2026-02-19] [MEDIUM] `beadloom doctor` shows `[info]` not `[warn]` for nodes without docs~~ **FIXED (BDL-027 BEAD-03)** — Promoted from `Severity.INFO` to `Severity.WARNING`, making it actionable for agents and CI.

39. ~~[2026-02-20] [MEDIUM] Debt report "untracked: 8" — no way to see which files~~ **FIXED (BDL-027 BEAD-03)** — `_count_untracked()` now returns `(count, ref_ids)` list in both human and JSON output.

40. ~~[2026-02-20] [MEDIUM] Oversized false positive on root and parent nodes~~ **FIXED (BDL-027 BEAD-03)** — `_count_oversized()` counts only direct files, excluding subdirectories claimed by child node source prefixes.

41. ~~[2026-02-20] [HIGH] C4 diagram: all elements render as `System()` — no Container/Component differentiation~~ **FIXED (BDL-027 BEAD-01)** — `_compute_depths()` filters self-referencing `part_of` edges. BFS correctly computes depths.

42. ~~[2026-02-20] [MEDIUM] C4 diagram: label and description are identical~~ **FIXED (BDL-027 BEAD-01)** — Label generated from ref_id via title-casing + hyphen-to-space; summary used as description only.

43. ~~[2026-02-20] [MEDIUM] C4 diagram: root node appears inside its own boundary~~ **FIXED (BDL-027 BEAD-01)** — `_load_edges()` skips self-referencing `part_of` entries.

44. ~~[2026-02-20] [LOW] C4 diagram: boundary ordering is non-semantic~~ **FIXED (BDL-027 BEAD-01)** — Orphan boundaries sorted by node kind/depth; root rendered first, then alphabetical.

45. ~~[2026-02-20] [LOW] C4 diagram: `!include` always uses `C4_Container.puml`~~ **FIXED (BDL-027 BEAD-01)** — PlantUML `!include` selects `C4_Context.puml` / `C4_Container.puml` / `C4_Component.puml` based on `--level` flag.

46. ~~[2026-02-20] [HIGH] TUI: Graph tree empty — only "Architecture" label visible~~ **FIXED (BDL-025)** — Self-referencing `part_of` edge caused `get_hierarchy()` infinite loop. Added `if child != parent` filter.

47. ~~[2026-02-20] [HIGH] TUI: Activity widget shows 0% for all domains~~ **FIXED (BDL-025)** — Wrong attribute name: `commit_count` → `commits_30d`. Normalization: `min(commits_30d * 2, 100)`.

48. ~~[2026-02-20] [MEDIUM] TUI: Enter on tree node only expands — doesn't navigate to Explorer~~ **FIXED (BDL-025)** — Leaf-node detection added: if `ref_id not in hierarchy`, opens Explorer screen.

49. ~~[2026-02-20] [HIGH] TUI: Doc Status screen shows "–" for all Doc Path and Reason~~ **FIXED (BDL-025)** — DB opened as `mode=ro` but `check_sync()` needs writes. Switched to WAL mode read-write.

50. ~~[2026-02-20] [MEDIUM] TUI: Explorer shows self-referencing edges as duplicates~~ **FIXED (BDL-025)** — Added `dst != ref_id` / `src != ref_id` filter to edge lists.

51. ~~[2026-02-20] [MEDIUM] TUI: Explorer defaults to "Downstream Dependents" — empty for leaf nodes~~ **FIXED (BDL-025)** — Default changed to `MODE_UPSTREAM`. User presses `d` to switch to downstream.

52. ~~[2026-02-20] [HIGH] `docs audit` high false positive rate (~86%) on real project~~ **FIXED (BDL-027 BEAD-02)** — Skip numbers <10 for count facts, percentage FP filter, SPEC.md/CONTRIBUTING.md excluded from scan.

53. ~~[2026-02-20] [MEDIUM] `docs audit` year "2026" matched as mcp_tool_count~~ **FIXED (BDL-027 BEAD-02)** — Standalone year regex `\b20[0-9]{2}\b` added to false positive filters.

54. ~~[2026-02-20] [MEDIUM] `docs audit` SPEC.md files dominate false positives~~ **FIXED (BDL-027 BEAD-02)** — `_graph/features/*/SPEC.md` excluded from default scan paths.

55. ~~[2026-02-20] [LOW] `docs audit` test_count ground truth seems inflated~~ **FIXED (BDL-027 BEAD-02)** — Labeled as symbol count in output; documented distinction between test symbols and test cases.

56. ~~[2026-02-20] [LOW] `docs audit` Rich output lacks file path context~~ **FIXED (BDL-027 BEAD-02)** — Stale mentions show full relative path from project root.

57. ~~[2026-02-20] [MEDIUM] `docs audit` version fact not collected for dynamic versioning~~ **FIXED (BDL-027 BEAD-02)** — Detects `dynamic = ["version"]` + `[tool.hatch.version]`; fallback to `importlib.metadata.version()`.

### v1.6.0 — BDL-017 (Context Oracle), BDL-019 (Docs Refresh)

16. ~~[2026-02-13] [MEDIUM] After BDL-012 bug-fixes, beadloom's own docs are outdated~~ **FIXED (BDL-019)** — All 13 domain/service docs refreshed. `symbols_changed` reduced from 35 to 0.

27. ~~[2026-02-16] [LOW] `docs polish` text format doesn't include routes/activity/tests data~~ **FIXED (BDL-017 BEAD-14)** — Smart `docs polish` now includes routes, activity level, test mappings, and deep config data.

28. ~~[2026-02-16] [INFO] `beadloom status` Context Metrics section working well~~ **CLOSED** — Confirmed working. No action needed.

### v1.5.0 — BDL-015 (Stabilization), BDL-016 (E2E Baseline)

15. ~~[2026-02-13] [HIGH] `doctor` 100% coverage + `Stale docs: 0` is misleading after major code changes~~ **FIXED (BDL-015 + BDL-016)** — Symbol-level drift detection via `_compute_symbols_hash()` + `_check_symbol_drift()`.

17. ~~[2026-02-14] [LOW] `setup-rules` auto-detect doesn't work for Windsurf and Cline~~ **FIXED (BDL-015 BEAD-12)** — Content-based detection instead of file presence.

18. ~~[2026-02-14] [HIGH] `sync-check` reports "31/31 OK" despite massive semantic drift~~ **FIXED (BDL-015 + BDL-016)** — Symbol-level drift detection works end-to-end.

19. ~~[2026-02-14] [MEDIUM] `.beadloom/AGENTS.md` not auto-generated during bootstrap~~ **FIXED (BDL-015 BEAD-06)**.

21. ~~[2026-02-14] [HIGH] Incremental reindex returns Nodes: 0 after YAML edit~~ **FIXED (BDL-015 BEAD-11)**.

22. ~~[2026-02-15] [HIGH] `.claude/CLAUDE.md` references obsolete project phases~~ **FIXED** — Updated phases, docs references.

23. ~~[2026-02-15] [HIGH] `/templates` has wrong project structure~~ **FIXED** — Fully rewritten with stabilized format.

24. ~~[2026-02-15] [HIGH] `/test` has wrong import paths~~ **FIXED** — Updated all paths and patterns.

25. ~~[2026-02-15] [MEDIUM] `/review` references old architecture layers~~ **FIXED** — Updated layer names.

### v1.0.0–v1.4.0 — BDL-012 (Bug Fixes), early fixes

1. ~~[2026-02-13] [MEDIUM] `doctor` warns about auto-generated skeleton docs as "unlinked from graph"~~ **FIXED** — `generate_skeletons()` writing to wrong paths. Fixed by using `docs:` paths from graph.

2. ~~[2026-02-13] [LOW] `lint` produces no output on success~~ **FIXED** — CLI now prints `"0 violations, N rules evaluated"` as confirmation.

3. ~~[2026-02-13] [LOW] `docs generate` creates skeleton files for services including the root~~ **FIXED** — Root detection changed from "empty source" to "no `part_of` edge as src".

4. ~~[2026-02-13] [INFO] MCP server description says "8 tools" / CLI "18 commands"~~ **FIXED** — services.yml updated to 20 commands, 9 tools.

5. ~~[2026-02-13] [HIGH] `doctor` shows 0% doc coverage on bootstrapped projects~~ **FIXED (BDL-012 BEAD-01)** — `generate_skeletons()` writes `docs:` field back to `services.yml` via `_patch_docs_field()`.

6. ~~[2026-02-13] [HIGH] `lint` false positives on hierarchical projects~~ **FIXED (BDL-012 BEAD-02)** — Rule engine accepts empty `has_edge_to: {}`. `service-needs-parent` removed.

7. ~~[2026-02-13] [MEDIUM] Dependencies empty in polish data~~ **FIXED (BDL-012 BEAD-03)** — `generate_polish_data()` reads `depends_on` edges from SQLite via `_enrich_edges_from_sqlite()`.

8. ~~[2026-02-13] [MEDIUM] `docs polish` text format = 1 line~~ **FIXED (BDL-012 BEAD-03)** — `format_polish_text()` renders multi-line output with node details, symbols, deps, doc status.

9. ~~[2026-02-13] [LOW] Generic summaries~~ **FIXED (BDL-012 BEAD-06)** — `_detect_framework_summary()` detects Django apps, React components, Python packages, Dockerized services.

10. ~~[2026-02-13] [LOW] Parenthesized ref_ids from Expo router~~ **FIXED (BDL-012 BEAD-06)** — `_sanitize_ref_id()` strips parentheses: `(tabs)` → `tabs`.

11. ~~[2026-02-13] [MEDIUM] Missing language parsers — 0 symbols with no warning~~ **FIXED (BDL-012 BEAD-05)** — `check_parser_availability()` + `_warn_missing_parsers()` in CLI.

12. ~~[2026-02-13] [LOW] `reindex` ignores new parser availability~~ **FIXED (BDL-012 BEAD-06)** — Parser fingerprint tracked in `file_index`. Extension changes trigger full reindex.

13. ~~[2026-02-13] [INFO] Bootstrap skeleton count includes pre-existing files~~ **FIXED (BDL-012 BEAD-06)** — CLI shows "N created, M skipped (pre-existing)".

14. ~~[2026-02-13] [MEDIUM] Preset misclassifies mobile apps as microservices~~ **FIXED (BDL-012 BEAD-04)** — `detect_preset()` checks for React Native/Expo and Flutter before `services/` heuristic.
