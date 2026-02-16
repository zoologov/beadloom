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

31. [2026-02-16] [LOW] `bd dep remove` says "✓ Removed" but dependency persists — Running `bd dep remove beadloom-3v0 beadloom-53o` reports success, but `bd show beadloom-3v0` still shows the dependency and `bd blocked` still lists it as blocked. Workaround: `bd update --status in_progress --claim` works regardless of blocks. **→ Beads CLI bug, not beadloom**

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
