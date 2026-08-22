# beadloom:domain=application
# beadloom:feature=flow-guards
"""``bead-claimed`` — is this edit covered by a claimed work item? (BDL-061 S1)

The flow's first rule ("never work a bead without claiming it") has until now
been prose the model may ignore. This is that rule as a mechanism: before an
edit, ask the tracker whether anything is in progress.

What it deliberately does NOT decide is whether the claimed bead is the *right*
one for this file — that needs a bead-to-node scope binding the graph does not
carry yet (S6). The check says so in ``not_covered`` rather than implying a
coverage it cannot demonstrate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.guards.contract import Guard, GuardFinding
from beadloom.application.guards.paths import UNNAMED_TARGET, PathScope

if TYPE_CHECKING:
    from beadloom.application.guards.contract import GuardRequest

_SCOPE_NOT_COVERED = "whether the claimed bead's scope actually covers this path"
_NO_PATH_NOT_COVERED = "the harness supplied no path, so the edit target was not considered"
_REMEDIATION = (
    "claim work first: `bd ready --claim`, or "
    "`bd update <bead-id> --status in_progress --claim`"
)


def _not_covered(request: GuardRequest) -> tuple[str, ...]:
    """What this evaluation did not verify, given what the caller supplied.

    Keyed on the path *scope*, not on ``relative_path is None``: that is also
    ``None`` for a target outside the project, and reporting "the harness
    supplied no path" about a path the harness did supply is a false note in the
    one field the reader is meant to trust. The outside-the-project case is
    named by the evaluator instead.
    """
    items = [_SCOPE_NOT_COVERED]
    if request.resolved_path.scope is PathScope.ABSENT:
        items.append(_NO_PATH_NOT_COVERED)
    return tuple(items)


def check_bead_claimed(request: GuardRequest) -> GuardFinding:
    """Report whether the tracker has at least one bead in progress."""
    not_covered = _not_covered(request)
    beads = request.probes.tracker.claimed_beads()
    if beads is None:
        return GuardFinding.skipped(
            "the work tracker is unavailable — cannot tell whether a bead is claimed",
            not_covered=not_covered,
        )
    if beads:
        claimed = ", ".join(bead.id for bead in beads)
        return GuardFinding.ok(f"in progress: {claimed}", not_covered=not_covered)
    target = request.resolved_path.label or UNNAMED_TARGET
    return GuardFinding.violated(
        f"no bead is in progress while editing {target}",
        remediation=_REMEDIATION,
        not_covered=not_covered,
    )


GUARD = Guard(
    name="bead-claimed",
    summary="An edit happens under a claimed work item, not off the record",
    check=check_bead_claimed,
)
