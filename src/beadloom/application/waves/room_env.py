"""The interpreter a clean room's verdict is taken under, and what it holds.

**The measured defect.** BDL-UX #256 was filed as an import-path failure and
half of it was already closed when it was filed: ``beadloom-0mdo.37``'s
invocation points ``PYTHONPATH`` at the room's own ``src``, and
``beadloom-0mdo.38`` verified in its own room that ``import beadloom`` printed a
path under the room. What survives is the environment. A room isolated the FILES
a verdict was taken over and nothing isolated the interpreter they ran under, so
the verdict was decided by whatever the machine happened to hold: measured over
one code base at one commit, ``mypy src/`` reports 0 errors under ``.[all,dev]``
and 82 under ``.[dev]``, and under the second the whole ``tui`` suite leaves the
run — three of its four modules skip and the fourth stops the collection.

**Which extras, and why the union.** The extras are the UNION of every extra any
leg of this project's own workflows installs, read by
:func:`~beadloom.application.rooms.leg_installs`. Not a constant, which would
answer for every adopter by fiat; and not the set most legs declare, which is
the wrong answer on this repository — four legs install ``dev, languages`` to
build a site or run a release gate, and the two that run the suite install five
extras. The union is taken because the two errors are not symmetric: a missing
extra removes tests from a run WITHOUT failing it, while a surplus one removes
nothing. Measured here, the surplus is 9 MB and no time — 169 MB and 1.07 s for
the union against 160 MB and 1.78 s for ``.[all,dev]``, both on a warm ``uv``
cache.

**What the derivation is NOT.** It is not
:func:`~beadloom.application.rooms.extras_satisfied_by`. That one answers which
extras an environment satisfies, needs the analysed distribution installed under
the running interpreter, and exists so two environments can be COMPARED. This
one answers what to type into an install command. They are two questions, and
the one parser both read a workflow through is
:func:`~beadloom.application.rooms.typed_extras_of_job`.

**Cost, and why it is paid per room rather than cached.** On a warm ``uv``
cache, macOS/APFS: ``uv venv`` 0.08 s and ``uv pip install -e`` 1.1 s for a room
of 184 MB apparent. Against a seven-minute suite that is under half a percent,
and every rebuild pays it again on purpose — a venv kept outside the room and
reused is a directory two rooms share, which is the property BDL-UX #235 was
filed about. The reuse that matters is ``uv``'s own package cache, which is
content-addressed and so cannot carry one room's source into another.

**Without ``uv``.** The stdlib path is used instead, and it is not the same
measurement: ``python -m venv`` plus ``pip install -e`` measured 1.84 s and 39.6
s against ``uv``'s 0.08 s and 1.1 s over the same tree. The room records which
installer built it, because a 40-second step and a 1-second step being reported
as one fact is how a cost that matters becomes invisible.

**From the lock, where the project keeps one** (BDL-083 S2b, BDL-UX #311 and #333).
``uv pip install -e`` resolves afresh and ignores ``uv.lock``, so a room's
environment held what the index offered that day rather than what CI installs:
gherkin-official 42 against the lock's 29 failed one self-check test in every room
of BDL-083 S1 and S2 and in no CI leg, and mypy 2.4.0 against the lock's 2.3.1
reported an error the tree did not. A project that keeps a ``uv.lock`` beside its
packaging is therefore installed with ``uv sync --frozen`` in the room's copy of that
project's directory, which is what this project's CI legs and the monorepo fixture's
pipeline run. A project without a lock, or a machine without ``uv``, is resolved
afresh as before, and the environment's ``resolution`` says so in words, naming the
packaging it resolved — the room cannot be held to a lock that is not there, and it
can refuse to let that pass unsaid.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.application.rooms import ALL_EXTRAS, declared_extra_names, leg_installs

if TYPE_CHECKING:
    from beadloom.application.waves.room_distribution import RoomDistribution

#: The directory a room keeps its interpreter in, beside the sources it holds.
ENVIRONMENT_DIR = ".venv"

#: Where the extras a room installs came from. Names rather than sentences, so
#: the record, the CLI and the tests all report the same fact.
SOURCE_LEGS = "legs"
SOURCE_CALLER = "caller"
SOURCE_UNDERIVED = "underived"

#: Which tool built the environment. Recorded because the two differ by a factor
#: of about thirty in time and by their resolver, and a verdict taken under one
#: is not evidence about the other.
INSTALLER_UV = "uv"
INSTALLER_STDLIB = "venv+pip"

_TEXT_CODEC = "utf-8"

#: The directory a room's measured project sits in when it is the room's root.
_ROOT = "."

#: Variables a parent environment may set that would point ``uv sync`` at an environment
#: outside the room — the tree's own, in the worst case.
_FOREIGN_ENVIRONMENT = ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")

#: How much of a failed install's own words the record keeps. Enough to name the
#: cause, short enough that a room's record stays a record.
_FAILURE_LINES = 12


@dataclass(frozen=True)
class ExtrasChoice:
    """The extras a room will install, and where the choice came from.

    ``source`` is :data:`SOURCE_UNDERIVED` when no leg of the project installs
    it and the caller named nothing. That is not the same as an empty list of
    extras: a project whose legs install none declares an environment, and a
    project this reader could not ask declares nothing at all.
    """

    extras: tuple[str, ...] = ()
    source: str = SOURCE_UNDERIVED
    why: str = ""

    @property
    def label(self) -> str:
        """``dev+tui``, or ``none`` — the value a room's record carries."""
        return "+".join(self.extras) if self.extras else "none"


