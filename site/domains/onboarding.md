---
title: onboarding
kind: domain
---

# onboarding

**Kind:** domain

Project bootstrap, doc import, architecture-aware presets, doc generation

**Source:** `src/beadloom/onboarding/`

## Public symbols

- `AdapterResult`
- `BranchProtectionRequest`
- `ConfigDrift`
- `FlowConfig`
- `FlowConfigError`
- `GhRunner`
- `Preset`
- `PresetRule`
- `ScaffoldResult`
- `apply_branch_protection`
- `auto_link_docs`
- `bootstrap_project`
- `build_agents_md_content`
- `build_flow_config`
- `build_protection_payload`
- `check_config_drift`
- `classify_doc`
- `compose_all_roles`
- `compose_role`
- `cursor_rules_body`
- `cursor_rules_relpath`
- `detect_preset`
- `detect_stack`
- `format_polish_text`
- `generate_adapters`
- `generate_agents_md`
- `generate_polish_data`
- `generate_rules`
- `generate_skeletons`
- `import_docs`
- `interactive_init`
- `load_flow_config`
- `load_flow_config_or_default`
- `non_interactive_init`
- `prime_context`
- `read_deep_config`
- `refresh_agentic_flow_files`
- `refresh_claude_md`
- `refresh_composed_adapters`
- `resolve_flow_config`
- `roles_templates_root`
- `scaffold`
- `scan_project`
- `setup_mcp_auto`
- `setup_rules_auto`
- `sync_agentic_flow`
- `templates_root`
- `vendored_flow_root`

## Relationships

- **part_of**: [beadloom](../services/beadloom.md)
- **Used by**: [application](../domains/application.md), [cli](../services/cli.md), [mcp-server](../services/mcp-server.md)
- **Parts**: [agent-prime](../features/agent-prime.md), [agentic-flow-setup](../features/agentic-flow-setup.md), [ai-techwriter-setup](../features/ai-techwriter-setup.md), [branch-protection](../features/branch-protection.md), [config-check](../features/config-check.md), [doc-generator](../features/doc-generator.md), [flow-config](../features/flow-config.md), [role-adapters](../features/role-adapters.md), [role-composer](../features/role-composer.md)

## Documentation

- [domains/onboarding/README.md](/docs/domains/onboarding/README.md)

## Diagram

```mermaid
C4Container
    System_Boundary(onboarding_boundary, "onboarding") {
        Component(agent_prime, "Agent Prime", "", "Cross-IDE context injection via prime CLI/MCP + AGENTS.md + IDE adapters")
        Component(agentic_flow_setup, "Agentic Flow Setup", "", "`setup-agentic-flow` — scaffold Beadloom's proven multi-agent dev flow (agents/commands templates, vendored 1:1 + drift-guard) into any repo")
        Component(ai_techwriter_setup, "Ai Techwriter Setup", "", "`setup-ai-techwriter` — scaffold the packaged AI tech-writer harness (CI workflow + recipe + guide) into any repo; no vendoring")
        Component(branch_protection, "Branch Protection", "", "`setup-branch-protection` — idempotent main branch-protection (PR-required + ci.yml required status checks)")
        Component(config_check, "Config Check", "", "AgentConfigAsCode — drift detection (and --fix) for generated agent-config artifacts (AGENTS.md, CLAUDE.md auto-blocks, IDE adapters)")
        Component(doc_generator, "Doc Generator", "", "Doc skeleton generation + AI polish data from architecture graph")
        Component(flow_config, "Flow Config", "", "`.beadloom/flow.yml` schema + loader (FlowConfig) — declares tools/architecture/stack/quality for the role configurator; strict validation + auto-detect/resolve defaults")
        Component(role_adapters, "Role Adapters", "", "generate_adapters — writes per-tool role adapter sets (.claude/agents/*, .cursor/agents/* + Cursor orchestrator) from composed roles; the drift-guard's single writer")
        Component(role_composer, "Role Composer", "", "compose_role — assembles a role file from CORE + one architecture overlay (ddd/fsd) + stack overlays (python/fastapi/js/ts/vue), deterministically ordered")
    }
```

