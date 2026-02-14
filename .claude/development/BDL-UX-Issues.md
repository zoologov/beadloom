# BDL UX Feedback Log

> Collected during implementation of Plug & Play Onboarding.
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

15. [2026-02-13] [HIGH] `doctor` 100% coverage + `Stale docs: 0` is misleading after major code changes — `doctor` checks only that a doc file is linked to a graph node (existence), NOT that the doc content reflects the actual code. After BDL-012 added ~2000 lines and 12 new functions (`_patch_docs_field`, `_enrich_edges_from_sqlite`, `format_polish_text`, `check_parser_availability`, `_detect_framework_summary`, `_sanitize_ref_id`, etc.), `doctor` still reports "100% coverage, 0 stale". In reality, domain READMEs and feature SPECs describe pre-BDL-012 state and are outdated. Stale detection (`sync_state`) compares file hashes between reindexes but doesn't detect semantic drift (code changed, doc didn't). This is a **product-level problem**: beadloom's killer feature is doc-code sync, but agents relying on `doctor` and `status` will work with stale specs thinking they're current. Fix options: (a) compare code_symbols hash vs doc hash per node — if code changed but doc didn't, mark as stale; (b) include symbol diff in `docs polish` output to highlight what's new/removed; (c) `doctor` should warn "N nodes have code changes since last doc update".

16. [2026-02-13] [MEDIUM] After BDL-012 bug-fixes, beadloom's own docs are outdated — Specific files needing update: `docs/domains/onboarding/README.md` (missing `_patch_docs_field`, `_sanitize_ref_id`, `format_polish_text`, `check_parser_availability`), `docs/domains/onboarding/features/doc-generator/SPEC.md` (missing SQLite edges enrichment, text format, docs: writeback), `docs/domains/graph/features/rule-engine/SPEC.md` (missing empty matcher `{}`), `docs/domains/infrastructure/README.md` (missing parser fingerprint in reindex). Should be fixed immediately as a hygiene task.

17. [2026-02-14] [LOW] `setup-rules` auto-detect doesn't work for Windsurf and Cline — For windsurf (`.windsurfrules`) and cline (`.clinerules`), the IDE marker file IS the same path as the rules file. This means `setup_rules_auto()` can never auto-create these files: if the marker exists, the file exists and is skipped. Only Cursor has a distinct marker (`.cursor/` directory) separate from `.cursorrules`. Users must use `beadloom setup-rules --tool windsurf` or `--tool cline` explicitly. Consider: (a) using different markers (e.g., `.windsurf/` directory for Windsurf), (b) documenting this clearly, (c) checking if the existing file is already a beadloom adapter and skipping only if it's user-written.

18. [2026-02-14] [HIGH] `sync-check` reports "31/31 OK" despite massive semantic drift in docs — After BDL-011 through BDL-014 added 3 CLI commands (`prime`, `setup-rules`, `setup-mcp`), 2 MCP tools (`generate_docs`, `prime`), and multiple new functions, `sync-check` still showed all pairs as synchronized. Meanwhile: README.md said "18 CLI commands" (actual: 21), "8 MCP tools" (actual: 10); docs/architecture.md same; docs/services/mcp.md used `ref_ids` (array) for parameter names that are actually `ref_id` (singular); docs/services/cli.md documented `--ref` flag but code has `--ref-id`; docs/domains/onboarding/README.md was missing 3 exported functions; `getting-started.md` said "Python only" but 4 languages are supported. **Root cause:** same as #15 — sync-check tracks file-level hash changes between reindexes but can't detect when code and docs diverge semantically. This is concrete evidence that the current sync model misses real staleness.

19. [2026-02-14] [MEDIUM] `.beadloom/AGENTS.md` not auto-generated during `beadloom init --bootstrap` — After BDL-014 added `generate_agents_md()` and the `beadloom prime --update` flag, the AGENTS.md file is still not generated automatically during bootstrap. The bootstrap flow calls `setup_rules_auto()` (added in BDL-014 D6) but NOT `generate_agents_md()`. Users must run `beadloom prime --update` manually after init. Consider calling `generate_agents_md()` from `bootstrap_project()` alongside `setup_rules_auto()`.

20. [2026-02-14] [LOW] `.beadloom/README.md` MCP tools list was stale after BDL-014 — Listed 8 tools, missing `get_status` and `prime`. The file is generated once by BDL-013 but never auto-updated. Unlike AGENTS.md which has `generate_agents_md()`, README.md has no regeneration mechanism. Low severity because `.beadloom/README.md` is a static guide, not agent-facing.

21. [2026-02-14] [HIGH] `beadloom reindex` (incremental) returns `Nodes: 0, Edges: 0` after `services.yml` edit — After changing the root node summary in `.beadloom/_graph/services.yml` (version string update), `beadloom reindex` (incremental, default mode) reported `Nodes: 0, Edges: 0, Docs: 1`. A `beadloom reindex --full` correctly showed `Nodes: 20, Edges: 36`. The incremental reindex appears to either skip graph YAML reloading entirely or fail silently when graph YAML changes. Users who edit `services.yml` and run `beadloom reindex` without `--full` will get a corrupted index. **Workaround:** always use `beadloom reindex --full` after editing graph YAML files.
