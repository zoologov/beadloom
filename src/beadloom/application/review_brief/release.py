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

**Honest limits.** Four of them, and they are limits rather than decorations —
the first review to use this command found a defect in the paragraph that was
written to avoid overstating what it does (BDL-061.23), so the list is now the
one thing in this module that must not be read as generous.

1. This withholds an input; it does not lock a door. A reviewer with a shell can
   read the tracker directly, and a coordinator can paste the author's summary
   into the launch prompt — which is exactly what happened throughout this
   epic's own S5 wave, deliberately, to save cycles. What the command changes is
   the DEFAULT: the cheap path is now the independent one, the withholding is
   visible and counted, and the role file names the paste as something the
   reviewer must report in its verdict, because the reviewer is the only party
   that can see it happen.
2. The paste it names is the author's SUMMARY. It does not model the
   coordinator's own observations, and a launch prompt carrying a directed hint
   is not a summary — the review of this slice reported that two of its findings
   came from one such hint. The duty to report therefore covers anything in the
   prompt the reviewer did not derive itself, not only a pasted account.
3. "Description-against-comment is structural" holds for a bead written before
   the work. It does not hold for a FIX bead, whose description IS the previous
   review — five numbered findings with their diagnoses, handed over as THE
   ASSIGNMENT. That is correct, because it is the assignment, and it also means
   a fix bead's reviewer is converged on the previous reviewer's framing by
   design. The mechanism cannot separate those, and does not claim to.
4. WHO recorded the verdict is compared and REPORTED; it is not enforced. See
   :data:`SELF_RECORDED_VERDICT` for the measurement behind that choice.
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

#: What the gate could not establish, in the words the reviewer reads. Two of
#: them, kept apart because their remedies differ: one says the identities matched
#: and one says the tracker gave none.
#:
#: **Reported rather than refused, and the reason is measured.** In this
#: repository every comment on every bead carries the one tracker identity
#: `v.zoologov` — the dev agent, the review agent and the human all write under
#: it, and it is also the assignee of every bead. A gate that refused a
#: self-recorded verdict would therefore refuse every release here, and a gate
#: nobody can pass is bypassed rather than obeyed: the reviewer would run
#: `bd comments` directly, which this module has never been able to prevent. So
#: the comparison is made, its answer is printed BEFORE the account, and it costs
#: the run its exit code — the same shape `beadloom-mr2l.80` gave an unmeasured
#: medium, which is a finding rather than a silent pass.
SELF_RECORDED_VERDICT = (
    "the verdict was recorded under the same tracker identity as the bead's own "
    "author ({author}), so this gate cannot tell an independent verdict from the "
    "author's own — say which it was in your review"
)

UNNAMED_VERDICT_AUTHOR = (
    "the tracker named no author for the verdict comment, so this gate could not "
    "tell whether the account was released by its own author — say so in your review"
)


def _opening_marker(text: str) -> str | None:
    """The verdict marker *text* OPENS with, or ``None``.

    Two conditions, and the module's history is the argument for each. The marker
    must carry its COLON, because the previous version anchored to a line start
    and stopped there — so "REVIEW ISSUES are still open, will fix" released the
    account, which is the exact string the docstring named as the case it
    prevented (BDL-061.23 M1). And it must open the FIRST non-blank line of the
    comment, because a verdict comment opens with its verdict: the review role is
    instructed to write `REVIEW PASSED: ...` as the first thing it says, and a
    marker allowed anywhere in the body let "COMPLETED: shipped it / REVIEW
    PASSED: I checked my own work" open the gate from inside a checkpoint.
    """
    for line in text.splitlines():
        stripped = line.lstrip("#*-> \t").upper()
        if not stripped:
            continue
        for marker in VERDICT_MARKERS:
            if stripped.startswith(f"{marker}:"):
                return marker
        return None
    return None


def _verdict_note(notes: Sequence[AuthorNote]) -> tuple[AuthorNote, str] | None:
    """The first note that records a verdict, with the marker it recorded it in."""
    for note in notes:
        marker = _opening_marker(note.text)
        if marker is not None:
            return note, marker
    return None


def verdict_recorded(notes: Sequence[AuthorNote]) -> str | None:
    """The marker of the first recorded verdict among *notes*, or ``None``."""
    found = _verdict_note(notes)
    return found[1] if found is not None else None


def _same_party(one: str, other: str) -> bool:
    """Whether two tracker identities name the same party, ignoring case and space."""
    return one.strip().casefold() == other.strip().casefold()


def release_notes(
    notes: Sequence[AuthorNote], *, bead_author: str = ""
) -> ReleaseOutcome:
    """Release the author's account, or refuse with the reason it stays withheld.

    ``bead_author`` is the tracker's assignee for the bead — the party whose
    account is being withheld. It is COMPARED with the author of the verdict
    comment, and the answer is reported on the outcome. Before
    ``beadloom-mr2l.83`` the field was read from the tracker and never used, so
    the author of a bead released the author's own account by writing a verdict
    comment on it, and nothing said so.
    """
    found = _verdict_note(notes)
    if found is None:
        return ReleaseOutcome(released=(), refused_reason=REFUSED_NO_VERDICT)
    note, marker = found
    return ReleaseOutcome(
        released=tuple(AuthorNote(n.text, n.author, n.created) for n in notes),
        verdict_marker=marker,
        verdict_author=note.author,
        independence_note=_independence_note(note.author, bead_author),
    )


def _independence_note(verdict_author: str, bead_author: str) -> str | None:
    """What the gate could not establish about who recorded the verdict."""
    if not verdict_author.strip() or not bead_author.strip():
        return UNNAMED_VERDICT_AUTHOR
    if _same_party(verdict_author, bead_author):
        return SELF_RECORDED_VERDICT.format(author=verdict_author.strip())
    return None
