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
| `missing` | recorded, or in a project that accounts for its writes, and gone from disk | `error` |
| `unverified` | nothing accounts for it — no manifest, no provenance stamp | `warn` |

`unverified` is an answer, not a guess. Reporting it as `warn` is what keeps
the CONTEXT constraint that no adopter's green project turns red on upgrade;
`hand_edited` stays an `error` because the drift-guard's job did not change —
only its remedy did. `--fix` now names `.beadloom/flow/<kind>/<name>.md` instead
of deleting the edit (BDL-UX #139, #152).

The word is `sync-check`'s (BDL-061 `.46`/`.47`), on purpose: *unverifiable is
not clean*, and two surfaces that mean the same thing must not spell it two
ways. It replaced `unmanaged` in `.57`.

`alternates` lets a caller pass other bodies Beadloom itself could have written
(the shipped core without the project layer), so a repo that predates the
manifest and was never edited still reads `stale` rather than `unverified`.

### Absence is not evidence

`classify` takes `accounted`: whether Beadloom's writes to this artifact are
accounted for **at all**. Without it, `rm .beadloom/flow-manifest.json` turned a
hand edit from `error` into `warn` and `config-check` from exit 1 into exit 0 —
measured on a scaffolded temp project, same edit, same file (BDL-061 `.57`,
review `.11` MAJOR 2). The gate is not satisfied by having less to check
(BDL-UX #174).

A project is accounted for when it keeps a **usable** manifest (present, parseable,
with a `written` map) *or* when the artifact itself carries the provenance stamp
only a manifest-era composer writes. A body that is then absent from the record
was not written by us, and reads `hand_edited`. Only a project with neither
signal is genuinely pre-manifest, and only that one reads `unverified`.

A corrupt manifest counts as *not* accounted for, deliberately: a file we cannot
read tells us nothing about what we wrote, and treating it otherwise would make
an unreadable manifest stricter than a missing one.

`.beadloom/flow-manifest.json` is generated, and it belongs in git. It is the
record of what Beadloom wrote; a clone without it can only report `unverified`,
which `config-check` says in those words rather than passing silently.

### Ownership boundary

`config-check` verifies a `CLAUDE.md` body only when the file is Beadloom's: it
has a manifest entry, or it carries the `<!-- beadloom:composed` provenance
stamp the shipped core now begins with. A project's own hand-written
`CLAUDE.md` is not ours to JUDGE — the same boundary `_is_beadloom_adapter`
draws for IDE adapter files, and the reason the BDL-UX #73 false-positive class
does not return.

It is a boundary on the VERDICT, not on the reporting. In a project that adopted
the flow, a `CLAUDE.md` with neither signal is named and reported `unverified` at
`warn` rather than passed over in silence — see the config-check SPEC, *Ownership
boundary* and *The honest floor*.

## API

Module `src/beadloom/onboarding/flow_manifest.py`:
- `digest(text)`, `load_manifest(root)`, `record(root, entries)`
- `read_manifest(root)` → `(entries, usable)` — the map, and whether this project
  keeps a usable manifest (the `accounted` input)
- `classify(*, on_disk, expected, recorded, alternates=(), accounted=False)` →
  `ArtifactState`
- `state_of(root, relpath, *, expected, manifest=None, alternates=(), accounted=None)`
- `FLOW_MANIFEST_RELPATH` — `.beadloom/flow-manifest.json`

## Testing

Tests: `tests/test_flow_composition.py`, `tests/test_config_sync.py`.
