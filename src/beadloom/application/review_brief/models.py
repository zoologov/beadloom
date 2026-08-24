"""What a reviewer is handed, and what is held back from it.

One responsibility: name the parts of a reviewer's input as data, so that
*assembling* the input and *deciding whether the author's account may be read*
stay two separate decisions with two separate modules.

The vocabulary carries the design position rather than leaving it in prose. A
bead's DESCRIPTION is the assignment and is handed over as
:attr:`ReviewBrief.assignment`; its COMMENTS are the author's report and arrive
as :class:`AuthorNote` values that the brief never holds — only
:class:`WithheldNotes`, which is a count and a way out.
"""

# beadloom:feature=review-brief

from __future__ import annotations

from dataclasses import dataclass

#: Findings a brief can carry. Each is a reason the reviewer's input rests on
#: something unstated, and each is printable, because this codebase's standing
#: rule is that an absence is reported with its reason rather than left silent.
FINDING_NO_SCOPE = "no-declared-scope"
FINDING_UNKNOWN_REF = "unknown-ref"
FINDING_UNMEASURED_CHANGE = "unmeasured-change"
FINDING_OUTSIDE_SCOPE = "changed-outside-scope"
FINDING_NO_SCENARIO = "no-bound-scenario"

#: Why the author's comments are not in the brief, in the words a reviewer reads.
WITHHELD_REASON = (
    "the author's account of the change converges the reviewer on the author's "
    "framing before the reviewer has looked at the code"
)

#: What ends the withholding. Stated on the brief itself so the reviewer is never
#: left guessing whether the notes are missing or merely deferred.
RELEASE_CONDITION = (
    "a verdict recorded on the bead; then `beadloom review-brief <bead> --release`"
)


#: What the reviewer — and only the reviewer — can observe, said on the brief
#: itself. Withholding an input is not the same as locking a door: a coordinator
#: can paste the author's summary into the launch prompt, which is what happened
#: throughout this epic's own S5 wave, deliberately, to save cycles. Nothing in
#: this process can see that happen except the agent reading the prompt, so the
#: duty to report it is placed where the observation is.
DEFEAT_NOTICE = (
    "if your launch prompt already carried the author's summary, this withholding "
    "was defeated before it ran — say so in your verdict; you are the only party "
    "that can see it"
)


@dataclass(frozen=True)
class AuthorNote:
    """One comment on the bead, as the tracker holds it.

    Never reached by :class:`ReviewBrief`: the brief counts these and stops. The
    type exists so the count and the release both talk about the same thing.
    """

    text: str
    author: str = ""
    created: str = ""


@dataclass(frozen=True)
class WithheldNotes:
    """The author's account, reduced to a count and the condition that frees it.

    Absence must not be silence — the same rule that makes a suppressed lint
    crossing and an excused document countable rather than implicit. A reviewer
    that sees ``0 withheld`` learns the author wrote nothing; a reviewer that sees
    ``6 withheld`` learns there is an account and that it is deliberately later.
    """

    count: int
    reason: str = WITHHELD_REASON
    release_condition: str = RELEASE_CONDITION
    defeat_notice: str = DEFEAT_NOTICE


@dataclass(frozen=True)
class ReleaseOutcome:
    """The answer to "may the author's account be read now?", with its reason.

    ``released`` is empty exactly when ``refused_reason`` is set, so a caller
    cannot read a partial release as a full one.
    """

    released: tuple[AuthorNote, ...] = ()
    refused_reason: str | None = None
    verdict_marker: str | None = None


@dataclass(frozen=True)
class ChangedFile:
    """One path that differs from the base ref, and whose node owns it.

    ``owner`` is ``None`` for a path no node's source covers — a test, a
    document, a configuration file. That is NOT the same as being outside the
    declared scope, and the two are kept apart: conflating them would file a
    finding against every changed test file and drown the one that matters.
    """

    path: str
    owner: str | None = None
    in_scope: bool = False


@dataclass(frozen=True)
class SpecDocument:
    """A document the graph binds to a node in the bead's declared scope."""

    ref: str
    path: str
    kind: str = ""


@dataclass(frozen=True)
class BoundScenario:
    """An acceptance scenario that names this bead in its ``@bead:`` tag."""

    name: str
    path: str
    line: int


@dataclass(frozen=True)
class ReviewBrief:
    """Everything a reviewer is handed before it records a verdict.

    Three things and no fourth: what the bead was asked to do
    (:attr:`assignment`, the tracker's description), what the specification says
    (:attr:`docs` and :attr:`scenarios`), and what actually changed
    (:attr:`changed`). The author's account of the change is represented by
    :attr:`withheld` and by nothing else.
    """

    bead_id: str
    title: str = ""
    assignment: str = ""
    refs: tuple[str, ...] = ()
    unknown_refs: tuple[str, ...] = ()
    docs: tuple[SpecDocument, ...] = ()
    changed: tuple[ChangedFile, ...] = ()
    change_measured: bool = True
    scenarios: tuple[BoundScenario, ...] = ()
    withheld: WithheldNotes = WithheldNotes(count=0)
    findings: tuple[str, ...] = ()

    @property
    def outside_scope(self) -> tuple[ChangedFile, ...]:
        """The changed files a node owns that the bead did not declare."""
        return tuple(
            changed
            for changed in self.changed
            if changed.owner is not None and not changed.in_scope
        )
