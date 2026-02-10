# CLI Reference

Beadloom CLI is built on Click and provides a set of commands for managing the knowledge index.

## Specification

### Global Options

```
beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND
```

- `--verbose` / `-v` — verbose output
- `--quiet` / `-q` — errors only
- `--version` — show version

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
- `monolith` — top dirs are domains; subdirs map to features, entities, services
- `microservices` — top dirs are services; shared code becomes domains
- `monorepo` — packages/apps are services; manifest deps become edges

When `--preset` is omitted, Beadloom auto-detects: `services/` or `cmd/` → microservices, `packages/` or `apps/` → monorepo, otherwise → monolith.

`--import` classifies .md files (ADR, feature, architecture, other) and generates `.beadloom/_graph/imported.yml`.

Projects without a `docs/` directory work fine — Beadloom operates in zero-doc mode with code-only context (graph nodes, annotations, context oracle).

### beadloom reindex

Full reindex: drops all tables and reloads from scratch.

```bash
beadloom reindex [--project DIR]
```

Order: drop tables → create schema → load graph YAML → index docs → index code → set meta.

### beadloom ctx

Get a context bundle for the specified ref_id(s).

```bash
beadloom ctx REF_ID [REF_ID...] [--json|--markdown] [--depth N] [--max-nodes N] [--max-chunks N] [--project DIR]
```

Outputs Markdown by default. `--json` for machine-readable format.

### beadloom graph

Knowledge graph visualization.

```bash
# Full graph in Mermaid format
beadloom graph [--project DIR]

# Subgraph from specified nodes
beadloom graph REF_ID [REF_ID...] [--depth N] [--json]
```

### beadloom status

Index statistics.

```bash
beadloom status [--project DIR]
```

Shows: node count (broken down by kind), edges, documents, chunks, symbols, documentation coverage, stale documents.

### beadloom doctor

Knowledge graph validation.

```bash
beadloom doctor [--project DIR]
```

Checks:
- Nodes with empty summary
- Documents not linked to nodes
- Nodes without documentation
- Isolated nodes (no edges)

### beadloom sync-check

Check doc↔code synchronization.

```bash
beadloom sync-check [--porcelain] [--ref REF_ID] [--project DIR]
```

Exit codes: 0 = all OK, 1 = error, 2 = stale pairs found.

`--porcelain` — TAB-separated output for scripts.

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

### beadloom setup-mcp

Configure MCP server in `.mcp.json`.

```bash
beadloom setup-mcp [--project DIR]
beadloom setup-mcp --remove [--project DIR]
```

### beadloom mcp-serve

Launch MCP stdio server.

```bash
beadloom mcp-serve [--project DIR]
```

## API

All commands accept `--project DIR` to specify the project root. The current directory is used by default.

## Testing

CLI is tested via `click.testing.CliRunner`. Each command has a corresponding test file in `tests/test_cli_*.py`.
