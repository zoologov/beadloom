"""Which files a guard evaluation changed, and whose change each one was."""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

#: Floor for the control window that decides "the guard wrote" from "somebody
#: else did". The measurement window is normally ~1s of real ``bd``/``git``
#: calls; a control shorter than that would be a weaker probe than the thing it
#: is checking, and would rule out a concurrent writer it never had time to see.
_CONTROL_WINDOW_FLOOR_S = 0.5


def differing(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Names whose digest changed, appeared, or vanished between two snapshots."""
    return sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))


def _moved_with_nothing_running(
    snapshot: Callable[[], dict[str, str]], window_s: float
) -> list[str]:
    """Names that change over an idle window — evidence of a CONTINUOUS writer.

    Non-empty means the repository is being written by a process this test does
    not control, so a change seen during the measurement window cannot be
    charged to the guard. Empty means the repository was quiescent *for the
    duration of one window* — which is weaker than "the evaluation is the only
    candidate left", and the gap is what BDL-UX #233 was filed about.

    The probe can only see a writer that is still writing when the control
    window opens. It answers correctly for a concurrent ``beadloom lint``, which
    holds the index open for as long as it runs, and cannot answer at all for a
    ``bd`` export, which is one deferred burst with nothing in the session
    marking when it lands. That is why the caller attributes by FILE first and
    only reaches this probe for the files timing can decide.
    """
    before = snapshot()
    time.sleep(max(window_s, _CONTROL_WINDOW_FLOOR_S))
    return differing(before, snapshot())


#: The tracker export, and the one member of the live test's tracked set that no
#: guard can write. It is here to be ATTRIBUTED, never to be excluded: it stays
#: in the digest, a change to it is still detected and still named, and only the
#: writer it is charged to differs. Dropping it would make the live test green
#: and blind, because a guard genuinely must not write the tracker either.
#:
#: Measured on this repository (BDL-UX #233), and the second measurement is the
#: one that matters. Three consecutive ``bd list --status in_progress --json
#: --limit 0`` calls — the evaluation's only tracker call — left
#: ``.beads/issues.jsonl`` unmoved in both byte digest and mtime, so the file
#: moves only when some OTHER process mutates the tracker. But the rewrite is
#: **deferred**, not synchronous: four ``bd update --priority`` writes each left
#: the export unmoved when sampled immediately afterwards, and the file had been
#: rewritten by the next sample. The flush is therefore a burst that no session
#: command marks the moment of, which is strictly worse for a control window
#: than a burst inside its own invocation would be — the window has nothing to
#: overlap with on purpose. A two-writer wave makes it likelier, not rarer,
#: since both agents run ``bd comments add``.
_TRACKER_EXPORT_NAMES = frozenset({"issues.jsonl"})


def _attribute_by_file(moved: Sequence[str]) -> tuple[list[str], list[str]]:
    """Split changed names into ``(the guard could have written, it could not)``.

    Attribution by file rather than by timing, because the digest already names
    the path that differed and the information is therefore in hand. Every name
    handed in comes back in exactly one half and none is dropped — "this write
    was not the guard's" and "this path is not checked" are different facts, and
    only the first one is ever made here.

    An unrecognised name is the guard's. A file this test has never seen before
    appearing beside the index is precisely the shape a new write takes, and a
    default of "somebody else's" would let the next one in without a word.
    """
    ours = [name for name in moved if name not in _TRACKER_EXPORT_NAMES]
    theirs = [name for name in moved if name in _TRACKER_EXPORT_NAMES]
    return ours, theirs


@dataclass(frozen=True)
class Attribution:
    """Who wrote the files that moved — three verdicts, because there are three.

    ``charged``
        the guard's to answer for, and the only one that makes the live test red.
    ``elsewhere``
        another process's, decided by the path. The write happened, it was seen,
        it was named, and it was not the guard's. This is NOT "not checked".
    ``unattributable``
        the repository is being written and nothing here can say by whom. The
        live test skips on this, which is a check that did not happen and says so.
    """

    charged: list[str]
    elsewhere: list[str]
    unattributable: list[str]


def attribute(
    moved: Sequence[str],
    *,
    snapshot: Callable[[], dict[str, str]],
    window_s: float,
) -> Attribution:
    """Charge every changed name to a writer, cheapest instrument first.

    The FILE decides first and decides for good: a path outside every guard's
    reach was written by another process whatever the clock says, and the answer
    costs nothing. The control WINDOW is consulted only for what is left, so the
    common case in a wave — a neighbour's ``bd comments add`` and nothing else —
    now pays no control window at all, where before it paid one and got the
    wrong answer from it.

    Order matters in one direction only: attributing a burst elsewhere never
    excuses an index write seen in the same window, because the two halves are
    disjoint by path.
    """
    charged, elsewhere = _attribute_by_file(moved)
    if not charged:
        return Attribution([], elsewhere, [])
    if _moved_with_nothing_running(snapshot, window_s):
        return Attribution([], elsewhere, charged)
    return Attribution(charged, elsewhere, [])


def report_attribution(attribution: Attribution, *, window_s: float) -> None:
    """Deliver an attribution as this session's three outcomes, in three words.

    Separated from the measurement because the measurement cannot be driven
    deterministically — the tracker defers its export, so a burst cannot be
    scheduled into a window — while this can, and the words are the part a
    reader acts on.

    The order is deliberate. What was attributed elsewhere is said FIRST and
    without stopping the run, so a change charged to the guard in the same
    window is still raised: a report about one path must never excuse another.
    """
    if attribution.elsewhere:
        warnings.warn(
            "attributed elsewhere, NOT excluded from the comparison: "
            f"{', '.join(attribution.elsewhere)} changed during the measurement "
            "window. No guard can write it — the evaluation's only tracker call "
            "is a read — so this is another process's `bd` write, which a wave "
            "makes likelier since both agents run `bd comments add` "
            "(BDL-UX #233). The read-only claim over the index was still "
            "measured, and is this test's verdict.",
            RuntimeWarning,
            stacklevel=2,
        )
    if attribution.charged:
        raise AssertionError(
            "the evaluation changed a file it may only read: " + ", ".join(attribution.charged)
        )
    if attribution.unattributable:
        pytest.skip(
            "cannot attribute: this repository is being written by another "
            f"process right now — {', '.join(attribution.unattributable)} changed "
            f"over an idle {max(window_s, _CONTROL_WINDOW_FLOOR_S):.2f}s control "
            "window with no guard running. `beadloom lint` writes the index by "
            "design (#147) and is the continuous writer this window can see."
        )
