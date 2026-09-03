# beadloom:domain=application
# beadloom:component=mutation-scope
"""What a mutation run produced, over the scope a project declared (BDL-068 S3.1).

The scope half of this component asks whether a declared target COULD run a
mutant. This half asks what a run over it DID, and it exists because nothing in
this repository could previously tell a performed mutation check from a sentence
claiming one.

**The counter vocabulary is names, not a tool.** A run leaves behind a JSON
object of counters; this module reads them by name, accepts the two spellings of
the mutant total that runners disagree about, and REPORTS a counter it did not
find rather than reading it as zero. That last rule is the whole design: a
missing ``killed`` read as zero yields "0%", and a number is what gets pasted
into a bead comment. An absence has to stay an absence.

**Timeouts count as killed; mutants no test covers do not.** A mutant that hung
the suite was detected. A mutant no test executes was not, and leaving that class
out of the denominator is exactly how a slice with no tests at all scores 100%.

**A score carries the room it was measured in** (BDL-UX #227): the same suite
skips fifteen tests on Linux that it does not skip on macOS, and a mutation score
is a ratio over whatever ran. The room is DERIVED from the interpreter and the
platform rather than typed by the caller, because a room a caller can spell is a
room a caller can spell wrongly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.application.mutation_scope.scope import (
    MutationScopeFinding,
    check_mutation_scope,
    load_mutation_targets,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: A declared target no run in the report covered.
MUTATION_TARGET_UNMEASURED = "mutation-target-unmeasured"

#: The run covered the target and produced no mutants at all.
MUTATION_RUN_ZERO_MUTANTS = "mutation-run-zero-mutants"

#: The run's counters do not carry a number the score is computed from.
MUTATION_COUNTERS_MISSING = "mutation-counters-missing"

#: Counters without which there is no ratio, and the spellings accepted for each.
REQUIRED_COUNTERS: dict[str, tuple[str, ...]] = {
    "killed": ("killed",),
    "survived": ("survived",),
}

#: Counters a run may or may not classify. Absent means zero of that class,
#: which is a different statement from "the runner never said" for the two
#: above: a run with no timeouts and a run that does not model timeouts agree
#: on the ratio, while a run that does not say how many it killed has none.
OPTIONAL_COUNTERS: dict[str, tuple[str, ...]] = {
    "timeout": ("timeout", "timed_out"),
    "no_tests": ("no_tests",),
    "skipped": ("skipped",),
    "suspicious": ("suspicious",),
    "mutants": ("mutants", "total"),
}


@dataclass(frozen=True)
class MutationCounters:
    """The counters a run left behind, and the ones it did not."""

    values: Mapping[str, int] = field(default_factory=dict)
    missing: tuple[str, ...] = ()

    @property
    def scored(self) -> int:
        """Mutants a verdict was reached about, either way."""
        classes = ("killed", "timeout", "survived", "no_tests")
        return sum(self.values.get(name, 0) for name in classes)

    @property
    def produced(self) -> int:
        """Mutants the run generated, as the run counted them if it did."""
        if "mutants" in self.values:
            return self.values["mutants"]
        return self.scored + self.values.get("skipped", 0) + self.values.get("suspicious", 0)

    @property
    def score(self) -> float | None:
        """Killed over scored, or nothing at all when nothing can be divided."""
        if self.missing or self.scored == 0:
            return None
        return (self.values.get("killed", 0) + self.values.get("timeout", 0)) / self.scored


@dataclass(frozen=True)
class MutationRun:
    """One mutation run: what tool, what room, what scope, what counters."""

    tool: str
    room: str
    covered: tuple[str, ...]
    counters: MutationCounters


@dataclass(frozen=True)
class MutationReport:
    """The declared scope held against the run that was supposed to cover it."""

    declared: tuple[str, ...]
    run: MutationRun | None
    score: float | None
    findings: tuple[MutationScopeFinding, ...]
    #: Declared targets this run was not answerable for. Named rather than
    #: dropped: a slice that measures one target of several is the normal state,
    #: and a report that omitted the rest would read as full coverage.
    not_judged: tuple[str, ...] = ()


def describe_room() -> str:
    """The room a measurement was taken in, derived rather than declared.

    Platform, machine, interpreter and the parallelism available to it. A
    mutation score is a ratio over whatever ran, and what runs differs by room.

    One home since BDL-068 S3.2: the same sentence is printed beside a Gate
    verdict and beside a mutation score, so :mod:`beadloom.application.rooms`
    composes it and this function keeps the name its callers import.
    """
    from beadloom.application.rooms import current_room, room_line

    return room_line(current_room())


def read_run_counters(path: Path) -> MutationCounters:
    """Read a run's counters from a JSON object of counter names.

    A file that is absent, unreadable or not a JSON object is missing every
    required counter — the same answer as a file that omits them, because the
    consequence is the same: no ratio can be computed.
    """
    data = _read_json_object(path)
    values: dict[str, int] = {}
    missing: list[str] = []
    for name, spellings in REQUIRED_COUNTERS.items():
        found = _counter(data, spellings)
        if found is None:
            missing.append(name)
        else:
            values[name] = found
    for name, spellings in OPTIONAL_COUNTERS.items():
        found = _counter(data, spellings)
        if found is not None:
            values[name] = found
    return MutationCounters(values=values, missing=tuple(missing))


def report_mutation_score(
    project_root: Path,
    run: MutationRun | None,
    *,
    only: tuple[str, ...] | None = None,
) -> MutationReport:
    """Hold a run's counters against the scope the project declared.

    Three findings, all ``warn``, and each of them a state in which a number
    would be a claim rather than a measurement: a declared target no run
    covered, a run that produced no mutants, and counters the score cannot be
    computed from.

    The scope half is asked as well, and only about the targets this run is
    answerable for. Until BDL-068 S3.3 it was not: a target naming a path the
    code had moved away from could be "measured" at 100 percent and exit 0,
    because the command producing the NUMBER never asked whether the target
    could have produced a mutant. ``config-check`` and the Gate did ask, and a
    reader holding a score in their hand was looking at neither.

    ``only`` names the declared targets this run is answerable for. A first
    slice measures one target of several, and both obvious answers are wrong:
    reporting the rest as findings makes a job permanently red, which is how a
    check stops being read, and dropping them from the declaration deletes the
    duty. What is named in ``only`` is judged; the rest are carried on
    :attr:`MutationReport.not_judged` and printed.
    """
    declared = load_mutation_targets(project_root)
    judged = tuple(t for t in declared if only is None or _is_covered(t, only))
    not_judged = tuple(t for t in declared if t not in judged)
    findings: list[MutationScopeFinding] = []

    covered = run.covered if run else ()
    for target in judged:
        if not _is_covered(target, covered):
            findings.append(_unmeasured(target, covered))

    findings.extend(f for f in check_mutation_scope(project_root) if f.target in judged)

    if run is not None:
        findings.extend(_counter_findings(run))
    return MutationReport(
        declared=declared,
        run=run,
        score=run.counters.score if run else None,
        findings=tuple(findings),
        not_judged=not_judged,
    )


def _counter_findings(run: MutationRun) -> list[MutationScopeFinding]:
    """What the run's own counters say about whether they can be scored."""
    scope = ", ".join(run.covered) or "the declared scope"
    if run.counters.missing:
        names = ", ".join(run.counters.missing)
        return [
            MutationScopeFinding(
                check=MUTATION_COUNTERS_MISSING,
                target=scope,
                why=(
                    f"the run over {scope} left no {names} counter, so no score "
                    f"can be computed from it — and a missing counter read as "
                    f"zero would produce a number instead"
                ),
                remediation=(
                    "have the runner write the counters it classified, or name "
                    "the file it wrote them to"
                ),
            )
        ]
    if run.counters.produced == 0:
        return [
            MutationScopeFinding(
                check=MUTATION_RUN_ZERO_MUTANTS,
                target=scope,
                why=(
                    f"the run over {scope} produced no mutants, so its score is "
                    f"a ratio over an empty denominator rather than evidence of "
                    f"test strength"
                ),
                remediation=(
                    "check the runner's own scope against the declared targets: "
                    "a run producing nothing is usually pointed somewhere else"
                ),
            )
        ]
    if run.counters.scored == 0:
        return [
            MutationScopeFinding(
                check=MUTATION_RUN_ZERO_MUTANTS,
                target=scope,
                why=(
                    f"the run over {scope} produced {run.counters.produced} "
                    f"mutants and reached a verdict on none of them, so the "
                    f"score is a ratio over an empty denominator — a run whose "
                    f"every mutant was skipped states no more than a run that "
                    f"never happened"
                ),
                remediation=(
                    "check why the runner classified nothing — a suite that "
                    "cannot start in the runner's copied tree skips every "
                    "mutant and leaves counters that look like a clean sheet"
                ),
            )
        ]
    return []


