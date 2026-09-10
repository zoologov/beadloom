"""Build the clean room a bead owns, and refuse a directory this run did not create.

**Two measurements, one missing guarantee.** The convention this replaces named
the room after the CONCEPT and said nothing about entering one twice, and both
halves cost a verdict:

* BDL-UX #235. In BDL-068 S4 wave 1, ``beadloom-0mdo.27`` and ``beadloom-0mdo.31``
  each built a room at the same session-scratchpad path. Reconstructed from
  mtimes: ``.31``'s archive at 22:53, ``.27``'s files copied in at 23:16,
  ``.31``'s at 23:26. ``.31``'s run there reported 8 failures and five of them
  were ``.27``'s — acceptance steps and annotation checks over a graph node
  ``HEAD`` does not carry — none a defect in either bead. Rebuilt under a
  bead-unique name it reported 1, a stated property of the room.
* BDL-UX #243. ``beadloom-0mdo.41`` measured the second entry: copying changed
  files into an already reindexed room produces ``sync-check`` exit 2 with
  ``stale: 2`` against a change that is clean at ``HEAD``, because the copy
  postdates the room's own doc-freshness baseline. The failure is manufactured by
  the room's lifecycle and is shaped exactly like a real one.

**So the room is DERIVED and the build is exclusive.** The path comes from
:func:`~beadloom.application.waves.media.room_for`, so no two beads can be handed
one directory, and the room directory is created with an exclusive ``mkdir``: a
directory that already exists is refused, never entered. That is what answers
#243 without a rule anybody has to remember — a convention that is only correct
when performed exactly once, and does not say so, will be performed twice.
``rebuild=True`` is the second build, and it REPLACES the room rather than
refreshing it, so every file inside a room still postdates nothing.

**What it copies is what the caller names, and nothing else.** There is
deliberately no "copy everything that differs from ``HEAD``" mode: on a shared
working tree that set contains the neighbour's work, which is #235 reached by a
second route.

**A rebuild reproduces the REQUEST, over the working tree's files.** Naming every
file is correct and it is retyped on every rebuild: measured by
``beadloom-0mdo.37`` while using this command on the bead that built it, 16
``--carry`` flags entered twice, once after each fix the room itself caught. The
room is right and the retyping costs seconds; what makes it worth removing is
that the alternative an agent reaches for under that friction is to copy files
into the live room, which is #243 again — a fix that makes the correct path more
tedious than the wrong one has a countdown on it. And ``beadloom-0mdo.74`` made
a rebuild cost more than it did when that was measured, because a room now builds
its own interpreter. So the record carries the request that built it and
``rebuild=True`` reuses it. **What is reused is the LIST and never the content**:
the files are copied from the working tree at build time, which is the whole of
#243, and a ``carry`` or ``extras`` named beside ``rebuild`` REPLACES its
remembered counterpart rather than adding to it, so the command never grows a set
nobody named.

**One rule decides what a rebuild may remember: it must never silently produce a
room whose verdict is greener or less isolated than the one it replaces.** That
is why the extras a caller PINNED are reused — forgetting ``--extras dev`` would
silently widen the room to the legs' union, and on this code base at one commit
that is 0 mypy errors where the pinned leg reports 82 (BDL-UX #236). It is also
why ``--no-environment`` is recorded and NOT reused: remembering a decline would
hand back a room whose verdict is the machine's, which is BDL-UX #256, and leave
no way to ask for an environment short of deleting the room. Forgetting it costs
a measured 3.6 s and 160 MB and takes the safe direction. A set the LEGS derived
is re-derived rather than remembered, for the same reason the mode above does not
exist: pinning it would carry a set nobody named into every later room.

**What a room cannot tell you.** It carries no ``.git``, so a doc-freshness check
inside it has no baseline; and it isolates the swept SOURCE, not the environment.
A room's verdict is a claim about the files in it and never about the combined
tree, which is the wave gate owner's measurement.

**What the record now states, and why it is not the same as controlling it.**
BDL-UX #236: measured on this repository at ``6c4d0a9``, over one code base at
one commit, ``mypy src/`` reports 0 errors under ``.[all,dev]`` and 82 under
``.[dev]``, and under the second the whole ``tui`` suite leaves the run — three of
its four modules skip and the fourth stops the collection with an error. So the
marker records the extras the invocation's interpreter has, derived by
:func:`~beadloom.application.rooms.installed_extras` — the same derivation
``beadloom rooms`` reports, because two answers to one question are two things
that can disagree. The room does NOT build an environment of its own: which
extras a verdict SHOULD be taken under is a decision, and BDL-UX #256 owns it.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from beadloom.application.rooms import ExtraSet, installed_extras
from beadloom.application.waves.media import room_for
from beadloom.application.waves.room_env import (
    RoomEnvironment,
    build_environment,
    extras_a_room_installs,
    room_python,
    site_packages,
)

#: The file that makes a room able to say whose it is. A directory without one
#: is a directory, whatever it is called — which is the whole of #235 in a
#: sentence, and the only thing a rebuild is allowed to delete on.
ROOM_MARKER = ".beadloom-room.json"

#: The half of a room's record that says what it was ASKED for, kept apart from
#: what the build did. ``carried`` is an outcome and ``request.carry`` is a
#: request; they agree today, and only the second is a thing a rebuild may
#: reproduce without inventing an intention nobody stated.
REQUEST_KEY = "request"

#: Refusal reasons. Names rather than sentences, so the CLI, ``--json`` and the
#: tests all report the same fact and a caller can branch on it.
REFUSAL_ALREADY_EXISTS = "already_exists"
REFUSAL_NOT_A_ROOM = "not_a_room"
REFUSAL_INSIDE_THE_PROJECT = "inside_the_project"
REFUSAL_NO_COMMIT = "no_commit"
REFUSAL_FILE_MISSING = "file_missing"
REFUSAL_NOT_A_FILE = "not_a_file"
REFUSAL_FILE_OUTSIDE = "file_outside_the_project"

#: Where a project keeps the environment its suite runs under, POSIX first.
_PROJECT_INTERPRETERS = (
    Path(".venv") / "bin" / "python",
    Path(".venv") / "Scripts" / "python.exe",
)

_TEXT_CODEC = "utf-8"


@dataclass(frozen=True)
class RoomBuild:
    """What one build attempt did, and why it did not do more.

    ``built`` and ``refusal`` are the two halves of one answer: a refusal is
    never a room with a warning attached, because a caller that measures in a
    room it did not create is the defect this class exists to prevent.
    """

    bead_id: str
    path: Path
    built: bool
    detail: str
    refusal: str | None = None
    commit: str | None = None
    carried: tuple[str, ...] = ()
    invocation: tuple[str, ...] = ()
    #: The optional extras the invocation's interpreter has, or ``None`` when
    #: the derivation could not answer. ``None`` is not "no extras": a report
    #: printing the second for the first is the defect this field closes.
    extras: str | None = None
    #: The interpreter the room holds, or the reason it holds none. Never
    #: ``None`` on a built room: a room that could not build one says so, and a
    #: reader who is not told falls back to the project's without knowing.
    environment: RoomEnvironment | None = None
    #: The parts of the request this build took from the record of the room it
    #: replaced, ``carry`` and ``extras``. Reported rather than inferred: a
    #: caller who did not type a list has to be able to see that one was used,
    #: or the room's contents become a fact with no stated source.
    reused: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoomRequest:
    """What a room was asked for, in the caller's own terms.

    ``extras`` is ``None`` when the caller named none and left the derivation to
    the project's legs. That is not an empty tuple, which asks for an environment
    with no extras at all — the same distinction ``--extras ""`` carries at the
    command line, and collapsing it would make a rebuild pin a set nobody named.
    """

    carry: tuple[str, ...] = ()
    extras: tuple[str, ...] | None = None
    environment: bool = True


#: The request parts a rebuild may take from the room it replaces. Named here
#: because the report prints them and the tests assert on them, and three
#: spellings of one vocabulary is how a report and a check stop agreeing.
REUSABLE_CARRY = "carry"
REUSABLE_EXTRAS = "extras"


def room_path(parent: Path, bead_id: str) -> Path:
    """The directory *bead_id* owns under *parent* — derived, never chosen."""
    return Path(parent) / room_for(bead_id)


def room_owner(path: Path) -> str | None:
    """The bead a room records as its owner, or ``None`` if this is not a room.

    ``None`` covers every way of not being a room — no marker, unreadable bytes,
    JSON that is not an object, an object naming no bead. They are one answer
    because they license one action: leave the directory alone.
    """
    record = _record(path)
    if record is None:
        return None
    owner = record.get("bead")
    return owner if isinstance(owner, str) and owner else None


def room_request(path: Path) -> RoomRequest | None:
    """The request the room at *path* recorded, or ``None`` if it recorded none.

    A room built before the request was recorded still names the files it
    carried, and that list IS the carry request: the build copies exactly what
    the caller named and nothing else. Reading it keeps such a room rebuildable,
    where the alternative is a rebuild that silently carries nothing — the one
    failure this whole reuse exists to prevent, arriving by another door.
    """
    record = _record(path)
    if record is None:
        return None
    asked = record.get(REQUEST_KEY)
    if not isinstance(asked, dict):
        return RoomRequest(carry=_names(record.get("carried")))
    extras = asked.get(REUSABLE_EXTRAS)
    return RoomRequest(
        carry=_names(asked.get(REUSABLE_CARRY)),
        extras=None if extras is None else _names(extras),
        environment=asked.get("environment", True) is not False,
    )


def _record(path: Path) -> dict[str, Any] | None:
    """A room's own marker as data, or ``None`` for every way of not being one."""
    marker = Path(path) / ROOM_MARKER
    try:
        record = json.loads(marker.read_text(encoding=_TEXT_CODEC))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) else None