@dataclass(frozen=True)
class RoomEnvironment:
    """The interpreter a room holds, or the reason it holds none.

    ``built`` false with a ``detail`` is the whole answer, never a warning
    attached to a usable one: a caller that measures under an interpreter it
    believes is the room's, and is not, is the defect this class exists to make
    visible.
    """

    built: bool = False
    detail: str = ""
    python: Path | None = None
    extras: tuple[str, ...] = ()
    source: str = SOURCE_UNDERIVED
    installer: str | None = None
    seconds: float = 0.0
    #: The measured project's directory, POSIX and relative to the room.
    distribution: str = _ROOT
    #: The lock the environment was installed from, or ``None`` when it was resolved
    #: afresh (BDL-UX #311): a room whose versions are not the lock's says so here.
    lock: str | None = None
    #: How the environment's versions were chosen, in words a report can quote.
    resolution: str = ""

    @property
    def label(self) -> str:
        """``dev+tui``, or ``none`` — the extras this environment was given."""
        return "+".join(self.extras) if self.extras else "none"


def extras_a_room_installs(
    project_root: Path,
    asked: tuple[str, ...] | None = None,
    *,
    distribution_root: Path | None = None,
) -> ExtrasChoice:
    """The extras a room installs: what the caller named, or what the legs do.

    A caller naming them wins, because reproducing one particular leg is the
    reason to override a union and the union cannot express it. A leg asking for
    every extra is expanded from the packaging of *distribution_root*, the measured
    project's directory, which is the project root unless the room measures a
    project below it.
    """
    if asked is not None:
        return ExtrasChoice(
            extras=tuple(sorted({part.strip() for part in asked if part.strip()})),
            source=SOURCE_CALLER,
            why="named by the caller",
        )
    legs = leg_installs(project_root)
    if not legs:
        return ExtrasChoice(
            why=(
                "no leg of this project's workflows installs it, so the extras a "
                "verdict here should be taken under are not declared anywhere "
                "this reader follows"
            )
        )
    named = {extra for leg in legs for extra in leg.extras}
    if ALL_EXTRAS in named:
        named = (named - {ALL_EXTRAS}) | set(
            declared_extra_names(distribution_root or project_root)
        )
    return ExtrasChoice(
        extras=tuple(sorted(named)),
        source=SOURCE_LEGS,
        why=(
            f"the union of every extra the {len(legs)} installing leg(s) of this "
            "project name, because a missing extra removes tests from a run "
            "without failing it and a surplus one removes nothing"
        ),
    )


