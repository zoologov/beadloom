# beadloom:domain=application
# beadloom:feature=flow-guards
"""The shipped guard registry — name -> :class:`Guard` (BDL-061 S1).

Adding a guard is adding a module here and one entry to :data:`BUILTIN_GUARDS`;
nothing else in the primitive changes. The registry is also the validation set
for ``flow.yml``: a ``guards:`` key naming something absent here is a
configuration error rather than a silently dead gate.
"""

from __future__ import annotations

from beadloom.application.guards.checks.bead_claimed import GUARD as BEAD_CLAIMED
from beadloom.application.guards.checks.working_branch import GUARD as WORKING_BRANCH
from beadloom.application.guards.contract import Guard

#: Every guard Beadloom ships, keyed by its declared name.
BUILTIN_GUARDS: dict[str, Guard] = {
    BEAD_CLAIMED.name: BEAD_CLAIMED,
    WORKING_BRANCH.name: WORKING_BRANCH,
}

#: Guard names, deterministically ordered (CLI listings, liveness reports).
GUARD_NAMES: tuple[str, ...] = tuple(sorted(BUILTIN_GUARDS))

__all__ = ["BUILTIN_GUARDS", "GUARD_NAMES", "Guard"]