def _names(value: object) -> tuple[str, ...]:
    """The non-empty strings in a recorded list, and nothing else.

    A record is a file on disk that another tool may have written, so a value
    that is not a list of names yields no names rather than an exception: the
    room is still deletable and rebuildable, with a request the caller states.
    """
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def room_invocation(path: Path, *, project_root: Path | None = None) -> tuple[str, ...]:
    """How to run a suite IN the room, and how to check that you did.

    The measured trap this closes (found building the room for ``beadloom-67t1``):
    with an editable install, running the suite from inside the room under the
    project's environment imports the TREE's source. The first attempt did
    exactly that and it showed up in a warning path rather than in a failure — a
    green that is a measurement of the tree wearing a room's name. ``PYTHONPATH``
    pointing at the room's own ``src`` fixes it, and the import line is the check:
    it must print a path under the room.

    The room's OWN interpreter is named when it has one (BDL-UX #256), and the
    project's otherwise. ``PYTHONPATH`` is kept in both spellings: under the
    room's own interpreter it is redundant, and it is the line whose output is
    the check, so removing it would remove the evidence rather than the need.
    """
    room = Path(path)
    sources = room / "src"
    interpreter = _interpreter(project_root, room=room)
    return (
        f"PYTHONPATH={sources} {interpreter} -c "
        f'"import beadloom; print(beadloom.__file__)"  # must print a path under {room}',
        f"PYTHONPATH={sources} {interpreter} -m pytest {room / 'tests'}",
    )


