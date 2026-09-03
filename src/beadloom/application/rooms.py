# beadloom:domain=application
# beadloom:component=verdict-room
"""The rooms a verdict can be taken in, derived from where a project declares them.

A measurement is true of the room it was taken in. Read as a claim about the
product, it is the defect this module exists to report, and this project has
measured it four times: nine "green on the tree" claims taken on macOS against
CI legs that are Ubuntu, with the tenth measurement red on six of them; fifteen
tests that skip on Linux and not on macOS; a type check run against one
interpreter locally and four in CI, where an unnecessary ``type: ignore``
became a red pull request in eighteen seconds; and a clean-room verdict that is
correct and structurally cannot see an interaction with a bead running beside
it.

**Naming the room does not make a verdict stronger. It makes it answerable.**
The verdict is the same verdict; a reader can now see which rooms it covers.

**The rooms are derived, never listed.** The interpreters a project supports are
declared in its packaging metadata; the legs are declared in its CI workflows.
A hand-written room list satisfies every test written beside it and goes stale
the first time a leg changes -- which happened three times to this repository's
own ``DEFAULT_STATUS_CHECK_CONTEXTS``.

**One rule decides whether a run entered a leg:** every dimension of the leg is
comparable and equal. Anything else is "not entered", with the dimension that
decided it named. The direction is deliberate -- a comparison that cannot be
made must never resolve to a match, because a match manufactures coverage
nobody has.

**The packaging metadata is read without a TOML parser.** ``tomllib`` is 3.11+
and ``tomli`` is not a runtime dependency, so a parse would answer differently
on 3.10 than on 3.13 -- a room-dependent answer from the module whose subject is
rooms. Two scalars out of one known file do not need one; the same reasoning
``scanner/project_facts.py`` states for the project version.
"""

from __future__ import annotations

import itertools
import os
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping

#: Runner-label families and the platform each names. A VOCABULARY, not a room
#: list: it translates the names GitHub gives its images into what
#: :func:`platform.system` reports. A label outside it is unresolved rather than
#: assumed, so ``self-hosted`` never reads as a match.
RUNNER_PLATFORMS: dict[str, str] = {
    "ubuntu": "Linux",
    "macos": "Darwin",
    "windows": "Windows",
}

#: Matrix keys that mean the interpreter version, and the name this report uses
#: for that dimension. Every workflow in this repository spells it
#: ``python-version``; a key outside this map keeps its own spelling, so a
#: dimension nobody anticipated is still reported.
_PYTHON_KEYS = frozenset({"python-version", "python_version", "python"})

#: ``Programming Language :: Python :: 3.11`` — the bare ``:: 3`` is not a
#: version and is not matched.
_CLASSIFIER_RE = re.compile(
    r"Programming Language :: Python :: (\d+\.\d+)",
)

