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
  body).

Until BDL-083 S2h this writer also wrote `.cursor/rules/beadloom-flow.md`, a 17-line
pointer that named the roles and carried no core, no project layer and no command, so a
Cursor agent ran the flow without them (BDL-UX #356). The pointer is retired: the scaffold
writes the composed core and the four commands as `alwaysApply` rules under
`.cursor/rules/`, and [`tool-reach`](../tool-reach/SPEC.md) states what each tool reads.
`AdapterResult.extra` stays and is empty. `cursor_rules_body()` and `cursor_rules_relpath()`
are gone with the pointer.

### Orphaned adapters — a tool that leaves `flow.yml`

`generate_adapters` writes for the tools `config.tools` names, and so does every reader of
what it wrote. So narrowing the tool subset does not report the files the dropped tool left
behind; it removes them from the check. Measured on 2026-09-09 with a control: in a project
scaffolded for `claude` and `cursor` and then narrowed to `claude`, the same two lines
appended to `.claude/agents/dev.md` are an `error` and the same two appended to
`.cursor/agents/dev.md` are exit 0.

`orphaned_adapters(project_root, config)` names them. Its population is the **flow
manifest**, not `TOOL_AGENT_DIRS` crossed with `ROLE_NAMES`, and both consequences are
wanted: a file Beadloom never recorded writing belongs to somebody else — an adopter who
drives Cursor by hand owns `.cursor/agents/dev.md` outright — and a role a later release
renames or retires is still reported, because the record of the write does not depend on the
roles this release composes. `diverged` says the body no longer matches the digest recorded
for it, which tells a file that has already changed apart from one that has merely stopped
being watched. An undecodable body counts as diverged: `_write` writes UTF-8, so a body that
will not decode as UTF-8 is not the one Beadloom wrote.

`.cursor/rules/` is **not** in this population: the rules sit outside the agent directory
the population is read from. When `cursor` leaves `tools:`, the `.cursor/rules/*.mdc` files
are therefore not reported as orphaned; that is a stated limit, not a decision about them.

Stated limit: provenance comes from the manifest, so a project whose
`.beadloom/flow-manifest.json` was deleted has none and is under-reported here.

### Modules

- **role_adapters.py** — `generate_adapters(config, project_root, preserve=…)`,
  `AdapterResult`, `TOOL_AGENT_DIRS`, `cursor_rules_relpath()`,
  `cursor_rules_body()`, `orphaned_adapters()`, `OrphanedAdapter`,
  `ORPHAN_MARKER`.

### Invariants

- Idempotent: the bytes depend only on `config` + the overlay sources, so
  re-running with the same config rewrites identical files.
- A hand-edit of any adapter, or a CORE/overlay change without regenerating,
  makes the on-disk file differ from the recomputed composition and is flagged
  by `config-check`. Which of the two it is, is decided by the flow manifest:
  every write records the body's sha256, so a file Beadloom wrote and nobody
  touched is recomposed while a hand-edited one is reported and left alone.
- **Who owns a body is the caller's judgement, not this module's — and both
  callers now make the same judgement.** Each passes the paths it cannot prove
  Beadloom wrote in `preserve`, derived from
  `config_sync.declined_adapter_rewrites()`, and those paths are neither written
  nor recorded: recording a digest we did not write would make the next run
  believe the edit was ours (BDL-UX #186). `config-check --fix` has done this
  since BDL-061 `.59`; `setup-agentic-flow` did not until BDL-068 `.67`, on the
  reading that a scaffold is an explicit instruction to compose. See
  [the agentic-flow-setup SPEC](../agentic-flow-setup/SPEC.md#one-policy-for-every-artifact-the-command-writes)
  for why that reading was retired (BDL-UX #191).
- The exception this list used to carry, the Cursor pointer rewritten
  unconditionally, is gone with the pointer (BDL-083 S2h). The rules that replaced
  it are written by the scaffold under the same policy as every other composed file.
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
- `orphaned_adapters(project_root, config)` → `tuple[OrphanedAdapter, ...]` — the
  manifest-recorded role adapters that sit under a tool `config.tools` does not
  name, sorted by path; empty when every recorded tool is declared
- `OrphanedAdapter` — `file`, `tool`, `diverged`, plus the `why` and
  `remediation` `config-check` prints for it
- `ORPHAN_MARKER` — the phrase every orphan finding carries, so a caller
  recognises one without matching a sentence a reword would break

Writes are fingerprinted through `flow_manifest.record()`.

## Testing

Tests: `tests/test_role_configurator.py`, `tests/test_flow_composition.py`,
`tests/test_orphaned_adapters.py`, and
`tests/acceptance/onboarding/config-check/orphaned_adapters.feature` for what an adopter is shown.