def room_python(room: Path, directory: str = _ROOT) -> Path | None:
    """The interpreter of the project at *directory* in *room*, or ``None``."""
    return _python_in(_environment_dir(room, directory))


def site_packages(room: Path, directory: str = _ROOT) -> tuple[str, ...]:
    """Where *room*'s interpreter keeps its installed metadata.

    Returned as a search path rather than read here, because the extras a room
    has are derived by the one function that derives them anywhere
    (:func:`~beadloom.application.rooms.installed_extras`), and this module only
    tells it where to look.
    """
    venv = _environment_dir(room, directory)
    found = [p for p in sorted(venv.glob("lib/python*/site-packages")) if p.is_dir()]
    windows = venv / "Lib" / "site-packages"
    if windows.is_dir():
        found.append(windows)
    return tuple(str(p) for p in found)


def build_environment(
    *,
    room: Path,
    choice: ExtrasChoice,
    otherwise: str,
    distribution: RoomDistribution | None = None,
    interpreter: str | None = None,
) -> RoomEnvironment:
    """Build the measured project's own interpreter in *room* and install it there.

    *otherwise* is the interpreter the room's verdict would be taken under if
    this fails — the project's own environment. It is named in the sentence a
    room without an environment reports, and it is the version a lock-less
    environment is created from, so the room measures on the interpreter it
    replaces rather than on whichever one is first on the path.

    *distribution* is the project measured, at the room's root when absent.
    *interpreter* is the environment that project keeps in the tree: a locked
    sync is created from it when there is one, and otherwise ``uv`` chooses by the
    project's ``requires-python``, because a monorepo's root keeps no environment
    and the process's own interpreter may not satisfy the project at all.
    """
    directory = distribution.directory if distribution is not None else _ROOT
    if choice.source == SOURCE_UNDERIVED:
        return RoomEnvironment(
            detail=_borrowed(choice.why, otherwise),
            source=choice.source,
            distribution=directory,
        )
    started = time.monotonic()
    plan = _plan(room, distribution)
    if plan.locked:
        failure = _run(plan.sync(choice, interpreter), plan.target, env=plan.env)
    else:
        failure = _create(plan, otherwise) or _install(plan, choice)
    seconds = round(time.monotonic() - started, 3)
    if failure is not None:
        # A half-built environment is worse than none: it is an interpreter that
        # exists, answers imports, and holds an unknown subset of what a verdict
        # here needs. The same rule the room itself follows.
        shutil.rmtree(plan.venv, ignore_errors=True)
        return RoomEnvironment(
            detail=_borrowed(failure, otherwise),
            extras=choice.extras,
            source=choice.source,
            installer=plan.installer,
            seconds=seconds,
            distribution=directory,
            lock=plan.lock,
            resolution=plan.resolution,
        )
    return RoomEnvironment(
        built=True,
        detail=(
            f"built by {plan.installer} in {seconds}s with extras {choice.label}, "
            f"{plan.resolution} — {choice.why}"
        ),
        python=room_python(room, directory),
        extras=choice.extras,
        source=choice.source,
        installer=plan.installer,
        seconds=seconds,
        distribution=directory,
        lock=plan.lock,
        resolution=plan.resolution,
    )


@dataclass(frozen=True)
class _InstallPlan:
    """Where the measured project's environment goes, and how its versions are chosen."""

    target: Path
    venv: Path
    installer: str
    lock: str | None
    resolution: str
    env: dict[str, str]

    @property
    def locked(self) -> bool:
        return self.lock is not None

    def sync(self, choice: ExtrasChoice, interpreter: str | None) -> list[str]:
        """``uv sync --frozen`` with the chosen extras, from the tree's interpreter if any."""
        command = ["uv", "sync", "--frozen"]
        for extra in choice.extras:
            command += ["--extra", extra]
        if interpreter is not None:
            command += ["--python", interpreter]
        return command


