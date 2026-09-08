# Gate Coverage (component)

The verifications a project's pipeline declares that no step of a gate run performed.

**Source:** `src/beadloom/application/gate_coverage.py`

---

## Overview

`beadloom ci` runs reindex, lint, sync-check, docs-audit, docs-quality, doc-spaces,
scope-check, config-check and doctor. It does not run the test suite. The division is
reasonable and every step it *does* run is named in the output. What was missing until
BDL-UX #247 is the other half: the run never said the suite was not among them, while the
text around it promises otherwise — `CLAUDE.md` calls the pre-push hook "the full `beadloom
ci`" and the coordinator skill calls it "the authoritative blocking backstop" whose red
"blocks the push".

Measured twice in one slice, both times by the coordinator that wrote most of BDL-068:

- at `8befa96` a document change altered the approved node set and reddened two tests, and
  the Gate returned rc 0 over that tree;
- the S4 docs wave spilled an inline code span carrying `<doc>` onto the next line in
  `docs/services/cli.md`. `beadloom ci` returned rc 0 over that tree twice, PR #61 opened and
  all six test legs went red on one assertion that reproduces locally in 0.07 s — roughly 55
  runner-minutes to learn what one local command answers instantly.

**Naming what was not run does not change the verdict.** It is not a step: it has no status,
it adds no finding and it moves no exit code. `tests/test_gate_not_run.py` fails if that
stops being true.

## Two sides, both derived

| Side | Read from | Goes stale when |
|------|-----------|-----------------|
| what this run performed | the run's own `GateStep` names, plus any verification the caller ran beside it | never — a suite step added to the gate removes the line by the same act |
| what the project verifies | `.github/workflows/*.yml`, through `rooms.load_jobs` | never — a job added to the pipeline is read on the next run |

A hand-written sentence ("this gate does not run pytest") is the defect one level up:
`beadloom-0mdo.42` measured that trap when a derivation shipped behind a hand-written
`^(src|tests)/` filter and the filter, not the derivation, decided the answer. So the claim
here is a property of the step list, and nothing in this module names a step of the gate.

On this repository the run reports three:

```
Not run by this gate:
  the test suite — `uv run pytest --cov=beadloom --cov-report=term-missing --cov-fail-under=80` (.github/workflows/ci.yml: tests)
  the style linter — `uv run ruff check src/ tests/` (.github/workflows/ci.yml: tests)
  the type checker — `uv run mypy src/` (.github/workflows/ci.yml: tests)
```

The second and third are the ones nobody had filed. The gate's own step is named `lint` and
checks the **architecture boundaries**, not the source style, so `[PASS] lint` beside a green
verdict reads as ruff to anyone who has not read the step. `DUTIES` therefore binds the style
duty to `ruff`/`style`/`format` and deliberately not to `lint`.

## The vocabulary decides whether anything is said, never what is claimed

`DUTIES` recognises `pytest`; `ruff`, `flake8`, `pylint`; `mypy`, `pyright`. A command is
matched by its tool token after any runner prefix, so `uv run pytest --cov`, `python -m
pytest` and `poetry run mypy src` are one answer and `uv sync --extra dev` is none.

A project that verifies under a name this list does not hold is told the population is empty,
with the list named — never that nothing is left to run. That is the same distinction this
epic has shipped for an empty typed surface (`NOTHING TO CHECK`), an unowned path (`not
compared`), an unresolvable write target (`not_covered`) and a guard that cannot evaluate
itself (`unresolved`).

Four statements, one of which every run makes:

| Situation | What the report says |
|-----------|----------------------|
| the pipeline runs a verification no step performed | each one, with the command and the workflow job it was read from |
| every verification read is performed by a step | `every verification this report reads is performed by a step of this run` |
| workflows exist and declare none it reads | the count of files read, the tools it recognises, and that another name is not claimed about |
| a workflow could not be parsed | the file and the reason, and no claim about what was not run |
| no workflow exists | `this project declares no pipeline` |

## What is deliberately outside it

The nightly mutation run. It is a verification this project holds and no push gate could be
mistaken for running it: BDL-068 measured 54 min 55 s over 3 989 mutants with six workers on
a 10-core machine, against the ~16-28 runner-minute budget that withdrew `tests-windows`.
Naming it on every gate run would add a line no reader can act on. `config-check` already
reports the mutation **scope**, which is the part a gate can check in milliseconds.

## Where it surfaces

- `beadloom ci --format rich` — a block under the verdict, beside the room lines.
- `--format json` — `not_run: {performed, not_performed, unresolved, inspected}`.
- `--format github` — one `::notice::` naming the duties and their commands.
- the MCP `complete_bead` tool — `not_run`, on both the PASS and the FAIL payload. That tool
  runs the suite itself when `run_tests=True`, and passes `performed_elsewhere=("tests",)` to
  the gate so one run cannot report the suite as not run while that run ran it.

## Related

- `verdict-room` — the same shape one axis over: which rooms a verdict is true of.
- `ci-gate` — the run this component qualifies.
