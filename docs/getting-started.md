# Getting Started

Getting started with Beadloom.

## Requirement

- Python 3.10+
- uv (recommended) or pip

## Installation

```bash
uv tool install beadloom
# or
pip install beadloom
```

## Quick Start

### Step 1: Initialization

```bash
cd your-project

# Automatically generate graph from code structure
beadloom init --bootstrap
```

This will create:
- `.beadloom/_graph/services.yml` — architecture graph (nodes + edges)
- `.beadloom/_graph/rules.yml` — auto-generated architecture lint rules
- `.beadloom/config.yml` — project configuration
- `docs/` — documentation skeletons for each graph node
- `.mcp.json` (or equivalent) — MCP config for the detected editor

It also runs a full reindex automatically: code symbols are extracted, imports are resolved, and `depends_on` edges are inferred from code.

If Cursor, Windsurf, or Cline are detected, IDE adapter files (`.cursorrules`, etc.) are created to point agents at `.beadloom/AGENTS.md`.

### Step 2: Refine the graph

Open `.beadloom/_graph/services.yml` and refine:
- Node names and descriptions
- Relationships between components
- Documentation bindings (the `docs` field)

Then reindex to pick up changes:

```bash
beadloom reindex
```

### Step 3: Verification

```bash
# Statistics
beadloom status

# Graph validation
beadloom doctor

# Architecture lint (boundary rules)
beadloom lint

# Context bundle for a node
beadloom ctx my-service

# Graph visualization (Mermaid)
beadloom graph
```

### Step 4: Configure AI agents

```bash
# Configure MCP for your editor
beadloom setup-mcp

# Create IDE rules files (.cursorrules, etc.)
beadloom setup-rules

# Generate AGENTS.md with project context
beadloom prime --update
```

`beadloom setup-mcp` creates `.mcp.json` (Claude Code), `.cursor/mcp.json` (Cursor), or `~/.codeium/windsurf/mcp_config.json` (Windsurf).

### Step 5: Keep docs in sync

```bash
# Check doc↔code synchronization
beadloom sync-check

# Install git pre-commit hook
beadloom install-hooks
```

`sync-check` detects when code changes haven't been reflected in documentation. Exit code 2 means stale docs found.

## Optional Extras

```bash
# Additional language parsers (TypeScript/JavaScript, Go, Rust)
uv tool install "beadloom[languages]"

# Interactive terminal dashboard
uv tool install "beadloom[tui]"

# File watcher for auto-reindex
uv tool install "beadloom[watch]"

# Everything
uv tool install "beadloom[all]"
```

## Limits

- Code indexer supports Python out of the box; TypeScript/JavaScript, Go, and Rust via `beadloom[languages]`
- Documentation is indexed from the `docs/` directory (configurable via `config.yml`)
- Graph is described in YAML (`.yml`) files under `.beadloom/_graph/`
- Maximum documentation chunk size: 2000 characters
