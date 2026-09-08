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

import functools
import importlib.metadata as metadata
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

#: Where a project declares its pipeline. Public because two derivations read
#: one declaration: this module's rooms, and the verifications a gate run did
#: not perform (:mod:`beadloom.application.gate_coverage`).
WORKFLOW_DIR = Path(".github") / "workflows"

#: The dimension this module gives the optional extras an environment installed.
EXTRAS_DIMENSION = "extras"

#: ``name = "beadloom"`` in the packaging metadata. Read with a regular
#: expression for the reason the module docstring states about ``tomllib``.
_PROJECT_NAME_RE = re.compile(r'^\s*name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

#: ``extra == "dev"`` — a marker that says the requirement belongs to one extra
#: and to nothing else. A marker carrying any further clause is NOT this, and
#: the extra it names is reported unresolved rather than decided.
_EXTRA_MARKER_RE = re.compile(r"""^extra\s*==\s*["']([^"']+)["']$""")

#: ``extra`` appearing anywhere in a marker this report cannot read whole.
_EXTRA_MENTION_RE = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")

#: ``some-dist[a,b]>=1.2`` — the distribution a requirement names, and the
#: extras of it the requirement asks for.
_REQUIREMENT_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[(?P<extras>[^\]]*)\])?"
)

#: ``uv sync --extra dev --extra=languages`` in a workflow step.
_UV_EXTRA_RE = re.compile(r"--extra[=\s]+([A-Za-z0-9][A-Za-z0-9._-]*)")

#: ``pip install`` in any of its spellings, including ``uv pip install``. It is
#: NOT ``uv python install``, which carries the word and installs no project.
_PIP_INSTALL_RE = re.compile(r"\bpip\s+install\b")

#: ``pip install -e .`` / ``pip install .`` — the project itself, with no extra.
_PIP_LOCAL_RE = re.compile(r"""(?:-e\s+)?['"]?\.(?:/[\w./-]*)?['"]?(?:\s|$)""")

#: What ``--all-extras`` stands for until the declaration is known.
_ALL_EXTRAS = "*"

#: ``pip install -e '.[all,dev]'`` — the bracket on a local path requirement.
_PIP_EXTRAS_RE = re.compile(r"""[.'"][.\w/-]*\[([^\]]+)\]""")


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
class AbsentExtra:
    """An extra a project declares that this environment does not satisfy.

    ``absent`` names the distributions that decided it, because "you are missing
    ``tui``" is a fact a reader can act on only once it says what ``tui`` is.
    """

    extra: str
    absent: tuple[str, ...]


@dataclass(frozen=True)
class ExtraSet:
    """The optional extras an environment has, and the ones it does not.

    Three states, never two. ``resolved`` is false when the project's
    distribution is not installed under this interpreter or its metadata cannot
    be read: an unresolved answer is not an empty one, and reporting "no extras"
    for "I could not look" is the shape this module exists to refuse.
    """

    distribution: str | None = None
    installed: tuple[str, ...] = ()
    absent: tuple[AbsentExtra, ...] = ()
    unresolved: tuple[UnresolvedRoom, ...] = ()
    resolved: bool = False

    @property
    def label(self) -> str:
        """``dev+languages``, or ``none`` — the value the room dimension carries."""
        return "+".join(self.installed) if self.installed else "none"


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
    extras: ExtraSet = field(default_factory=ExtraSet)


