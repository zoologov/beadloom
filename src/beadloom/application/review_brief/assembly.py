"""Assemble the reviewer's input from the graph, the change and the tracker.

One responsibility: turn a bead into the three things a reviewer needs before it
forms a judgement — the assignment, the specification, the change — and turn the
author's comments into a count. Whether that count may later become text is
:mod:`beadloom.application.review_brief.release`'s decision, not this module's,
and what the reviewer can reach through channels this command does not control
is :mod:`beadloom.application.review_brief.reachability`'s.

The bead's scope is resolved by :func:`beadloom.application.waves.resolve_scope`
rather than by a parser of this module's own. A bead declares its scope in one
grammar, and a second reader of that grammar is the two-sources-of-truth defect
this epic has already met three times (BDL-UX #171, #177, #179).

**Ownership decides "outside the declared scope", not the file index.** A file
added by the change under review is not in the index yet, so asking the index
would report every new file as unowned and the check would be blind to exactly
the change it exists to look at. :func:`get_owning_ref_id` answers from the
nodes' declared sources, which a new file matches the moment it is written.
"""

# beadloom:feature=review-brief

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.review_brief.models import (
    FINDING_AMBIGUOUS_SCOPE,
    FINDING_NO_SCENARIO,
    FINDING_NO_SCOPE,
    FINDING_OUTSIDE_SCOPE,
    FINDING_UNKNOWN_REF,
    FINDING_UNMEASURED_CHANGE,
    BoundScenario,
    ChangedFile,
    ReviewBrief,
    SpecDocument,
    WithheldNotes,
)
from beadloom.application.review_brief.reachability import reachability_of
from beadloom.application.waves import (
    UNRESOLVED_NO_DECLARATION,
    remedy_for,
    resolve_scope,
)
from beadloom.infrastructure.repository import get_docs_for_ref, get_owning_ref_id

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from beadloom.application.review_brief.models import AuthorNote, Commit
    from beadloom.application.waves import BeadRecord
    from beadloom.graph.scenarios import Scenario


def _spec_documents(conn: sqlite3.Connection, refs: Iterable[str]) -> tuple[SpecDocument, ...]:
    """Every document the graph binds to *refs*, sorted so a report is stable."""
    documents = [
        SpecDocument(ref=ref, path=path, kind=kind)
        for ref in sorted(refs)
        for path, kind in get_docs_for_ref(conn, ref)
    ]
    return tuple(sorted(documents, key=lambda doc: (doc.path, doc.ref)))


def _change_inventory(
    conn: sqlite3.Connection, changed_paths: Iterable[str], refs: frozenset[str]
) -> tuple[ChangedFile, ...]:
    """Each changed path with its owning node, and whether the bead declared it."""
    inventory = []
    for path in sorted(changed_paths):
        owner = get_owning_ref_id(conn, path)
        inventory.append(
            ChangedFile(path=path, owner=owner, in_scope=owner is not None and owner in refs)
        )
    return tuple(inventory)


def _bound_scenarios(
    scenarios: Iterable[Scenario], bead_id: str
) -> tuple[BoundScenario, ...]:
    """The scenarios whose ``@bead:`` tag names *bead_id*, in file order."""
    return tuple(
        BoundScenario(name=item.name, path=item.path, line=item.line)
        for item in scenarios
        if bead_id in item.beads
    )


def assemble_brief(
    conn: sqlite3.Connection,
    record: BeadRecord,
    *,
    assignment: str,
    changed_paths: frozenset[str] | None,
    measured_since: str = "",
    notes: Sequence[AuthorNote] = (),
    scenarios: Sequence[Scenario] = (),
    project_root: Path | None = None,
    branch: str | None = None,
    commits: Sequence[Commit] | None = None,
) -> ReviewBrief:
    """The reviewer's input for *record*, with the author's comments withheld.

    ``assignment`` is passed separately from ``record.declaration`` because the
    two strings answer different questions. The declaration is everything the
    bead says about itself, including the ``notes`` field, and it exists so the
    ``refs:`` TOKEN can be found wherever the author happened to write it — this
    epic's own beads put it in ``notes`` as often as in the description. The
    assignment is what the bead was ASKED to do, and a caller composes it from
    the title and the description alone, because ``notes`` is also where a dev
    appends progress and handing that over is the advocacy this command withholds.

    ``changed_paths`` is ``None`` when the change could not be measured — no
    repository, no such base ref, no git. That is reported as a finding and never
    as an empty change set: "nothing changed" and "nobody looked" reaching the
    reviewer as the same brief is the silent false-green this command exists to
    remove.

    ``project_root``, ``branch`` and ``commits`` are what the REACHABILITY
    statement is derived from, and each absence is reported as itself rather
    than as an empty channel. ``commits`` follows ``changed_paths``' convention:
    ``None`` is *git gave no answer*, and an empty sequence is *the range holds
    no commits*, which are two different facts about what a reviewer can read.

    ``measured_since`` is the ref the caller measured that change against, and it
    is required by the ``changed-outside-scope`` finding rather than by the
    inventory. The change is everything the BRANCH did, not everything the BEAD
    did — no per-bead attribution exists in the commits — so on a branch carrying
    five beads all five briefs report the same files and four of them would
    otherwise accuse a bead of a sibling's work (BDL-061.23 M8). The finding names
    its window instead of claiming an attribution it cannot make.
    """
    scope = resolve_scope(conn, record)
    findings: list[str] = []
    if scope.unresolved == UNRESOLVED_NO_DECLARATION:
        findings.append(FINDING_NO_SCOPE)
    elif scope.unresolved is not None and not scope.unknown_refs:
        # Every OTHER way the declaration could not be read: written inside a
        # sentence, or naming a second ref the parser had to throw away. Both are
        # findings here for the same reason they serialise the bead in a wave —
        # the reviewer is being handed a scope that is narrower than the bead's.
        findings.append(
            f"{FINDING_AMBIGUOUS_SCOPE}: {scope.unresolved} — "
            f"{remedy_for(scope.unresolved)}"
        )
    if scope.unknown_refs:
        findings.append(f"{FINDING_UNKNOWN_REF}: {', '.join(scope.unknown_refs)}")

    if changed_paths is None:
        findings.append(FINDING_UNMEASURED_CHANGE)
        inventory: tuple[ChangedFile, ...] = ()
    else:
        inventory = _change_inventory(conn, changed_paths, scope.refs)
        outside = [item.path for item in inventory if item.owner is not None and not item.in_scope]
        if outside:
            findings.append(
                f"{FINDING_OUTSIDE_SCOPE}: measured over the branch since "
                f"{measured_since or 'the base ref'}, so a sibling bead's file "
                f"appears here too — {', '.join(outside)}"
            )

    bound = _bound_scenarios(scenarios, record.bead_id)
    if not bound:
        findings.append(FINDING_NO_SCENARIO)

    return ReviewBrief(
        bead_id=record.bead_id,
        title=record.title,
        assignment=assignment,
        measured_since=measured_since,
        refs=tuple(sorted(scope.refs)),
        unknown_refs=scope.unknown_refs,
        docs=_spec_documents(conn, scope.refs),
        changed=inventory,
        change_measured=changed_paths is not None,
        scenarios=bound,
        withheld=WithheldNotes(count=len(notes)),
        reachability=reachability_of(
            notes=notes,
            project_root=project_root,
            branch=branch,
            commits=commits,
            since=measured_since,
            bead_id=record.bead_id,
        ),
        findings=tuple(findings),
    )
