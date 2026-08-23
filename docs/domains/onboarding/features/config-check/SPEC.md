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
- the **body** of `.claude/CLAUDE.md`, the `.claude/commands/*` files and the
  `.claude/agents/*` adapters — each against its **composition result**, not
  against fixed bytes (BDL-061 S3).
- `.beadloom/flow.yml` itself (unknown tool / architecture / stack / language,
  a suppression missing its reason or exit condition).

Absent targets are skipped — not flagged as drift — so a repo without the flow
scaffolded is never reported for it. `refresh_composed_adapters` and
`refresh_agentic_flow_files` re-render the managed files (the `--fix` path).

### The composition result, not file bytes

Byte-guarding a generated file against a fixed template makes extension
impossible: any project addition is drift and `--fix` deletes it, which is what
BDL-UX #139 and #152 record. Comparing against the *composition* — CORE + the
`flow.yml` overlays + the project layer in `.beadloom/flow/` — keeps both
properties at once: a project extension is part of the expected output, while a
change to a shipped fragment still differs from it and is reported.

### What was NOT checked before, measured

The `CLAUDE.md` **body** was verified by nothing. `_claude_md_drift` diffed only
the marker-bounded auto-regions, so on a freshly scaffolded project: appending a
project-local paragraph returned `[]`; deleting the whole of section 7 returned
`[]`; replacing the entire file with the single line `# gone` returned `[]` —
and the Gate printed `config-check PASS: agent-config in sync` over it
(BDL-UX #177, #178's shape on a second surface).

### Four states, four severities

`_state_drift` maps the flow-manifest classification onto a severity, because a
check that prints one word over several situations is the failure this epic
exists to remove:

| state | severity | what happens |
|-------|----------|--------------|
| `clean` | — | no finding |
| `stale` | `error` | recompose (`beadloom setup-agentic-flow`) |
| `hand_edited` | `error` | reported, **never rewritten**; the message names `.beadloom/flow/<kind>/<name>.md` |
| `unmanaged` | `warn` | predates the manifest, so a hand edit cannot be told apart from an upgrade — reported, does not block |

`unmanaged` is a warning so that no adopter's green project turns red on
upgrade. `hand_edited` stays an error because the drift-guard's job did not
change; only its remedy did — `--fix` moves nothing and deletes nothing, it
tells you where the edit belongs.

### Ownership boundary

The `CLAUDE.md` body check runs only when the file is Beadloom's: it has a flow
manifest entry, or it carries the `<!-- beadloom:composed` provenance stamp the
shipped core begins with. A project's own hand-written `CLAUDE.md` is not ours
to police — the same boundary `_is_beadloom_adapter` draws for IDE adapter
files, and the reason the BDL-UX #73 false-positive class does not return.

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
- `ConfigDrift` — `file` (project-relative path), `reason` (agent-actionable
  explanation), `severity` (`error` blocks the Gate, `warn` does not) and
  `remediation` (the concrete next move, or `None` for the caller's generic
  advice).
- `refresh_composed_adapters(project_root) -> list[str]` — re-render the
  composed role adapters.
- `refresh_agentic_flow_files(project_root) -> list[str]` — recompose the
  scaffolded flow files through the scaffold's own non-forcing path, so a
  hand-edited file survives `--fix`.

## Testing

Tests: `tests/test_config_sync.py`, `tests/test_flow_composition.py`,
`tests/test_cli_config_check.py`
