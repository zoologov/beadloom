# beadloom:domain=graph
# beadloom:feature=rule-engine
"""What a same-layer exemption excuses, and whether it has run out.

BDL-070 B2 (``beadloom-xmfs``). A layer rule that reports peer crossings needs a
way to say "this one is known and decided", or the only way to get a green
result is to narrow the rule until it catches nothing. That is what an exemption
is for, and it is honest only while it stays VISIBLE — the two ways an entry can
stop being visible are the ones :mod:`.exemptions` names for ``forbid_import``,
and they are the same two here:

* it excuses a crossing and nobody says so, so the run reports no finding and a
  reader cannot tell "nothing crossed" from "what crossed was excused";
* its stated exit condition passes and nobody notices.

This module closes both and owns nothing else. :mod:`.layers` decides what
crosses — :func:`~beadloom.graph.rules.layers.same_layer_crossings` — and this
decides what an exemption does about it, exactly the split
:mod:`.exemptions` draws for the import boundary rules.

**An exemption here excuses a decision, never a measurement.** The population a
layer rule judged is counted before any exemption is consulted, so excusing a
crossing does not shrink the denominator a reader checks the verdict against.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.types import Violation, liveness_finding
from beadloom.infrastructure.exit_condition import deadline_passed, exit_condition_deadline

if TYPE_CHECKING:
    from datetime import date

    from beadloom.graph.rules.types import LayerExemption, LayerRule

#: What to do about an entry whose stated exit condition has passed. It offers
#: both honest moves, because "delete it" alone is advice nobody can take while
#: the crossing is still in the code.
EXPIRED_LAYER_EXEMPTION_HINT = (
    "Fix the crossing and delete the exemption, or replace `until:` with a new "
    "date and the reason it still holds. An exit condition that has passed is a "
    "decision nobody has revisited, not a licence that renews itself."
)

#: What to do about an entry that excuses nothing. Deleting it is the whole
#: remedy: the edge it named is gone, which is what the entry said it was
#: waiting for.
DEAD_LAYER_EXEMPTION_HINT = (
    "Delete the entry. The edge it names is no longer in the graph, so the "
    "exemption excuses nothing and only hides the next one that looks like it."
)


def layer_exemption_index_for(rule: LayerRule, src_ref_id: str, dst_ref_id: str) -> int | None:
    """The index of the first entry excusing this crossing, if any.

    First rather than best: entries are read in declaration order, so a project
    that wrote a wide entry above a narrow one gets the wide one's reason in
    every report about it, which is the reason it wrote down.
    """
    for index, exemption in enumerate(rule.exempt):
        if exemption.covers(src_ref_id, dst_ref_id):
            return index
    return None


def excused_crossings(
    rule: LayerRule, crossings: list[tuple[str, str]]
) -> tuple[list[tuple[str, str]], dict[int, int]]:
    """Split *crossings* into the ones no entry excuses, and a count per entry.

    Both halves come back because both are needed and deriving one from the
    other twice is how the excused count and the reported count come to
    disagree: the first half is what the rule reports, the second is what says
    whether each entry is still earning its place.
    """
    reported: list[tuple[str, str]] = []
    excused: dict[int, int] = {}
    for src_ref_id, dst_ref_id in crossings:
        index = layer_exemption_index_for(rule, src_ref_id, dst_ref_id)
        if index is None:
            reported.append((src_ref_id, dst_ref_id))
        else:
            excused[index] = excused.get(index, 0) + 1
    return reported, excused


def stale_layer_exemption_findings(
    rule: LayerRule,
    excused_per_exemption: dict[int, int],
    *,
    today: date | None = None,
) -> list[Violation]:
    """One finding per entry that has stopped earning its place — at most one each.

    *excused_per_exemption* maps each entry's index to the number of crossings it
    excused in this run, which is knowable only from the edge set the rule
    evaluation already walked.
    """
    findings: list[Violation] = []
    for index, exemption in enumerate(rule.exempt):
        count = excused_per_exemption.get(index, 0)
        if count == 0:
            findings.append(_dead_finding(rule, exemption))
        elif deadline_passed(exemption.until, today=today):
            findings.append(_expired_finding(rule, exemption, count))
    return findings


def _dead_finding(rule: LayerRule, exemption: LayerExemption) -> Violation:
    """Report an entry that excuses nothing — its exit condition having fired."""
    return liveness_finding(
        rule_name=rule.name,
        rule_description=rule.description,
        message=(
            f"Rule '{rule.name}': the exemption for '{exemption.from_glob}' -> "
            f"'{exemption.to_glob}' excuses nothing — no such same-layer crossing is "
            f"left in the graph. Its exit condition ({exemption.until}) is met; delete it"
        ),
        remediation=DEAD_LAYER_EXEMPTION_HINT,
    )


def _expired_finding(rule: LayerRule, exemption: LayerExemption, excused: int) -> Violation:
    """Report an entry still excusing crossings past the date it gave itself."""
    deadline = exit_condition_deadline(exemption.until)
    crossings = "crossing" if excused == 1 else "crossings"
    return liveness_finding(
        rule_name=rule.name,
        rule_description=rule.description,
        message=(
            f"Rule '{rule.name}': the exemption for '{exemption.from_glob}' -> "
            f"'{exemption.to_glob}' expired on {deadline} and is still excusing "
            f"{excused} same-layer {crossings}"
        ),
        remediation=EXPIRED_LAYER_EXEMPTION_HINT,
    )
