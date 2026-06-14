<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T12:30:18.610981+00:00 · coverage 100% (`role-adapters`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Role Adapters

Generates per-tool role adapters from composed roles (BDL-052 S3).

**Source:** `src/beadloom/onboarding/role_adapters.py`

---

## Specification

### Purpose

The role configurator's output stage: given a `FlowConfig`, compose each role
once and write a **per-tool adapter set** for every configured tool. Every
adapter body is exactly `compose_role(...)`, so this is the single writer the
drift-guard verifies against.

### Tool adapter sets

- **claude** → `.claude/agents/<role>.md` (the Claude-Code subagent files). The
  slash-command set (`.claude/commands/*`) is vendored separately by
  `agentic_flow_setup` and is not regenerated here.
- **cursor** → `.cursor/agents/<role>.md` (Cursor subagents — same composed
  body) plus a thin `.cursor/rules/beadloom-flow.md` orchestrator pointer (the
  coordinator-as-Cursor-mode entry point).

### Modules

- **role_adapters.py** — `generate_adapters(config, project_root)`,
  `AdapterResult`, `TOOL_AGENT_DIRS`, `cursor_rules_relpath()`,
  `cursor_rules_body()`.

### Invariants

- Idempotent: the bytes depend only on `config` + the overlay sources, so
  re-running with the same config rewrites identical files.
- A hand-edit of any adapter, or a CORE/overlay change without regenerating,
  makes the on-disk file differ from the recomputed composition and is flagged
  by `config-check` (and the drift-guard test).
- Beadloom's own `.claude/agents/*` reproduce exactly from
  `compose_role(ddd, python)`.

## API

Module `src/beadloom/onboarding/role_adapters.py`:
- `generate_adapters(config, project_root)` → `AdapterResult`
- `AdapterResult` — `agents: dict[str, list[str]]`, `extra: list[str]`
- `TOOL_AGENT_DIRS` — `{claude: .claude/agents, cursor: .cursor/agents}`
- `cursor_rules_relpath()` → `Path`
- `cursor_rules_body()` → `str`

## Testing

Tests: `tests/test_role_configurator.py`