#: ``requires-python = ">=3.10"`` in the packaging metadata.
_REQUIRES_PYTHON_RE = re.compile(
    r'^\s*requires-python\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)

#: ``${{ matrix.os }}`` in a ``runs-on``.
_MATRIX_EXPRESSION_RE = re.compile(r"^\$\{\{\s*matrix\.([A-Za-z0-9_-]+)\s*\}\}$")

#: ``${{ anything }}`` — an expression this report cannot resolve.
_ANY_EXPRESSION_RE = re.compile(r"\$\{\{(.+?)\}\}")

_WORKFLOW_DIR = Path(".github") / "workflows"


@dataclass(frozen=True)
class Room:
    """One room a measurement can be taken in, and where it was declared.

    ``dimensions`` are free-form because a project's axes are its own: this
    repository varies the interpreter and the locale and deliberately does not
    vary the platform. ``source`` names the declaration, so a reader can go and
    change it rather than asking who wrote the list.
    """

    dimensions: Mapping[str, str]
    source: str

    @property
    def label(self) -> str:
        """``os=ubuntu-latest python=3.10`` — the dimensions, in a stable order."""
        return " ".join(f"{k}={v}" for k, v in sorted(self.dimensions.items()))


@dataclass(frozen=True)
class UnresolvedRoom:
    """Something the derivation could not turn into a room, and why.

    A derivation that omits what it could not parse hands back a clean list, and
    a clean list is trusted and stopped at. An unresolved entry is the answer's
    other half, not its failure.
    """

    source: str
    why: str


@dataclass(frozen=True)
class RoomComparison:
    """One declared room, and whether this run was in it."""

    room: Room
    entered: bool
    why: str = ""


@dataclass(frozen=True)
class DeclaredRooms:
    """What a project declares about the rooms its work is measured in."""

    rooms: tuple[Room, ...] = ()
    unresolved: tuple[UnresolvedRoom, ...] = ()
    supported: tuple[str, ...] = ()
    floor: str | None = None


@dataclass(frozen=True)
class RoomCensus:
    """The room a run is in, the rooms declared, and the ones it did not enter."""

    current: Room
    comparisons: tuple[RoomComparison, ...] = ()
    unresolved: tuple[UnresolvedRoom, ...] = ()
    supported: tuple[str, ...] = ()
    floor: str | None = None
    supported_without_a_leg: tuple[str, ...] = field(default=())

    @property
    def entered(self) -> tuple[RoomComparison, ...]:
        """The declared rooms this run can be held to."""
        return tuple(c for c in self.comparisons if c.entered)

    @property
    def not_entered(self) -> tuple[RoomComparison, ...]:
        """The declared rooms this run says nothing about."""
        return tuple(c for c in self.comparisons if not c.entered)


# ---------------------------------------------------------------------------
# The room this process is in
# ---------------------------------------------------------------------------


def current_room() -> Room:
    """The room this process is running in, derived rather than declared.

    A room a caller can spell is a room a caller can spell wrongly, so nothing
    here is an argument.
    """
    return Room(
        dimensions={
            "os": platform.system(),
            "arch": platform.machine(),
            "python": f"{sys.version_info[0]}.{sys.version_info[1]}",
            "python_full": platform.python_version(),
            "implementation": platform.python_implementation(),
            "cores": str(os.cpu_count() or 1),
        },
        source="this process",
    )


def room_line(room: Room) -> str:
    """The one-line human description of a room: platform, interpreter, width."""
    d = room.dimensions
    parts = [f"{d.get('os', '?')} {d.get('arch', '?')}".strip()]
    interpreter = f"{d.get('implementation', '')} {d.get('python_full', d.get('python', ''))}"
    parts.append(interpreter.strip())
    if "cores" in d:
        parts.append(f"{d['cores']} cores")
    return " · ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# What the project declares
# ---------------------------------------------------------------------------


def derive_declared_rooms(project_root: Path) -> DeclaredRooms:
    """Read the rooms a project declares out of its packaging and its workflows.

    Nothing here is a list this function owns: adding a leg to a workflow, or an
    interpreter to the classifiers, changes the answer by the same act.
    """
    supported, floor, packaging_unresolved = _read_packaging(project_root)
    rooms, workflow_unresolved = _read_workflows(project_root)
    return DeclaredRooms(
        rooms=rooms,
        unresolved=tuple(packaging_unresolved) + tuple(workflow_unresolved),
        supported=supported,
        floor=floor,
    )


def _read_packaging(
    project_root: Path,
) -> tuple[tuple[str, ...], str | None, list[UnresolvedRoom]]:
    """The interpreters the packaging metadata enumerates, and the floor it sets."""
    path = project_root / "pyproject.toml"
    unresolved: list[UnresolvedRoom] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return (
            (),
            None,
            [
                UnresolvedRoom(
                    source="pyproject.toml",
                    why=(
                        "no readable packaging metadata, so the interpreters this "
                        "project supports are unknown rather than none"
                    ),
                )
            ],
        )
    floor_match = _REQUIRES_PYTHON_RE.search(text)
    floor = floor_match.group(1) if floor_match else None
    supported = tuple(dict.fromkeys(_CLASSIFIER_RE.findall(text)))
    if not supported:
        unresolved.append(
            UnresolvedRoom(
                source="pyproject.toml",
                why=(
                    "no `Programming Language :: Python :: X.Y` classifier, so the "
                    f"supported set is not enumerated{_floor_clause(floor)} — a "
                    "floor cannot be counted upward without pinning a newest "
                    "Python, which is the list this report refuses to hold"
                ),
            )
        )
    return supported, floor, unresolved


def _floor_clause(floor: str | None) -> str:
    return f" (the floor is `{floor}`)" if floor else ""


def _read_workflows(
    project_root: Path,
) -> tuple[tuple[Room, ...], list[UnresolvedRoom]]:
    """One room per matrix combination, per job, per workflow file."""
    directory = project_root / _WORKFLOW_DIR
    files = sorted(p for p in directory.glob("*.y*ml") if p.is_file())
    if not files:
        return (), [
            UnresolvedRoom(
                source=str(_WORKFLOW_DIR),
                why=(
                    "no workflow file declares a leg, so this project declares no "
                    "room a verdict could be held against"
                ),
            )
        ]
    rooms: list[Room] = []
    unresolved: list[UnresolvedRoom] = []
    for path in files:
        rel = path.relative_to(project_root).as_posix()
        jobs, failure = _load_jobs(path)
        if failure is not None:
            unresolved.append(UnresolvedRoom(source=rel, why=failure))
            continue
        for name, job in jobs.items():
            job_rooms, job_unresolved = _rooms_of_job(f"{rel}: {name}", job)
            rooms.extend(job_rooms)
            unresolved.extend(job_unresolved)
    return tuple(rooms), unresolved


def _load_jobs(path: Path) -> tuple[dict[str, Any], str | None]:
    """The ``jobs`` mapping of a workflow, or the reason there is none."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return {}, f"the workflow could not be parsed ({type(exc).__name__})"
    if not isinstance(document, dict):
        return {}, "the workflow is not a mapping, so it declares no jobs"
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return {}, "the workflow declares no `jobs` mapping"
    return {k: v for k, v in jobs.items() if isinstance(v, dict)}, None


def _rooms_of_job(
    source: str, job: Mapping[str, Any]
) -> tuple[list[Room], list[UnresolvedRoom]]:
    """Expand one job's ``runs-on`` and matrix into the rooms it declares."""
    unresolved: list[UnresolvedRoom] = []
    matrix, matrix_unresolved = _matrix_of(source, job)
    unresolved.extend(matrix_unresolved)
    runs_on = _runs_on_of(job)
    if runs_on is None:
        return [], [
            *unresolved,
            UnresolvedRoom(
                source=source,
                why="the job declares no `runs-on`, so its platform is unknown",
            ),
        ]
    rooms: list[Room] = []
    for combination in _combinations(matrix):
        label, failure = _resolve_runs_on(runs_on, combination)
        if failure is not None:
            unresolved.append(UnresolvedRoom(source=source, why=failure))
            continue
        dimensions = {"os": label}
        dimensions.update(
            {k: v for k, v in combination.items() if k != _matrix_os_key(runs_on)}
        )
        rooms.append(Room(dimensions=dimensions, source=source))
    return rooms, unresolved


def _runs_on_of(job: Mapping[str, Any]) -> str | None:
    """The job's ``runs-on`` as one label, or ``None`` when it declares none.

    A list of labels is a self-hosted runner selected by every label at once.
    Joining them keeps the job as a declared ROOM that no run entered, which is
    the honest answer; dropping the job would lose a leg from the census
    entirely, and a leg nobody is told about is the failure this module reports.
    """
    value = job.get("runs-on")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list) and value and all(isinstance(v, str) for v in value):
        return "+".join(str(v).strip() for v in value)
    return None


