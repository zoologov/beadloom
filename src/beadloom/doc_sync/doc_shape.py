# beadloom:domain=doc-sync
# beadloom:feature=doc-shape
"""Whether a document still carries the sections its kind requires (BDL-061 S4b).

``sync-check``'s five reasons all compare CONTENT — a hash moved, a symbol set
moved, a file appeared, a module went unmentioned, a declared doc vanished. None
of them can see that a README was edited down to a title, because its bytes
changing IS the thing they measure. ``missing_sections`` compares STRUCTURE, and
it is the only reason here that says something about the document's shape rather
than its currency.

**Peer-relative, deliberately.** The finding this check exists to make is "this
document departs from the shape its peers keep". So a required section counts as
in use for a kind only when a MAJORITY of that kind's documents carry it;
anything less is not the peers' shape, and reporting every other document
against it inverts the finding — measured on this repository, ``## Parent`` is
carried by one feature SPEC of 36, and a presence-of-one rule would have reported
the 35 that follow the actual convention. A section below the majority is
reported ONCE, against the KIND, with its ratio, because it is a statement about
the project's convention and is fixed in the template rather than in 35 files.
That is the shape `.13` settled on when a features glob matching zero files
reports the glob rather than every node. A tie counts as not in use: half the
documents doing something is not yet a convention to be held to.

The required sections arrive as an argument. ``doc_sync`` is a peer domain of
``onboarding``, where the templates they are derived from live, so the
application layer computes them (:func:`beadloom.onboarding.doc_templates.
required_sections_by_node_kind`) and passes them in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from beadloom.doc_sync.doc_quality import QualityFinding, document_kind
from beadloom.infrastructure.doc_roots import resolve_docs_dir

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

#: A document that is CURRENT and does not carry the shape its kind requires.
#: Not ``stale`` — nothing about it went out of date — and deliberately absent
#: from ``BLOCKING_STATUSES``: a new check ships as ``warn`` so no adopter's
#: green project turns red on upgrade.
STATUS_INCOMPLETE = "incomplete"

#: This document lacks sections its peers of the same kind carry.
REASON_MISSING_SECTIONS = "missing_sections"

#: A required section that no MAJORITY of this kind's documents carries. A
#: statement about the convention, carried in the same rows so a caller needs no
#: second channel.
REASON_SECTION_NOT_IN_USE = "section_not_in_use"

#: A planning document lacks a section its kind's template carries and its peers
#: keep. The ``doc-quality`` name for what ``missing_sections`` reports about a
#: node document — one policy, two corpora, so the two cannot disagree.
MISSING_SECTION = "missing-section"

#: A required section whose heading is there and whose body says nothing. A
#: heading with nothing under it satisfies a presence check and answers no
#: question, which is the failure mode a naive structural check ships with.
EMPTY_SECTION = "empty-section"

_HEADING_RE = re.compile(r"^(#{1,6}) +(.+?)\s*$")

#: A markdown horizontal rule — a separator, never a section's content.
_HRULE_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")


@dataclass(frozen=True)
class Section:
    """One heading, the line it sits on, its depth, and the lines under it."""

    title: str
    lineno: int
    depth: int = 2
    body: tuple[str, ...] = ()
    #: Whether this heading, or anything NESTED under it, states anything. A
    #: section whose content lives in its subsections is not empty, and judging
    #: emptiness on the heading's own lines alone reported 155 documents on this
    #: repository whose ``## Code Standards`` is a heading over four ``###``.
    states_something: bool = False

    @property
    def is_empty(self) -> bool:
        """Whether nothing at all is said under the heading."""
        return not self.states_something


def _says_anything(body: Iterable[str]) -> bool:
    return any(line.strip() and not _HRULE_RE.match(line) for line in body)


def read_sections(text: str) -> tuple[Section, ...]:
    """Every heading in *text* with its line number and its body, fences skipped.

    A ``## `` inside a fenced block is a QUOTED template, not a section of this
    document — the same reading ``unfilled-placeholder`` already applies to the
    same corpus, and without it a BRIEF that quotes its own skeleton would be
    credited with every section the skeleton names.
    """
    found: list[tuple[str, int, int, tuple[str, ...]]] = []
    fenced = False
    title = ""
    lineno = 0
    depth = 2
    body: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            body.append(line)
            continue
        heading = None if fenced else _HEADING_RE.match(line)
        if heading is None:
            body.append(line)
            continue
        if title:
            found.append((title, lineno, depth, tuple(body)))
        title, lineno = heading.group(2), number
        depth, body = len(heading.group(1)), []
    if title:
        found.append((title, lineno, depth, tuple(body)))

    states = [_says_anything(entry[3]) for entry in found]
    for index in range(len(found) - 1, -1, -1):
        follower = index + 1
        while follower < len(found) and found[follower][2] > found[index][2]:
            if states[follower]:
                states[index] = True
                break
            follower += 1
    return tuple(
        Section(entry[0], entry[1], entry[2], entry[3], states[index])
        for index, entry in enumerate(found)
    )


def document_sections(text: str) -> tuple[str, ...]:
    """Section titles a markdown document carries, at any heading depth.

    Depth is deliberately ignored: a document that promoted ``## Source`` to
    ``# Source`` or demoted it to ``### Source`` still states the fact the
    section exists for, and reporting it as missing would be a finding about
    markdown rather than about documentation.
    """
    return tuple(section.title for section in read_sections(text))


def carries_section(sections: Iterable[str], required: str) -> bool:
    """Whether any of *sections* states the section named *required*.

    Matched as a whole-word PHRASE, case-insensitively, rather than by string
    equality: ``## Features and components`` is not a document that lost its
    Features section, and reporting it as one is a finding about the heading's
    wording. Measured on this repository, equality reported two domain READMEs
    that carry the section under a wider title.

    The limit this accepts, stated rather than discovered: a heading that merely
    contains the word satisfies the requirement. The check answers "is this
    stated somewhere under a heading that names it", not "is this stated well" —
    the second is what the section-quality checks are for.
    """
    pattern = re.compile(rf"\b{re.escape(required)}\b", re.IGNORECASE)
    return any(pattern.search(section) for section in sections)


@dataclass(frozen=True)
class SectionConvention:
    """A required section a majority of a kind's documents do not carry.

    A statement about the project's convention rather than about any one
    document: the ratio rides along because "Axes (0/12)" says what a bare
    section name cannot, which is how far from a convention the section is.
    """

    kind: str
    section: str
    carried: int
    total: int

    @property
    def ratio(self) -> str:
        """``carried/total``, the denominator the finding is read against."""
        return f"{self.carried}/{self.total}"


@dataclass(frozen=True)
class LostSections:
    """One document and the in-use sections of its kind it does not carry."""

    kind: str
    document: str
    sections: tuple[str, ...]


def peer_section_shape(
    documents: Mapping[str, Sequence[tuple[str, Sequence[str]]]],
    requirements: Mapping[str, tuple[str, ...]],
) -> tuple[tuple[SectionConvention, ...], tuple[LostSections, ...]]:
    """The peer-relative shape policy, over any corpus of ``kind -> documents``.

    *documents* maps a kind to ``(identifier, the section titles it carries)``.
    One policy, two corpora — generated node documentation and the flow's
    planning documents — because a second implementation of "does a majority
    carry this" is a second thing that can disagree with the first.

    A section counts as IN USE for a kind only when a majority of that kind's
    documents carry it; below that it is reported once against the kind, and no
    document is reported for it. A tie counts as not in use: half the documents
    doing something is not yet a convention to be held to.
    """
    conventions: list[SectionConvention] = []
    lost: list[LostSections] = []
    for kind in sorted(documents):
        required = requirements.get(kind, ())
        if not required:
            continue
        present = {
            identifier: frozenset(s for s in required if carries_section(titles, s))
            for identifier, titles in documents[kind]
        }
        total = len(present)
        carried = {
            section: sum(1 for held in present.values() if section in held)
            for section in required
        }
        in_use = {section for section, n in carried.items() if n * 2 > total}
        conventions.extend(
            SectionConvention(kind, section, carried[section], total)
            for section in required
            if section not in in_use
        )
        for identifier, held in present.items():
            missing = tuple(s for s in required if s in in_use and s not in held)
            if missing:
                lost.append(LostSections(kind, identifier, missing))
    return tuple(conventions), tuple(lost)


@dataclass(frozen=True)
class PlanningShapeReport:
    """What the structural checks found over the flow's planning documents.

    ``kinds_judged`` is the honest half: a document kind no template describes
    is not judged at all, and saying so is the difference between "checked and
    clean" and "never entered" — the distinction BDL-UX #173 was filed for.
    """

    findings: tuple[QualityFinding, ...] = ()
    conventions: tuple[SectionConvention, ...] = ()
    kinds_judged: tuple[str, ...] = ()
    documents: int = 0


def check_planning_sections(
    documents: Iterable[tuple[str, str]],
    requirements: Mapping[str, tuple[str, ...]],
) -> PlanningShapeReport:
    """Hold each planning document to the sections its own template carries.

    *documents* are ``(path, text)`` pairs; *requirements* map a DOCUMENT kind
    (``BRIEF``, ``RFC``) to the sections its composed skeleton carries, derived
    by :func:`beadloom.onboarding.doc_templates.required_sections_by_document_kind`.
    They arrive as an argument because ``doc_sync`` is a peer domain of
    ``onboarding`` and may not import a template.

    Two findings, and they answer different questions. ``missing-section`` is
    peer-relative, so a section the archive never adopted is reported once
    against the kind instead of once per document. ``empty-section`` is not:
    a heading the author wrote with nothing under it is a defect whatever the
    peers do, and it is the one a presence check is satisfied by.
    """
    read: dict[str, list[tuple[str, tuple[Section, ...]]]] = {}
    count = 0
    for path, text in documents:
        kind = document_kind(path)
        if kind not in requirements:
            continue
        count += 1
        read.setdefault(kind, []).append((path, read_sections(text)))

    conventions, lost = peer_section_shape(
        {
            kind: [(path, [s.title for s in sections]) for path, sections in entries]
            for kind, entries in read.items()
        },
        requirements,
    )

    findings = [
        QualityFinding(
            check=MISSING_SECTION,
            path=entry.document,
            line=1,
            excerpt=", ".join(entry.sections),
            why=(
                f"the {entry.kind} is missing section(s) its template carries and "
                f"its peers keep"
            ),
            remediation=(
                "add the section(s), or drop them from the document template in "
                ".beadloom/flow/commands/templates.md if they do not belong there"
            ),
        )
        for entry in lost
    ]
    for kind, entries in sorted(read.items()):
        for path, sections in entries:
            for required in requirements[kind]:
                stated = [s for s in sections if carries_section([s.title], required)]
                if not stated or not all(section.is_empty for section in stated):
                    continue
                findings.append(
                    QualityFinding(
                        check=EMPTY_SECTION,
                        path=path,
                        line=stated[0].lineno,
                        excerpt=stated[0].title,
                        why=(
                            f"the {kind} carries the required section "
                            f"{required!r} with nothing under it"
                        ),
                        remediation=(
                            "state the section's content, or remove the heading — "
                            "a heading with nothing under it answers no question"
                        ),
                    )
                )
    findings.sort(key=lambda finding: (finding.path, finding.line, finding.check))
    return PlanningShapeReport(
        findings=tuple(findings),
        conventions=conventions,
        kinds_judged=tuple(sorted(read)),
        documents=count,
    )


def _documents_by_node_kind(
    conn: sqlite3.Connection,
    project_root: Path,
    kinds: frozenset[str],
) -> dict[str, list[tuple[str, str, str]]]:
    """``node kind -> [(ref_id, doc path, text)]`` for every readable document.

    A declared document that is not on disk is skipped: that is a ``missing``
    pair, already reported with its own reason, and calling it "a document with
    no sections" would report one fault twice under two names.
    """
    docs_dir = resolve_docs_dir(project_root)
    by_kind: dict[str, list[tuple[str, str, str]]] = {}
    rows = conn.execute(
        "SELECT n.ref_id AS ref_id, n.kind AS kind, d.path AS path "
        "FROM docs d JOIN nodes n ON n.ref_id = d.ref_id "
        "WHERE d.ref_id IS NOT NULL ORDER BY d.path, n.ref_id"
    ).fetchall()
    for row in rows:
        kind = row["kind"]
        if kind not in kinds:
            continue
        path = project_root / docs_dir / row["path"]
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        by_kind.setdefault(kind, []).append((row["ref_id"], row["path"], text))
    return by_kind


def check_section_shape(
    conn: sqlite3.Connection,
    project_root: Path,
    requirements: Mapping[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Report documents missing the sections their peers carry.

    Returns rows in ``check_sync``'s shape so a caller formats one kind of
    result: ``missing_sections`` names a document, ``section_not_in_use`` names
    a node kind and the section its documents never use.
    """
    documents = _documents_by_node_kind(
        conn, project_root, frozenset(requirements)
    )
    paths = {
        ref_id: path
        for entries in documents.values()
        for ref_id, path, _ in entries
    }
    conventions, lost = peer_section_shape(
        {
            node_kind: [
                (ref_id, document_sections(text)) for ref_id, _, text in entries
            ]
            for node_kind, entries in documents.items()
        },
        requirements,
    )

    results: list[dict[str, Any]] = []
    by_kind: dict[str, list[SectionConvention]] = {}
    for convention in conventions:
        by_kind.setdefault(convention.kind, []).append(convention)
    for node_kind in sorted(documents):
        unused = by_kind.get(node_kind, [])
        if unused:
            results.append(
                {
                    "doc_path": "",
                    "code_path": "",
                    "ref_id": f"{node_kind} documents",
                    "status": STATUS_INCOMPLETE,
                    "reason": REASON_SECTION_NOT_IN_USE,
                    # The denominator rides along: "Source (3/36)" says what a
                    # bare section name cannot, which is how far from a
                    # convention the section actually is.
                    "details": ", ".join(
                        f"{c.section} ({c.ratio})" for c in unused
                    ),
                }
            )
        results.extend(
            {
                "doc_path": paths[entry.document],
                "code_path": "",
                "ref_id": entry.document,
                "status": STATUS_INCOMPLETE,
                "reason": REASON_MISSING_SECTIONS,
                "details": ", ".join(entry.sections),
            }
            for entry in sorted(
                (e for e in lost if e.kind == node_kind),
                key=lambda entry: entry.document,
            )
        )
    return results
