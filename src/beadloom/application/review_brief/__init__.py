"""The reviewer's input: the change and the specification, not the author's account.

Public surface of the ``review-brief`` feature. Two decisions, kept apart because
they can be got wrong independently: :func:`assemble_brief` says what a reviewer
is handed, and :func:`release_notes` says when the author's account stops being
withheld.
"""

from beadloom.application.review_brief.assembly import assemble_brief
from beadloom.application.review_brief.models import (
    DEFEAT_NOTICE,
    FINDING_AMBIGUOUS_SCOPE,
    FINDING_NO_SCENARIO,
    FINDING_NO_SCOPE,
    FINDING_OUTSIDE_SCOPE,
    FINDING_UNKNOWN_REF,
    FINDING_UNMEASURED_CHANGE,
    RELEASE_CONDITION,
    WITHHELD_REASON,
    AuthorNote,
    BoundScenario,
    ChangedFile,
    ReleaseOutcome,
    ReviewBrief,
    SpecDocument,
    WithheldNotes,
)
from beadloom.application.review_brief.release import (
    REFUSED_NO_VERDICT,
    SELF_RECORDED_VERDICT,
    UNNAMED_VERDICT_AUTHOR,
    VERDICT_MARKERS,
    release_notes,
    verdict_recorded,
)

__all__ = [
    "DEFEAT_NOTICE",
    "FINDING_AMBIGUOUS_SCOPE",
    "FINDING_NO_SCENARIO",
    "FINDING_NO_SCOPE",
    "FINDING_OUTSIDE_SCOPE",
    "FINDING_UNKNOWN_REF",
    "FINDING_UNMEASURED_CHANGE",
    "REFUSED_NO_VERDICT",
    "RELEASE_CONDITION",
    "SELF_RECORDED_VERDICT",
    "UNNAMED_VERDICT_AUTHOR",
    "VERDICT_MARKERS",
    "WITHHELD_REASON",
    "AuthorNote",
    "BoundScenario",
    "ChangedFile",
    "ReleaseOutcome",
    "ReviewBrief",
    "SpecDocument",
    "WithheldNotes",
    "assemble_brief",
    "release_notes",
    "verdict_recorded",
]
