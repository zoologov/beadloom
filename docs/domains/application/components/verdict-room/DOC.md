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
| a job's install step | the optional extras that leg's environment satisfies |
| the project distribution's installed metadata | the optional extras this run's interpreter has |

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
- the leg installs optional extras this run has not, or this run has extras the leg does not;
- the runner label names no platform at all, such as a self-hosted job's label list.

The direction is deliberate. A comparison that cannot be made must never resolve to a match,
because a match manufactures coverage nobody has. The runner-label vocabulary
(`ubuntu` → Linux, `macos` → Darwin, `windows` → Windows) is a translation between names, not a
room list: a label outside it is reported as unresolved.

## The extras dimension

BDL-UX #236. Measured on this repository at `6c4d0a9`, in one clean room, over one code base at
one commit: `mypy src/` reports **0 errors under `.[all,dev]` and 82 under `.[dev]`**, and
under the second **the whole `tui` suite leaves the run** — three of its four modules skip and
the fourth stops the collection with an error. Nothing about the code differs between those two runs. The
environment does, and until this dimension existed no report said so — so two agents following
one convention returned different verdicts and neither was wrong.

Both sides are derived, and neither is a list this component owns.

- **What this run has** comes from the analysed project's own distribution as the running
  interpreter holds it: `Provides-Extra` names the extras, the `extra == "…"` markers on
  `Requires-Dist` name what each one needs, and an extra is *installed* when every distribution
  it needs is present. The project is read from `pyproject.toml`'s `name`, not assumed to be
  Beadloom, because under `uv tool install beadloom` those are different distributions.
- **What a leg installs** comes from the install step its job declares — `uv sync --extra …`,
  `--all-extras`, or a `pip install` of a local path with a bracket.

**The comparison is on what an environment SATISFIES, not on what somebody typed.** A leg
installing `dev,languages,tui,watch,graphql` also satisfies `all`, because `all`'s requirements
are the union of those five. Comparing the typed lists would report two identical environments
as two different rooms.

Three answers, never two. When the interpreter holds no distribution of that name, or the
packaging names none, the census carries **no `extras` dimension at all** and reports the reason
under Unresolved. A value spelling `unknown` would compare unequal to every leg and read as a
difference in the environment, when what happened is that nothing looked.

The current room's extras are computed from the project the census is taken over, so a bare
`current_room()` — the mutation score's room line, for one — carries no extras dimension.

## The unresolved population is part of the answer

A derivation that omits what it could not parse hands back a clean list, and a clean list is
trusted and stopped at. `UnresolvedRoom` carries the declaration and the reason: a workflow that
does not parse, a job with no `runs-on`, a `runs-on` expression over an input, a matrix using
`include` or `exclude` (which this report does not expand), and a matrix version left unquoted in
YAML, where `python-version: [3.10]` reaches the reader as the number `3.1`.

Three of them are about extras: a job that installs the project through a **local composite
action**, whose environment is declared somewhere this report does not follow; a job installing
an extra the **packaging does not declare**; and an extra whose requirements carry a **marker
beyond `extra ==`**, so whether this environment installed it cannot be decided from what is
present. A job that installs nothing runs no verdict and declares no environment, so it is not
reported as an absence.

## Where a room is reported

```bash
beadloom rooms                            # the census, in full
beadloom rooms --json                     # the same facts for a monitor
beadloom rooms --dimension python         # one axis, one value per line
beadloom rooms --dimension extras         # the environments this project's legs declare
beadloom ci                               # the verdict, with the room beside it
```

`beadloom ci` prints the room under its verdict in all three formats, and the MCP `complete_bead`
tool carries it on the verdict a bead is closed on. `beadloom mutation` names the same room beside
its score through `describe_room`, which composes it here so both surfaces print one sentence.

`--dimension` exits **2** when no declared room carries the axis, naming the axes that exist. An
empty answer would read as "this project has no such axis", which is the clean list an agent
trusts and stops at.

## Measured on this repository

Taken on 2026-09-08 on macOS, Apple silicon, under the interpreter this project is developed
on: 21 declared rooms across four workflow files, **0 entered** by a local run, four supported
interpreters each with a leg, and two unresolved jobs — the self-hosted `ai-techwriter` runner,
whose label list names no platform this report knows, and the `gate` job, which installs through
a local composite action.

The extras axis reports **four** distinct environments across those legs, and the local run
matched exactly one of them: this development environment carries `mutation`, which only
`mutation.yml` installs, so it differs from every `tests` leg by an extra nothing previously
named. That is the dimension doing its job on the machine that added it.

The room string itself is not quoted here. `docs audit` reads a version-like number beside the
word Python as a claim about the package version, and a document repeating one room's
interpreter build would go stale in a way that says nothing about this component. Run
`beadloom rooms` for the current answer.
