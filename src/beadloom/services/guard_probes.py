# beadloom:service=cli
# beadloom:component=guard-probes
"""Concrete read-only probes binding guards to the real ``bd`` and ``git`` (BDL-061 S1).

The guard checks are written against ports
(:mod:`beadloom.application.guards.contract`); this is where those ports meet
the actual tools. It lives in the **services** layer for one hard reason: the
``bd`` seam does, and the application layer must not import services
(``architecture-layers``, severity ``error``). Wiring the adapters at the CLI
boundary keeps the dependency pointing inward.

Every probe is read-only and fail-quiet-but-honest: when a tool is missing,
errors, or is not configured for this project, the probe returns ``None`` — the
value that makes a guard **skip with a reason** rather than pass. Nothing here
falls back to a default that would manufacture a green verdict.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from beadloom.application.guards.contract import ClaimedBead, GuardProbes

if TYPE_CHECKING:
    from pathlib import Path

#: bd status token meaning "someone has claimed this and is working on it".
CLAIMED_STATUS = "in_progress"

#: ``bd list`` caps its answer at 50 rows unless told otherwise; ``0`` lifts it.
#: Reading one page and filtering client-side made an in-progress bead beyond it
#: invisible, so ``bead-claimed`` reported a violation of a condition that held.
UNLIMITED = "0"

#: Seconds before a wedged ``git`` call is abandoned (then reported as unknown).
_GIT_TIMEOUT_S = 10

#: The codec that turns git's bytes into text, STATED rather than inherited.
#: ``text=True`` decodes with ``locale.getpreferredencoding(False)`` — the image's
#: locale — so the same repository answered differently on a C-locale container
#: than on the author's UTF-8 machine: ``ascii`` raises (and the exception escaped
#: the handler below), ``latin-1`` returns a branch name nobody checked out. git
#: stores a ref name as bytes and prints them back unchanged, so UTF-8 is the
#: project's decision about how to read them, not a fact about the image.
_GIT_ENCODING = "utf-8"

#: ``surrogateescape``, and the reason is which way each alternative fails.
#: ``strict`` would make a branch name that is not valid UTF-8 unreadable, the
#: probe would answer ``None``, and ``working-branch`` would *skip* — an exemption
#: nobody declared, for a repository whose branch name is perfectly legal on
#: POSIX. ``replace`` would map distinct names onto the same string, so a
#: comparison could be given a wrong answer by a byte. ``surrogateescape`` is the
#: only handler of the three that is injective: it round-trips to the exact bytes
#: git holds, so ``branch == trunk`` stays truthful and the name survives into the
#: message (escaped by ``repr``, hence still printable on an ASCII-only stdout).
_GIT_DECODE_ERRORS = "surrogateescape"


class BdWorkTracker:
    """:class:`~beadloom.application.guards.contract.WorkTracker` over the ``bd`` CLI."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        """Beads reported ``in_progress``, or ``None`` when bd cannot answer.

        The tracker is queried only when the project actually has a ``.beads/``
        directory: invoking ``bd`` in an unrelated repo could initialise state
        there, and a guard must never change the project it inspects.

        The query asks bd for the claimed beads rather than filtering its first
        page: see :data:`UNLIMITED`. The client-side status check is kept as
        belt-and-braces, so a bd whose ``--status`` filter changes meaning
        cannot turn an unclaimed project into a passing one.
        """
        from beadloom.services.bd_seam import BdUnavailableError, run_bd

        if not (self._project_root / ".beads").is_dir():
            return None
        try:
            result = run_bd(
                ["list", "--status", CLAIMED_STATUS, "--json", "--limit", UNLIMITED],
                cwd=str(self._project_root),
            )
        except BdUnavailableError:
            return None
        if not result.ok:
            return None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, list):
            return None
        return tuple(
            ClaimedBead(id=bead["id"], title=str(bead.get("title") or ""))
            for bead in payload
            if isinstance(bead, dict)
            and isinstance(bead.get("id"), str)
            and bead.get("status") == CLAIMED_STATUS
        )


class GitWorkspace:
    """:class:`~beadloom.application.guards.contract.Workspace` over ``git``."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def current_branch(self) -> str | None:
        """The checked-out branch, or ``None`` outside a repo / on a detached HEAD.

        Uses ``git branch --show-current`` rather than ``rev-parse
        --abbrev-ref``: it answers correctly on an unborn branch (a fresh repo
        before its first commit) and prints nothing when HEAD is detached.
        """
        try:
            result = subprocess.run(  # fixed argv, no shell
                ["git", "branch", "--show-current"],  # noqa: S607
                cwd=str(self._project_root),
                capture_output=True,
                encoding=_GIT_ENCODING,
                errors=_GIT_DECODE_ERRORS,
                timeout=_GIT_TIMEOUT_S,
                check=False,
            )
        except Exception:  # as wide as the sentence it holds; see below
            # AS WIDE AS THE SENTENCE IT HOLDS: "a probe that cannot answer
            # returns None". The previous handler was `(OSError,
            # subprocess.SubprocessError)`, which is an enumeration and not that
            # sentence — it misses `UnicodeDecodeError`, which is a `ValueError`
            # and therefore neither. Measured: with `text=True` on this UTF-8
            # machine, a HEAD pointing at `refs/heads/features/<0xff>-bad` raises
            # it straight past this handler, and the invocation boundary turns
            # that into an `error` verdict at exit 2 — a BLOCKED edit for a
            # reason that is not the real one, where the designed answer is a
            # skip that says why (BDL-061.37, the third instance of .36's
            # family). Adding the class would fix this decode and leave the next
            # one open.
            #
            # `Exception`, deliberately NOT `BaseException`: an interrupt while
            # git is running is the process being stopped, not git declining to
            # answer, and the boundary already reports that distinctly.
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None


def build_probes(project_root: Path) -> GuardProbes:
    """The real probe set for *project_root*."""
    return GuardProbes(
        tracker=BdWorkTracker(project_root), workspace=GitWorkspace(project_root)
    )
