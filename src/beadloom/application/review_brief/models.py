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
FINDING_AMBIGUOUS_SCOPE = "ambiguous-scope"

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
#:
#: It asks about anything the reviewer did not derive, not only a pasted summary.
#: The first review to run under this notice reported that its prompt carried the
#: coordinator's own observation of the wave — not the author's account, so
#: nothing here modelled it — and that two of its findings came from that hint. A
#: notice that named only the paste would have been answered truthfully and would
#: have missed it.
DEFEAT_NOTICE = (
    "if your launch prompt carried anything about this change that you did not "
    "derive yourself — the author's summary, or the coordinator's own observation "
    "of it — this withholding was defeated before it ran; say so in your verdict, "
    "you are the only party that can see it"
)


#: The channels the report speaks about, named as constants so the derivation,
#: the renderer and a test cannot spell one of them three ways.
CHANNEL_BEAD_COMMENTS = "bead comments"
CHANNEL_WORK_ITEM_DOCUMENTS = "the work item's documents"
CHANNEL_COMMIT_BODIES = "the commit bodies of the reviewed range"
CHANNEL_LAUNCH_PROMPT = "the launch prompt"


@dataclass(frozen=True)
class Commit:
    """One commit of the reviewed range, and how much prose its body carries.

    The subject and the body LENGTH, never the body text: this is a statement
    about what a reviewer can reach, and a report that quoted the bodies would
    be the leak it exists to make visible.
    """

    sha: str
    subject: str
    body_lines: int


@dataclass(frozen=True)
class Channel:
    """One way the change's account can reach the reviewer, and what it carries.

    ``inspected=False`` with no items is NOT the same statement as
    ``inspected=True`` with no items, and the two must never render alike. That
    is :class:`beadloom.application.impact.Population`'s rule one layer up: a
    channel this command could not look into, reported as a channel it looked
    into and found empty, is a claim about the reviewer's knowledge that nobody
    measured.

    ``reason`` is required in both directions — why the channel could not be
    inspected, or what the count was taken over — because a number whose window
    is unstated is the defect ``0 withheld`` was (BDL-UX #204).
    """

    name: str
    inspected: bool
    items: tuple[str, ...] = ()
    reason: str = ""

    @property
    def carries(self) -> int:
        """How many things this channel was found to carry."""
        return len(self.items)

    def statement(self) -> str:
        """The one line a reader gets, in the shape that keeps the two apart."""
        if not self.inspected:
            return f"{self.name}: NOT INSPECTED — {self.reason}"
        counted = f"{self.name}: {self.carries} item(s)"
        return f"{counted} — {self.reason}" if self.reason else counted


@dataclass(frozen=True)
class Reachability:
    """What can reach the reviewer about this change, channel by channel.

    It replaces the withheld count rather than joining it. ``0 withheld`` was
    true of bead comments and was read as a statement about the reviewer's
    knowledge; three measured defeats of the withholding — through ``ACTIVE.md``,
    through the commit bodies of the reviewed range, and through a launch prompt
    nothing here can see — all reached a reviewer that had been told nothing was
    held back (BDL-UX #204, #212, #219).

    It raises detectability and closes nothing. Every one of those three was
    known only because a reviewer declared it unprompted, and no report can stop
    a reviewer reading a commit body its own protocol sends it to.
    """

    channels: tuple[Channel, ...] = ()

    def named(self, name: str) -> Channel | None:
        """The channel called *name*, or ``None`` when the report has none."""
        for channel in self.channels:
            if channel.name == name:
                return channel
        return None

    @property
    def uninspected(self) -> tuple[Channel, ...]:
        """Every channel this command could not look into, in report order."""
        return tuple(channel for channel in self.channels if not channel.inspected)


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

    ``independence_note`` is the third answer, and it is why the type is not a
    boolean: a release can happen and still rest on a verdict whose independence
    the tracker cannot confirm. Reporting that as a plain success is the silent
    false-green this whole feature exists to remove.
    """

    released: tuple[AuthorNote, ...] = ()
    refused_reason: str | None = None
    verdict_marker: str | None = None
    verdict_author: str = ""
    independence_note: str | None = None


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

    :attr:`reachability` is a statement about the reviewer rather than about the
    brief: :attr:`withheld` says what THIS command holds back, and that is the
    sentence three defeats were read through. What the reviewer can reach is a
    different question with a different answer, and it is reported per channel.
    """

    bead_id: str
    title: str = ""
    assignment: str = ""

    #: The ref the change was measured AGAINST, carried on the brief rather than
    #: passed beside it. The window is part of what the change inventory means:
    #: a branch holding five beads reports all five beads' files to each of them,
    #: so a finding about the change has to name what it was measured over.
    measured_since: str = ""
    refs: tuple[str, ...] = ()
    unknown_refs: tuple[str, ...] = ()
    docs: tuple[SpecDocument, ...] = ()
    changed: tuple[ChangedFile, ...] = ()
    change_measured: bool = True
    scenarios: tuple[BoundScenario, ...] = ()
    withheld: WithheldNotes = WithheldNotes(count=0)
    reachability: Reachability = Reachability()
    findings: tuple[str, ...] = ()

    @property
    def outside_scope(self) -> tuple[ChangedFile, ...]:
        """The changed files a node owns that the bead did not declare."""
        return tuple(
            changed
            for changed in self.changed
            if changed.owner is not None and not changed.in_scope
        )
