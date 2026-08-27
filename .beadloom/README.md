# beadloom — AI Agent Native Architecture Graph

This project uses **Beadloom** for architecture-as-code — a local architecture
graph that keeps documentation in sync with code, enforces architectural
boundaries, and provides structured context to AI agents.

## What is Beadloom?

Beadloom - the architecture graph of your codebase, and the gate that holds documentation, boundaries, cross-repo contracts and the agentic workflow to it.

It maintains a queryable architecture graph over your codebase, so agents
spend less time searching and more time building.

## Quick Start

### Essential Commands

    # Compact context for an AI agent, at the start of a session
    beadloom prime

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

    # Every check at once, and the one command CI runs
    beadloom ci

### For AI Agents (MCP)

Beadloom exposes tools via Model Context Protocol (MCP):

    beadloom mcp-serve             # start MCP server (stdio)
    beadloom setup-mcp             # configure your editor

MCP tools: `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`, `update_node`, `mark_synced`, `search`, `generate_docs`, `prime`, `why`, `diff`, `lint`, `get_debt_report`, `task_init`, `bead_context`, `complete_bead`, `checkpoint`.

## Directory Contents

    .beadloom/
    ├── _graph/
    │   ├── services.yml    # Architecture graph (nodes + edges)
    │   └── rules.yml       # Architecture lint rules
    ├── AGENTS.md           # What an AI agent reads first
    ├── config.yml          # Project configuration
    ├── beadloom.db         # SQLite index (gitignored)
    └── README.md           # This file

## Why Beadloom?

- **Agent Native** — structured context for LLMs, not another LLM wrapper
- **Doc Sync** — detects when docs go stale after code changes
- **AaC Lint** — enforces architectural boundaries, and reports a rule that
  could check nothing rather than passing it
- **Local-first** — SQLite + YAML, no cloud services, no API keys
