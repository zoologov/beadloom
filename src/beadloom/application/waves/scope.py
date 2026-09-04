"""Resolve a bead to the graph nodes and source files it occupies.

One responsibility, and the reason it is separate from the decision: *what a bead
occupies* is a fact about the graph, while *whether two beads may run at once* is
a judgement about a pair. Keeping them apart is what lets an unresolved scope be
reported as its own finding instead of disappearing into a verdict.

**A bead declares its scope in its own words.** The declaration is the tracker
text — ``refs: billing, shipping`` or ``ref: billing`` — which is the convention
the MCP ``bead_context`` tool already reads. It is parsed in exactly one place
(:func:`parse_declaration`) and COMPOSED in exactly one place
(:func:`compose_declaration`), so the tool and the planner cannot come to
disagree about what a bead said, which is the two-sources-of-truth defect this
epic has now met three times (BDL-UX #171, #177, #179).

**And every way it cannot be read serialises.** The parser used to fail toward a
NARROWER scope: a second ref after a semicolon was dropped, a ``refs:`` inside a
sentence adopted the next word, and a narrower scope compares independent of more
beads than the true one does. A wave shape is acted on, so a parser whose failure
modes increase parallelism is worse than no parser. Four unresolved reasons now
cover the four ways the declaration can defeat this module, and each of them
serialises the bead the way ``no_declared_refs`` already did.

**A scope expands through ``part_of``.** A node's own file set deliberately
excludes a nested node's files, so a bead scoped to a domain and a bead scoped to
one of its components would otherwise look disjoint while editing the same
package. The expansion makes the containment visible as a shared NODE.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.waves.models import (
    UNRESOLVED_DROPPED_NODE,
    UNRESOLVED_NO_DECLARATION,
    UNRESOLVED_UNANCHORED,
    UNRESOLVED_UNKNOWN_REF,
    BeadRecord,
    BeadScope,
)
from beadloom.infrastructure.repository import (
    get_node,
    get_owned_code_files,
    get_part_of_children,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable, Mapping, Sequence

#: A declaration OPENS A LINE. ``refs:`` (or ``ref:``, or ``area:``) at the start
#: of a line, optionally behind list or quote markup, followed by the rest of that
#: line as a comma- or semicolon-separated list.
#:
#: **Anchored, because a mention is not a declaration.** The pattern used to match
#: ``\brefs?:`` anywhere, so a sentence ABOUT the grammar became a declaration and
#: the bead was handed the next word as a genuine, fully RESOLVED scope. Bead
#: ``beadloom-mr2l.80`` did exactly that while describing this parser, and every
#: pairwise verdict for it then rested on a scope its author never named
#: (BDL-061.23 M4). An unanchored ``refs:`` is now prose, which leaves the bead
#: unresolved, which serialises it.
#:
#: **The list runs to the end of the line, not to the first ``.`` or ``;``.** It
#: used to stop at either, so ``refs: wave-plan; sync-check`` declared one ref and
#: dropped the other in silence, and ``refs: svc.billing`` truncated to ``svc``
#: (BDL-061.23 M3, ruled from OBSERVATION BDL-061.22-A). A dropped word the graph
#: confirms is a node is reported instead — see :class:`Declaration`.
#:
#: The separator between the colon and the list is spaces and tabs, NOT ``\s``.
#: ``\s`` matches newlines, so an empty ``refs:`` header skipped forward to the
#: next non-empty line and read that line as the declaration (BDL-061.22-5).
_DECLARATION = re.compile(
    r"^[ \t>*#\-]*(?:refs?|area)[ \t]*:[ \t]*([^\n]*)$",
    re.IGNORECASE | re.MULTILINE,
)

#: The same token written anywhere at all. Used only to tell "the author never
#: declared a scope" from "the author declared one where a parser cannot read it",
#: because those two have different remedies and reporting them as one would send
#: an author looking for a declaration they had already written.
_MENTION = re.compile(r"\b(?:refs?|area)[ \t]*:", re.IGNORECASE)

#: What separates one item of the list from the next. Both, because this project's
#: own prose writes a list either way.
_ITEM_SEPARATORS = re.compile(r"[,;]")

#: A ref id as this codebase writes them: letters, digits, dash, underscore, dot.
#: Anything else in the list is not a ref and is dropped rather than guessed at.
_REF_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

#: Punctuation a ref id can pick up from the prose around it. Stripped from both
#: ends, so ```billing`,`` and ``svc.billing.`` reach the graph as ids while a
#: dotted id keeps its own dots.
_SURROUNDING = "`'\".,;:!?()[]"


@dataclass(frozen=True)
class Declaration:
    """What a bead's own words say about its scope, before the graph is asked.

    Three fields because the parser has three distinct answers and collapsing
    them loses the one that matters. ``refs`` is what was read. ``dropped`` is
    every other id-shaped word inside a declaration list — candidates only, since
    a declaration is written inside prose and most of those words are prose.
    ``unanchored`` says a ``refs:`` token exists somewhere in the text but never
    where a declaration is read from.

    Which of ``dropped`` is a real loss is not a question this parser can answer:
    it needs the graph. :func:`resolve_scope` asks.
    """

    refs: tuple[str, ...] = ()
    dropped: tuple[str, ...] = ()
    unanchored: bool = False


def _token(word: str) -> str:
    """*word* with the punctuation of the surrounding prose taken off both ends."""
    return word.strip(_SURROUNDING)


def parse_declaration(declaration: str) -> Declaration:
    """Read *declaration* as a scope, and say what it could not read.

    Accepts ``ref:``, ``refs:`` and ``area:`` — the three spellings already in
    use — and every occurrence of them, so a bead that names its scope twice in
    two lines is read as naming both.
    """
    text = declaration or ""
    found: set[str] = set()
    dropped: set[str] = set()
    anchored = False
    for match in _DECLARATION.finditer(text):
        anchored = True
        for chunk in _ITEM_SEPARATORS.split(match.group(1)):
            # The FIRST word of each item, because a declaration is written
            # inside prose: `ref: FEAT-1 Touches FEAT-1` names one node and then
            # talks about it, and reading the whole run as an id found nothing at
            # all rather than finding the id. The rest are kept as CANDIDATES so
            # a real ref written without a comma can still be reported.
            words = [_token(word) for word in chunk.split()]
            ids = [word for word in words if _REF_TOKEN.match(word)]
            if not ids:
                continue
            if words[0] == ids[0]:
                found.add(ids[0])
                dropped.update(ids[1:])
            else:
                dropped.update(ids)
    return Declaration(
        refs=tuple(sorted(found)),
        dropped=tuple(sorted(dropped - found)),
        unanchored=not anchored and _MENTION.search(text) is not None,
    )


def declared_refs(declaration: str) -> tuple[str, ...]:
    """Every ref id *declaration* names, de-duplicated and sorted."""
    return parse_declaration(declaration).refs


#: The tracker fields a bead's declaration is composed from, and the ORDER they
#: are composed in. Named here because three callers compose it — `beadloom
#: waves`, `beadloom review-brief` and the MCP `bead_context` tool — and they used
#: to do it three times: two joined with a newline and one with a space, which put
#: the next field's first word directly behind a dangling `refs:` header and gave
#: the MCP caller back the defect `.80` had just closed (BDL-061.23 M5). Two
#: readings of one declaration is how a tool and a planner come to disagree about
#: what a bead said.
DECLARATION_FIELDS: tuple[str, ...] = ("title", "description", "design", "notes")


def compose_declaration(record: Mapping[str, object]) -> str:
    """Everything *record* says about itself, joined the one way every caller joins it.

    Newlines, not spaces: the declaration pattern is line-anchored and its list
    ends at a line end, so the join is what makes a field boundary a boundary.
    """
    return "\n".join(str(record.get(key, "") or "") for key in DECLARATION_FIELDS)


def _expand_part_of(conn: sqlite3.Connection, roots: Iterable[str]) -> set[str]:
    """*roots* plus every node reachable from them by ``part_of``, downward."""
    seen: set[str] = set()
    pending = list(roots)
    while pending:
        ref = pending.pop()
        if ref in seen:
            continue
        seen.add(ref)
        pending.extend(child.ref_id for child in get_part_of_children(conn, ref))
    return seen


def resolve_scope(conn: sqlite3.Connection, record: BeadRecord) -> BeadScope:
    """The nodes and files *record* occupies, or the reason it could not be told.

    An unresolved scope is returned as a scope with a reason, never as an empty
    one: an empty scope compares independent of everything, which is exactly the
    silent false-green this command exists to remove.

    Every way the declaration cannot be read with confidence lands here, with a
    reason and a remedy, and every one of them serialises. That is the direction
    the parser fails in, and it is deliberate: the wave shape is trusted, so a
    parser whose errors WIDEN a wave is worse than no parser at all.
    """
    declaration = parse_declaration(record.declaration)
    if not declaration.refs:
        return BeadScope(
            bead_id=record.bead_id,
            refs=frozenset(),
            files=frozenset(),
            unresolved=(
                UNRESOLVED_UNANCHORED
                if declaration.unanchored
                else UNRESOLVED_NO_DECLARATION
            ),
        )
    names = declaration.refs
    unknown = tuple(name for name in names if get_node(conn, name) is None)
    known = [name for name in names if name not in unknown]
    # A word the parser threw away that the GRAPH has as a node is a ref the bead
    # declared and this parser did not read. It cannot be added — reading every
    # following word as a ref id found nothing at all — so it is reported, and the
    # bead serialises until its author writes the list with a comma.
    dropped = tuple(word for word in declaration.dropped if get_node(conn, word))
    refs = _expand_part_of(conn, known)
    files = {
        path
        for ref in refs
        for path, _hash in get_owned_code_files(conn, ref)
    }
    unresolved = None
    if unknown:
        unresolved = UNRESOLVED_UNKNOWN_REF
    elif dropped:
        unresolved = UNRESOLVED_DROPPED_NODE
    return BeadScope(
        bead_id=record.bead_id,
        refs=frozenset(refs),
        files=frozenset(files),
        unresolved=unresolved,
        unknown_refs=unknown,
        dropped_refs=dropped,
        declared=names,
    )


def resolve_scopes(
    conn: sqlite3.Connection, records: Sequence[BeadRecord]
) -> tuple[BeadScope, ...]:
    """Resolve every record, in sorted bead order so the answer is stable."""
    return tuple(
        resolve_scope(conn, record)
        for record in sorted(records, key=lambda r: r.bead_id)
    )
