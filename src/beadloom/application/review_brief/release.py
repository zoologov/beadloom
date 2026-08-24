"""Decide whether the author's account of the change may be read yet.

One responsibility, and it is a decision rather than a filter: the brief already
withheld the comments: this module says when the withholding ends, and answers
with a reason either way.

**The pivot is a recorded verdict, not the content of a comment.** The obvious
alternative — hand over the measurements and withhold the claims — cannot be
built: this epic's six understated honesty notes were each accurate about what
their bead set out to do while silent about what it missed, so a measurement and
a claim arrive in the same sentence and separating them needs a judgement no
mechanism can make and an author could phrase around. Description-against-comment
is structural; claim-against-measurement is not.

**And the account is released, not destroyed.** The author's comments are where
deliberate deferrals, sabotage tables and measured numbers live, and a reviewer
denied them re-derives work and files findings against things the author
deferred on purpose with a stated reason. A rule that makes review slower without
making it more independent is not an improvement. Once the reviewer's own
judgement is on the record it cannot be un-said, so reading the account after
that point can only add findings or explain a deferral.

**A bead that already carries a verdict releases at once, deliberately.** A
second pass is a re-review of the author's response to a judgement the reviewer
formed independently and recorded; the hidden-profile risk is in the first pass,
and re-imposing the delay there would cost cycles for an independence already
established.

**Honest limit.** This withholds an input; it does not lock a door. A reviewer
with a shell can read the tracker directly, and a coordinator can paste the
author's summary into the launch prompt — which is exactly what happened
throughout this epic's own S5 wave, deliberately, to save cycles. What the
command changes is the DEFAULT: the cheap path is now the independent one, the
withholding is visible and counted, and the role file names the paste as
something the reviewer must report in its verdict, because the reviewer is the
only party that can see it happen.
"""

# beadloom:feature=review-brief

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.review_brief.models import AuthorNote, ReleaseOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence

#: How a recorded verdict is spelled on the bead. A VOCABULARY, not a guess: these
#: are the exact openings the review role is instructed to write, so recognising
#: them here and emitting them there are one convention rather than two. A verdict
#: written in any other words is not recognised, and the release says so by name
#: instead of opening — a marker list that quietly accepted anything would make the
#: gate unfalsifiable.
VERDICT_MARKERS: tuple[str, ...] = (
    "REVIEW PASSED",
    "REVIEW ISSUES",
    "REVIEW FINDINGS",
)

#: Why a release was refused, in the words the reviewer reads.
REFUSED_NO_VERDICT = (
    "no verdict is recorded on this bead — the author's account stays withheld "
    "until one is. Record it with `bd comments add <bead> \"REVIEW PASSED: ...\"` "
    "or a findings comment opening `REVIEW ISSUES:`"
)


def _marker_in(text: str) -> str | None:
    """The verdict marker *text* opens with, matched at the start of any line.

    Anchored to a line start rather than searched anywhere in the comment, so a
    checkpoint that MENTIONS a review ("REVIEW ISSUES are still open") does not
    read as one being recorded.
    """
    for line in text.splitlines():
        stripped = line.lstrip("#*-> \t").upper()
        for marker in VERDICT_MARKERS:
            if stripped.startswith(marker):
                return marker
    return None


def verdict_recorded(notes: Sequence[AuthorNote]) -> str | None:
    """The marker of the first recorded verdict among *notes*, or ``None``."""
    for note in notes:
        marker = _marker_in(note.text)
        if marker is not None:
            return marker
    return None


def release_notes(notes: Sequence[AuthorNote]) -> ReleaseOutcome:
    """Release the author's account, or refuse with the reason it stays withheld."""
    marker = verdict_recorded(notes)
    if marker is None:
        return ReleaseOutcome(released=(), refused_reason=REFUSED_NO_VERDICT)
    return ReleaseOutcome(
        released=tuple(AuthorNote(n.text, n.author, n.created) for n in notes),
        verdict_marker=marker,
    )
