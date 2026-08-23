# Flow Manifest

What the composer last wrote, so a later run can tell its own output from a hand
edit.

**Source:** `src/beadloom/onboarding/flow_manifest.py`

---

## Specification

### Purpose

A composed artifact on disk can differ from its expected composition for two
opposite reasons that need opposite treatments:

- **the composition moved** — the shipped core was upgraded, or the project
  layer changed. Recompose it.
- **a human edited the file** — that edit is the only copy of somebody's
  intent. Report it with somewhere to put it, and never rewrite it.

Nothing in the file distinguishes the two. So every write records the SHA-256 of
exactly what was written, in `.beadloom/flow-manifest.json`.

### States

| state | meaning | severity in `config-check` |
|-------|---------|---------------------------|
| `clean` | byte-identical to the expected composition | — |
| `stale` | matches what Beadloom last wrote (or a shipped body) — the composition moved | `error` (recompose) |
| `hand_edited` | differs from both — a human changed a file Beadloom wrote | `error`, and **never** rewritten |
| `unmanaged` | no manifest entry — scaffolded before the manifest existed | `warn` |

`unmanaged` is a third answer, not a guess. Reporting it as `warn` is what keeps
the CONTEXT constraint that no adopter's green project turns red on upgrade;
`hand_edited` stays an `error` because the drift-guard's job did not change —
only its remedy did. `--fix` now names `.beadloom/flow/<kind>/<name>.md` instead
of deleting the edit (BDL-UX #139, #152).

`alternates` lets a caller pass other bodies Beadloom itself could have written
(the shipped core without the project layer), so a repo that predates the
manifest and was never edited still reads `stale` rather than `unmanaged`.

### Ownership boundary

`config-check` verifies a `CLAUDE.md` body only when the file is Beadloom's: it
has a manifest entry, or it carries the `<!-- beadloom:composed` provenance
stamp the shipped core now begins with. A project's own hand-written
`CLAUDE.md` is not ours to police — the same boundary `_is_beadloom_adapter`
draws for IDE adapter files, and the reason the BDL-UX #73 false-positive class
does not return.

## API

Module `src/beadloom/onboarding/flow_manifest.py`:
- `digest(text)`, `load_manifest(root)`, `record(root, entries)`
- `classify(*, on_disk, expected, recorded, alternates=())` → `ArtifactState`
- `state_of(root, relpath, *, expected, manifest=None, alternates=())`
- `FLOW_MANIFEST_RELPATH` — `.beadloom/flow-manifest.json`

## Testing

Tests: `tests/test_flow_composition.py`, `tests/test_config_sync.py`.
