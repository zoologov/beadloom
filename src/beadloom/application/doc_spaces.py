# beadloom:domain=application
# beadloom:component=doc-spaces
"""Hold an epic's recorded intent against the documentation of reality.

The claim this module makes checkable is *"the intent recorded in TO-BE is
reflected in AS-IS"*. It is deliberately a **relation between two artifacts**
rather than a flag on one: nothing here marks a PRD "done", because a planning
document stays the record of what was intended and a *different* document — the
node's AS-IS documentation — is what gets updated when reality moves. A status
field on the planning document could not express that, and could not be verified
against anything.

The join, and why it is a declaration rather than an inference
--------------------------------------------------------------
An epic's ``CONTEXT.md`` (or a task's ``BRIEF.md``) carries a *Related Files*
section naming the graph nodes the work touches. That list is a **declaration**,
so the relation is read from it and from nothing else. Scanning the whole
document for backticked tokens that happen to be ref ids was measured first and
rejected: on this repository it attributed the node ``status`` to nine epics
whose documents merely used the English word, which is the false-positive class
BDL-UX #169 and #190 already record against the audit scanner.

The consequence is stated rather than hidden: an epic that declares no node is
**unresolved**, counted in its own bucket, and never silently counted as clean.
An absent declaration is not evidence of anything (this epic's `.57`), and a
denominator that shrinks without saying why is BDL-UX #174's equation.

What is checked, and what is not
--------------------------------
One leg: an epic with at least one closed bead that declares node *X*, where *X*
has **no AS-IS document at all**. Intent was recorded, the work finished, and
reality was never written down.

Deliberately NOT a second leg on staleness. ``sync-check`` already holds every
AS-IS document against its code and reports the stale ones by name; a second
check saying the same thing from a different angle would double one finding and
make the count of real problems unreadable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from beadloom.infrastructure.doc_roots import (
    SPACE_TO_BE,
    SPACE_WORKING,
    SPACES,
    DocSpaces,
    resolve_doc_spaces,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

#: An epic declared a node whose reality was never documented.
FINDING_NO_AS_IS = "intent_without_as_is"

#: The graph declares a WORKING document as a node's documentation, while the
#: configuration declares that document exempt from freshness. Two artifacts
#: disagree about what the file is, which is what makes a wrong declaration
#: DETECTABLE rather than merely believed.
FINDING_WORKING_CONTRADICTED = "working_declaration_contradicted"

#: The WORKING exemption matched no document — declared and excusing nothing.
FINDING_WORKING_INERT = "working_exemption_inert"

#: The ``doc_roots`` block could not be read as written.
FINDING_CONFIG = "doc_roots_config"

#: An epic that declares nodes, whose completion the tracker cannot resolve.
#: Unverifiable, and therefore reported rather than skipped: ``bd close`` writes
#: only the local database, so an epic leaves ``.beads/issues.jsonl`` by ordinary
#: use and its intent-to-reality relation stops being checked with nothing said.
FINDING_EPIC_NOT_IN_TRACKER = "epic_not_in_tracker"

#: Which tracker answered. Named rather than implied, because the command
#: prefers the live ``bd`` database and the gate reads the committed export, so
#: the two can differ on one tree at one moment (BDL-UX #171's shape) and a
#: difference nobody prints is a difference nobody can act on.
TRACKER_BD = "bd list --all --json"
TRACKER_EXPORT = ".beads/issues.jsonl"

#: No tracker answered at all — a whole missing denominator, one global cause.
TRACKER_UNREADABLE = "no tracker was readable"

#: A planning document that exists and cannot be decoded. A finding ABOUT the
#: document, rather than the silent loss of the epic that owns it: the handler
#: is as wide as the call and says what it could not read (the ledger `.68`
#: built, and `.14`'s BDL-061.14-3 on the reference leg).
FINDING_INTENT_UNREADABLE = "intent_document_unreadable"

#: Why an epic declared no node. Three situations, and blurring them is how a
#: denominator shrinks without saying so: the document was read and declares
#: nothing, the directory carries no intent document at all, or the document is
#: there and cannot be decoded.
UNRESOLVED_NO_NODE_DECLARED = "no_node_declared"
UNRESOLVED_NO_INTENT_DOCUMENT = "no_intent_document"
UNRESOLVED_UNREADABLE_INTENT = "unreadable_intent_document"

#: Headings under which an epic declares the nodes it touches.
_RELATED_HEADINGS = ("related file", "related code", "primary ref")

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*$")
_TICKED_RE = re.compile(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`")


@dataclass(frozen=True)
class SpaceFinding:
    """One reported disagreement, in the shape the gate and ``--json`` share."""

    rule: str
    path: str
    line: int
    why: str
    remediation: str


@dataclass(frozen=True)
class EpicIntent:
    """One epic's recorded intent: where it is, what it declares, how far it got.

    ``bead_statuses`` is ``None`` when the tracker could not resolve this epic,
    and ``unknown_status_reason`` says which of the two ways that happened: the
    tracker answered nothing at all (:data:`TRACKER_UNREADABLE`), or it answered
    and does not name this epic (the source it was read from). They are
    different facts and were one empty tuple before — "the export has no record
    of this epic" and "this epic's beads are all open" both skipped, and only
    the second an honest skip. A skip always says why.
    """

    key: str
    path: str
    declared_refs: tuple[tuple[str, int], ...]
    bead_statuses: tuple[str, ...] | None
    unknown_status_reason: str | None = None
    unresolved_reason: str | None = None
    """Why this epic declares no node, or ``None`` when it declares one.

    A directory holding intent that carries no readable intent document used to
    be appended to nothing at all — absent from ``epics``, from
    ``unresolved_epics`` and from every NOT CHECKED line — while its documents
    stayed in the TO-BE population, so one report stated two sizes for one tree.
    It is unresolved WITH A REASON now, which is the shape `.17` had already
    applied one layer up.
    """

    @property
    def has_closed_bead(self) -> bool:
        """Whether the tracker shows at least one closed bead for this epic."""
        return bool(self.bead_statuses) and any(
            s == "closed" for s in self.bead_statuses or ()
        )


@dataclass(frozen=True)
class SpacesReport:
    """What each space contains, and where intent did not reach reality."""

    populations: Mapping[str, int]
    epics: int
    epics_with_closed_beads: int
    epics_declaring_nodes: int
    epics_declaring_nothing: int
    epics_without_bead_status: int
    refs_checked: int
    working_documents: int
    working_exempt: bool
    working_reason: str
    findings: tuple[SpaceFinding, ...] = ()
    unresolved_epics: tuple[str, ...] = ()
    unresolved_reasons: Mapping[str, str] = MappingProxyType({})
    """Why each unresolved epic is unresolved, keyed by epic key."""
    epics_unknown_to_tracker: tuple[str, ...] = ()
    """Epics a READABLE tracker does not name, by key.

    Empty when no tracker answered at all: that is one global cause, reported
    once, and a name per epic would say the same thing as many times as there
    are epics.
    """

    @property
    def relation_checked(self) -> bool:
        """Whether the relation had anything at all to relate.

        A relation check over an empty population reports nothing and reads
        exactly like one that found no problem — the vacuity this epic's `.48`
        and `.68` both exist to make visible.
        """
        return self.refs_checked > 0


# ---------------------------------------------------------------------------
# Reading intent off disk
# ---------------------------------------------------------------------------


def _related_refs(text: str, known_refs: frozenset[str]) -> list[tuple[str, int]]:
    """Ref ids a document DECLARES under its related-files heading.

    Scoped to the section, deliberately. The unscoped version of this function
    was written, measured on 60 epics and thrown away; the scoped one is the
    difference between reading a declaration and guessing from prose.
    """
    found: list[tuple[str, int]] = []
    seen: set[str] = set()
    in_section = False
    for number, line in enumerate(text.splitlines(), start=1):
        heading = _HEADING_RE.match(line)
        if heading is not None:
            title = heading.group(1).lower()
            in_section = any(word in title for word in _RELATED_HEADINGS)
            continue
        if not in_section:
            continue
        for match in _TICKED_RE.finditer(line):
            ref = match.group(1)
            if ref in known_refs and ref not in seen:
                seen.add(ref)
                found.append((ref, number))
    return found


def _bead_statuses(
    key: str,
    beads_by_epic: Mapping[str, tuple[str, ...]] | None,
    tracker_source: str,
) -> tuple[tuple[str, ...] | None, str | None]:
    """This epic's bead statuses, or ``None`` and the reason they are unknown.

    ``beads_by_epic.get(key, ())`` was the defect: it answered the empty tuple
    for an epic the tracker never heard of and for one whose beads are all open,
    and only the second is an honest skip. An epic the export forgot is
    UNVERIFIABLE, not compliant.
    """
    if beads_by_epic is None:
        return None, TRACKER_UNREADABLE
    statuses = beads_by_epic.get(key)
    if statuses is None:
        return None, tracker_source
    return statuses, None


def read_epic_intents(
    project_root: Path,
    *,
    spaces: DocSpaces,
    known_refs: frozenset[str],
    beads_by_epic: Mapping[str, tuple[str, ...]] | None,
    tracker_source: str = TRACKER_EXPORT,
) -> list[EpicIntent]:
    """Every TO-BE directory, with the nodes its intent document declares.

    **An epic is a directory that holds a TO-BE document**, and nothing narrower.
    It was "a directory carrying an intent document" and the difference was four
    of this repository's 61 directories, in NO field of the report — not
    ``epics``, not ``unresolved_epics``, not a NOT CHECKED line — while their
    documents stayed in the TO-BE population. One report, two sizes, one tree.

    An epic whose document declares nothing is unresolved rather than absent, and
    so is one whose directory carries no readable intent document at all; each
    carries its own reason. Filtering the first out was the original
    implementation and it was wrong in the way this epic keeps meeting: it
    removed 34 of 57 epics from the denominator and the report then said "16 of
    23", which reads like coverage of two thirds where the real figure is under
    a third. Absence is not evidence, and a denominator that shrinks without
    saying why is BDL-UX #174's equation.
    """
    directories: dict[Path, None] = {}
    for path in spaces.documents_in(project_root, SPACE_TO_BE):
        directories.setdefault(path.parent, None)
    intents: list[EpicIntent] = []
    for directory in directories:
        key = directory.name
        statuses, unknown = _bead_statuses(key, beads_by_epic, tracker_source)
        declaration = _read_declaration(directory, spaces, known_refs)
        intents.append(
            EpicIntent(
                key=key,
                path=_relative(declaration.path, project_root),
                declared_refs=declaration.refs,
                bead_statuses=statuses,
                unknown_status_reason=unknown,
                unresolved_reason=declaration.unresolved_reason,
            )
        )
    return sorted(intents, key=lambda i: i.key)


@dataclass(frozen=True)
class _Declaration:
    """What a directory's intent document declares, and where that was read."""

    path: Path
    refs: tuple[tuple[str, int], ...]
    unresolved_reason: str | None