def _matrix_os_key(runs_on: str) -> str | None:
    """The matrix key ``runs-on`` reads, so it is not repeated as a dimension."""
    match = _MATRIX_EXPRESSION_RE.match(runs_on.strip())
    return _canonical(match.group(1)) if match else None


def _matrix_of(
    source: str, job: Mapping[str, Any]
) -> tuple[dict[str, tuple[str, ...]], list[UnresolvedRoom]]:
    """The job's matrix axes, canonically named, and what widened them unseen."""
    strategy = job.get("strategy")
    if not isinstance(strategy, dict):
        return {}, []
    matrix = strategy.get("matrix")
    if not isinstance(matrix, dict):
        return {}, []
    unresolved: list[UnresolvedRoom] = []
    axes: dict[str, tuple[str, ...]] = {}
    for key, value in matrix.items():
        if key in {"include", "exclude"}:
            unresolved.append(
                UnresolvedRoom(
                    source=source,
                    why=(
                        f"the matrix carries `{key}`, which this report does not "
                        "expand, so the real set of legs is wider or narrower than "
                        "the combinations reported here"
                    ),
                )
            )
            continue
        if not isinstance(value, list) or not value:
            continue
        values: list[str] = []
        for item in value:
            if isinstance(item, float):
                unresolved.append(
                    UnresolvedRoom(
                        source=source,
                        why=(
                            f"`{key}: {item}` is unquoted in YAML, so it reached "
                            f"this report as the number {item} and not as a version"
                        ),
                    )
                )
            values.append(str(item))
        axes[_canonical(str(key))] = tuple(values)
    return axes, unresolved


