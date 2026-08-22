# beadloom:domain=application
# beadloom:feature=flow-guards
"""``working-branch`` — is the edit happening off the protected trunk? (BDL-061 S1)

Trunk-based development says every change reaches ``main`` through a PR. The
failure this catches is mundane and expensive: a session that starts editing
before branching, discovered only at push time when the trunk is protected.

The trunk's name is configuration (``options.trunk`` in ``flow.yml``), not an
assumption, because ``master`` / ``trunk`` / ``develop`` are all somebody's
default.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.guards.contract import Guard, GuardFinding

if TYPE_CHECKING:
    from beadloom.application.guards.contract import GuardRequest

#: Trunk branch assumed when ``options.trunk`` is not configured.
DEFAULT_TRUNK = "main"

_NOT_COVERED = (
    "whether the working branch is named after the claimed work item",
    "whether the trunk is actually protected on the remote",
)


def check_working_branch(request: GuardRequest) -> GuardFinding:
    """Report whether the checked-out branch is something other than the trunk."""
    trunk = request.options.get("trunk", DEFAULT_TRUNK)
    branch = request.probes.workspace.current_branch()
    if branch is None:
        return GuardFinding.skipped(
            "no branch is checked out (not a git working copy, or a detached HEAD)",
            not_covered=_NOT_COVERED,
        )
    if branch == trunk:
        return GuardFinding.violated(
            f"editing on the protected trunk branch {branch!r}",
            remediation=f"branch first: `git switch -c features/<ISSUE-KEY>` (trunk is {trunk!r})",
            not_covered=_NOT_COVERED,
        )
    return GuardFinding.ok(
        f"on working branch {branch!r} (trunk is {trunk!r})", not_covered=_NOT_COVERED
    )


GUARD = Guard(
    name="working-branch",
    summary="Work happens on a working branch, never directly on the protected trunk",
    check=check_working_branch,
    default_events=("edit",),
)
