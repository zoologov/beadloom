# Onboarding

Project bootstrap, documentation import, and architecture-aware initialization.

## Specification

### Modules

- **scanner.py** — `bootstrap_project()` scans source directories, classifies subdirectories using preset rules, infers edges from directory nesting, generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`. Also detects project name, generates architecture rules, configures MCP for the detected editor, and creates IDE adapter files via `setup_rules_auto()`. Provides `import_docs()` for classifying existing .md files (ADR, feature, architecture, other). `generate_rules()` creates structural rules with empty `has_edge_to: {}` matcher for hierarchy validation. `_detect_framework_summary()` detects 20+ framework patterns (Django, Flask, FastAPI, NestJS, Angular, Next.js, Expo, React Native, Spring Boot, Actix, Gin, Vue, SwiftUI, Jetpack Compose, UIKit, Express, etc.). `_build_contextual_summary()` combines framework detection, tree-sitter symbol counts, README excerpts, and entry-point labels into a 120-char summary. `_sanitize_ref_id()` strips parentheses from Expo router dirs. `generate_agents_md()` creates `.beadloom/AGENTS.md` with MCP tool list (13 tools) and architecture rules (preserves user content below `## Custom`). `prime_context()` returns compact project context (static config + dynamic DB queries) for AI agent sessions. `_discover_entry_points()` detects CLI, script, server, and app entry points across 8 languages (Python Click/Typer/argparse, Go, Rust, Java, Kotlin, Swift, JS/TS). `_quick_import_scan()` infers `depends_on` edges between clusters by sampling code imports via tree-sitter. `interactive_init()` runs the interactive initialization wizard with re-init detection, mode selection, and auto-reindex. `non_interactive_init()` runs initialization without prompts for CI/script use, supporting `mode` (bootstrap/import/both), `force` (delete existing .beadloom/), and automatic doc linking + skeleton generation + reindex. `auto_link_docs()` fuzzy-matches existing `docs/` markdown files to graph nodes by ref_id similarity (exact path, stem match, partial match) and patches the `docs:` field in `services.yml`. `_ingest_readme()` extracts project metadata (description, tech stack, architecture notes) from README/CONTRIBUTING/ARCHITECTURE files.
- **presets.py** — Architecture presets (`monolith`, `microservices`, `monorepo`) with directory classification rules and edge inference logic. `Preset` dataclass defines `name`, `description`, `dir_rules`, `default_kind`, `infer_part_of`, `infer_deps_from_manifests`. `PresetRule` dataclass maps directory name patterns to node kinds with confidence levels. `detect_preset()` checks for mobile app indicators (React Native/Expo via `package.json`, Flutter via `pubspec.yaml`) before falling back to directory heuristics.
- **doc_generator.py** — `generate_skeletons()` creates docs/ tree from graph nodes (architecture.md, domain READMEs, service pages, feature SPECs with `_doc_path_for_node()` resolution), writes `docs:` field back to `services.yml` via `_patch_docs_field()`, and generates `.beadloom/README.md` quick-start. `generate_polish_data()` returns structured JSON for AI-driven doc enrichment with SQLite dependency edges, symbol change detection (`_detect_symbol_changes()`), and routes/activity/tests from `nodes.extra`. `format_polish_text()` renders multi-line human-readable polish output including symbol drift warnings, routes, activity level, and test metadata.
- **config_reader.py** — `read_deep_config()` extracts scripts, workspaces, path aliases, and build metadata from project configuration files. Parses `pyproject.toml` ([project.scripts], [tool.pytest], [tool.ruff], [build-system]), `package.json` (scripts, workspaces, engines), `tsconfig.json` (compilerOptions.paths, baseUrl), `Cargo.toml` ([workspace] members, [features]), and `build.gradle`/`build.gradle.kts` (plugins, dependencies via regex). Merges results from multiple config sources with deduplication for scripts and workspaces.

### CLI Commands

