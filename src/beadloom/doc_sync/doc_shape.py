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
from typing import TYPE_CHECKING, Any

from beadloom.infrastructure.doc_roots import resolve_docs_dir

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable, Mapping
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

_HEADING_RE = re.compile(r"^#{1,6} +(.+?)\s*$", re.MULTILINE)


def document_sections(text: str) -> tuple[str, ...]:
    """Section titles a markdown document carries, at any heading depth.

    Depth is deliberately ignored: a document that promoted ``## Source`` to
    ``# Source`` or demoted it to ``### Source`` still states the fact the
    section exists for, and reporting it as missing would be a finding about
    markdown rather than about documentation.
    """
    return tuple(match.group(1) for match in _HEADING_RE.finditer(text))


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
    results: list[dict[str, Any]] = []

    for node_kind in sorted(documents):
        required = requirements[node_kind]
        present_by_doc = {
            ref_id: (
                path,
                frozenset(
                    s for s in required if carries_section(document_sections(text), s)
                ),
            )
            for ref_id, path, text in documents[node_kind]
        }
        total = len(present_by_doc)
        carried = {
            section: sum(
                1 for _, present in present_by_doc.values() if section in present
            )
            for section in required
        }
        in_use = {s for s, n in carried.items() if n * 2 > total}
        unused = [s for s in required if s not in in_use]
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
                        f"{s} ({carried[s]}/{total})" for s in unused
                    ),
                }
            )
        for ref_id in sorted(present_by_doc):
            path, present = present_by_doc[ref_id]
            missing = [s for s in required if s in in_use and s not in present]
            if missing:
                results.append(
                    {
                        "doc_path": path,
                        "code_path": "",
                        "ref_id": ref_id,
                        "status": STATUS_INCOMPLETE,
                        "reason": REASON_MISSING_SECTIONS,
                        "details": ", ".join(missing),
                    }
                )
    return results
