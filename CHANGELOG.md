# Changelog

All notable changes to Beadloom are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2026-02-20

Interactive Architecture TUI (Phase 12.10). 207 TUI tests.

### Added
- **Multi-screen TUI** -- 3-screen architecture workstation with Dashboard, Explorer, and Doc Status screens (`beadloom tui`)
- **7 data providers** -- thin read-only wrappers over existing infrastructure APIs (Graph, Lint, Sync, Debt, Activity, Why, Context)
- **GraphTreeWidget** -- interactive architecture hierarchy tree with doc status indicators (fresh/stale/missing) and edge count badges
- **DebtGaugeWidget** -- debt score display with severity coloring (green/yellow/red)
- **LintPanelWidget** -- violation counts with severity icons and individual violation details
- **ActivityWidget** -- per-domain git activity progress bars with color coding
- **StatusBarWidget** -- health metrics, watcher status indicator, auto-dismissing notifications
- **NodeDetailPanel** -- node deep-dive with ref_id, kind, summary, source, edges, doc status
- **DependencyPathWidget** -- upstream/downstream dependency tree visualization with impact summary
- **ContextPreviewWidget** -- context bundle preview with token estimation
- **DocHealthTable** -- per-node documentation health table with coverage tracking and row selection
- **FileWatcherWorker** -- background file watcher with 500ms debounce, extension filtering, `ReindexNeeded` messages
- **SearchOverlay** -- modal FTS5 search with LIKE fallback and result navigation
- **HelpOverlay** -- modal keybinding reference organized by context
- **17 keyboard bindings** -- screen switching (1/2/3), navigation, actions (r/l/s/S), overlays (?//)
- `beadloom tui` command (primary), `beadloom ui` kept as alias
- `--no-watch` flag to disable file watcher

### Changed
- Textual dependency upgraded from `>=0.50` to `>=0.80`

## [1.7.0] - 2026-02-17

AaC Rules v2, Init Quality, and Architecture Intelligence. 1657 tests.

### Added
- **NodeMatcher** — tag/kind-based node matching for rule definitions; `matches(ref_id, kind, tags=)` method (BDL-021 BEAD-01)
- **Node tags/labels** — tags stored in `extra` JSON column, bulk assignment via `tags:` block in rules.yml v3; `get_node_tags()` API (BDL-021 BEAD-01)
- **ForbidEdgeRule** — deny rules evaluated against `edges` table (vs DenyRule which checks `code_imports`); supports tag-based matching (BDL-021 BEAD-02)
- **LayerRule** — enforce layered architecture: define ordered layers with `allow_skip`, violation on reverse-direction edges (BDL-021 BEAD-03)
- **CycleRule** — circular dependency detection via iterative DFS; configurable `edge_kind` (single or tuple) and `max_depth`; reports full cycle path (BDL-021 BEAD-04)
- **ImportBoundaryRule** — file-level import restrictions using fnmatch glob patterns on `code_imports` file paths (BDL-021 BEAD-05)
- **CardinalityRule** — architectural smell detection: `max_symbols`, `max_files`, `min_doc_coverage` thresholds per node (BDL-021 BEAD-06)
- **Rules schema v3** — top-level `tags:` block for bulk tag assignments; backward compatible with v1/v2 (BDL-021 BEAD-01)
- **`load_rules_with_tags()`** — returns both rules and tag assignments from rules.yml (BDL-021 BEAD-01)
- **Architecture snapshots** — `beadloom snapshot save/list/compare`: save graph state to `graph_snapshots` table, list history, compare any two snapshots (BDL-021 BEAD-12)
- **Enhanced diff** — `NodeChange` now tracks source path changes, tag changes, symbol counts; `compute_diff_from_snapshot()` for snapshot-based comparison (BDL-021 BEAD-13)
- **Non-interactive init** — `beadloom init --mode bootstrap --yes --force` for CI/scripts; `non_interactive_init()` API (BDL-021 BEAD-08)
- **Doc auto-linking** — `auto_link_docs()` fuzzy-matches existing docs to graph nodes by path/ref_id similarity during init (BDL-021 BEAD-11)
- **Docs generate in init** — `beadloom init` offers doc skeleton generation as a final step (BDL-021 BEAD-10)
- **Enhanced `why --reverse`** — `render_why_tree()` for reverse dependency view; `--reverse` and `--format` flags on CLI (BDL-021 BEAD-14)
- **Scan all code directories** — bootstrap now scans all top-level dirs with code files, not just manifest-adjacent ones (BDL-021 BEAD-07)
- **249 new tests** (1657 total)

### Changed
- **Rule engine** — `Rule` type union expanded: `DenyRule | RequireRule | CycleRule | ImportBoundaryRule | ForbidEdgeRule | LayerRule | CardinalityRule`
- **`evaluate_all()`** — dispatches all 7 rule types (was 2)
- **`render_diff()`** — shows source path changes, tag changes, symbol counts for changed nodes
- **4 domain docs refreshed** — context-oracle, graph, onboarding, cli documentation updated

### Fixed
- **Root service rule** — `service-needs-parent` rule no longer fails on root node; root detection uses `part_of` edge presence (BDL-021 BEAD-09)

## [1.6.0] - 2026-02-17

Deep Code Analysis, Honest Doc-Sync, and Agent Infrastructure. 1408 tests.

### Added
- **API route extraction** — tree-sitter + regex detection for 12 frameworks: FastAPI, Flask, Django, Express, NestJS, Spring Boot, Gin, Echo, Fiber, Actix, GraphQL (schema + code-first), gRPC (BDL-017 BEAD-01)
- **Git history analysis** — `analyze_git_activity()` classifies modules as hot/warm/cold/dormant based on 6-month commit history (BDL-017 BEAD-02)
- **Test mapping** — `map_tests()` detects test framework (pytest, jest, go test, JUnit, XCTest) and maps test files to source modules (BDL-017 BEAD-03)
- **Rule severity levels** — rules support `severity: warn` vs `severity: error` (default); `beadloom lint` shows both, `--strict` fails only on errors; backward-compatible v1→v2 migration (BDL-017 BEAD-04)
- **MCP tool `why`** — impact analysis via MCP: upstream dependencies + downstream dependents as structured JSON (BDL-017 BEAD-05)
- **MCP tool `diff`** — graph changes since a git ref via MCP (BDL-017 BEAD-06)
- **MCP tool `lint`** — architecture validation via MCP with severity in JSON output (BDL-017 BEAD-12)
- **Deep config reading** — extracts scripts, workspaces, path aliases from pyproject.toml, package.json, tsconfig.json, Cargo.toml, build.gradle (BDL-017 BEAD-07)
- **Context cost metrics** — `beadloom status` shows average/max bundle sizes in estimated tokens (BDL-017 BEAD-08)
- **Smart `docs polish`** — enriched with routes, activity, tests, config data from deep analysis (BDL-017 BEAD-14)
- **AGENTS.md v3** — now documents 13 MCP tools (was 10) (BDL-017 BEAD-15)
- **3-layer staleness detection** — `check_sync()` now detects: `symbols_changed` (hash mismatch), `untracked_files` (files in source dir not tracked), `missing_modules` (doc doesn't mention module) (BDL-018)
- **Source coverage check** — `check_source_coverage()` finds Python files in node source directories not tracked in sync_state or code_symbols (BDL-018 BEAD-02)
- **Doc coverage check** — `check_doc_coverage()` verifies documentation mentions all modules in source directory (BDL-018 BEAD-03)
- **Hierarchy-aware coverage** — `check_source_coverage()` queries `part_of` edges to recognize files annotated to child feature nodes as tracked under parent domain (BDL-020 BEAD-02)
- **`/tech-writer` role** — new agent skill for systematic documentation updates using sync-check + ctx + sync-update workflow (BDL-019)
- **`/task-init` skill** — unified task initialization for all types (epic, feature, bug, task, chore); replaces `/epic-init` (BDL-021)
- **`BRIEF.md` template** — simplified doc format for bug/task/chore (one-approval flow)
- **255 new tests** (1408 total)

### Changed
- **`sync-check` CLI output** — now shows reason (symbols_changed, untracked_files, missing_modules) and details per stale entry (BDL-018)
- **`sync-check --json`** — structured JSON output with `reason` and `details` fields (BDL-018)
- **Routes/activity/tests integrated into reindex** — stored as JSON in `nodes.extra` during full and incremental reindex (BDL-017 BEAD-09, BEAD-10, BEAD-11)
- **Deep config integrated into bootstrap** — config data in root node `extra.config` (BDL-017 BEAD-13)
- **13 domain/service docs refreshed** — all documentation updated to match current code (BDL-019)
- **`.claude/commands/templates.md`** — stabilized: no numbered sections, strict status lifecycle (Draft/Approved/Done)
- **`.claude/CLAUDE.md`** — added `/task-init`, `/tech-writer`; updated file memory to include BRIEF.md

### Fixed
- **Symbol drift detection E2E** — `incremental_reindex()` now preserves `symbols_hash` baseline across reindexes (BDL-016)
- **`_compute_symbols_hash()` annotation query** — fixed to handle both `"ref_id"` and `["ref_id"]` JSON formats (BDL-018 BEAD-01)
- **Sync baseline preservation** — `_snapshot_sync_baselines()` preserves symbol hashes during full reindex (BDL-018 BEAD-01)
- **4 annotation mismatches** — `why.py` (was `impact-analysis`→`context-oracle`), `doctor.py` (was `doctor`→`infrastructure`), `watcher.py` (was `watcher`→`infrastructure`), `app.py` (was missing→`tui`) (BDL-020 BEAD-01)

## [1.5.0] - 2026-02-16

Smart Bootstrap v2, Doc Sync v2, 5 new languages, and a full documentation overhaul. 1153 tests.

### Changed
- **README.md + README.ru.md** — rewritten with new positioning: "Architecture as Code → Architectural Intelligence"; Agent Prime as flagship feature; real dogfooding examples; research references; full EN/RU parity
- **`docs/architecture.md`** — rewritten: 13 SQLite tables (was 7), 22 CLI commands (was 21), 9 import analysis languages (was 4); new sections: Rules Engine, Cache Architecture, Incremental Reindex, Health Snapshots, Agent Prime, Configuration
- **`.claude/CLAUDE.md`** — Beadloom dogfooding: `beadloom prime` as first session step, `beadloom ctx`/`why` for context discovery, expanded CLI reference (17 commands)
- **`.claude/commands/*`** — all 7 skills updated with Beadloom integration (`prime`, `ctx`, `why`, `search`, `lint --strict`)
- **Social preview** — `.github/social-preview.svg` for GitHub/messenger previews

### Added
- **README/doc ingestion** — `_ingest_readme()` extracts project description, tech stack, and architecture notes from README.md, CONTRIBUTING.md, ARCHITECTURE.md
- **Extended framework detection (18+)** — FastAPI, Flask, Django, Express, NestJS, Angular, Next.js, Vue, Spring Boot, Actix, Gin, SwiftUI, Jetpack Compose, React Native, Expo, and more
- **Entry point discovery** — `_discover_entry_points()` detects CLI tools (Click, Typer, argparse), server entry points, `__main__.py`, and `func main()` across 6 languages
- **Import analysis at bootstrap** — `_quick_import_scan()` infers `depends_on` edges between clusters from import statements (capped at 50)
- **Contextual node summaries** — `_build_contextual_summary()` combines framework, symbols, README excerpt, and entry points into rich summaries like "FastAPI service: auth — JWT auth, 3 classes, 5 fns"
- **Symbol-level drift detection** — `_compute_symbols_hash()` tracks SHA-256 of code symbols per ref_id; `check_sync()` detects semantic drift even when file hashes match
- **Doctor drift warnings** — `_check_symbol_drift()` and `_check_stale_sync()` surface drift/stale entries in `beadloom doctor`
- **Symbol diff in polish** — `_detect_symbol_changes()` shows drift warnings in `beadloom docs polish` output
- **`service-needs-parent` rule** — auto-generated require rule: every service node must have a `part_of` edge
- **Kotlin support** — `_load_kotlin()`, `_extract_kotlin_imports()` with stdlib filtering (kotlin.*, kotlinx.*, java.*, javax.*, android.*)
- **Java support** — `_load_java()`, `_extract_java_imports()` with static/wildcard imports and stdlib filtering
- **Swift support** — `_load_swift()`, `_extract_swift_imports()` with 35 Apple framework filters
- **C/C++ support** — `_load_c()`, `_load_cpp()`, `_extract_c_cpp_imports()` with 80+ system header filters; extended `_get_symbol_name()` for declarator chains
- **Objective-C support** — `_load_objc()`, `_extract_objc_imports()` with #import/#include and @import support; 48 system framework filters
- **306 new tests** (1153 total)

### Fixed
- **Reindex graph YAML detection** — `_graph_yaml_changed()` checks graph files before `_diff_files` to catch changes even with stale `file_index`
- **AGENTS.md template** — added `beadloom ctx <ref-id>` and `beadloom search "<query>"` CLI commands
- **Content-aware `setup_rules_auto()`** — detects beadloom adapter files vs user content; updates adapters, skips user files

## [1.4.0] - 2026-02-14

Agent Prime: cross-IDE context injection for AI agents. Full documentation audit.

### Added
- **`beadloom prime`** — output compact project context (architecture summary, health, rules, domains) for AI agent session start
- **`prime` MCP tool** — 10th tool; returns JSON context for agent sessions
- **`beadloom setup-rules`** — create IDE adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) that reference `.beadloom/AGENTS.md`
- **AGENTS.md v2** — `generate_agents_md()` produces `.beadloom/AGENTS.md` with MCP tool list, architecture rules from `rules.yml`, and `## Custom` section preservation
- **`prime_context()`** — three-layer architecture: static config + dynamic DB queries with graceful degradation
- **`setup_rules_auto()`** — auto-detect IDEs by marker files; integrated into `beadloom init --bootstrap`
- **`agent-prime` graph node** — 20th node in architecture graph (feature under onboarding)
- **Architecture lint CI** — `.github/workflows/beadloom-aac-lint.yml` runs `beadloom lint --strict` on PRs
- **Known Issues section** — README.md and README.ru.md link to UX Issues Log
- **36 new tests** (847 total)

### Fixed
- **12 documentation discrepancies** — README/architecture/CLI/MCP docs all said "18 commands, 8 tools" (actual: 21 commands, 10 tools); `docs polish` documented `--ref` flag but code uses `--ref-id`; MCP docs used `ref_ids` (array) but schema is `ref_id` (string); `list_nodes` had undocumented `kind` filter; onboarding README missing 3 exported functions; infrastructure README missing 5 reindex pipeline steps; getting-started.md said "Python only" (supports 4 languages); root graph node said "v1.3.0" (was v1.3.1)
- **`docs/getting-started.md`** — fully rewritten to reflect current bootstrap flow (rules, skeletons, MCP, IDE adapters, sync-check)
- **`.beadloom/README.md`** — added missing `get_status` and `prime` to MCP tools list

## [1.3.1] - 2026-02-13

Onboarding Quality: 10 bug-fixes from dogfooding on real projects (cdeep, dreamteam).

### Fixed
- **Doctor 0% coverage** — `generate_skeletons()` writes `docs:` field back to services.yml (cdeep: 0% → 95%, dreamteam: 0% → 83%)
- **Lint false positives** — empty `has_edge_to: {}` matcher (any node), removed `service-needs-parent` rule (cdeep: 33 → 0 violations)
- **Polish deps empty** — `generate_polish_data()` reads `depends_on` edges from SQLite post-reindex
- **Polish text = 1 line** — new `format_polish_text()` with node details, symbols, deps, doc status
- **Preset misclassifies mobile** — `detect_preset()` checks React Native/Expo/Flutter before `services/` heuristic
- **Missing parser warning** — `check_parser_availability()` warns about missing tree-sitter grammars in bootstrap/reindex
- **Generic summaries** — detects Django apps, React components, Python packages, Dockerized services
- **Parenthesized ref_ids** — strips `()` from Expo router dirs (`(tabs)` → `tabs`)
- **Reindex ignores parsers** — parser fingerprint tracked; new parsers trigger full reindex
- **Skeleton count** — CLI shows "N created, M skipped (pre-existing)"

## [1.3.0] - 2026-02-13

Plug & Play Onboarding: from install to first useful result in one command.

### Added
- **`beadloom docs generate`** — generate doc skeletons (architecture.md, domain READMEs, service pages, feature SPECs) from knowledge graph
- **`beadloom docs polish`** — structured JSON/text output with code symbols, Mermaid diagrams, and AI enrichment prompts for agent-driven doc polish
- **`generate_docs` MCP tool** — 9th tool, returns polish data as JSON for AI agents
- **Auto-rules generation** — `beadloom init --bootstrap` now generates `rules.yml` with structural require rules (domain-needs-parent, feature-needs-domain, service-needs-parent)
- **Auto MCP config** — bootstrap auto-detects editor (Cursor, Windsurf, Claude Code) and creates `.mcp.json`
- **Root node + project name detection** — reads name from pyproject.toml/package.json/go.mod/Cargo.toml with directory fallback
- **Enhanced init output** — summary with Graph/Rules/Docs/MCP/Index counts and Next steps
- **Doc-generator feature** — added to knowledge graph under onboarding domain
- **13 end-to-end integration tests** — full pipeline from bootstrap through docs generate/polish with idempotency checks

## [1.2.0] - 2026-02-13

DDD restructuring: code, docs, and knowledge graph now follow domain-driven design.

### Changed
- **Code → DDD packages** — flat modules reorganized into 5 domain packages (`infrastructure/`, `context_oracle/`, `doc_sync/`, `onboarding/`, `graph/`) with `__init__.py` re-exports
- **Package names aligned to docs** — `context/` → `context_oracle/`, `sync/` → `doc_sync/`, `infra/` → `infrastructure/`
- **Services layer** — `cli.py` and `mcp_server.py` moved into `services/` package
- **Loose files absorbed** — `doctor.py` → `infrastructure/`, `watcher.py` → `infrastructure/`, `why.py` → `context_oracle/`
- **Docs → domain-first layout** — `docs/` restructured into `domains/`, `services/`, `guides/` directories
- **Knowledge graph updated** — 18 nodes (5 domains, 3 services, 9 features, 1 root), 32+ edges reflecting DDD structure; `doctor` and `watcher` reclassified as features under `infrastructure`
- **Architecture lint rules** — 2 rules: `domain-needs-parent`, `feature-needs-domain`
- **CLI reference** — all 18 commands documented
- **MCP docs** — all 8 tools documented
- **Doc coverage 100%** — SPEC.md for all 9 features (cache, search, why, graph-diff, rule-engine, import-resolver, doctor, reindex, watcher) + TUI service doc
- **`guides/ci-setup.md`** — linked to `beadloom` root node in knowledge graph
- **`architecture.md` constraints** — updated for multi-language support and configurable paths
- **`import-resolver` summary** — corrected from "Python import analysis" to "Multi-language import analysis"
- **README.md + README.ru.md** — abstract examples replaced with real Beadloom data (architecture rules, docs tree, context bundle example)

### Fixed
- Circular import in `graph/linter.py` resolved via lazy import of `incremental_reindex`
- Integration tests updated for new graph structure (domain nodes instead of `linter` node)

## [1.1.0] - 2026-02-12

Improved import analysis and broader project support.

### Added
- **Deep import analysis** — `depends_on` edges generated from resolved imports between graph nodes
- **Hierarchical source-prefix resolver** — handles Django-style imports (`apps.core.models`), TypeScript `@/` aliases, and nodes with/without trailing slash
- **Auto-reindex after init** — no more manual `beadloom reindex` needed after `--bootstrap` or interactive setup
- **Noise directory filtering** — `static`, `templates`, `migrations`, `fixtures`, `locale`, `media`, `assets` excluded from architecture node generation

### Fixed
- Source dir discovery expanded (`backend`, `frontend`, `server`, `client`, etc.) with fallback to scanning all non-vendor dirs
- `reindex` and `import_resolver` now read `scan_paths` from `config.yml` instead of hardcoding `src/lib/app`
- `node_modules` and other junk dirs filtered from recursive scans
- `.vue` files recognized as code extensions

## [1.0.0] - 2026-02-11

Architecture as Code: Beadloom evolves from documentation tool to architecture enforcement platform.

### Added
- **`beadloom lint`** — validate code against architecture boundary rules defined in YAML
- **Rule engine** — declarative `rules.yml` with `deny` and `require` directives
- **Import resolver** — static analysis for Python, TypeScript/JavaScript, Go, and Rust
- **Agent-aware constraints** — `get_context` MCP tool returns active rules alongside context
- **CI architecture gate** — `beadloom lint --strict` exits 1 on violations

### Fixed
- `beadloom ui` traceback when textual not installed (lazy import guard)
- TUI shows real data — edges, docs, sync status, proper counts
- `beadloom reindex` shows "up to date" with DB totals when nothing changed
- `beadloom watch` traceback when watchfiles not installed

## [0.7.0] - 2026-02-11

Developer Experience: interactive exploration and real-time feedback.

### Added
- **`beadloom ui`** — interactive terminal dashboard (Textual) for browsing domains, nodes, and edges
- **`beadloom why REF_ID`** — impact analysis showing upstream deps and downstream dependents
- **`beadloom diff`** — show graph changes since a git ref (nodes/edges added, removed, modified)
- **`beadloom watch`** — auto-reindex on file changes during development

## [0.6.0] - 2026-02-10

Performance and agent-native evolution: caching, search, and write operations.

### Added
- **L1 in-memory cache** — ContextCache integrated with MCP server for token savings
- **L2 SQLite cache** — persistent `bundle_cache` table survives MCP restarts
- **Incremental reindex** — `file_index` tracks hashes, only re-processes changed files
- **Auto-reindex in MCP** — detects stale index, triggers incremental reindex before responding
- **FTS5 full-text search** — `beadloom search` command + MCP `search` tool
- **MCP write tools** — `update_node`, `mark_synced` for agent-driven graph updates
- **`beadloom search`** — CLI command for searching nodes, docs, and code symbols

### Removed
- `sync-update --auto` flag and `llm_updater.py` — Beadloom is now fully agent-native with no LLM API dependency

## [0.5.0] - 2026-02-10

Team adoption: CI integration, health metrics, and external linking.

### Added
- **CI integration** — `beadloom sync-check --porcelain` for GitHub Actions / GitLab CI
- **Health dashboard** — `beadloom status` shows doc coverage trends, stale doc counts
- **`beadloom link`** — connect graph nodes to Jira, GitHub Issues, Linear
- **MCP templates** — ready-made `.mcp.json` snippets for Cursor, Claude Code, Windsurf

## [0.4.0] - 2026-02-10

Lower the barrier: from install to useful context in under 5 minutes.

### Added
- **Architecture presets** — `beadloom init --preset {monolith,microservices,monorepo}`
- **Smarter bootstrap** — infers domains from directory structure, detects common patterns
- **Zero-doc mode** — graph-only workflow without any Markdown files
- **Interactive bootstrap review** — confirm/edit generated nodes before committing

## [0.3.0] - 2026-02-10

Foundation and agent-native pivot.

### Added
- **AGENTS.md generation** — `beadloom reindex` produces `.beadloom/AGENTS.md` for AI agents
- **README rewrite** — new positioning, value proposition, comparison table
- **README.ru.md** — Russian translation

### Changed
- Deprecated `sync-update --auto` in favor of agent-native workflow
- Annotation coverage improved to 100% across all modules

## [0.2.0] - 2026-02-09

Extended features: interactive sync, multi-language indexing, PyPI publishing.

### Added
- `sync-update --auto` — LLM-assisted doc update (later removed in v0.6)
- Interactive `sync-update` review mode
- Multi-language tree-sitter indexer
- Init wizard for guided project setup
- PyPI publishing workflow with dynamic versioning
- End-to-end test suite

### Fixed
- Module-level annotation parsing
- Doc ref_map collision on duplicate prefixes
- Heading collision in Mermaid graph output

## [0.1.0] - 2026-02-09

Initial release: Context Oracle + Doc Sync Engine.

### Added
- **Context Oracle** — BFS graph traversal, deterministic context bundles
- **Doc Sync Engine** — code-to-doc relationship tracking, staleness detection
- **Knowledge graph** — YAML-based node/edge definition
- **MCP server** — stdio transport with `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`
- **CLI** — `init`, `reindex`, `ctx`, `graph`, `status`, `doctor`, `sync-check`, `sync-update`
- **Tree-sitter indexer** — Python source code annotation extraction
- **Git hooks** — pre-commit doc sync check
- mypy strict mode, 91% test coverage, MIT license
