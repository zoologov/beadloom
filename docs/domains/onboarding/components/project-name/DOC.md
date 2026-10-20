# Project Name (component)

Internal building block of the onboarding domain.

**Source:** `src/beadloom/onboarding/project_name.py`

---

## Overview

The shipped core of `CLAUDE.md` carries the neutral token `__BEADLOOM_PROJECT_NAME__` in its
`## 0.1 Project:` heading, and the composer fills in the project's name. This component
decides that name and records where it was read.

On 9.0.0 the name came from a root manifest or, failing one, from the directory the files sat
in. A project that names itself in no root manifest therefore composed one body in its main
checkout and was compared against another in a `git worktree` and in a clean room of the same
files. Measured at `f3d6f293` over a copy of the monorepo fixture: `config-check` exited 0, 1
and 1 in the three places (BDL-UX #334, RFC D7).

## Resolution order

`composition_project_name(project_root)` returns the first of these:

| Order | Read from | `source` | `declared` |
|-------|-----------|----------|------------|
| 1 | `project_name:` in `.beadloom/config.yml` | `.beadloom/config.yml (project_name:)` | `True` |
| 2 | a root manifest: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml` | the manifest's file name | `True` |
| 3 | the `## 0.1 Project:` heading of `.claude/CLAUDE.md`, then of the Cursor core rule | `<file>, the heading its last composition wrote` | `False` |
| 4 | the name of the resolved project directory | `the directory's name` | `False` |

A blank or non-string `project_name:` is not a name and falls through to the next row. A
heading that still holds the token records no name.

The third row is a record, not a declaration. It lives in a tracked file, so the checkout, a
worktree and a room read the same name. The price is that a hand edit of the heading's name
is not detected: the comparison takes the name from the file it compares. `config-check`
says so in its `CLAUDE.md:` line and names `project_name:` as the way to have the name
compared. The fourth row is reached only by the first composition of a project that declares
nothing, which writes the name into the heading and so moves the project to the third row.

## Public surface

- `composition_project_name(project_root) -> ProjectName` — the name and its source.
- `ProjectName` — `value`, `source` and `declared`, frozen.
- `PROJECT_NAME_KEY` (`"project_name"`) — the `config.yml` key.
- `PROJECT_NAME_PLACEHOLDER` — the token the shipped core carries.
- `PROJECT_HEADING_PREFIX` (`"## 0.1 Project: "`) — the text before the token. A test holds
  the shipped core to it, so the reader of the heading cannot drift from its writer.
- `DIRECTORY_SOURCE` — the `source` of the fourth row.

## Readers

`agentic_flow_setup` composes `.claude/CLAUDE.md` and the Cursor core rule with this name, and
`config_sync` compares against a composition with it: the body check, the `ClaudeComparison`
that names the comparison's inputs, and the corpus the suppression check matches against.
`init` and `prime` still use `scanner._detect_project_name`, whose fallback is the directory's
name. They name a project once or print it, and compare nothing.

## Testing

`tests/unit/onboarding/project_name/test_the_composition_takes_the_declared_name.py` holds the
resolution order. The verdicts it decides are held by
`tests/acceptance/onboarding/config-check/one_verdict_wherever_it_runs.feature`.