def _plan(room: Path, distribution: RoomDistribution | None) -> _InstallPlan:
    """Decide where the environment goes and whether its versions come from a lock."""
    directory = distribution.directory if distribution is not None else _ROOT
    target = Path(room) if directory == _ROOT else Path(room) / directory
    venv = target / ENVIRONMENT_DIR
    env = {k: v for k, v in os.environ.items() if k not in _FOREIGN_ENVIRONMENT}
    env["UV_PROJECT_ENVIRONMENT"] = str(venv)
    has_uv = shutil.which("uv") is not None
    installer = INSTALLER_UV if has_uv else INSTALLER_STDLIB
    packaging = distribution.packaging if distribution is not None else "pyproject.toml"
    lock = distribution.lock if distribution is not None else None
    if lock is not None and has_uv:
        return _InstallPlan(
            target=target,
            venv=venv,
            installer=installer,
            lock=lock,
            resolution=f"installed from {lock} with `uv sync --frozen`",
            env=env,
        )
    why = (
        f"uv is not on PATH, so {lock} is not read"
        if lock is not None
        else f"no uv.lock beside {packaging}"
    )
    return _InstallPlan(
        target=target,
        venv=venv,
        installer=installer,
        lock=None,
        resolution=(
            f"resolved afresh outside any lock ({why}), so its versions are the index's "
            "today and not necessarily what CI installs"
        ),
        env=env,
    )


def _borrowed(cause: str, otherwise: str) -> str:
    """The sentence a room without an environment of its own reports."""
    return (
        f"no environment was built: {cause}. This room's verdict is therefore taken "
        f"under {otherwise}, which is the project's own environment and not this "
        "room's — name it when reporting"
    )


def _environment_dir(room: Path, directory: str) -> Path:
    """The environment directory of the project at *directory* in *room*."""
    base = Path(room) if directory == _ROOT else Path(room) / directory
    return base / ENVIRONMENT_DIR


def _create(plan: _InstallPlan, otherwise: str) -> str | None:
    """Create the project's virtual environment in the room, or say why there is none."""
    if plan.installer == INSTALLER_UV:
        command = ["uv", "venv", "--python", otherwise, str(plan.venv)]
    else:
        command = [otherwise, "-m", "venv", str(plan.venv)]
    return _run(command, plan.target)


def _install(plan: _InstallPlan, choice: ExtrasChoice) -> str | None:
    """Install the room's own sources into it, or say why they are not there."""
    python = _python_in(plan.venv)
    if python is None:
        return (
            f"{plan.installer} reported no failure and the room holds no interpreter "
            f"under {plan.venv}"
        )
    spec = f".[{','.join(choice.extras)}]" if choice.extras else "."
    if plan.installer == INSTALLER_UV:
        command = ["uv", "pip", "install", "--python", str(python), "-e", spec]
    else:
        command = [str(python), "-m", "pip", "install", "-q", "-e", spec]
    return _run(command, plan.target)


def _python_in(venv: Path) -> Path | None:
    """The interpreter of the environment at *venv*, or ``None``."""
    for relative in (Path("bin") / "python", Path("Scripts") / "python.exe"):
        candidate = venv / relative
        if candidate.exists():
            return candidate
    return None


def _run(command: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> str | None:
    """Run one install step in the room, and report its failure in its own words."""
    try:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            capture_output=True,
            encoding=_TEXT_CODEC,
            errors="surrogateescape",
            check=False,
            env=env,
        )
    except OSError as exc:
        return f"`{' '.join(command[:2])}` could not be run ({exc})"
    if result.returncode == 0:
        return None
    said = (result.stderr or result.stdout or "").strip().splitlines()
    tail = " / ".join(line.strip() for line in said[-_FAILURE_LINES:] if line.strip())
    return f"`{' '.join(command[:3])}` exited {result.returncode}: {tail}"
