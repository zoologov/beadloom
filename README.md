# Beadloom

**From documentation bedlam to structured knowledge.**

Beadloom is a local developer tool that turns scattered documentation, code, and architectural knowledge into a queryable context layer for humans and AI agents.

It solves two problems of AI-assisted development on large codebases:

1. **Context window waste.** Agents spend most of their tokens searching and reading docs/code before doing actual work. Beadloom provides a ready-made, compact context bundle for any feature/domain/service — zero search tokens.

2. **Documentation rot.** After code changes, related docs go stale silently. Beadloom tracks doc↔code links and flags outdated documentation on every commit.

## Install

```bash
uv tool install beadloom        # recommended
pipx install beadloom            # alternative
```

## Quick start

```bash
# 1. Bootstrap: scan code and generate an initial knowledge graph
beadloom init --bootstrap

# 2. Review and edit the generated graph YAML files
#    (nodes = features, services, entities; edges = relationships)
vi .beadloom/_graph/bootstrap.yml

# 3. Build the SQLite index from graph + docs + code
beadloom reindex

# 4. Check project status
beadloom status

# 5. Get a context bundle for a feature or domain
beadloom ctx AUTH-001              # human-readable Markdown
beadloom ctx AUTH-001 --json       # machine-readable JSON

# 6. Check documentation freshness
beadloom sync-check

# 7. Set up MCP for AI agents
beadloom setup-mcp
```

Agents connect via MCP (Model Context Protocol) -- no HTTP daemon, no extra setup:

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "beadloom",
      "args": ["mcp-serve"]
    }
  }
}
```

## Key features

- **Context Oracle** — deterministic graph traversal → compact JSON bundle in <20ms
- **Doc Sync Engine** — tracks code changes, detects stale documentation, integrates with git hooks
- **Onboarding** — bootstrap graph from code (no docs needed), import existing docs, incremental coverage
- **MCP server** — native integration with Claude Code, Cursor, and other MCP-compatible agents
- **Local-first** — single CLI binary + single SQLite file, no Docker, no cloud dependencies

## How it works

Beadloom maintains a **knowledge graph** that maps your project's architecture. The graph is
defined in YAML files under `.beadloom/_graph/` and consists of **nodes** (features, services,
domains, entities, ADRs) connected by **edges** (part_of, uses, depends_on, etc.).

The **indexing pipeline** reads three sources and merges them into a single SQLite database:

1. **Graph YAML** -- nodes and edges that describe the project structure.
2. **Documentation** -- Markdown files linked to graph nodes, split into searchable chunks.
3. **Code** -- source files parsed with tree-sitter to extract symbols (functions, classes) and
   `# beadloom:key=value` annotations that link code to graph nodes.

When an agent (or human) requests context for a node, the **Context Oracle** runs a
breadth-first traversal from that node, collects the relevant subgraph, documentation chunks,
and code symbols, then returns a compact JSON bundle -- typically in under 20ms.

The **Doc Sync Engine** tracks which documentation files correspond to which code files. On every
commit (via a git hook), it detects stale docs and either warns or blocks the commit.

## Documentation structure

Beadloom uses a **domain-first** layout — features are grouped under their domain, not in a flat list:

```
docs/
  architecture.md
  decisions/
    ADR-001-cache-strategy.md
  domains/
    routing/
      README.md              # domain overview, invariants
      features/
        PROJ-123/
          SPEC.md
          API.md
    billing/
      README.md
      features/
        PROJ-456/
          SPEC.md
  _imported/                 # unclassified docs from import
```

## Beads integration

*A context loom for your [beads](https://github.com/steveyegge/beads).*

Beadloom complements [Beads](https://github.com/steveyegge/beads) by providing structured context to planner/coder/reviewer agents. Beads workers call `get_context(feature_id)` via MCP and receive a ready-made bundle instead of searching the codebase from scratch.

Beadloom works independently of Beads — the integration is optional.

## CLI commands

| Command | Description |
|---------|-------------|
| `init --bootstrap` | Scan code and generate an initial knowledge graph |
| `init --import DIR` | Import and classify existing documentation |
| `reindex` | Drop and rebuild the SQLite index from graph, docs, and code |
| `ctx REF_ID` | Get a context bundle (graph + docs + code symbols) |
| `graph [REF_ID]` | Show the knowledge graph as Mermaid or JSON |
| `status` | Show project index statistics and doc coverage |
| `doctor` | Run validation checks on the knowledge graph |
| `sync-check` | Check doc-code synchronization status |
| `sync-update REF_ID` | Show stale docs and update them (supports `--auto`) |
| `install-hooks` | Install or remove the beadloom pre-commit hook |
| `setup-mcp` | Create or update `.mcp.json` for the MCP server |
| `mcp-serve` | Run the MCP server (stdio transport) |

All commands accept `--project PATH` to specify a project root other than the current directory.

## MCP tools

AI agents connect via MCP and can call these tools:

| Tool | Description |
|------|-------------|
| `get_context` | Get a context bundle for a ref_id (graph + docs + code symbols) |
| `get_graph` | Get a subgraph around a node (nodes and edges as JSON) |
| `list_nodes` | List all graph nodes, optionally filtered by kind |
| `sync_check` | Check if documentation is up-to-date with code |
| `get_status` | Get project documentation coverage and index statistics |

## Configuration

Beadloom stores all project data under `.beadloom/` in your repository root:

- **`.beadloom/config.yml`** -- project settings: `scan_paths`, `languages`, sync engine options.
- **`.beadloom/_graph/*.yml`** -- knowledge graph definition (nodes and edges in YAML).
- **`.beadloom/beadloom.db`** -- SQLite index (auto-generated by `reindex`, add to `.gitignore`).

Code annotations link source files to graph nodes:

```python
# beadloom:feature=AUTH-001
# beadloom:service=user-service
def authenticate(user_id: str) -> bool:
    ...
```

## Development

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check src/
uv run ruff format src/

# Type checking
uv run mypy
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System design and component overview |
| [docs/getting-started.md](docs/getting-started.md) | Quick start guide |
| [docs/context-oracle.md](docs/context-oracle.md) | BFS algorithm and context assembly |
| [docs/cli-reference.md](docs/cli-reference.md) | CLI commands reference |
| [docs/mcp-server.md](docs/mcp-server.md) | MCP integration guide |
| [docs/sync-engine.md](docs/sync-engine.md) | Doc sync engine details |
| [docs/graph-format.md](docs/graph-format.md) | YAML graph format specification |

## License

MIT
