# Config Check (AgentConfigAsCode)

Drift detection for generated agent-config artifacts, in the onboarding domain.

**Source:** `src/beadloom/onboarding/config_sync.py`

---

## Specification

### Purpose

Treat the agent-config artifacts that Beadloom generates as code: detect drift
between the generated output and the committed files, and re-render them on
demand. This is the `config-check` step in `beadloom ci` and the seam behind
`--fix`.

### Owned artifacts

`check_config_drift` regenerates each managed artifact in memory and diffs it
against disk, returning one `ConfigDrift` per drifted artifact, sorted by path:

- `.beadloom/AGENTS.md` — fully generated, with a preserved `custom` block
  between the `beadloom:custom-start` / `custom-end` markers.
- the auto-managed sections of `.claude/CLAUDE.md` — between the
  `beadloom:auto-start` / `auto-end` markers.
- the thin IDE adapter files (`.cursorrules`, …).
- when a repo has the agentic flow fully scaffolded, each `.claude/agents/*` and
  `.claude/commands/*` file is byte-compared against its shipped vendored
  template, and the composed adapters and `flow.yml` are checked.

Absent targets are skipped — not flagged as drift — so a repo without the flow
scaffolded is never reported for it. `refresh_composed_adapters` and
`refresh_agentic_flow_files` re-render the managed files (the `--fix` path).

## Invariants

- User-authored `custom` blocks and prose outside the managed markers are
  preserved across regeneration.
- An absent target is not drift; only a present-but-stale artifact is flagged.
- The generator derives everything from the on-disk graph (`rules.yml`) and
  project metadata; the `conn` parameter exists only for signature symmetry with
  the gate orchestrator.

## API

Module `src/beadloom/onboarding/config_sync.py`:

- `check_config_drift(project_root, conn) -> list[ConfigDrift]` — report every
  drifted artifact, sorted by path.
- `ConfigDrift` — `file` (project-relative path) and `reason`
  (agent-actionable explanation).
- `refresh_composed_adapters(project_root) -> list[str]` — re-render the
  composed role adapters.
- `refresh_agentic_flow_files(project_root) -> list[str]` — re-render the
  scaffolded flow files.

## Testing

Tests: `tests/test_config_sync.py`
