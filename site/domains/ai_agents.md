---
title: ai_agents
kind: domain
---

# ai_agents

**Kind:** domain

Governed AI-agent harnesses (Goose + model) over Beadloom read APIs + bd/beadloom shells; ships in the package

**Source:** `src/beadloom/ai_agents/`

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

- **part_of**: [beadloom](../services/beadloom.md)
- **Parts**: [ai-techwriter](../features/ai-techwriter.md)

## Documentation

- [domains/ai_agents/README.md](/docs/domains/ai_agents/README.md)

## Diagram

```mermaid
C4Container
    System_Boundary(ai_agents_boundary, "ai_agents") {
        Component(ai_techwriter, "Ai Techwriter", "", "Deterministic, seam-isolated PR-triggered doc-refresh harness (discover drift -> packet -> agent -> fixpoint -> gate -> publish; verdict ok/flagged/infra)")
    }
```

