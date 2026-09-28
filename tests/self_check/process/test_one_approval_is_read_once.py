"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_s4_the_instruments_agree.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.declared_scope import (
    scope_check,
    work_item_axes,
)

if TYPE_CHECKING:
    from pathlib import Path


#: This repository's own branch, and the work item it names. Used only where the
#: assertion needs a project that HAS an index: resolving a work item's axes
#: needs one, which a bare `tmp_path` cannot supply.
_OWN_BRANCH = "features/BDL-068"


_OWN_WORK_ITEM = "BDL-068"


class TestOneApprovalIsReadOnce:
    """`waves` and `scope-check` judge one work item through one read.

    `declared_scope.work_item_axes` states in its own docstring that it is "a
    second RENDERING of the read `scope_of_branch` already makes, never a second
    read", because a commit gate and a wave plan disagreeing about one approval
    is the two-homes class BDL-068 exists to remove. `beadloom-en0x`'s unit
    suite builds `WorkItemAxes` literals and never calls the function, so the
    sentence was carried by the docstring alone.

    The three reasons below are the whole population of ways the read can fail —
    `scope_of_branch` returns `(None, reason)` on each — and a rendering that
    dropped or reworded any of them would let the plan and the gate print
    different accounts of the same absent approval.
    """


    def test_a_resolved_approval_is_named_identically_by_both(
        self, self_check_snapshot: Path
    ) -> None:
        """The positive case, on the one project that has an index.

        Measured against this repository rather than a synthetic tree: resolving
        a work item needs a built index, and a fixture reindexed inside the test
        would be measuring the fixture's own graph.

        It takes `self_check_snapshot` rather than reading the ambient
        `.beadloom/beadloom.db`, and it asserts over the APPROVAL rather than
        over the run's verdict. Both are corrections a clean room made to this
        test, in that order. Reading the ambient index, it passed on the tree
        and failed in a room, because `git archive` carries no gitignored index
        and the read stopped at `NO_INDEX`. Requiring `run.reason is None`, it
        then failed again, because `scope_check` goes on to ask git which paths
        the commit changes and a room has no `.git` — `GIT_SILENT`.

        The second failure is the sharper statement of what these two functions
        share. They read the approval once and diverge immediately afterwards:
        only `scope_check` needs a working tree, and `work_item_axes` answers a
        plan-time question that has none. So the shared half is the work item and
        the document it was read from, and `run.reason` is deliberately not
        asserted here — it is a fact about the tree the run was taken in, and
        pinning it is what made this assertion room-dependent twice (BDL-UX
        #236's class, inside a test about instruments that must not be).
        """
        run = scope_check(self_check_snapshot, branch=_OWN_BRANCH)
        axes = work_item_axes(self_check_snapshot, branch=_OWN_BRANCH)
        assert axes.reason is None, axes.reason
        assert run.work_item == axes.work_item == _OWN_WORK_ITEM
        assert run.document == axes.document
        assert axes.document, "the fixture must resolve a document to compare"
