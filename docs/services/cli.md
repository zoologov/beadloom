# CLI Reference

Beadloom CLI is built on Click and provides a set of commands for managing the knowledge index.

## Specification

### Global Options

```
beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND
```

- `--verbose` / `-v` -- verbose output
- `--quiet` / `-q` -- errors only
- `--version` -- show version

### beadloom init

Project initialization. Three modes:

```bash
# Generate graph from code structure (auto-detects architecture)
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}] [--project DIR]

# Import existing documentation
beadloom init --import DOCS_DIR [--project DIR]

# Interactive mode (default when no flags given)
beadloom init [--project DIR]
```

`--bootstrap` scans source directories (src, lib, app, services, packages), classifies subdirectories using architecture-aware preset rules, infers edges from directory nesting, and generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`.

`--preset` selects an architecture preset:
- `monolith` -- top dirs are domains; subdirs map to features, entities, services
- `microservices` -- top dirs are services; shared code becomes domains
- `monorepo` -- packages/apps are services; manifest deps become edges

When `--preset` is omitted, Beadloom auto-detects: `services/` or `cmd/` -> microservices, `packages/` or `apps/` -> monorepo, otherwise -> monolith.

`--import` classifies .md files (ADR, feature, architecture, other) and generates `.beadloom/_graph/imported.yml`.

Projects without a `docs/` directory work fine -- Beadloom operates in zero-doc mode with code-only context (graph nodes, annotations, context oracle).

### beadloom reindex

Full reindex: drops all tables and reloads from scratch.

```bash
beadloom reindex [--full] [--docs-dir DIR] [--project DIR]
```

- `--full` -- force full rebuild (drop all tables and re-create)
- `--docs-dir` -- documentation directory (default: from config.yml or `docs/`)

Default mode is incremental (only changed files). Use `--full` to force complete rebuild.

Order: drop tables -> create schema -> load graph YAML -> index docs -> index code -> resolve imports -> load rules -> build sync state -> populate FTS5 -> take health snapshot.

When no changes are detected, displays current DB totals (nodes, edges, docs, symbols) instead of reindex counts. Warns about missing tree-sitter parsers when symbols == 0.

### beadloom ctx

Get a context bundle for the specified ref_id(s).

```bash
beadloom ctx REF_ID [REF_ID...] [--json|--markdown] [--depth N] [--max-nodes N] [--max-chunks N] [--project DIR]
```

Outputs Markdown by default. `--json` for machine-readable format.

### beadloom graph

Architecture graph visualization.

```bash
# Full graph in Mermaid format
beadloom graph [--project DIR]

# Subgraph from specified nodes
beadloom graph REF_ID [REF_ID...] [--depth N] [--json]
```

### beadloom status

Index statistics with health trends.

```bash
beadloom status [--json] [--project DIR]
```

Shows Rich-formatted dashboard with: node count (broken down by kind), edges, documents, symbols, per-kind documentation coverage, stale docs, isolated nodes, empty summaries. Includes trend indicators comparing current reindex with previous snapshot. Also displays context metrics: average bundle token size, largest bundle (ref_id + tokens), total indexed symbols.

`--json` -- structured JSON output.

### beadloom doctor

Architecture graph validation.

```bash
beadloom doctor [--project DIR]
```

Checks:
- Nodes with empty summary
- Documents not linked to nodes
- Nodes without documentation
- Isolated nodes (no edges)

### beadloom sync-check

Check doc-code synchronization.

```bash
beadloom sync-check [--porcelain] [--json] [--report] [--ref REF_ID] [--project DIR]
```

Exit codes: 0 = all OK, 1 = error, 2 = stale pairs found.

- `--porcelain` -- TAB-separated output for scripts. Format: `status\tref_id\tdoc_path\tcode_path\treason`.
- `--json` -- structured JSON output with summary and pair details. Each pair includes `status`, `ref_id`, `doc_path`, `code_path`, `reason`, and optional `details`.
- `--report` -- ready-to-post Markdown report for CI (GitHub/GitLab).
- `--ref` -- filter results by ref_id.

Human-readable output includes reason-aware formatting:
- `untracked_files` reason: displays list of untracked files in `details`.
- `missing_modules` reason: displays list of missing modules in `details`.
- Other stale reasons (e.g. `symbols_changed`, `content_changed`): displays `reason` next to the code path.

### beadloom sync-update

Review and update stale documentation.

```bash
# Show sync status for a ref_id
beadloom sync-update REF_ID --check [--project DIR]

# Interactive: open stale docs in $EDITOR, mark synced after editing
beadloom sync-update REF_ID [--project DIR]
```

For automated doc updates, use your AI agent (Claude Code, Cursor, etc.) with Beadloom's MCP tools. See `.beadloom/AGENTS.md` for agent instructions.

### beadloom install-hooks

Install git pre-commit hook for synchronization checking.

```bash
# Install (warning mode)
beadloom install-hooks [--mode warn|block] [--project DIR]

# Remove
beadloom install-hooks --remove [--project DIR]
```

### beadloom link

Manage external tracker links on graph nodes.

```bash
# Add a link (label auto-detected from URL)
beadloom link REF_ID URL [--label LABEL] [--project DIR]

# List links for a node
beadloom link REF_ID [--project DIR]