def _read_declaration(
    directory: Path, spaces: DocSpaces, known_refs: frozenset[str]
) -> _Declaration:
    """The nodes *directory*'s intent document declares, or why there are none.

    Three outcomes, kept apart because they call for three different actions:
    the document was read and names nodes; it was read and names none; or there
    is no readable intent document, either because the directory carries none of
    the configured names or because the one it carries cannot be decoded.
    """
    for name in spaces.intent_documents:
        candidate = directory / name
        if not candidate.is_file():
            continue
        text = _read(candidate)
        if text is None:
            return _Declaration(candidate, (), UNRESOLVED_UNREADABLE_INTENT)
        refs = tuple(_related_refs(text, known_refs))
        return _Declaration(
            candidate, refs, None if refs else UNRESOLVED_NO_NODE_DECLARED
        )
    return _Declaration(directory, (), UNRESOLVED_NO_INTENT_DOCUMENT)


def _read(path: Path) -> str | None:
    """*path* as text, or ``None`` when it cannot be decoded.

    A planning document is a UTF-8 contract, so a decode failure is a real answer
    about the document rather than a reason to abandon the run — the handler is
    as wide as the call, which is the ledger `.68` built.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# The relation
# ---------------------------------------------------------------------------


def check_spaces(
    project_root: Path,
    *,
    spaces: DocSpaces,
    known_refs: frozenset[str],
    documented_refs: frozenset[str],
    declared_doc_paths: frozenset[str],
    beads_by_epic: Mapping[str, tuple[str, ...]] | None,
    tracker_source: str = TRACKER_EXPORT,
) -> SpacesReport:
    """Classify every document, then hold declared intent against the AS-IS space.

    Every input the graph supplies arrives as an argument. ``doc_spaces`` reads
    no database of its own so the relation can be exercised against a project
    that is not this one — the axis :mod:`tests.adopter_project` exists for.
    """
    populations = {
        space: len(spaces.documents_in(project_root, space)) for space in SPACES
    }
    working_docs = spaces.working_documents(project_root)
    populations[SPACE_WORKING] = len(working_docs)

    intents = read_epic_intents(
        project_root,
        spaces=spaces,
        known_refs=known_refs,
        beads_by_epic=beads_by_epic,
        tracker_source=tracker_source,
    )
    findings: list[SpaceFinding] = [
        SpaceFinding(
            rule=FINDING_CONFIG,
            path=".beadloom/config.yml",
            line=0,
            why=error,
            remediation="correct the `doc_roots` block; the shipped defaults are in use meanwhile",
        )
        for error in spaces.config_errors
    ]
    findings.extend(_working_findings(spaces, working_docs, declared_doc_paths, project_root))

    checked = 0
    declaring = 0
    no_status = 0
    unresolved: list[str] = []
    unresolved_reasons: dict[str, str] = {}
    unknown_to_tracker: list[str] = []
    with_closed = 0
    for intent in intents:
        if intent.bead_statuses is None:
            no_status += 1
        if intent.declared_refs:
            declaring += 1
        else:
            unresolved.append(intent.key)
            unresolved_reasons[intent.key] = (
                intent.unresolved_reason or UNRESOLVED_NO_NODE_DECLARED
            )
        if intent.unresolved_reason == UNRESOLVED_UNREADABLE_INTENT:
            findings.append(_unreadable_intent(intent))
        if intent.unknown_status_reason not in (None, TRACKER_UNREADABLE):
            unknown_to_tracker.append(intent.key)
            if intent.declared_refs:
                findings.append(_unverifiable_epic(intent))
        if not intent.has_closed_bead:
            continue
        with_closed += 1
        for ref, line in intent.declared_refs:
            checked += 1
            if ref in documented_refs:
                continue
            findings.append(
                SpaceFinding(
                    rule=FINDING_NO_AS_IS,
                    path=intent.path,
                    line=line,
                    why=(
                        f"epic {intent.key} declares the node `{ref}` and has closed "
                        f"beads, but `{ref}` has no AS-IS document — the intent was "
                        f"recorded and reality was never written down"
                    ),
                    remediation=(
                        f"add a document to `{ref}`'s `docs:` list and pair it with the "
                        f"code, or remove `{ref}` from this epic's related files if the "
                        f"work never touched it"
                    ),
                )
            )
    return SpacesReport(
        populations=populations,
        epics=len(intents),
        epics_with_closed_beads=with_closed,
        epics_declaring_nodes=declaring,
        epics_declaring_nothing=len(unresolved),
        epics_without_bead_status=no_status,
        refs_checked=checked,
        working_documents=len(working_docs),
        working_exempt=spaces.working.exempt_from_freshness,
        working_reason=spaces.working.reason,
        findings=tuple(findings),
        unresolved_epics=tuple(sorted(unresolved)),
        unresolved_reasons=MappingProxyType(dict(sorted(unresolved_reasons.items()))),
        epics_unknown_to_tracker=tuple(sorted(unknown_to_tracker)),
    )


#: How each non-default unresolved reason reads in a summary line.
_UNRESOLVED_SAID: Mapping[str, str] = MappingProxyType(
    {
        UNRESOLVED_NO_INTENT_DOCUMENT: "carry no readable intent document",
        UNRESOLVED_UNREADABLE_INTENT: "carry one that could not be decoded",
    }
)


def describe_unresolved(reasons: Mapping[str, str]) -> str:
    """The unresolved bucket's composition, when it holds more than one case.

    A directory that carries no readable intent document is not an epic whose
    author forgot to declare a node; it is a directory that is not an epic at
    all. Both are honestly unresolved, and a single count of 56 tells a reader
    which of them they are looking at only by accident. Empty when every
    unresolved epic is the ordinary case, so the everyday line keeps its shape.

    Shared by the gate and the command so one bucket cannot be described two
    ways — the shape `beadloom-mr2l.75` had to repair one layer down.
    """
    counts: dict[str, int] = {}
    for reason in reasons.values():
        if reason != UNRESOLVED_NO_NODE_DECLARED:
            counts[reason] = counts.get(reason, 0) + 1
    if not counts:
        return ""
    parts = [
        f"{count} {_UNRESOLVED_SAID.get(reason, reason)}"
        for reason, count in sorted(counts.items())
    ]
    return f" ({', '.join(parts)})"


def _unreadable_intent(intent: EpicIntent) -> SpaceFinding:
    """A planning document that exists and cannot be decoded.

    Unlike a directory that carries no intent document — which is a directory
    that is not an epic, and no defect — a document that is there and unreadable
    is a defect in that document. Reporting it is the difference between naming
    the file and losing the epic.
    """
    return SpaceFinding(
        rule=FINDING_INTENT_UNREADABLE,
        path=intent.path,
        line=0,
        why=(
            f"epic {intent.key}'s intent document is not valid UTF-8, so the nodes "
            f"it declares could not be read and its intent was held against nothing"
        ),
        remediation=(
            "re-save the document as UTF-8 — a planning document is a UTF-8 "
            "contract, and a decode failure is a fact about the file rather than "
            "a reason to drop the epic that owns it"
        ),
    )


def _unverifiable_epic(intent: EpicIntent) -> SpaceFinding:
    """An epic that declares nodes and whose completion the tracker cannot say.

    Reported only when the epic DECLARES something. An epic that declares no
    node is already counted and named in its own bucket, and reporting it a
    second time under another name would say one thing twice.
    """
    return SpaceFinding(
        rule=FINDING_EPIC_NOT_IN_TRACKER,
        path=intent.path,
        line=0,
        why=(
            f"epic {intent.key} declares "
            f"{len(intent.declared_refs)} node(s) and "
            f"`{intent.unknown_status_reason}` has no record of it, so whether its "
            f"work finished is unknown and its intent was held against nothing"
        ),
        remediation=(
            "sync the tracker export (`bd close` writes only the local database, "
            "so a closed bead reaches `.beads/issues.jsonl` only when the export "
            "is committed), or remove the planning directory if the epic never ran"
        ),
    )


def _working_findings(
    spaces: DocSpaces,
    working_docs: Sequence[Path],
    declared_doc_paths: frozenset[str],
    project_root: Path,
) -> list[SpaceFinding]:
    """Whether the WORKING declaration is doing what it claims to.

    Two ways a declaration is wrong, and neither is inferred from an absence:

    * it excuses **nothing** — declared kinds that no document uses. An exclusion
      that quietly stops applying is how a gate is switched off, so it reports
      itself, the shape `.48`'s rule liveness and `.49`'s expired exemption both
      carry. Scoped to a declaration the PROJECT made: a project that inherited
      the default and simply has no ephemeral documents has switched nothing off,
      and firing on it would make the finding a greeting rather than a finding.
    * it is **contradicted** — the graph declares one of these documents as a
      node's documentation, so one artifact says "this describes the code" while
      another says "this is exempt from being held against it".
    """
    if not spaces.working.exempt_from_freshness:
        return []
    declared_kinds = spaces.kinds.get(SPACE_WORKING, ())
    declared_roots = spaces.roots.get(SPACE_WORKING, ())
    findings: list[SpaceFinding] = []
    # A root reaches the exemption exactly as a kind does, so an exemption
    # declared only by root and matching nothing reports itself too: an
    # exclusion that quietly stops applying is how a gate is switched off, and
    # which half of the declaration carries it changes nothing about that.
    if spaces.working.declared and (declared_kinds or declared_roots) and not working_docs:
        declares = " and ".join(
            part
            for part in (
                f"kind(s) {', '.join(declared_kinds)}" if declared_kinds else "",
                f"root(s) {', '.join(declared_roots)}" if declared_roots else "",
            )
            if part
        )
        findings.append(
            SpaceFinding(
                rule=FINDING_WORKING_INERT,
                path=".beadloom/config.yml",
                line=0,
                why=(
                    f"the WORKING exemption declares {declares} but no document "
                    f"was found under them, so it excused nothing"
                ),
                remediation=(
                    "point `doc_roots` at the tree the ephemeral documents live in, or "
                    "drop the declaration — an exemption that matches nothing reports "
                    "no problem and reads exactly like one that found none"
                ),
            )
        )
    for path in working_docs:
        rel = _relative(path, project_root)
        if rel not in declared_doc_paths:
            continue
        findings.append(
            SpaceFinding(
                rule=FINDING_WORKING_CONTRADICTED,
                path=rel,
                line=0,
                why=(
                    "the graph declares this document as a node's documentation while "
                    "`doc_roots` declares its kind exempt from freshness — one artifact "
                    "says it describes the code and the other says it must not be held "
                    "against it"
                ),
                remediation=(
                    "remove it from the node's `docs:` list if it is ephemeral, or move "
                    "its kind out of the WORKING space if it describes reality"
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# The database reads the relation needs
# ---------------------------------------------------------------------------


def graph_facts(conn: sqlite3.Connection) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """``(known_refs, documented_refs, declared_doc_paths)`` from the index.

    ``documented_refs`` is drawn from ``declared_docs`` rather than from the
    ``docs`` table: declaration is a fact of the committed graph, and a node
    whose only document was deleted must still count as declaring one — else
    deleting the file would make the check quieter (BDL-UX #174).
    """
    known = frozenset(str(r[0]) for r in conn.execute("SELECT ref_id FROM nodes"))
    rows = conn.execute("SELECT ref_id, declared_path FROM declared_docs").fetchall()
    documented = frozenset(str(r[0]) for r in rows)
    paths = frozenset(str(r[1]).replace("\\", "/") for r in rows)
    return known, documented, paths


def beads_by_epic(records: Iterable[Mapping[str, object]]) -> dict[str, tuple[str, ...]]:
    """Group tracker records by the epic key their title names.

    The shipped flow writes ``[BDL-061.17][dev] …`` into a bead's title, so the
    key is read from there. A record whose title names no key belongs to no epic
    and is dropped rather than guessed at.
    """
    grouped: dict[str, list[str]] = {}
    for record in records:
        title = record.get("title")
        if not isinstance(title, str):
            continue
        match = _EPIC_KEY_RE.search(title)
        if match is None:
            continue
        status = record.get("status")
        grouped.setdefault(match.group(1), []).append(
            status if isinstance(status, str) else ""
        )
    return {key: tuple(values) for key, values in grouped.items()}


#: ``[BDL-061.17]`` / ``[BDL-061]`` / ``[BDL-025-UX]`` — the key up to the first
#: dot, which is where the shipped convention puts the bead number.
_EPIC_KEY_RE = re.compile(r"\[([A-Za-z][A-Za-z0-9]*-[0-9]+(?:-[A-Za-z]+)?)[.\]]")


def jsonl_records(project_root: Path) -> list[Mapping[str, object]] | None:
    """The tracked ``.beads/issues.jsonl`` export, or ``None`` when unreadable.

    The tracker read that needs no binary. ``bd close`` writes only the local
    database, so this file and the live tracker can disagree — which is why the
    caller that HAS ``bd`` prefers it and falls back here, and why the gate,
    which must run in a fresh checkout with no tracker installed, reads this one
    and says so.
    """
    import json

    path = project_root / ".beads" / "issues.jsonl"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    records: list[Mapping[str, object]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records or None


@dataclass(frozen=True)
class TrackerRead:
    """Bead statuses grouped by epic key, and which tracker answered.

    The source travels with the answer because two entry points read two
    different trackers on purpose — the gate the committed export, so it gives
    the same verdict in a fresh CI checkout, and the command the live ``bd``
    database, which is the more current of the two. Whichever ran, the surface
    says which, so a disagreement is readable rather than mysterious.
    """

    statuses: Mapping[str, tuple[str, ...]] | None
    source: str


def read_tracker_export(project_root: Path) -> TrackerRead:
    """The committed ``.beads/issues.jsonl`` export, grouped by epic key."""
    records = jsonl_records(project_root)
    if records is None:
        return TrackerRead(None, TRACKER_UNREADABLE)
    return TrackerRead(beads_by_epic(records), TRACKER_EXPORT)


def spaces_report(
    conn: sqlite3.Connection,
    project_root: Path,
    *,
    beads: Mapping[str, tuple[str, ...]] | None,
    tracker_source: str = TRACKER_EXPORT,
) -> SpacesReport:
    """The whole report for *project_root*, resolving configuration itself."""
    known, documented, paths = graph_facts(conn)
    return check_spaces(
        project_root,
        spaces=resolve_doc_spaces(project_root),
        known_refs=known,
        documented_refs=documented,
        declared_doc_paths=paths,
        beads_by_epic=beads,
        tracker_source=tracker_source,
    )
