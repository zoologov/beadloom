# Verdict Room (component)

The rooms a verdict can be taken in: the one this run is in, the ones the project declares, and
the ones the run did not enter.

**Source:** `src/beadloom/application/rooms.py`

---

## Overview

A measurement is true of the room it was taken in. Read as a claim about the product, it is the
defect this component reports, and this project has measured it four times:

- BDL-067 reported "green on the tree" nine times. All nine were measured on macOS, the CI legs
  are Ubuntu, and the tenth measurement was red on six of them.
- `beadloom-mr2l.61`: fifteen tests skip on Linux that do not skip on macOS.
- BDL-UX #227: `mypy --strict` ran against one interpreter locally and four in CI, and an
  unnecessary `type: ignore` landed as a red pull request in eighteen seconds.
- BDL-UX #181: a clean-room verdict is correct and structurally cannot see an interaction with a
  bead running beside it.

**Naming the room does not make a verdict stronger. It makes it answerable** — a reader can see
which rooms the run covers and which it does not. The Gate's `ok`, its exit code and its findings
are unchanged by the room, and `tests/test_gate_verdict_room.py` fails if that stops being true.

## The rooms are derived, never listed

| Source | What it declares |
|--------|------------------|
| `pyproject.toml` classifiers | the interpreter versions the project supports |
| `pyproject.toml` `requires-python` | the floor, kept as a floor |
| `.github/workflows/*.yml` | one room per matrix combination, per job, per file |

A hand-written room list satisfies every test written beside it and goes stale the first time a
leg changes — which happened three times to this repository's own `DEFAULT_STATUS_CHECK_CONTEXTS`.
Adding a leg to a workflow, or an interpreter to the classifiers, changes the answer by the same
act that added it.

**A floor is not a set.** `requires-python = ">=3.10"` counted upward would need a hardcoded
newest Python, so a project with a floor and no classifiers gets an unresolved entry rather than
an enumerated set that quietly ages.

**The packaging metadata is read without a TOML parser.** `tomllib` is 3.11+ and `tomli` is not a
runtime dependency, so a parse would answer differently on 3.10 than on 3.13 — a room-dependent
answer from the component whose subject is rooms. `scanner/project_facts.py` states the same
reasoning for the project version.

## One rule decides whether a run entered a leg

A run **enters** a declared leg only when every dimension of that leg is comparable and equal.
Every other outcome is *not entered*, with the dimension that decided it named:

- the runner label names another platform — `ubuntu-latest` is Linux and this run is Darwin;
- the leg names another interpreter;
- the leg carries a dimension this run cannot describe, such as the `locale` legs;
- the runner label names no platform at all, such as a self-hosted job's label list.

The direction is deliberate. A comparison that cannot be made must never resolve to a match,
because a match manufactures coverage nobody has. The runner-label vocabulary
(`ubuntu` → Linux, `macos` → Darwin, `windows` → Windows) is a translation between names, not a
room list: a label outside it is reported as unresolved.

## The unresolved population is part of the answer

A derivation that omits what it could not parse hands back a clean list, and a clean list is
trusted and stopped at. `UnresolvedRoom` carries the declaration and the reason: a workflow that
does not parse, a job with no `runs-on`, a `runs-on` expression over an input, a matrix using
`include` or `exclude` (which this report does not expand), and a matrix version left unquoted in
YAML, where `python-version: [3.10]` reaches the reader as the number `3.1`.

## Where a room is reported

```bash
beadloom rooms                            # the census, in full
beadloom rooms --json                     # the same facts for a monitor
beadloom rooms --dimension python         # one axis, one value per line
beadloom ci                               # the verdict, with the room beside it
```

`beadloom ci` prints the room under its verdict in all three formats, and the MCP `complete_bead`
tool carries it on the verdict a bead is closed on. `beadloom mutation` names the same room beside
its score through `describe_room`, which composes it here so both surfaces print one sentence.

`--dimension` exits **2** when no declared room carries the axis, naming the axes that exist. An
empty answer would read as "this project has no such axis", which is the clean list an agent
trusts and stops at.

## Measured on this repository

Taken on 2026-09-03 on macOS, Apple silicon, under the interpreter this project is developed
on: 21 declared rooms across five workflow files, **0 entered** by a local run, four supported
interpreters each with a leg, and one unresolved job — the self-hosted `ai-techwriter` runner,
whose label list names no platform this report knows.

The room string itself is not quoted here. `docs audit` reads a version-like number beside the
word Python as a claim about the package version, and a document repeating one room's
interpreter build would go stale in a way that says nothing about this component. Run
`beadloom rooms` for the current answer.