```bash
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}]
beadloom init --import DOCS_DIR
beadloom init  # interactive mode
beadloom init --yes [--mode {bootstrap,import,both}] [--force]  # non-interactive mode
beadloom docs generate   # create doc skeletons from graph
beadloom docs polish     # structured data for AI enrichment (text or JSON)
beadloom prime           # compact project context for AI agent injection
beadloom setup-rules     # create IDE adapter files (.cursorrules, etc.)
beadloom snapshot save [--label LABEL]           # save current graph state
beadloom snapshot list [--json]                  # list all saved snapshots
beadloom snapshot compare OLD_ID NEW_ID [--json] # compare two snapshots
```

## API

Module `src/beadloom/onboarding/scanner.py`:
- `scan_project(project_root)` -- scan project structure, return manifests, source_dirs, file_count, languages
- `classify_doc(doc_path)` -- classify a markdown document (adr, feature, architecture, other)
- `bootstrap_project(root, *, preset_name=None)` -- auto-generate graph from code structure (incl. root node, rules, MCP config, AGENTS.md, IDE rules)
- `import_docs(root, docs_dir)` -- classify and import existing documentation
- `generate_rules(nodes, edges, project_name, rules_path)` -- generate architecture rules with empty matcher for hierarchy validation
- `setup_mcp_auto(project_root)` -- auto-detect editor and create MCP config
- `setup_rules_auto(project_root)` -- auto-detect IDEs and create adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`); content-aware: skips user-edited files
- `generate_agents_md(project_root)` -- generate `.beadloom/AGENTS.md` with 13 MCP tools and rules; preserves content below `## Custom`
- `prime_context(project_root, *, fmt="markdown")` -- compact project context for AI agent injection (static + dynamic layers, <=2K tokens)
- `interactive_init(project_root)` -- interactive wizard with re-init detection, mode selection, review table, auto-reindex
- `non_interactive_init(project_root, *, mode="bootstrap", force=False)` -- non-interactive init for CI/scripts; supports bootstrap/import/both modes, force-deletes existing .beadloom/ when force=True, auto-links docs, generates skeletons, runs reindex
- `auto_link_docs(project_root, nodes)` -- fuzzy-match existing docs/ files to graph nodes by ref_id (exact path, stem, partial match); patches docs: field in services.yml via _patch_docs_field; returns count of linked docs

Module `src/beadloom/onboarding/presets.py`:
- `Preset` -- frozen dataclass: name, description, dir_rules, default_kind, infer_part_of, infer_deps_from_manifests
- `PresetRule` -- frozen dataclass: pattern, kind, confidence
- `Preset.classify_dir(dir_name)` -- return (kind, confidence) for a directory name
- `PRESETS` -- dict mapping preset names to `Preset` instances
- `detect_preset(root)` -- auto-detect architecture (mobile-aware: checks React Native/Expo/Flutter first)

Module `src/beadloom/onboarding/doc_generator.py`:
- `generate_skeletons(project_root, nodes?, edges?)` -- create docs/ tree from graph, write `docs:` back to YAML, generate `.beadloom/README.md`
- `generate_polish_data(project_root, ref_id?)` -- return structured JSON with SQLite dependency edges, symbol change detection, routes/activity/tests
- `format_polish_text(data)` -- render polish data as multi-line human-readable text with symbol drift, routes, activity, tests

Module `src/beadloom/onboarding/config_reader.py`:
- `read_deep_config(project_root)` -- extract scripts, workspaces, path aliases from pyproject.toml, package.json, tsconfig.json, Cargo.toml, build.gradle

## Testing

Tests: `tests/test_onboarding.py`, `tests/test_presets.py`, `tests/test_cli_init.py`, `tests/test_doc_generator.py`, `tests/test_cli_docs.py`, `tests/test_integration_onboarding.py`, `tests/test_bead06_misc_fixes.py`, `tests/test_config_reader.py`, `tests/test_auto_link_docs.py`, `tests/test_init_doc_generation.py`, `tests/test_snapshot.py`, `tests/test_cli_snapshot.py`
