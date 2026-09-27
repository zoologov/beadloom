"""Whether a project's doc-code pairs carry a freshness baseline to be judged against."""

from __future__ import annotations

from beadloom.doc_sync.engine import BASELINE_NONE


def pairs_have_no_freshness_baseline(pairs: list[dict[str, object]]) -> bool:
    """Whether NOTHING in *pairs* was compared against a baseline at all.

    Doc freshness is decided against two baselines and a checkout may hold
    neither: the index database, which is gitignored, and ``git`` history, which
    ``sync-check`` consults through ``changed_paths``. With both absent every
    pair comes back ``unverified`` with ``baseline: none`` — not ``stale``,
    because nothing was compared. ``changed_paths`` is asked once per run, so
    the answer is a property of the CHECKOUT and the whole population carries it
    or none of it does.

    The decision reads ``baseline`` and never ``status``: ``unverified`` also
    names the ``sibling_symbols_changed`` verdict, which comes WITH an index
    baseline and is a finding about this tree. Reading the status would let a
    real finding buy itself a skip, which is the failure mode a skip has.

    An EMPTY population answers ``False`` deliberately. No pairs at all is a
    broken sample rather than a missing baseline, and ``True`` there would turn
    a check that found nothing into a skip blaming the room.
    """
    return bool(pairs) and all(str(pair.get("baseline")) == BASELINE_NONE for pair in pairs)


def no_baseline_skip_reason(pairs: list[dict[str, object]]) -> str:
    """Why the freshness assertion did not run, and what would make it run."""
    return (
        f"no freshness baseline in this checkout: all {len(pairs)} sampled "
        f"sync-check pair(s) report baseline '{BASELINE_NONE}', which is the "
        "verdict for a document compared against nothing. Both baselines are "
        "absent from a room built by `beadloom clean-room`: the index database "
        "is gitignored and `git archive` carries no `.git`. WHAT MAKES IT RUN: "
        "either baseline. It runs in this repository's working tree, and on "
        "every CI leg, where actions/checkout provides `.git`; it would run in "
        "a room on the day `beadloom clean-room` carries a baseline into one."
    )