def _interpreter(project_root: Path | None, *, room: Path | None = None) -> str:
    """The interpreter a verdict in the room is taken under.

    The room's own comes first when it has one: isolating the FILES and leaving
    the interpreter to the machine is BDL-UX #256, where a correctly-named room
    returned a verdict decided by whatever happened to be installed. The rest of
    this docstring is about the fallback, which is what a room without an
    environment of its own still names.

    Found by using this command on its own bead. ``sys.executable`` is the
    interpreter of the CLI PROCESS, and Beadloom installed as a ``uv`` tool runs
    under ``~/.local/share/uv/tools/beadloom/bin/python3`` — an interpreter with
    neither ``pytest`` nor the project's development dependencies, so the
    invocation handed back could not be run at all. What the suite runs under is
    the environment the project keeps beside itself, so that is what is named
    when it exists, and ``sys.executable`` is the fallback for a project that
    keeps none.
    """
    if room is not None:
        own = room_python(room)
        if own is not None:
            return str(own)
    if project_root is not None:
        root = Path(project_root)
        for relative in _PROJECT_INTERPRETERS:
            candidate = root / relative
            if candidate.exists():
                return str(candidate)
    return sys.executable


def build_room(
    *,
    bead_id: str,
    project_root: Path,
    parent: Path,
    carry: tuple[str, ...] = (),
    rebuild: bool = False,
    extras: tuple[str, ...] | None = None,
    environment: bool = True,
) -> RoomBuild:
    """Build *bead_id*'s room under *parent* from ``HEAD`` plus the named files.

    Every refusal is returned rather than raised: a refusal is an answer about
    the room, and the caller needs the derived path in order to report it.

    *extras* names the optional extras the room's own interpreter installs; the
    default is derived from the project's own legs. *environment* false builds
    the files and no interpreter, which is a room whose verdict is taken under
    the project's environment — a caller who wants that must ask for it, because
    getting it by omission is BDL-UX #256.
    """
    root = Path(project_root).resolve()
    path = room_path(parent, bead_id).resolve()

    refusal = _refuse_the_room(bead_id, root, path, rebuild=rebuild)
    if refusal is not None:
        return refusal

    # The room's own record is read before anything deletes it, and the carried
    # paths are checked over the request that results — a remembered file the
    # tree no longer holds refuses the rebuild by the same route an explicit one
    # would, and refuses it while the room, and its record, are still there.
    asked = RoomRequest(carry=tuple(carry), extras=extras, environment=environment)
    request, reused = _remembering(path, asked, rebuild=rebuild)
    refusal = _refuse_the_request(bead_id, root, path, request.carry)
    if refusal is not None:
        return refusal

    commit = _head_commit(root)
    if commit is None:
        return _refused(
            bead_id,
            path,
            REFUSAL_NO_COMMIT,
            f"git has no HEAD to archive in {root} — a room is built from a commit",
        )

    if rebuild and path.exists():
        shutil.rmtree(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()  # exclusive by construction: a room is created, never entered

    try:
        _archive_head(root, path)
        carried = _carry(root, path, request.carry)
        built_environment = _environment(root, path, request)
        held = installed_extras(root, search_path=site_packages(path))
        _write_marker(bead_id, root, path, commit, request, held, built_environment)
    except (OSError, subprocess.SubprocessError, tarfile.TarError):
        # A half-built room is worse than none: it is a directory the next
        # attempt would refuse, for a reason that has nothing to do with a
        # neighbour. Remove it and let the caller try again.
        shutil.rmtree(path, ignore_errors=True)
        raise

    return RoomBuild(
        bead_id=bead_id,
        path=path,
        built=True,
        detail=(
            f"built from {commit[:8]} with {len(carried)} carried file(s)"
            + (f", reusing the replaced room's {' and '.join(reused)}" if reused else "")
            + "; no .git, so a freshness check inside it has no baseline"
        ),
        commit=commit,
        carried=carried,
        invocation=room_invocation(path, project_root=root),
        extras=held.label if held.resolved else None,
        environment=built_environment,
        reused=reused,
    )


def _remembering(
    path: Path, asked: RoomRequest, *, rebuild: bool
) -> tuple[RoomRequest, tuple[str, ...]]:
    """The request this build runs on, and which parts of it the room remembered.

    Only a rebuild remembers, and only what the caller left unsaid: a ``carry``
    or an ``extras`` given beside ``rebuild`` REPLACES its remembered
    counterpart rather than adding to it. The environment decision is recorded
    and never reused, because the two mistakes are not symmetric — forgetting a
    decline costs a measured 3.6 s and gives the room its own interpreter, while
    remembering one hands back a verdict the machine decides (BDL-UX #256) with
    no way to ask for anything else short of deleting the room.
    """
    if not rebuild:
        return asked, ()
    remembered = room_request(path)
    if remembered is None:
        return asked, ()
    reused: list[str] = []
    carry = asked.carry
    if not carry and remembered.carry:
        carry = remembered.carry
        reused.append(REUSABLE_CARRY)
    extras = asked.extras
    if extras is None and remembered.extras is not None:
        extras = remembered.extras
        reused.append(REUSABLE_EXTRAS)
    return (
        RoomRequest(carry=carry, extras=extras, environment=asked.environment),
        tuple(reused),
    )


def _environment(root: Path, path: Path, request: RoomRequest) -> RoomEnvironment:
    """Give the room its own interpreter, or say which one it borrows instead."""
    otherwise = _interpreter(root)
    if not request.environment:
        return RoomEnvironment(
            detail=(
                "no environment was built: the caller declined one. This room's "
                f"verdict is therefore taken under {otherwise}, which is the "
                "project's own environment and not this room's — name it when "
                "reporting"
            )
        )
    return build_environment(
        room=path,
        choice=extras_a_room_installs(root, request.extras),
        otherwise=otherwise,
    )


def _refuse_the_room(bead_id: str, root: Path, path: Path, *, rebuild: bool) -> RoomBuild | None:
    """The checks about the DIRECTORY, which decide whether it may be read at all.

    They run before the request is assembled, because a rebuild's request may
    come out of the record of the room at this path, and a directory this
    command may not delete is one whose record it may not act on either.
    """
    if path == root or path.is_relative_to(root):
        return _refused(
            bead_id,
            path,
            REFUSAL_INSIDE_THE_PROJECT,
            f"{path} is inside {root}: a room built in the tree it copies becomes "
            "untracked work in that tree, which every other agent then sees",
        )
    if path.exists():
        return _occupied(bead_id, path, rebuild=rebuild)
    return None


def _refuse_the_request(
    bead_id: str, root: Path, path: Path, carry: tuple[str, ...]
) -> RoomBuild | None:
    """The checks about the FILES asked for, whoever named them.

    A remembered path is checked exactly like a typed one: a file the working
    tree no longer holds refuses the rebuild rather than quietly dropping out of
    it, so a reused list can never shrink without the caller being told.
    """
    for named in carry:
        refusal = _refuse_carried(bead_id, root, path, named)
        if refusal is not None:
            return refusal
    return None


def _refuse_carried(bead_id: str, root: Path, path: Path, named: str) -> RoomBuild | None:
    """Refuse a carried path that is not a file of this project."""
    candidate = (root / named).resolve()
    if not candidate.is_relative_to(root):
        return _refused(
            bead_id,
            path,
            REFUSAL_FILE_OUTSIDE,
            f"{named} resolves outside {root}: a room carries this project's files",
        )
    if not candidate.exists():
        return _refused(
            bead_id, path, REFUSAL_FILE_MISSING, f"{named} is not a path this project holds"
        )
    if not candidate.is_file():
        return _refused(
            bead_id,
            path,
            REFUSAL_NOT_A_FILE,
            f"{named} is a directory: name your files, because a directory copy is "
            "how a neighbour's work reaches a room that is supposed to exclude it",
        )
    return None


def _occupied(bead_id: str, path: Path, *, rebuild: bool) -> RoomBuild | None:
    """Decide what an existing directory at the room's path means.

    A rebuild may delete a room this command built for THIS bead, and nothing
    else. The marker is what licenses the deletion, so a directory that merely
    carries the right name is refused: ``rmtree`` on a path chosen by a caller's
    typing is a worse failure than the one this command was written for.
    """
    owner = room_owner(path)
    if not rebuild:
        return _refused(
            bead_id,
            path,
            REFUSAL_ALREADY_EXISTS,
            f"{path} already exists and this run did not create it"
            + (f" (recorded owner: {owner})" if owner else "")
            + ". A room is built once: files copied into a room that has already "
            "been indexed postdate its own baseline (BDL-UX #243). Use --rebuild "
            "to replace it.",
        )
    if owner != bead_id:
        return _refused(
            bead_id,
            path,
            REFUSAL_NOT_A_ROOM,
            f"{path} carries no record naming {bead_id}"
            + (f" (recorded owner: {owner})" if owner else "")
            + ", so nothing here may be deleted. Remove it yourself if it is yours.",
        )
    return None


def _refused(bead_id: str, path: Path, reason: str, detail: str) -> RoomBuild:
    """One refusal, carrying the derived path so a caller can name it."""
    return RoomBuild(bead_id=bead_id, path=path, built=False, detail=detail, refusal=reason)


def _head_commit(root: Path) -> str | None:
    """The commit a room would be built from, or ``None`` if git cannot answer."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=root,
            capture_output=True,
            encoding=_TEXT_CODEC,
            errors="surrogateescape",
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def _archive_head(root: Path, path: Path) -> None:
    """Extract ``git archive HEAD`` into the room.

    ``git archive`` rather than a copy of the working tree, because the working
    tree is shared: copying it would carry every neighbour's in-progress edit
    into a room whose purpose is to exclude them.
    """
    with tempfile.TemporaryDirectory() as staging:
        archive = Path(staging) / "head.tar"
        subprocess.run(  # noqa: S603
            ["git", "archive", "--format=tar", "-o", str(archive), "HEAD"],  # noqa: S607
            cwd=root,
            capture_output=True,
            check=True,
        )
        with tarfile.open(archive) as tar:
            members = _within(tar, path)
            # `filter=` and `tarfile.data_filter` arrived together, and neither
            # exists on every interpreter this project declares (3.10 is in the
            # census). Asking for the attribute is how the extraction gets the
            # stricter behaviour where it is available without a version test
            # that goes stale.
            data_filter = getattr(tarfile, "data_filter", None)
            if data_filter is None:
                tar.extractall(path, members=members)  # noqa: S202
            else:
                tar.extractall(path, members=members, filter=data_filter)  # noqa: S202


def _within(tar: tarfile.TarFile, path: Path) -> list[tarfile.TarInfo]:
    """The members that land inside *path* — checked here rather than trusted.

    ``git`` cannot record a tree entry that escapes its root, so this filters
    nothing in practice. It is written out because the alternative is an
    ``extractall`` whose safety is an argument about another tool's invariants,
    and because ``tarfile``'s own filter argument is not available on every
    interpreter this project declares.
    """
    root = path.resolve()
    keep: list[tarfile.TarInfo] = []
    for member in tar.getmembers():
        target = (root / member.name).resolve()
        if target == root or target.is_relative_to(root):
            keep.append(member)
    return keep


def _carry(root: Path, path: Path, carry: tuple[str, ...]) -> tuple[str, ...]:
    """Copy the named project files into the room, before anything indexes it."""
    for named in carry:
        destination = path / named
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / named, destination)
    return tuple(carry)


def _write_marker(
    bead_id: str,
    root: Path,
    path: Path,
    commit: str,
    request: RoomRequest,
    extras: ExtraSet,
    environment: RoomEnvironment,
) -> None:
    """Record who the room belongs to and what a measurement in it is true of.

    Two interpreters are recorded and they are not the same one. The invocation
    names the environment the SUITE will run under; ``built_by`` is the process
    that made the room, which under a ``uv`` tool install is a different
    interpreter entirely. The extras are recorded beside them because they, and
    not the files, decided 82 mypy errors against 0 on one code base (BDL-UX
    #236) — a report that cannot be reproduced from what it prints is a claim
    rather than a measurement.

    ``interpreter.extras`` is read off the ROOM's own environment when it has
    one, and ``environment`` states what was asked for and who asked. The two
    can differ, and that is the point: what was typed is a request and what the
    interpreter holds is the answer, which is the distinction BDL-UX #236 was
    filed about.

    ``request`` is the third thing and is none of those: it is what the CALLER
    named, which a rebuild reproduces. It is recorded beside the outcome rather
    than read back out of it because the two come apart — a room given no
    environment records no extras choice at all, so a request reconstructed from
    the outcome would lose the one the caller pinned.
    """
    from beadloom import __version__

    record = {
        "bead": bead_id,
        "room": path.name,
        "project": str(root),
        "commit": commit,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "carried": list(request.carry),
        REQUEST_KEY: {
            REUSABLE_CARRY: list(request.carry),
            REUSABLE_EXTRAS: None if request.extras is None else list(request.extras),
            "environment": request.environment,
        },
        "interpreter": {
            # The room's own when it has one, which is what `room_invocation`
            # prints. Recording the project's here while printing the room's
            # would make the record disagree with the command that wrote it,
            # about the one fact BDL-UX #256 is that a report gets wrong.
            "invocation": _interpreter(root, room=path),
            "built_by": {
                "executable": sys.executable,
                "version": ".".join(str(part) for part in sys.version_info[:3]),
            },
            "extras": {
                "distribution": extras.distribution,
                "resolved": extras.resolved,
                "label": extras.label if extras.resolved else None,
                "installed": list(extras.installed),
                "absent": [
                    {"extra": a.extra, "needs": list(a.absent)} for a in extras.absent
                ],
            },
        },
        "environment": {
            "built": environment.built,
            "source": environment.source,
            "asked": list(environment.extras),
            "installer": environment.installer,
            "seconds": environment.seconds,
            "python": str(environment.python) if environment.python else None,
            "detail": environment.detail,
        },
        "beadloom": __version__,
    }
    (path / ROOM_MARKER).write_text(
        json.dumps(record, indent=2) + "\n", encoding=_TEXT_CODEC
    )
