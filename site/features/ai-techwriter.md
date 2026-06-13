---
title: ai-techwriter
kind: feature
---

# ai-techwriter

**Kind:** feature

Deterministic, seam-isolated PR-triggered doc-refresh harness (discover drift -> packet -> agent -> fixpoint -> gate -> publish; verdict ok/flagged/infra)

**Source:** `src/beadloom/ai_agents/ai_techwriter/`

## Public symbols

- `AgentResult`
- `AgentRunner`
- `CommandResult`
- `CommentPublisher`
- `ContextPacket`
- `DriftItem`
- `FakeAgentRunner`
- `FakePublisher`
- `GateResult`
- `GitHubPRBranchPublisher`
- `GitHubPublisher`
- `GitLabPRBranchPublisher`
- `GitLabPublisher`
- `GooseAgentRunner`
- `HarnessConfig`
- `HarnessResult`
- `ProviderConfig`
- `PublishResult`
- `ReviewPublisher`
- `RunRecord`
- `append_run`
- `beadloom_ci`
- `beadloom_ctx_json`
- `beadloom_docs_polish_json`
- `beadloom_sync_check_json`
- `beadloom_sync_update`
- `beadloom_why`
- `build_packet`
- `classify_verdict`
- `default_recipe_path`
- `discover_scope`
- `load_runs`
- `main`
- `parse_scope`
- `qwen_provider`
- `read_doc`
- `run_command`
- `run_harness`
- `runs_store_path`
- `select_polish_for_ref`

## Relationships

- **part_of**: [ai_agents](../domains/ai_agents.md)

## Documentation

- [domains/ai_agents/features/ai-techwriter/SPEC.md](/docs/domains/ai_agents/features/ai-techwriter/SPEC.md)

## Diagram

```mermaid
C4Container
    System_Boundary(beadloom_boundary, "Beadloom") {
        Container(ai_agents, "Ai_Agents", "", "Governed AI-agent harnesses (Goose + model) over Beadloom read APIs + bd/beadloom shells; ships in the package")
        Container(application, "Application", "", "Use-case orchestration: reindex, doctor, debt report, file watcher")
        Container(cli, "Cli", "", "Click-based CLI with 21 commands")
        Container(context_oracle, "Context Oracle", "", "Context bundle building via BFS graph traversal, code indexing, caching, search")
        Container(doc_sync, "Doc Sync", "", "Doc-code synchronization tracking and stale detection")
        Container(graph, "Graph", "", "YAML graph format, loader, diff, rule engine, import resolver, linter")
        Container(infrastructure, "Infrastructure", "", "Domain-agnostic SQLite database layer, health metrics, git activity")
        Container(mcp_server, "Mcp Server", "", "MCP stdio server with 14 tools for AI agents")
        Container(onboarding, "Onboarding", "", "Project bootstrap, doc import, architecture-aware presets, doc generation")
        Container(tui, "Tui", "", "Interactive 3-screen architecture workstation with dashboard, explorer, doc status")
        Container(vitepress_site, "Vitepress Site", "", "VitePress documentation site — renders the beadloom-produced site data (graph pages, dashboard.data.json, landscape Mermaid)")
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

