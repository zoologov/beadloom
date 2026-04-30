---
title: doc-generator
kind: feature
---

# doc-generator

**Kind:** feature

Doc skeleton generation + AI polish data from architecture graph

**Source:** `src/beadloom/onboarding/doc_generator.py`

## Public symbols

- `format_polish_text`
- `generate_polish_data`
- `generate_skeletons`

## Relationships

- **part_of**: [onboarding](../domains/onboarding.md)

## Documentation

- [domains/onboarding/features/doc-generator/SPEC.md](/docs/domains/onboarding/features/doc-generator/SPEC.md)

## Diagram

```mermaid
C4Container
    System_Boundary(beadloom_boundary, "Beadloom") {
        Container(application, "Application", "", "Use-case orchestration: reindex, doctor, debt report, file watcher")
        Container(cli, "Cli", "", "Click-based CLI with 21 commands")
        Container(context_oracle, "Context Oracle", "", "Context bundle building via BFS graph traversal, code indexing, caching, search")
        Container(doc_sync, "Doc Sync", "", "Doc-code synchronization tracking and stale detection")
        Container(graph, "Graph", "", "YAML graph format, loader, diff, rule engine, import resolver, linter")
        Container(infrastructure, "Infrastructure", "", "Domain-agnostic SQLite database layer, health metrics, git activity")
        Container(mcp_server, "Mcp Server", "", "MCP stdio server with 14 tools for AI agents")
        Container(onboarding, "Onboarding", "", "Project bootstrap, doc import, architecture-aware presets, doc generation")
        Container(tui, "Tui", "", "Interactive 3-screen architecture workstation with dashboard, explorer, doc status")
    }
    Rel(application, context_oracle, "depends_on")
    Rel(application, context_oracle, "uses")
    Rel(application, doc_sync, "depends_on")
    Rel(application, doc_sync, "uses")
    Rel(application, graph, "depends_on")
    Rel(application, graph, "uses")
    Rel(application, infrastructure, "depends_on")
    Rel(application, infrastructure, "uses")
    Rel(application, onboarding, "uses")
    Rel(beadloom, application, "depends_on")
    Rel(beadloom, context_oracle, "depends_on")
    Rel(beadloom, doc_sync, "depends_on")
    Rel(beadloom, graph, "depends_on")
    Rel(beadloom, infrastructure, "depends_on")
    Rel(cli, application, "uses")
    Rel(cli, context_oracle, "uses")
    Rel(cli, doc_sync, "uses")
    Rel(cli, graph, "uses")
    Rel(cli, infrastructure, "uses")
    Rel(cli, onboarding, "uses")
    Rel(context_oracle, infrastructure, "depends_on")
    Rel(doc_sync, infrastructure, "depends_on")
    Rel(graph, context_oracle, "depends_on")
    Rel(graph, infrastructure, "depends_on")
    Rel(mcp_server, application, "uses")
    Rel(mcp_server, context_oracle, "uses")
    Rel(mcp_server, doc_sync, "uses")
    Rel(mcp_server, graph, "uses")
    Rel(mcp_server, infrastructure, "uses")
    Rel(mcp_server, onboarding, "uses")
```