def _canonical(key: str) -> str:
    """The name this report gives a matrix key, keeping unknown spellings."""
    return "python" if key in _PYTHON_KEYS else key


def _combinations(
    axes: Mapping[str, tuple[str, ...]],
) -> list[dict[str, str]]:
    """Every combination of the matrix axes; one empty combination when there is none."""
    if not axes:
        return [{}]
    keys = list(axes)
    return [
        dict(zip(keys, values, strict=True))
        for values in itertools.product(*(axes[k] for k in keys))
    ]


def _resolve_runs_on(
    runs_on: str, combination: Mapping[str, str]
) -> tuple[str, str | None]:
    """The runner label a ``runs-on`` names, resolving ``${{ matrix.x }}``."""
    value = runs_on.strip()
    match = _MATRIX_EXPRESSION_RE.match(value)
    if match is not None:
        resolved = combination.get(_canonical(match.group(1)))
        if resolved is None:
            return "", (
                f"`runs-on: {value}` names a matrix axis the job does not declare"
            )
        return resolved, None
    expression = _ANY_EXPRESSION_RE.search(value)
    if expression is not None:
        return "", (
            f"`runs-on: {value}` is an expression over "
            f"{expression.group(1).strip()}, which this report cannot resolve"
        )
    return value, None


# ---------------------------------------------------------------------------
# The census
# ---------------------------------------------------------------------------


def take_census(
    project_root: Path,
    *,
    declared: tuple[Room, ...] | None = None,
) -> RoomCensus:
    """Hold the room this run is in against the rooms the project declares.

    ``declared`` is for a caller that already derived the population; passing it
    skips the file derivation rather than deriving it twice.
    """
    current = current_room()
    if declared is None:
        found = derive_declared_rooms(project_root)
        rooms, unresolved = found.rooms, list(found.unresolved)
        supported, floor = found.supported, found.floor
    else:
        rooms, unresolved = declared, []
        supported, floor = (), None
    comparisons: list[RoomComparison] = []
    for room in rooms:
        entered, why, label_unknown = _compare(current, room)
        comparisons.append(RoomComparison(room=room, entered=entered, why=why))
        if label_unknown is not None:
            unresolved.append(UnresolvedRoom(source=room.source, why=label_unknown))
    legs = {r.dimensions.get("python") for r in rooms}
    return RoomCensus(
        current=current,
        comparisons=tuple(comparisons),
        unresolved=tuple(unresolved),
        supported=supported,
        floor=floor,
        supported_without_a_leg=tuple(v for v in supported if v not in legs),
    )


def _compare(current: Room, room: Room) -> tuple[bool, str, str | None]:
    """Whether this run is in ``room``, why not, and any label it could not read.

    Every dimension must be comparable AND equal. The two other outcomes — a
    dimension this run cannot describe, and a runner label naming no platform —
    both resolve to "not entered", because the alternative is a report that
    claims coverage from an inability to check.
    """
    reasons: list[str] = []
    label_unknown: str | None = None
    for key in sorted(room.dimensions):
        want = room.dimensions[key]
        if key == "os":
            family = _platform_of(want)
            if family is None:
                label_unknown = (
                    f"the runner label `{want}` names no platform this report "
                    "knows, so no run can be said to have entered it"
                )
                reasons.append(f"os: {label_unknown}")
                continue
            have = current.dimensions.get("os", "")
            if family != have:
                reasons.append(f"os: the leg is {want} ({family}) and this run is {have}")
            continue
        if key == "python":
            have = current.dimensions.get("python", "")
            if want != have:
                reasons.append(f"python: the leg is {want} and this run is {have}")
            continue
        reasons.append(
            f"{key}: this run cannot describe the dimension `{key}`, which the "
            f"leg declares as {want}"
        )
    return not reasons, "; ".join(reasons), label_unknown


def _platform_of(runner_label: str) -> str | None:
    """The platform a runner label names, or ``None`` when the label is outside
    the vocabulary."""
    family = runner_label.split("-", 1)[0].strip().lower()
    return RUNNER_PLATFORMS.get(family)
