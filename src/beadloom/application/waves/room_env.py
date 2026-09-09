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
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from beadloom.application.rooms import ALL_EXTRAS, declared_extra_names, leg_installs

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

    @property
    def label(self) -> str:
        """``dev+tui``, or ``none`` — the extras this environment was given."""
        return "+".join(self.extras) if self.extras else "none"


def extras_a_room_installs(
    project_root: Path, asked: tuple[str, ...] | None = None
) -> ExtrasChoice:
    """The extras a room installs: what the caller named, or what the legs do.

    A caller naming them wins, because reproducing one particular leg is the
    reason to override a union and the union cannot express it.
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
        named = (named - {ALL_EXTRAS}) | set(declared_extra_names(project_root))
    return ExtrasChoice(
        extras=tuple(sorted(named)),
        source=SOURCE_LEGS,
        why=(
            f"the union of every extra the {len(legs)} installing leg(s) of this "
            "project name, because a missing extra removes tests from a run "
            "without failing it and a surplus one removes nothing"
        ),
    )


def room_python(room: Path) -> Path | None:
    """The interpreter inside *room*, or ``None`` when the room holds none."""
    venv = Path(room) / ENVIRONMENT_DIR
    for relative in (Path("bin") / "python", Path("Scripts") / "python.exe"):
        candidate = venv / relative
        if candidate.exists():
            return candidate
    return None


def site_packages(room: Path) -> tuple[str, ...]:
    """Where *room*'s interpreter keeps its installed metadata.

    Returned as a search path rather than read here, because the extras a room
    has are derived by the one function that derives them anywhere
    (:func:`~beadloom.application.rooms.installed_extras`), and this module only
    tells it where to look.
    """
    venv = Path(room) / ENVIRONMENT_DIR
    found = [p for p in sorted(venv.glob("lib/python*/site-packages")) if p.is_dir()]
    windows = venv / "Lib" / "site-packages"
    if windows.is_dir():
        found.append(windows)
    return tuple(str(p) for p in found)


def build_environment(
    *, room: Path, choice: ExtrasChoice, otherwise: str
) -> RoomEnvironment:
    """Build *room*'s own interpreter and install the project into it.

    *otherwise* is the interpreter the room's verdict would be taken under if
    this fails — the project's own environment. It is both the version the new
    interpreter is created from, so the room measures on the interpreter it
    replaces rather than on whichever one is first on the path, and the one
    named in the sentence a room without an environment reports.
    """
    if choice.source == SOURCE_UNDERIVED:
        return RoomEnvironment(
            detail=(
                f"no environment was built: {choice.why}. This room's verdict is "
                f"therefore taken under {otherwise}, which is the project's own "
                "environment and not this room's — name it when reporting"
            ),
            source=choice.source,
        )
    started = time.monotonic()
    installer = INSTALLER_UV if shutil.which("uv") else INSTALLER_STDLIB
    failure = _create(room, installer, otherwise) or _install(room, installer, choice)
    seconds = round(time.monotonic() - started, 3)
    if failure is not None:
        # A half-built environment is worse than none: it is an interpreter that
        # exists, answers imports, and holds an unknown subset of what a verdict
        # here needs. The same rule the room itself follows.
        shutil.rmtree(Path(room) / ENVIRONMENT_DIR, ignore_errors=True)
        return RoomEnvironment(
            detail=(
                f"no environment was built: {failure}. This room's verdict is "
                f"therefore taken under {otherwise}, which is the project's own "
                "environment and not this room's — name it when reporting"
            ),
            extras=choice.extras,
            source=choice.source,
            installer=installer,
            seconds=seconds,
        )
    return RoomEnvironment(
        built=True,
        detail=(
            f"built by {installer} in {seconds}s with extras {choice.label} — "
            f"{choice.why}"
        ),
        python=room_python(room),
        extras=choice.extras,
        source=choice.source,
        installer=installer,
        seconds=seconds,
    )


def _create(room: Path, installer: str, otherwise: str) -> str | None:
    """Create the room's virtual environment, or say why there is none."""
    venv = Path(room) / ENVIRONMENT_DIR
    if installer == INSTALLER_UV:
        command = ["uv", "venv", "--python", otherwise, str(venv)]
    else:
        command = [otherwise, "-m", "venv", str(venv)]
    return _run(command, room)


def _install(room: Path, installer: str, choice: ExtrasChoice) -> str | None:
    """Install the room's own sources into it, or say why they are not there."""
    python = room_python(room)
    if python is None:
        return (
            f"{installer} reported no failure and the room holds no interpreter "
            f"under {ENVIRONMENT_DIR}"
        )
    spec = f".[{','.join(choice.extras)}]" if choice.extras else "."
    if installer == INSTALLER_UV:
        command = ["uv", "pip", "install", "--python", str(python), "-e", spec]
    else:
        command = [str(python), "-m", "pip", "install", "-q", "-e", spec]
    return _run(command, room)


def _run(command: list[str], room: Path) -> str | None:
    """Run one install step in the room, and report its failure in its own words."""
    try:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=room,
            capture_output=True,
            encoding=_TEXT_CODEC,
            errors="surrogateescape",
            check=False,
        )
    except OSError as exc:
        return f"`{' '.join(command[:2])}` could not be run ({exc})"
    if result.returncode == 0:
        return None
    said = (result.stderr or result.stdout or "").strip().splitlines()
    tail = " / ".join(line.strip() for line in said[-_FAILURE_LINES:] if line.strip())
    return f"`{' '.join(command[:3])}` exited {result.returncode}: {tail}"
