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

Use `--yes` (or `--non-interactive`) to skip all prompts — useful for CI and automation.

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

# Impact analysis: what depends on this?
beadloom why my-service

# Graph visualization (Mermaid)
beadloom graph

# Save architecture snapshot for later comparison
beadloom snapshot save
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

# Audit docs for stale cross-references and mention freshness
beadloom docs audit

# Install git pre-commit hook
beadloom install-hooks
```

`sync-check` detects when code changes haven't been reflected in documentation. Exit code 2 means stale docs found.

`docs audit` scans documentation for cross-references to code symbols and reports which mentions are fresh or stale. Use `--stale-only` to filter, `--json` for structured output, or `--fail-on` for CI gates.

`install-hooks` sets up a git pre-commit hook that runs `sync-check`, `ruff` linting, and `mypy` type checking before each commit.

### Step 6: Enforce architecture boundaries

```bash
# Validate architecture rules
beadloom lint

# In CI: fail on violations
beadloom lint --strict

# Compare architecture changes
beadloom diff HEAD~5
```

Beadloom supports 7 rule types: `require`, `deny`, `forbid_edge`, `layer`, `cycle_detection`, `import_boundary`, and `cardinality`. Define rules in `.beadloom/_graph/rules.yml`.

## Optional Extras

```bash
# Additional language parsers (TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, C/C++, Objective-C)
uv tool install "beadloom[languages]"

# Interactive terminal dashboard (launch with: beadloom tui)
uv tool install "beadloom[tui]"

# File watcher for auto-reindex
uv tool install "beadloom[watch]"

# Everything
uv tool install "beadloom[all]"
```

## Limits

- Code indexer supports Python, TypeScript/JavaScript, Go, Rust out of the box; Kotlin, Java, Swift, C/C++, Objective-C via `beadloom[languages]`
- Documentation is indexed from the `docs/` directory (configurable via `config.yml`)
- Graph is described in YAML (`.yml`) files under `.beadloom/_graph/`
- Maximum documentation chunk size: 2000 characters
