# Role Adapters

Generates per-tool role adapters from composed roles (BDL-052 S3).

**Source:** `src/beadloom/onboarding/role_adapters.py`

---

## Specification

### Purpose

The role configurator's output stage: given a `FlowConfig`, compose each role
once and write a **per-tool adapter set** for every configured tool. Every
adapter body is exactly `compose_role(...)` for the repo's `flow.yml` **plus its
project layer** (`.beadloom/flow/roles/<role>.md`), so this is the single writer
the drift-guard verifies against — and a project extension is part of the
expected result rather than drift (BDL-UX #139, #152).

### Tool adapter sets

- **claude** → `.claude/agents/<role>.md` (the Claude-Code subagent files). The
  slash-command set (`.claude/commands/*`) is composed separately by
  `agentic_flow_setup` and is not regenerated here.
- **cursor** → `.cursor/agents/<role>.md` (Cursor subagents — same composed
  body) plus a thin `.cursor/rules/beadloom-flow.md` orchestrator pointer (the
  coordinator-as-Cursor-mode entry point).

The pointer's list of roles is **rendered over `ROLE_NAMES`**, not typed into it (BDL-068
S1.5). It used to spell the four names as prose, so a fifth role reached the composer, the
adapters and the drift-guard and was absent from the one file that tells a Cursor user which
roles exist.

### Modules

- **role_adapters.py** — `generate_adapters(config, project_root, preserve=…)`,
  `AdapterResult`, `TOOL_AGENT_DIRS`, `cursor_rules_relpath()`,
  `cursor_rules_body()`.

### Invariants

- Idempotent: the bytes depend only on `config` + the overlay sources, so
  re-running with the same config rewrites identical files.
- A hand-edit of any adapter, or a CORE/overlay change without regenerating,
  makes the on-disk file differ from the recomputed composition and is flagged
  by `config-check`. Which of the two it is, is decided by the flow manifest:
  every write records the body's sha256, so a file Beadloom wrote and nobody
  touched is recomposed while a hand-edited one is reported and left alone.
- **Who owns a body is the caller's judgement, not this module's.**
  `setup-agentic-flow` is an explicit instruction to compose and passes nothing;
  `config-check --fix` passes every adapter it cannot prove Beadloom wrote in
  `preserve`, and those paths are neither written nor recorded — recording a
  digest we did not write would make the next run believe the edit was ours
  (BDL-UX #186).
- Beadloom's own `.claude/agents/*` reproduce exactly from
  `compose_role(ddd, python)`.

## API

Module `src/beadloom/onboarding/role_adapters.py`:
- `generate_adapters(config, project_root, *, preserve=frozenset())` →
  `AdapterResult` — `preserve` names project-relative paths to leave exactly as
  they are
- `AdapterResult` — `agents: dict[str, list[str]]`, `extra: list[str]`,
  `preserved: list[str]`
- `TOOL_AGENT_DIRS` — `{claude: .claude/agents, cursor: .cursor/agents}`
- `cursor_rules_relpath()` → `Path`
- `cursor_rules_body()` → `str`

Writes are fingerprinted through `flow_manifest.record()`.

## Testing

Tests: `tests/test_role_configurator.py`, `tests/test_flow_composition.py`
