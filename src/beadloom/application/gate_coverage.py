# beadloom:domain=application
# beadloom:component=gate-coverage
"""The verifications a project's pipeline runs that no step of a gate run performed.

**The defect this closes** (BDL-UX #247): ``beadloom ci`` runs reindex, lint,
sync-check, docs-audit, docs-quality, doc-spaces, scope-check, config-check and
doctor, and it does not run the test suite. The division is reasonable and every
step it *does* run is named in its output. What was missing is the other half —
the run never said the suite was not among them, while ``CLAUDE.md`` calls the
pre-push hook "the full ``beadloom ci``" and the coordinator skill calls it "the
authoritative blocking backstop". Read together, a green gate at push time reads
as the last line of defence before a pull request. For tests it is not one, and
that was measured twice in one slice: a document change reddened two tests under
a gate that returned rc 0, and a docs wave spilled an inline code span past a
line under a gate that returned rc 0 over that tree twice — after which all six
test legs went red on one assertion that reproduces locally in 0.07 s.

**Two sides, and each is derived from a declaration rather than from a sentence.**

* *What the run performed* comes from the run's own step list. A suite step
  added to the gate later removes the line by the same act, so this cannot
  become the stale sentence one level up — the trap ``beadloom-0mdo.42``
  measured when a derivation shipped behind a hand-written path filter.
* *What the project verifies* comes from the project's CI workflows, read
  through :func:`beadloom.application.rooms.load_jobs` — the same declaration
  the room census reads for its legs, so one file has one reader.

**The limit is stated rather than discovered.** :data:`DUTIES` is a vocabulary
of the verification tools this report can recognise, and a pipeline that
verifies under another name is reported as an empty population with that limit
named — never as a pipeline with nothing left to run. The vocabulary decides
whether anything is *said*; it never decides the claim, and the claim
("no step of this run performed it") is a property of the step list alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from beadloom.application.rooms import WORKFLOW_DIR, load_jobs

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path


@dataclass(frozen=True)
class _Duty:
    """One verification, the tools that perform it and the step names that do.

    ``step_names`` is deliberately not ``{"lint"}`` for the style linter: the
    gate's own ``lint`` step checks the architecture boundaries, not the source
    style, and a reader who takes ``[PASS] lint`` for ruff is the confusion this
    module exists to end.
    """

    name: str
    tools: frozenset[str]
    step_names: frozenset[str]


#: The verifications this report can recognise in a pipeline, and the words a
#: gate step performing one would carry. Python-named because the stack overlays
#: Beadloom composes ship Python commands; a project verifying under another
#: name is told the population is empty, with this limit named.
DUTIES: tuple[_Duty, ...] = (
    _Duty(
        name="the test suite",
        tools=frozenset({"pytest"}),
        step_names=frozenset({"tests", "test", "test-suite", "suite", "pytest"}),
    ),
    _Duty(
        name="the style linter",
        tools=frozenset({"ruff", "flake8", "pylint"}),
        step_names=frozenset({"ruff", "style", "style-lint", "format"}),
    ),
    _Duty(
        name="the type checker",
        tools=frozenset({"mypy", "pyright"}),
        step_names=frozenset({"mypy", "types", "type-check", "typecheck"}),
    ),
)

#: Tokens that introduce a command without being one. ``uv run pytest`` and
#: ``python -m pytest`` are the same verification, so the tool is the first
#: token that is none of these.
_RUNNER_TOKENS = frozenset(
    {"uv", "uvx", "npx", "run", "poetry", "pipenv", "hatch", "pdm", "rye", "-m"}
)

#: Interpreters that run a module rather than being the verification.
_INTERPRETERS = frozenset({"python", "python3"})

#: Separators inside one ``run:`` block. A shell line can hold several commands
#: and the verification is often the second.
_SEPARATORS = ("&&", ";", "|")

#: How many verifications the human report names before it stops listing.
_NAMED_LIMIT = 5


@dataclass(frozen=True)
class Verification:
    """One verification a project's pipeline declares, with where it was read."""

    duty: str
    command: str
    source: str


@dataclass(frozen=True)
class UnreadPipeline:
    """A workflow file this report could not read, and why."""

    source: str
    why: str


@dataclass(frozen=True)
class GateCoverage:
    """What a gate run performed, and what its project verifies elsewhere."""

    performed: tuple[str, ...] = ()
    """The step names this run performed, including any a caller ran beside it."""

    declared: tuple[Verification, ...] = ()
    """Every verification read from the pipeline, performed by this run or not."""

    not_performed: tuple[Verification, ...] = ()
    """The declared verifications no step of this run performed."""

    unresolved: tuple[UnreadPipeline, ...] = ()
    """Workflow files this report could not read, so it claims nothing from them."""

    inspected: int = 0
    """Workflow files read. ``0`` with no ``unresolved`` means none exists."""


