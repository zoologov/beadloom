# Git Root (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/git_root.py`

---

## Overview

Beadloom takes its project root from the current directory or `--project` and never searches
upward. Git answers every question in paths relative to the root of its working tree. When
`.beadloom/` sits in a subfolder of a repository, the two frames disagree: `sync-check --since`
reads `git show <ref>:<path>` with a path git does not hold at that place, both sides come back
empty, and every pair is called fresh whatever changed (BDL-UX #325).

The owner ruled on 2026-10-12 that a nested root is a transition-period layout, so it is
refused by name rather than supported. This component is the one reader every refusing
surface asks, and it holds the one sentence they print: both roots, and the rule that the
project root must be the git root.

The question goes to git (`git rev-parse --show-cdup`) rather than to a search for a `.git`
above the directory, because git's answer is the one the other commands act on: a linked
worktree, a submodule and `GIT_CEILING_DIRECTORIES` are git's to decide. The answer is a run of
`../` segments, so no path git prints is decoded.

"Not nested" covers three answers: the project root is the git root, it is in no repository,
or git could not answer. None of them is a layout this component refuses.

## Public surface

- `nested_root(project_root)` — a `NestedRoot` when the git root lies above *project_root*,
  `None` otherwise.
- `NestedRoot` — the frozen pair `project_root` and `git_root`, both resolved.
- `NestedRoot.sentence()` — the refusal, starting `the git root is above the project root`.

## Collaborators

- `application/doctor.py` — the `git_root` row: `ERROR` when nested, which fails the Gate's
  `doctor` step and makes `beadloom doctor` exit 1.
- `services/commands/setup.py` — `init` refuses before any writer runs, in every mode.
- `services/commands/docsync.py` — `sync-check --since` refuses; `sync-check` without `--since`
  translates its paths through `--show-prefix` and is not refused.

> Component doc (BDL-083 S2e). Public surface verified against `git_root.py`.
