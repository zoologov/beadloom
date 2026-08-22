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
                text=True,
                timeout=_GIT_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None


def build_probes(project_root: Path) -> GuardProbes:
    """The real probe set for *project_root*."""
    return GuardProbes(
        tracker=BdWorkTracker(project_root), workspace=GitWorkspace(project_root)
    )