@dataclass(frozen=True)
class RoomCensus:
    """The room a run is in, the rooms declared, and the ones it did not enter."""

    current: Room
    comparisons: tuple[RoomComparison, ...] = ()
    unresolved: tuple[UnresolvedRoom, ...] = ()
    supported: tuple[str, ...] = ()
    floor: str | None = None
    supported_without_a_leg: tuple[str, ...] = field(default=())
    extras: ExtraSet = field(default_factory=ExtraSet)

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
    if EXTRAS_DIMENSION in d:
        parts.append(f"extras {d[EXTRAS_DIMENSION]}")
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
    extras = installed_extras(project_root)
    rooms, workflow_unresolved = _read_workflows(project_root, extras.distribution)
    return DeclaredRooms(
        rooms=rooms,
        unresolved=(
            tuple(packaging_unresolved)
            + tuple(workflow_unresolved)
            + (extras.unresolved if not extras.resolved else ())
        ),
        supported=supported,
        floor=floor,
        extras=extras,
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


# ---------------------------------------------------------------------------
# The extras an environment installed
# ---------------------------------------------------------------------------
#
# BDL-UX #236. Measured on this repository at `6c4d0a9`, in one clean room over
# one code base at one commit: `mypy src/` reports 0 errors under `.[all,dev]`
# and 82 under `.[dev]`, and under the second the whole `tui` suite leaves the
# run — three of its four modules skip and the fourth stops the collection with
# an error. Nothing
# about the code differs between the two runs; the environment does, and no
# report said so. A room's name isolates its FILES — which extras its
# interpreter has is a second question, and until it is answered two correct
# agents following one convention return different verdicts and neither is
# wrong.
#
# Both sides are DERIVED, for the reason the module derives every other
# dimension. What this run has comes from the project distribution's own
# metadata held against the distributions the interpreter can see; what a leg
# installs comes from the install step its workflow declares. Neither is a list
# this module owns, so an extra added to `pyproject.toml` or to a workflow
# changes the answer by the same act.


def project_distribution(project_root: Path) -> str | None:
    """The distribution name a project's packaging declares, or ``None``.

    The name matters because the extras are the ANALYSED project's, not this
    tool's. Under `uv tool install beadloom` those are different distributions,
    and reading Beadloom's own extras while reporting on somebody else's project
    would be a confident wrong answer rather than an unresolved one.
    """
    try:
        text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _PROJECT_NAME_RE.search(text)
    return match.group(1).strip() if match else None


def canonical_distribution(name: str) -> str:
    """The PEP 503 form of a distribution name, so two spellings compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


@functools.cache
def _installed_distributions() -> frozenset[str]:
    """Every distribution name this interpreter can see, canonically spelled.

    Cached because an interpreter does not gain a distribution part-way through
    a process, and the scan costs about 27 ms against a census that several
    verdicts take.
    """
    found: set[str] = set()
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        if name:
            found.add(canonical_distribution(name))
    return frozenset(found)


@dataclass(frozen=True)
class _ExtraDeclaration:
    """What one distribution's metadata says about the extras it declares.

    ``self_referenced`` exists because setuptools writes
    ``mypkg[a,b]; extra == "all"`` rather than flattening it, and a
    self-reference read as a plain requirement resolves to "installed" for every
    extra of every project that has one. ``conditional`` is the extras carrying
    a marker this report cannot read whole, kept apart from the ones it decided.
    """

    requirements: Mapping[str, frozenset[str]]
    self_referenced: Mapping[str, frozenset[str]]
    conditional: frozenset[str]
    base: frozenset[str]
    failure: str | None = None


@functools.cache
def _declared_requirements(distribution: str) -> _ExtraDeclaration:
    """One distribution's extras: their requirements, and what could not be read."""
    try:
        found = metadata.distribution(distribution)
    except (metadata.PackageNotFoundError, OSError, ValueError):
        return _ExtraDeclaration(
            requirements={},
            self_referenced={},
            conditional=frozenset(),
            base=frozenset(),
            failure=(
                f"this interpreter holds no distribution named `{distribution}`, "
                "so the extras it declares cannot be told from the ones it "
                "installed"
            ),
        )
    declared = [
        canonical_distribution(name)
        for name in (found.metadata.get_all("Provides-Extra") or [])
    ]
    requirements: dict[str, set[str]] = {name: set() for name in declared}
    self_referenced: dict[str, set[str]] = {name: set() for name in declared}
    conditional: set[str] = set()
    base: set[str] = set()
    own = canonical_distribution(distribution)
    for raw in found.metadata.get_all("Requires-Dist") or []:
        _record_requirement(
            str(raw), own, requirements, self_referenced, conditional, base
        )
    return _ExtraDeclaration(
        requirements={k: frozenset(v) for k, v in requirements.items()},
        self_referenced={k: frozenset(v) for k, v in self_referenced.items()},
        conditional=frozenset(conditional),
        base=frozenset(base),
    )


def _record_requirement(
    raw: str,
    own: str,
    requirements: dict[str, set[str]],
    self_referenced: dict[str, set[str]],
    conditional: set[str],
    base: set[str],
) -> None:
    """File one ``Requires-Dist`` line under the extra its marker names."""
    body, _, marker = raw.partition(";")
    marker = marker.strip()
    parsed_base = _REQUIREMENT_RE.match(body.strip())
    if not marker:
        # A base requirement: it belongs to no extra and is present in every
        # environment, so a leg's satisfied set must count it as available.
        if parsed_base is not None:
            base.add(canonical_distribution(parsed_base.group("name")))
        return
    named = _EXTRA_MARKER_RE.match(marker)
    if named is None:
        mentioned = _EXTRA_MENTION_RE.search(marker)
        if mentioned is not None:
            conditional.add(canonical_distribution(mentioned.group(1)))
        return
    extra = canonical_distribution(named.group(1))
    if extra not in requirements:
        requirements[extra] = set()
        self_referenced[extra] = set()
    parsed = _REQUIREMENT_RE.match(body.strip())
    if parsed is None:
        conditional.add(extra)
        return
    name = canonical_distribution(parsed.group("name"))
    if name == own:
        self_referenced[extra].update(
            canonical_distribution(part)
            for part in (parsed.group("extras") or "").split(",")
            if part.strip()
        )
        return
    requirements[extra].add(name)


def _closure(extra: str, declaration: _ExtraDeclaration) -> frozenset[str]:
    """Every distribution *extra* asks for, following its self-references."""
    seen: set[str] = set()
    pending = [extra]
    needed: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        needed.update(declaration.requirements.get(current, frozenset()))
        pending.extend(declaration.self_referenced.get(current, frozenset()))
    return frozenset(needed)


def extras_satisfied_by(distribution: str, available: frozenset[str]) -> tuple[str, ...]:
    """The declared extras every requirement of which is in *available*.

    The question is asked this way round on purpose. A leg's install step names
    the extras somebody TYPED, and an environment is what those requirements
    make it: a leg installing ``dev,languages,tui,watch,graphql`` also satisfies
    ``all``, and comparing the typed lists would report two identical
    environments as different rooms.
    """
    declaration = _declared_requirements(distribution)
    if declaration.failure is not None:
        return ()
    present = available | declaration.base
    satisfied: list[str] = []
    for extra in sorted(declaration.requirements):
        if extra in declaration.conditional:
            continue
        needed = _closure(extra, declaration)
        if needed and needed <= present:
            satisfied.append(extra)
    return tuple(satisfied)


def installed_extras(project_root: Path) -> ExtraSet:
    """Which of the project's declared extras this interpreter actually has.

    The answer is about the ANALYSED project's distribution as this interpreter
    holds it, which is why it is unresolved rather than empty when the
    interpreter holds no such distribution.
    """
    distribution = project_distribution(project_root)
    if distribution is None:
        return ExtraSet(
            unresolved=(
                UnresolvedRoom(
                    source="pyproject.toml",
                    why=(
                        "the packaging metadata names no distribution, so the "
                        "optional extras an environment installed cannot be "
                        "named and a verdict cannot state them"
                    ),
                ),
            )
        )
    declaration = _declared_requirements(distribution)
    if declaration.failure is not None:
        return ExtraSet(
            distribution=distribution,
            unresolved=(
                UnresolvedRoom(source="pyproject.toml", why=declaration.failure),
            ),
        )
    available = _installed_distributions() | declaration.base
    installed: list[str] = []
    absent: list[AbsentExtra] = []
    unresolved: list[UnresolvedRoom] = [
        UnresolvedRoom(
            source=f"{distribution}[{extra}]",
            why=(
                "its requirements carry a marker beyond `extra ==`, so whether "
                "this environment installed it cannot be decided from what is "
                "present"
            ),
        )
        for extra in sorted(declaration.conditional)
        if extra in declaration.requirements
    ]
    for extra in sorted(declaration.requirements):
        if extra in declaration.conditional:
            continue
        needed = _closure(extra, declaration)
        if not needed:
            unresolved.append(
                UnresolvedRoom(
                    source=f"{distribution}[{extra}]",
                    why=(
                        "it names no requirement, so no environment can be told "
                        "apart by having installed it"
                    ),
                )
            )
            continue
        missing = tuple(sorted(needed - available))
        if missing:
            absent.append(AbsentExtra(extra=extra, absent=missing))
        else:
            installed.append(extra)
    return ExtraSet(
        distribution=distribution,
        installed=tuple(installed),
        absent=tuple(absent),
        unresolved=tuple(unresolved),
        resolved=True,
    )


def _leg_extras(
    distribution: str | None, source: str, job: Mapping[str, Any]
) -> tuple[str | None, list[UnresolvedRoom]]:
    """The extras a job installs, as the set of extras that environment satisfies.

    Three answers, and the third is the point. A job whose step names them gets
    the label; a job that installs the project through something this report
    does not follow — a local composite action — gets an unresolved entry rather
    than a room with one fewer dimension; and a job that installs the project at
    all gets neither, because a job that runs no verdict declares no
    environment for one.
    """
    steps = job.get("steps")
    if not isinstance(steps, list):
        return None, []
    typed: set[str] | None = None
    composite = False
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses")
        if isinstance(uses, str) and uses.strip().startswith("./"):
            composite = True
        run = step.get("run")
        if not isinstance(run, str):
            continue
        found = _extras_of_command(run)
        if found is not None:
            typed = found if typed is None else typed | found
    if typed is None:
        if composite:
            return None, [
                UnresolvedRoom(
                    source=source,
                    why=(
                        "the job installs the project through a local action, so "
                        "the optional extras its verdict is taken under are "
                        "declared somewhere this report does not follow"
                    ),
                )
            ]
        return None, []
    if distribution is None:
        return None, []
    declaration = _declared_requirements(distribution)
    if declaration.failure is not None:
        return None, []
    if _ALL_EXTRAS in typed:
        typed = (typed - {_ALL_EXTRAS}) | set(declaration.requirements)
    unresolved: list[UnresolvedRoom] = []
    unknown = sorted(typed - set(declaration.requirements))
    if unknown:
        unresolved.append(
            UnresolvedRoom(
                source=source,
                why=(
                    f"the job installs `{', '.join(unknown)}`, which "
                    f"`{distribution}` does not declare as an extra, so the "
                    "environment it creates cannot be named from the packaging"
                ),
            )
        )
    available = frozenset(declaration.base).union(
        *(_closure(extra, declaration) for extra in typed)
    )
    satisfied = extras_satisfied_by(distribution, available)
    return ("+".join(satisfied) if satisfied else "none"), unresolved


def _extras_of_command(run: str) -> set[str] | None:
    """The extras one ``run:`` block installs, or ``None`` if it installs none.

    An empty set and ``None`` are different answers: ``uv sync`` with no
    ``--extra`` DECLARES an environment with no extras, and a step that installs
    nothing declares nothing at all. `uv python install 3.12` is the trap this
    separation exists for — it carries the word and installs no project.
    """
    found: set[str] | None = None
    for line in run.splitlines():
        if "uv sync" in line:
            found = (found or set()) | _uv_sync_extras(line)
            continue
        pip = _pip_project_extras(line)
        if pip is not None:
            found = (found or set()) | pip
    return found


def _uv_sync_extras(line: str) -> set[str]:
    """``--extra dev --extra=languages``, or every declared extra for ``--all-extras``."""
    if "--all-extras" in line:
        return {_ALL_EXTRAS}
    return {canonical_distribution(name) for name in _UV_EXTRA_RE.findall(line)}


def _pip_project_extras(line: str) -> set[str] | None:
    """The extras a ``pip install`` of THIS project names, or ``None``.

    A ``pip install`` of something else — a requirements file, a pinned tool —
    declares nothing about the project's own extras, so it is not an install
    this report reads.
    """
    if not _PIP_INSTALL_RE.search(line):
        return None
    bracketed = _PIP_EXTRAS_RE.search(line)
    if bracketed is not None:
        return {
            canonical_distribution(part)
            for part in bracketed.group(1).split(",")
            if part.strip()
        }
    return set() if _PIP_LOCAL_RE.search(line) else None


def _read_workflows(
    project_root: Path, distribution: str | None = None
) -> tuple[tuple[Room, ...], list[UnresolvedRoom]]:
    """One room per matrix combination, per job, per workflow file."""
    directory = project_root / WORKFLOW_DIR
    files = sorted(p for p in directory.glob("*.y*ml") if p.is_file())
    if not files:
        return (), [
            UnresolvedRoom(
                source=str(WORKFLOW_DIR),
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
        jobs, failure = load_jobs(path)
        if failure is not None:
            unresolved.append(UnresolvedRoom(source=rel, why=failure))
            continue
        for name, job in jobs.items():
            job_rooms, job_unresolved = _rooms_of_job(
                f"{rel}: {name}", job, distribution
            )
            rooms.extend(job_rooms)
            unresolved.extend(job_unresolved)
    return tuple(rooms), unresolved


def load_jobs(path: Path) -> tuple[dict[str, Any], str | None]:
    """The ``jobs`` mapping of a workflow, or the reason there is none.

    Public alongside :data:`WORKFLOW_DIR` because the gate's coverage report
    reads the same declaration for a different question, and one reader means
    one answer to "this workflow could not be parsed" rather than two that can
    word it differently.
    """
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
    source: str, job: Mapping[str, Any], distribution: str | None = None
) -> tuple[list[Room], list[UnresolvedRoom]]:
    """Expand one job's ``runs-on``, matrix and install step into its rooms."""
    unresolved: list[UnresolvedRoom] = []
    matrix, matrix_unresolved = _matrix_of(source, job)
    unresolved.extend(matrix_unresolved)
    extras, extras_unresolved = _leg_extras(distribution, source, job)
    unresolved.extend(extras_unresolved)
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
        if extras is not None:
            dimensions[EXTRAS_DIMENSION] = extras
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
    extras = installed_extras(project_root)
    current = _room_with_extras(current_room(), extras)
    if declared is None:
        found = derive_declared_rooms(project_root)
        rooms, unresolved = found.rooms, list(found.unresolved)
        supported, floor = found.supported, found.floor
    else:
        rooms, unresolved = declared, []
        supported, floor = (), None
        if not extras.resolved:
            unresolved.extend(extras.unresolved)
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
        extras=extras,
    )


def _room_with_extras(room: Room, extras: ExtraSet) -> Room:
    """The room this run is in, carrying the extras dimension when it has one.

    An unresolved answer adds no dimension. The alternative — an ``extras``
    value spelling "unknown" — would compare unequal to every leg and read as a
    difference in the environment, when what happened is that nothing looked.
    """
    if not extras.resolved:
        return room
    return Room(
        dimensions={**room.dimensions, EXTRAS_DIMENSION: extras.label},
        source=room.source,
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
        if key == EXTRAS_DIMENSION:
            difference = _extras_difference(current.dimensions.get(key), want)
            if difference is not None:
                reasons.append(f"{EXTRAS_DIMENSION}: {difference}")
            continue
        reasons.append(
            f"{key}: this run cannot describe the dimension `{key}`, which the "
            f"leg declares as {want}"
        )
    return not reasons, "; ".join(reasons), label_unknown


def _extras_difference(have: str | None, want: str) -> str | None:
    """Why this run's extras are not the leg's, or ``None`` when they are.

    Named in both directions. An extra the leg installs and this run has not is
    the failure BDL-UX #236 records — 82 mypy errors against 0, and 363 tests
    that do not exist — and an extra this run has and the leg does not is the
    same failure read the other way, which is how a green taken here can be red
    there.
    """
    if have is None:
        return (
            "this run cannot describe the extras it installed, which the leg "
            f"declares as {want}"
        )
    if have == want:
        return None
    here = {name for name in have.split("+") if name and name != "none"}
    there = {name for name in want.split("+") if name and name != "none"}
    clauses = []
    if there - here:
        clauses.append(f"the leg installs {', '.join(sorted(there - here))} and this run has not")
    if here - there:
        clauses.append(f"this run has {', '.join(sorted(here - there))} and the leg does not")
    return "; ".join(clauses) if clauses else f"the leg is {want} and this run is {have}"


def _platform_of(runner_label: str) -> str | None:
    """The platform a runner label names, or ``None`` when the label is outside
    the vocabulary."""
    family = runner_label.split("-", 1)[0].strip().lower()
    return RUNNER_PLATFORMS.get(family)
