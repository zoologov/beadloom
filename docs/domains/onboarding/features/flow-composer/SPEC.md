# Flow Composer

`compose(core, architecture, stack, project)` — the one layered assembly behind
every flow artifact (BDL-061 S3).

**Source:** `src/beadloom/onboarding/composer.py`

---

## Specification

### Purpose

BDL-052 S3 composed *role files* from three shipped layers. S3 of BDL-061
generalises that in two directions at once, because both were needed to make
`CLAUDE.md` "modular and compact, and adaptable to a specific project without
breaking the Beadloom gate":

1. **Every** flow artifact composes — role files, slash commands, and
   `CLAUDE.md`. `CLAUDE.md` in particular used to be a byte-snapshot of
   Beadloom's own live file, which is why one project's local text kept
   reaching every adopter (BDL-UX #177).
2. A fourth, **project** layer is appended from `.beadloom/flow/<kind>/`, so an
   adopting team has a supported place for its standing practices instead of
   hand-editing a drift-guarded file (BDL-UX #139, #152).

### Layers

`compose(kind, name, *, config, project_root)` concatenates, in fixed order:

| # | Layer | Source | Optional |
|---|-------|--------|----------|
| 1 | `core` | the shipped CORE fragment for the kind | no |
| 2 | `architecture:<a>` | one methodology overlay (`ddd` \| `fsd`) | yes |
| 3 | `stack:<s>` | each stack overlay, **sorted** | yes |
| 4 | `project` | `.beadloom/flow/<kind>/<name>.md` in the adopting repo | yes |

### Artifact kinds

| kind | core fragment | overlay root | project fragment |
|------|---------------|--------------|------------------|
| `roles` | `templates/roles/core/<role>.md.txt` | `templates/roles/` | `.beadloom/flow/roles/<role>.md` |
| `commands` | `templates/agentic_flow/commands/<cmd>.md.txt` | `templates/commands/` | `.beadloom/flow/commands/<cmd>.md` |
| `claude` | `templates/agentic_flow/CLAUDE.md.txt` | `templates/claude/` | `.beadloom/flow/claude/CLAUDE.md` |

The commands and `CLAUDE.md` keep their vendored location as the CORE and gain
an overlay root beside it; moving them would have churned the whole scaffold for
no signal.

### Overlays are append-only

Nothing in the composer can remove core text. A project that must stand down a
core rule *declares* it (see `flow-suppression`), and the declaration is
appended as a visible notice — the core text stays, so drift on it is still
detectable and a reader is told what was stood down, by whom and until when.

### Language

A layer prefers `<name>.<lang>.md.txt` when `flow.yml` declares a non-default
`language`. A missing localisation falls back to the default **and records why
in `Composition.notes`** — a fallback to English is never silent (BDL-UX #136).

### Why `config-check` verifies the composition RESULT

Byte-guarding a generated file against a fixed template makes extension
impossible: any project addition is drift, and `--fix` deletes it. Verifying the
*result* keeps both properties — a project extension is part of the expected
output, while a change to a shipped fragment still differs from it and is
reported. The three-way classification that makes this safe lives in
`flow-manifest`.

### Invariants

- Deterministic: same `(kind, name, config, project layer)` → same bytes.
- An unknown `kind`, or a missing CORE fragment, raises `FlowConfigError` —
  loud, not a silently-empty file.
- A layer that contributes nothing is absent from `fragments`; a layer that
  could not do what was asked says so in `notes`.

## API

Module `src/beadloom/onboarding/composer.py`:
- `compose(kind, name, *, config, project_root=None)` → `Composition`
- `Composition.text` → the composed body
- `templates_dir()`, `project_fragment_path(kind, name, project_root)`
- `ARTIFACT_KINDS`, `CLAUDE_ARTIFACT_NAME`, `COMPOSED_MARKER`,
  `PROJECT_FLOW_DIRNAME`

## Testing

Tests: `tests/test_flow_composition.py`, `tests/test_role_configurator.py`,
`tests/test_role_configurator_hardening.py`.
