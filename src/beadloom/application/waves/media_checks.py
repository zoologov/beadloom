"""Whether each shared medium's plan-time precondition holds — one check per medium.

:mod:`.media` STATES what a wave shares no matter how independent its beads' code
is. Stating it was half the guarantee and the half that could not fail: the
media were a constant tuple, so a wave asserted a property nothing verified
(BDL-061.22, "clause two is printed, not enforced"). This module is the other
half. Each medium gets a check that can come back ``failed``, and a medium nobody
measured comes back ``unmeasured`` rather than passing in silence — an absent
answer that reads as a clean one is the defect this whole command exists for.

**What these checks are, precisely.** They are PRECONDITIONS, measured before the
wave runs: the tree it starts from, the hook that will judge its commits, what its
artifacts tell an agent about the landing lock, whether the document every one of
its beads writes gives each of them a row, the doc baseline it inherits, and the
ids its beads already carry. They are not
verification of the wave's conduct. Nothing here can check that the gate owner
actually ran the tree afterwards, because that happens after the plan exists and
no plan can reach it. The sentence in :mod:`beadloom.application.waves` names
that split rather than leaving a reader to discover it.

**Where the observations come from.** Five of the six are facts about files —
git, the installed hook, the doc index, the composed flow artifacts, the flow's
own planning documents — and they arrive as a :class:`WaveEnvironment` gathered
by the caller rather than read here, so this layer keeps taking its input as data
and the checks stay runnable without a git binary, a repository, a hook or a
scaffolded flow. The sixth needs nothing but the bead records the planner already
holds, and the focus-document check needs both: the file's rows as data, and the
records to say whose row each is.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.application.active_table import names_bead
from beadloom.application.waves.landing import LOCK_COMMAND, defect_detail
from beadloom.application.waves.media import (
    MEDIUM_COMMIT_GATE,
    MEDIUM_DOC_BASELINE,
    MEDIUM_FOCUS_DOCUMENT,
    MEDIUM_LANDING_ORDER,
    MEDIUM_TRACKER_IDS,
    MEDIUM_WORKING_TREE,
)
from beadloom.application.waves.models import (
    GATE_ABSENT,
    GATE_COMMIT_SCOPED,
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNMEASURED,
    MediumCheck,
    WaveEnvironment,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beadloom.application.waves.models import BeadRecord

#: A bead reference as this project's title convention writes one: an identifier
#: that starts with a letter, a dot, and a number (``BDL-061.39``,
#: ``beadloom-mr2l.21``). The bounding classes keep a version string out —
#: ``v2.2.0`` and ``3.10`` are not references, and reading a number out of a
#: larger token is the misparse BDL-UX #169 already cost this project once.
_TITLE_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9._-])([A-Za-z][A-Za-z0-9_-]*)\.(\d+[a-z]?)(?![A-Za-z0-9._-])"
)

#: The trailing number of an allocated tracker id, when it has one.
_ID_SUFFIX = re.compile(r"\.(\d+[a-z]?)$")


def title_references(text: str) -> tuple[str, ...]:
    """Every bead reference *text* states, in the order it states them.

    The reader half of :func:`title_id_mismatches`, public because the same
    grammar is needed where a number is WRITTEN and not only where it is
    compared. `beadloom-0mdo.53` reads it at bead-CREATION time, which is where
    the divergence BDL-UX #171 describes is created and where there is no
    allocated id to compare against yet; this module reads it afterwards, which
    is where the divergence is detected. One grammar read twice, which is the
    rule `beadloom-0mdo.51` applied when it deleted the merge-slot regex from a
    second module.
    """
    return tuple(match.group(0) for match in _TITLE_REFERENCE.finditer(text))


def title_id_mismatches(records: Sequence[BeadRecord]) -> tuple[tuple[str, str], ...]:
    """Every ``(bead_id, reference)`` where a bead's title numbers it differently.

    This is BDL-UX #171, and the comparison it needs was already in hand: the
    command holds the id the tracker ALLOCATED and the id the author WROTE INTO
    THE TITLE, and never compared them. In #171 the coordinator authored two
    beads as ``.39`` and ``.40``, a concurrent agent took ``.39`` first, and the
    two landed as ``.40`` and ``.41`` still carrying the old numbers in their
    titles — after which ``bd dep add`` built a real, valid, WRONG edge that only
    a human reading the echoed titles caught.

    Only the trailing number is compared. The prefixes deliberately differ (the
    title convention is ``BDL-061.<n>``, the tracker's id is
    ``beadloom-mr2l.<n>``), so comparing whole ids would report every bead in the
    project and comparing prefixes would report none of them.
    """
    found: list[tuple[str, str]] = []
    for record in sorted(records, key=lambda r: r.bead_id):
        allocated = _ID_SUFFIX.search(record.bead_id)
        title = record.title or record.declaration.split("\n", 1)[0]
        for match in _TITLE_REFERENCE.finditer(title):
            written = match.group(2)
            if allocated is not None and written == allocated.group(1):
                continue
            found.append((record.bead_id, match.group(0)))
    return tuple(found)


def _check_tracker_ids(records: Sequence[BeadRecord]) -> MediumCheck:
    """Whether every bead's title numbers it the way the tracker did.

    Checked whether or not the plan is concurrent, and that is deliberate. The
    mis-wiring in #171 happened at bead CREATION, before any wave ran, so a plan
    that serialises the beads it mis-wired is exactly the plan whose ids most
    need checking. Since BDL-UX #228 every other check is unconditional too, so
    this one is no longer the exception it was written as.
    """
    mismatches = title_id_mismatches(records)
    if not mismatches:
        return MediumCheck(
            MEDIUM_TRACKER_IDS,
            STATUS_PASSED,
            "every bead's title agrees with the number the tracker allocated",
        )
    named = "; ".join(f"{bead} is titled {ref}" for bead, ref in mismatches)
    return MediumCheck(
        MEDIUM_TRACKER_IDS,
        STATUS_FAILED,
        f"{len(mismatches)} bead(s) carry a number their id does not have — "
        f"{named}. Verify every dependency edge against the titles the tracker "
        "echoes, not against the ids you intended (BDL-UX #171)",
    )


def _check_working_tree(
    environment: WaveEnvironment, owned: frozenset[str]
) -> MediumCheck:
    """Whether the tree the wave starts from carries work no bead in it owns.

    #181 is not that the tree was dirty — it is that four clean-room greens were
    each measured over their own files while the combination was never measured
    at all. A path already changed in the shared tree and owned by no bead in the
    plan is in exactly that position from the first minute: no bead's clean room
    contains it, and the gate owner meets it at the end.
    """
    if environment.tree_changed_paths is None:
        return MediumCheck(
            MEDIUM_WORKING_TREE,
            STATUS_UNMEASURED,
            "git could not answer what differs from HEAD, so the tree this wave "
            "starts from is unknown — it is not known to be clean",
        )
    unowned = tuple(sorted(set(environment.tree_changed_paths) - owned))
    if not unowned:
        return MediumCheck(
            MEDIUM_WORKING_TREE,
            STATUS_PASSED,
            "every path that differs from HEAD is inside a bead of this plan",
        )
    shown = ", ".join(unowned[:5]) + (" ..." if len(unowned) > 5 else "")
    return MediumCheck(
        MEDIUM_WORKING_TREE,
        STATUS_FAILED,
        f"{len(unowned)} path(s) differ from HEAD and are owned by no bead in "
        f"this plan ({shown}) — no bead's clean room contains them, so only the "
        "gate owner's tree run will meet them (BDL-UX #181)",
    )


def _check_commit_gate(environment: WaveEnvironment) -> MediumCheck:
    """Whether the hook that will judge this wave's commits judges the commit.

    An installed hook keeps its old behaviour until ``beadloom install-hooks`` is
    re-run, and nothing tells the repository to — measured on this project's own
    S6 commit, which was judged by the whole-tree hook the change had just
    replaced. A whole-tree hook fails one agent's commit on a neighbour's
    half-written file (BDL-UX #118), so a concurrent wave planned over one is
    planned over a gate that will misfire.
    """
    if environment.commit_gate is None:
        return MediumCheck(
            MEDIUM_COMMIT_GATE,
            STATUS_UNMEASURED,
            "the installed pre-commit hook could not be read, so what it judges "
            "is unknown",
        )
    if environment.commit_gate == GATE_COMMIT_SCOPED:
        return MediumCheck(
            MEDIUM_COMMIT_GATE,
            STATUS_PASSED,
            "the installed pre-commit hook judges the paths a commit stages",
        )
    if environment.commit_gate == GATE_ABSENT:
        return MediumCheck(
            MEDIUM_COMMIT_GATE,
            STATUS_FAILED,
            "no pre-commit hook is installed, so no gate judges these commits at "
            "all — run `beadloom install-hooks`",
        )
    return MediumCheck(
        MEDIUM_COMMIT_GATE,
        STATUS_FAILED,
        "the installed pre-commit hook judges the whole tree, so one bead's "
        "commit will be failed by a neighbour's in-progress work — re-run "
        "`beadloom install-hooks` to pick up the commit-scoped hook (BDL-UX #118)",
    )


def _check_doc_baseline(environment: WaveEnvironment) -> MediumCheck:
    """Whether the doc baseline this wave inherits is already reconciled.

    A wave that starts with pairs already stale hands its doc pass drift it
    cannot attribute: the pass cannot tell what this wave moved from what was
    moved before it. Since `beadloom-mr2l.78` the freshness fact is recorded per
    FILE, so the inherited drift is at least attributable to a file once it is
    reconciled — which is exactly why reconciling it BEFORE the wave starts is
    now worth requiring (BDL-UX #133, #182).
    """
    if environment.doc_baseline_stale_pairs is None:
        return MediumCheck(
            MEDIUM_DOC_BASELINE,
            STATUS_UNMEASURED,
            "the doc baseline was not evaluated, so what this wave inherits is "
            "unknown",
        )
    if environment.doc_baseline_stale_pairs == 0:
        return MediumCheck(
            MEDIUM_DOC_BASELINE,
            STATUS_PASSED,
            "no doc pair is stale before the wave starts",
        )
    return MediumCheck(
        MEDIUM_DOC_BASELINE,
        STATUS_FAILED,
        f"{environment.doc_baseline_stale_pairs} doc pair(s) are already stale — "
        "this wave's doc pass cannot tell its own drift from what it inherited "
        "(BDL-UX #133, #182)",
    )


def _check_landing_order(environment: WaveEnvironment) -> MediumCheck:
    """Whether every place this flow instructs the lock instructs the form that grants it.

    The medium is the branch a wave lands into, and the precondition is not about
    the tracker: ``bd merge-slot acquire`` refuses a held slot and exactly one of
    thirty-two simultaneous acquires won, measured on bd 1.0.4. What grants
    nothing is the CALL FORM the artifacts instruct, and that is a fact about
    files this project owns — which is why it is checkable here and why BDL-UX
    #194 and #237 were both filed against something nobody could fix.

    A verdict over an empty population says so. This project has never scaffolded
    a flow into a directory where the lock is instructed nowhere, but an adopter
    has, and a pass that only means *we found nothing to judge* is the silence
    this whole module exists to break.
    """
    sites = environment.landing_lock_sites
    if sites is None:
        return MediumCheck(
            MEDIUM_LANDING_ORDER,
            STATUS_UNMEASURED,
            "the flow artifacts were not read, so what this wave's agents are "
            f"told about `{LOCK_COMMAND}` is unknown",
        )
    if not sites:
        return MediumCheck(
            MEDIUM_LANDING_ORDER,
            STATUS_PASSED,
            f"no flow artifact instructs `{LOCK_COMMAND}`, so nothing tells an "
            "agent it holds a lock it does not hold — the landings of this wave "
            "are serialised by its derived scopes and by nothing else",
        )
    defective = tuple(site for site in sites if site.defects)
    if not defective:
        return MediumCheck(
            MEDIUM_LANDING_ORDER,
            STATUS_PASSED,
            f"all {len(sites)} instruction(s) of `{LOCK_COMMAND}` name the "
            "holder, so a hold names a bead and a release cannot free a "
            "neighbour's",
        )
    named = "; ".join(
        f"{site.source}:{site.line} `{site.invocation}` ({', '.join(site.defects)})"
        for site in defective[:3]
    ) + (" ..." if len(defective) > 3 else "")
    reasons = "; ".join(
        defect_detail(defect)
        for defect in sorted({d for site in defective for d in site.defects})
    )
    return MediumCheck(
        MEDIUM_LANDING_ORDER,
        STATUS_FAILED,
        f"{len(defective)} of {len(sites)} instruction(s) of `{LOCK_COMMAND}` "
        f"grant an agent nothing it is told they grant — {named}. {reasons} "
        "(BDL-UX #194, #237)",
    )


def _check_focus_document(
    environment: WaveEnvironment, records: Sequence[BeadRecord]
) -> MediumCheck:
    """Whether the document every bead of this plan writes gives each of them a row.

    The medium is shared by construction and cannot be planned away, so the
    precondition is not *do these beads share it* — they do — but whether the
    document gives each of them a place of its own to write in. A bead the
    document carries no row for has only the shared prose, and that is where a
    hunk written by one bead lands inside another bead's commit (BDL-UX #257).

    Read with the reader that already exists.
    :func:`~beadloom.application.active_table.names_bead` is how ``active-sync``
    decides which bead a row names, in both the full form the tracker allocates
    and the short form a table abbreviates it to, under whatever Markdown the
    author wrapped it in. A second reader of that one fact is the defect
    ``beadloom-0mdo.46`` lifted ``doc_sync/tables.py`` to stop happening a third
    time.

    **A bead named in ANY focus document counts as named.** The population is
    every work item's focus document rather than this plan's own, because the
    plan does not carry a work item id and deriving one would be a second source
    for a fact ``declared-scope`` already owns. The looseness can only turn a
    failure into a pass, and only for a wave whose beads span two work items —
    which would not collide in one document anyway.
    """
    documents = environment.focus_documents
    if documents is None:
        return MediumCheck(
            MEDIUM_FOCUS_DOCUMENT,
            STATUS_UNMEASURED,
            "the flow's routing and its planning documents were not read, so "
            "which document every bead of this plan writes into is unknown",
        )
    if not documents:
        return MediumCheck(
            MEDIUM_FOCUS_DOCUMENT,
            STATUS_PASSED,
            "no work item of this project holds a document every route writes, "
            "so this plan's beads share no focus document — their landings are "
            "serialised by the derived scopes above and by nothing else",
        )
    cells = tuple(cell for document in documents for cell in document.row_cells)
    missing = tuple(
        sorted(
            record.bead_id
            for record in records
            if not any(names_bead(cell, record.bead_id) for cell in cells)
        )
    )
    where = ", ".join(sorted({document.path for document in documents})[:3])
    if not missing:
        return MediumCheck(
            MEDIUM_FOCUS_DOCUMENT,
            STATUS_PASSED,
            f"all {len(records)} bead(s) of this plan are named by a row of the "
            f"{len(documents)} focus document(s) read, so each writes a line of "
            "its own rather than the prose around it",
        )
    named = ", ".join(missing)
    return MediumCheck(
        MEDIUM_FOCUS_DOCUMENT,
        STATUS_FAILED,
        f"{len(missing)} of {len(records)} bead(s) of this plan write into a "
        f"focus document no row of it names — {named}. The document is owned by "
        f"no bead's code, so the serialisation count above did not compare it; "
        f"give each bead a row in {where} before the wave starts, or its edit "
        "lands in the shared prose and is committed by whoever gets there first "
        "(BDL-UX #257)",
    )


def check_media(
    records: Sequence[BeadRecord],
    *,
    owned_paths: frozenset[str] = frozenset(),
    environment: WaveEnvironment | None = None,
) -> tuple[MediumCheck, ...]:
    """One verdict per shared medium, in the order :mod:`.media` states them.

    Every medium is checked at every wave size (BDL-UX #228). The first version
    reported the three that carry state between beads as ``not_applicable``
    whenever no wave held more than one bead, and that read the width of ONE
    plan as solitude. It is not: a plan is one slice of one epic, and
    :func:`_check_working_tree` exists precisely to report paths that differ from
    ``HEAD`` and are owned by no bead in the plan — work from outside it, in the
    same tree, judged by the same hook, against the same doc baseline. Measured
    against the consequence: roughly twenty single-bead waves ran across two
    epics, and the instrument was silent in all of them.
    """
    observed = environment or WaveEnvironment()
    return (
        _check_working_tree(observed, owned_paths),
        _check_commit_gate(observed),
        _check_landing_order(observed),
        _check_focus_document(observed, records),
        _check_doc_baseline(observed),
        _check_tracker_ids(records),
    )


def finding_for(check: MediumCheck) -> str | None:
    """The finding line *check* contributes, or ``None`` when it contributes none.

    Spelled here rather than at the planner's call site for the reason the
    serialisation reasons are named constants: a verdict spelled where it is used
    becomes several spellings of one fact.
    """
    if check.status == STATUS_FAILED:
        return f"medium_failed: {check.medium} — {check.detail}"
    if check.status == STATUS_UNMEASURED:
        return f"medium_unmeasured: {check.medium} — {check.detail}"
    return None
