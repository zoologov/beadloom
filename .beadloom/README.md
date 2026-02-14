# Beadloom — AI Agent Native Architecture Graph

This project uses **Beadloom** for architecture-as-code — a local architecture
graph that keeps documentation in sync with code, enforces architectural
boundaries, and provides structured context to AI agents.

## What is Beadloom?

Beadloom is a Context Oracle + Doc Sync Engine designed for AI-assisted
development. It maintains a queryable architecture graph over your codebase,
so agents spend less time searching and more time building.

**Learn more:** [github.com/vzoologov/beadloom](https://github.com/vzoologov/beadloom)

## Quick Start

### Essential Commands

    # Project overview
    beadloom status

    # Architecture graph (Mermaid)
    beadloom graph

    # Context bundle for a domain/feature
    beadloom ctx <ref-id>

    # Check doc-code freshness
    beadloom sync-check

    # Architecture boundary lint
    beadloom lint

    # Full-text search
    beadloom search "<query>"

    # Rebuild index after changes
    beadloom reindex

### For AI Agents (MCP)

Beadloom exposes tools via Model Context Protocol (MCP):

    beadloom mcp-serve             # start MCP server (stdio)
    beadloom setup-mcp             # configure your editor

MCP tools: `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`,
`search`, `update_node`, `mark_synced`, `generate_docs`, `prime`.

## Directory Contents

    .beadloom/
    ├── _graph/
    │   ├── services.yml    # Architecture graph (nodes + edges)
    │   └── rules.yml       # Architecture lint rules
    ├── config.yml          # Project configuration
    ├── beadloom.db         # SQLite index (gitignored)
    └── README.md           # This file

## Why Beadloom?

- **Agent Native** — structured context for LLMs, not another LLM wrapper
- **Doc Sync** — detects when docs go stale after code changes
- **AaC Lint** — enforces architectural boundaries via deny/require rules
- **Local-first** — SQLite + YAML, no cloud services, no API keys