def derive_gate_coverage(
    project_root: Path, *, performed: Iterable[str]
) -> GateCoverage:
    """The verifications *project_root* declares that *performed* does not cover.

    *performed* is the run's step names. Nothing about the answer is written
    down: a step whose name performs a duty removes that duty from the report,
    and a duty no workflow declares is never claimed.
    """
    step_names = tuple(performed)
    declared, unresolved, inspected = _read_pipeline(project_root)
    covered = {
        duty.name
        for duty in DUTIES
        if any(name in duty.step_names for name in step_names)
    }
    not_performed = tuple(item for item in declared if item.duty not in covered)
    return GateCoverage(
        performed=step_names,
        declared=declared,
        not_performed=not_performed,
        unresolved=unresolved,
        inspected=inspected,
    )


def gate_coverage_lines(coverage: GateCoverage) -> list[str]:
    """The human report's block: what this gate did not do, or why it cannot say.

    Lives beside the model rather than in a renderer because three formats and
    one MCP tool quote it, and a second wording is how two surfaces of one run
    come to disagree.
    """
    lines = ["Not run by this gate:"]
    if coverage.not_performed:
        for item in coverage.not_performed[:_NAMED_LIMIT]:
            lines.append(f"  {item.duty} — `{item.command}` ({item.source})")
        remaining = len(coverage.not_performed) - _NAMED_LIMIT
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")
        return lines
    lines.append(f"  {_empty_population(coverage)}")
    return lines


def _empty_population(coverage: GateCoverage) -> str:
    """Why nothing is named: read and covered, read and absent, or not read."""
    if coverage.unresolved:
        named = ", ".join(item.source for item in coverage.unresolved[:_NAMED_LIMIT])
        return (
            f"{len(coverage.unresolved)} workflow file(s) could not be read, so "
            f"this run makes no claim about what it did not do: {named}"
        )
    if coverage.declared:
        return "every verification this report reads is performed by a step of this run"
    if coverage.inspected == 0:
        return (
            "this project declares no pipeline, so there is no verification to "
            f"hold this run against ({WORKFLOW_DIR.as_posix()} has no workflow)"
        )
    return (
        f"{coverage.inspected} workflow file(s) declare no verification this "
        f"report reads ({_vocabulary()}); a pipeline verifying under another "
        "name is not claimed about"
    )


def _vocabulary() -> str:
    """The tools this report recognises, so an empty population is answerable."""
    return ", ".join(sorted(tool for duty in DUTIES for tool in duty.tools))


def _read_pipeline(
    project_root: Path,
) -> tuple[tuple[Verification, ...], tuple[UnreadPipeline, ...], int]:
    """One verification per duty, from the first command in the pipeline that runs it."""
    files = sorted(
        path for path in (project_root / WORKFLOW_DIR).glob("*.y*ml") if path.is_file()
    )
    found: dict[str, Verification] = {}
    unresolved: list[UnreadPipeline] = []
    for path in files:
        rel = path.relative_to(project_root).as_posix()
        jobs, failure = load_jobs(path)
        if failure is not None:
            unresolved.append(UnreadPipeline(source=rel, why=failure))
            continue
        for job_name, job in jobs.items():
            _collect_job(f"{rel}: {job_name}", job, found)
    ordered = tuple(
        found[duty.name] for duty in DUTIES if duty.name in found
    )
    return ordered, tuple(unresolved), len(files)


def _collect_job(
    source: str, job: Mapping[str, Any], found: dict[str, Verification]
) -> None:
    """Record the first command in one job that performs a duty not yet found."""
    steps = job.get("steps")
    if not isinstance(steps, list):
        return
    for step in steps:
        if not isinstance(step, dict):
            continue
        run = step.get("run")
        if not isinstance(run, str):
            continue
        for command in _commands(run):
            duty = _duty_of(command)
            if duty is not None and duty.name not in found:
                found[duty.name] = Verification(
                    duty=duty.name, command=command, source=source
                )


def _commands(run: str) -> list[str]:
    """The individual commands of one ``run:`` block, whitespace collapsed."""
    commands: list[str] = []
    for line in run.splitlines():
        for part in _split_on_separators(line):
            collapsed = " ".join(part.split())
            if collapsed:
                commands.append(collapsed)
    return commands


def _split_on_separators(line: str) -> list[str]:
    """``a && b ; c`` → ``["a", "b", "c"]`` — a shell line can hold several."""
    parts = [line]
    for separator in _SEPARATORS:
        parts = [piece for part in parts for piece in part.split(separator)]
    return parts


def _duty_of(command: str) -> _Duty | None:
    """The duty one command performs, or ``None`` when it performs none."""
    tool = _tool_of(command.split())
    if tool is None:
        return None
    for duty in DUTIES:
        if tool in duty.tools:
            return duty
    return None


def _tool_of(tokens: Sequence[str]) -> str | None:
    """The first token that is a tool rather than the runner in front of it.

    ``uv run pytest --cov`` and ``python -m pytest`` both answer ``pytest``;
    ``uv sync --extra dev`` answers ``sync``, which performs no duty. An option
    reached before any tool means the runner itself was the command, so there is
    nothing to name.
    """
    for index, token in enumerate(tokens):
        if token in _RUNNER_TOKENS:
            continue
        if token in _INTERPRETERS:
            if tokens[index + 1 : index + 2] == ["-m"]:
                continue
            return None
        if token.startswith("-"):
            return None
        return token.rsplit("/", 1)[-1]
    return None
