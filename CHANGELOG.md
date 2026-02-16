# Changelog

All notable changes to Beadloom are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