# Remove a link
beadloom link REF_ID --remove URL [--project DIR]
```

Auto-detected labels: `github`, `github-pr`, `jira`, `linear`, `link` (fallback).

### beadloom diff

Show graph changes since a git ref.

```bash
beadloom diff [--since REF] [--json] [--project DIR]
```

Compares current graph YAML with state at the given ref (default: HEAD). Exit code 0 = no changes, 1 = changes detected.

### beadloom search

Search nodes and documentation by keyword.

```bash
beadloom search QUERY [--kind {domain,feature,service,entity,adr}] [--limit N] [--json] [--project DIR]
```

Uses FTS5 full-text search when available, falls back to SQL LIKE. Run `beadloom reindex` first to populate the search index.

### beadloom why

Show impact analysis for a node -- upstream dependencies and downstream dependents.

```bash
beadloom why REF_ID [--depth N] [--json] [--project DIR]
```

### beadloom lint

Run architecture lint rules against the project.

```bash
beadloom lint [--format {rich,json,porcelain}] [--strict] [--fail-on-warn] [--no-reindex] [--project DIR]
```

Checks cross-boundary imports against rules defined in `rules.yml`. Format auto-detects: `rich` if TTY, `porcelain` if piped.

Exit codes: 0 = clean (or violations without `--strict`/`--fail-on-warn`), 1 = violations with `--strict` (errors only) or `--fail-on-warn` (any violation), 2 = configuration error.

### beadloom ui

Launch interactive terminal dashboard.

```bash
beadloom ui [--project DIR]
```

Browse domains, nodes, edges, and documentation coverage. Requires: `pip install beadloom[tui]`.

### beadloom watch

Watch files and auto-reindex on changes.

```bash
beadloom watch [--debounce MS] [--project DIR]
```

Monitors graph YAML, documentation, and source files. Graph changes trigger full reindex; other changes trigger incremental. Requires: `pip install beadloom[watch]`.

### beadloom docs generate

Generate documentation skeletons from the architecture graph.

```bash
beadloom docs generate [--project DIR]
```

Creates `docs/` tree: `architecture.md`, domain READMEs, service pages, feature SPECs. Never overwrites existing files. All generated files include `<!-- enrich with: beadloom docs polish -->` markers.

### beadloom docs polish

Generate structured data for AI-driven documentation enrichment.

```bash
beadloom docs polish [--format {text,json}] [--ref-id REF_ID] [--project DIR]
```

- `text` (default) -- human-readable summary with enrichment instructions
- `json` -- structured JSON with nodes (symbols, dependencies, existing docs), Mermaid diagram, and AI prompt
- `--ref-id` -- filter to a single node

### beadloom prime

Output compact project context for AI agent injection.

```bash
beadloom prime [--json] [--update] [--project DIR]
```

- `--json` -- structured JSON output
- `--update` -- regenerate `.beadloom/AGENTS.md` before outputting context

Returns architecture summary, health status (stale docs, lint violations), architecture rules, domain list, and agent instructions.

### beadloom setup-rules

Create IDE rules files that reference `.beadloom/AGENTS.md`.

```bash
# Auto-detect installed IDEs
beadloom setup-rules [--project DIR]

# Target a specific IDE
beadloom setup-rules --tool {cursor,windsurf,cline} [--project DIR]
```

Creates thin adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) that instruct agents to read AGENTS.md.

### beadloom setup-mcp

Configure MCP server for your editor.

```bash
beadloom setup-mcp [--tool {claude-code,cursor,windsurf}] [--project DIR]
beadloom setup-mcp --remove [--tool {claude-code,cursor,windsurf}] [--project DIR]
```

- `claude-code` (default) -- `.mcp.json` in project root
- `cursor` -- `.cursor/mcp.json` in project root
- `windsurf` -- `~/.codeium/windsurf/mcp_config.json` (global)

### beadloom mcp-serve

Launch MCP stdio server.

```bash
beadloom mcp-serve [--project DIR]
```

## API

Module `src/beadloom/services/cli.py`:

- `main` -- Click group: `beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND`
- `reindex` -- rebuild SQLite index (incremental by default, `--full` for complete rebuild)
- `ctx` -- get context bundle for ref_id(s)
- `graph` -- show architecture graph (Mermaid or JSON)
- `doctor` -- run validation checks
- `status` -- show index statistics with health trends and context metrics
- `sync_check` -- check doc-code sync with reason/details (reason-aware output for `untracked_files`, `missing_modules`, `symbols_changed`)
- `sync_update` -- review and update stale docs interactively
- `install_hooks` -- install/remove pre-commit hook
- `link` -- manage external tracker links
- `search` -- FTS5 search with LIKE fallback
- `why` -- impact analysis (upstream + downstream)
- `diff_cmd` -- graph changes since a git ref
- `lint` -- architecture lint with `--strict`, `--fail-on-warn`, auto-format detection
- `prime` -- compact project context for AI agents
- `setup_mcp` -- configure MCP server for editor
- `setup_rules` -- create IDE rules files
- `mcp_serve` -- run MCP stdio server
- `docs` -- Click group for doc commands (`generate`, `polish`)
- `ui` -- launch TUI dashboard
- `watch_cmd` -- watch files and auto-reindex
- `init` -- project initialization (bootstrap, import, interactive)

All commands accept `--project DIR` to specify the project root. The current directory is used by default.

## Testing

CLI is tested via `click.testing.CliRunner`. Each command has a corresponding test file in `tests/test_cli_*.py`: `test_cli_reindex.py`, `test_cli_ctx.py`, `test_cli_graph.py`, `test_cli_status.py`, `test_cli_sync_check.py`, `test_cli_sync_update.py`, `test_cli_hooks.py`, `test_cli_link.py`, `test_cli_docs.py`, `test_cli_mcp.py`, `test_cli_watch.py`, `test_cli_diff.py`, `test_cli_why.py`, `test_cli_lint.py`, `test_cli_init.py`.
