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
beadloom init                     # Interactive setup (bootstrap / import / scope)
beadloom reindex                  # Build SQLite index from graph + docs + code
beadloom ctx PROJ-123 --json      # Get context bundle (graph + docs + code symbols)
beadloom sync-check               # Check which docs are stale
beadloom status                   # See documentation coverage
beadloom setup-mcp                # Configure MCP for agents
```

Agents connect via MCP (Model Context Protocol) — no HTTP daemon, no extra setup:

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

## Documentation

IN PROGRESS

## License

MIT