def _unmeasured(target: str, covered: tuple[str, ...]) -> MutationScopeFinding:
    scope = ", ".join(covered) if covered else "no run"
    return MutationScopeFinding(
        check=MUTATION_TARGET_UNMEASURED,
        target=target,
        why=(
            f"the mutation target {target!r} is declared and was measured by "
            f"{scope} — the duty is stated and no score answers it"
        ),
        remediation=(
            "run the project's mutation tool over the target and report the "
            "counters it wrote, or drop the target from `mutation.targets`"
        ),
    )


def _is_covered(target: str, covered: tuple[str, ...]) -> bool:
    """Whether one declared target lies inside anything the run covered."""
    wanted = target.strip("/")
    return any(
        wanted == entry.strip("/") or wanted.startswith(f"{entry.strip('/')}/")
        for entry in covered
    )


def _read_json_object(path: Path) -> Mapping[str, object]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _counter(data: Mapping[str, object], spellings: tuple[str, ...]) -> int | None:
    """One counter, under any spelling, provided it is a whole non-negative number.

    ``bool`` is excluded on purpose: ``True`` is an ``int`` in Python and
    ``"killed": true`` is not a count.

    A NEGATIVE is excluded for the same reason and with a sharper consequence
    (BDL-068 S3.3): ``killed: -5`` beside ``survived: 1`` divided to
    "125.0% of -4 scored mutants" — a percentage over a negative denominator,
    printed with no finding beside it. A count that cannot be a count is not
    read, so a required counter written that way is MISSING and an optional one
    is absent, which are both states this module already reports.
    """
    for spelling in spellings:
        value = data.get(spelling)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            return value
    return None
