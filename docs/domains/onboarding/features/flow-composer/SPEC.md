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
| 2 | `core:<shared>` | a CORE fragment **every** artifact of the kind carries | yes |
| 3 | `architecture:<a>` | one methodology overlay (`ddd` \| `fsd`) | yes |
| 4 | `stack:<s>` | each stack overlay, **sorted** | yes |
| 5 | `project` | `.beadloom/flow/<kind>/<name>.md` in the adopting repo | yes |

**Shared CORE fragments** (`ArtifactKind.shared`, BDL-061 S4) are how one text
reaches several artifacts without being copied into each. There are two —
`SHARED_ROLE_FRAGMENTS = ("_writing", "_rooms", "_landing")` — and all three exist for the same
reason: several copies of one rule drift the moment one of them is edited.

`_writing` is the writing standard. It used to live inside the `tech-writer`
core, so the roles that produce the TO-BE documents were held to no standard at
all. `_landing` (BDL-068 S5) is what the merge slot grants and what it does not,
for every role that lands a commit in a tree it shares — the statement that was
prose in one slash command while every launch prompt mandated the primitive it
describes. `_rooms` (BDL-068 S3.2) is the statement every role that reports a
MEASUREMENT is held to: name the room a result was taken in, report a clean-room
result in the words that say it was one, and read a room-naming verdict as
answerable rather than as stronger. It also carries the limit of a clean room —
that it is blind by construction to an interaction with a bead running beside
you — which until then was stated only in the coordinator command, read by the
loop that orchestrates rather than by the roles that measure.

A shared fragment is a **layer and not a role**: it has no front matter, is
never written as an adapter, and `compose_role("_writing", …)` raises. Being a
normal layer, each is language-selectable like every other one
(`_writing.ru.md.txt`, `_rooms.ru.md.txt` and `_landing.ru.md.txt` ship).

### Artifact kinds

| kind | core fragment | overlay root | project fragment |
|------|---------------|--------------|------------------|
| `roles` | `templates/roles/core/<role>.md.txt` | `templates/roles/` | `.beadloom/flow/roles/<role>.md` |
| `commands` | `templates/agentic_flow/commands/<cmd>.md.txt` | `templates/commands/` | `.beadloom/flow/commands/<cmd>.md` |
| `claude` | `templates/agentic_flow/CLAUDE.md.txt` | `templates/claude/` | `.beadloom/flow/claude/CLAUDE.md` |
| `docs` | `templates/docs/core/<kind>.md.txt` | `templates/docs/` | `.beadloom/flow/docs/<kind>.md` |

`docs` (BDL-061 S4b) is the only kind with `carries_suppressions=False`: a
declared suppression stands down a rule addressed to an AGENT, and a generated
README has no rules to stand down, so appending the notice would publish flow
configuration as documentation. See
[`doc-templates`](../doc-templates/SPEC.md).

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
- `ARTIFACT_KINDS` (`roles`, `commands`, `claude`, `docs`), `CLAUDE_ARTIFACT_NAME`, `COMPOSED_MARKER`,
  `PROJECT_FLOW_DIRNAME`

## Testing

Tests: `tests/test_flow_composition.py`, `tests/test_role_configurator.py`,
`tests/test_role_configurator_hardening.py`.
