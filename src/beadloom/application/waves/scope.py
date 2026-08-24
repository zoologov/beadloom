"""Resolve a bead to the graph nodes and source files it occupies.

One responsibility, and the reason it is separate from the decision: *what a bead
occupies* is a fact about the graph, while *whether two beads may run at once* is
a judgement about a pair. Keeping them apart is what lets an unresolved scope be
reported as its own finding instead of disappearing into a verdict.

**A bead declares its scope in its own words.** The declaration is the tracker
text — ``refs: billing, shipping`` or ``ref: billing`` — which is the convention
the MCP ``bead_context`` tool already reads. It is parsed in exactly one place
(:func:`declared_refs`) so the tool and the planner cannot come to disagree about
what a bead said, which is the two-sources-of-truth defect this epic has now met
three times (BDL-UX #171, #177, #179).

**A scope expands through ``part_of``.** A node's own file set deliberately
excludes a nested node's files, so a bead scoped to a domain and a bead scoped to
one of its components would otherwise look disjoint while editing the same
package. The expansion makes the containment visible as a shared NODE.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.application.waves.models import (
    UNRESOLVED_NO_DECLARATION,
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
    from collections.abc import Iterable, Sequence

#: ``refs:`` (or ``ref:``, or ``area:``) followed by a comma-separated list. The
#: list ends at the first newline or sentence stop, so a declaration embedded in
#: prose cannot silently swallow the rest of the paragraph as ref ids.
_DECLARATION = re.compile(r"\b(?:refs?|area)\s*:\s*([^\n.;]+)", re.IGNORECASE)

#: A ref id as this codebase writes them: letters, digits, dash, underscore, dot.
#: Anything else in the list is not a ref and is dropped rather than guessed at.
_REF_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def declared_refs(declaration: str) -> tuple[str, ...]:
    """Every ref id *declaration* names, de-duplicated and sorted.

    Accepts ``ref:``, ``refs:`` and ``area:`` — the three spellings already in
    use — and every occurrence of them, so a bead that names its scope twice in
    two sentences is read as naming both.
    """
    found: set[str] = set()
    for match in _DECLARATION.finditer(declaration or ""):
        for chunk in match.group(1).split(","):
            # The FIRST word of each comma-separated item, because a declaration
            # is written inside prose: `ref: FEAT-1 Touches FEAT-1` names one
            # node and then talks about it, and reading the whole run as an id
            # found nothing at all rather than finding the id.
            words = chunk.split()
            if not words:
                continue
            token = words[0].strip("`\'\"")
            if _REF_TOKEN.match(token):
                found.add(token)
    return tuple(sorted(found))


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
    """
    names = declared_refs(record.declaration)
    if not names:
        return BeadScope(
            bead_id=record.bead_id,
            refs=frozenset(),
            files=frozenset(),
            unresolved=UNRESOLVED_NO_DECLARATION,
        )
    unknown = tuple(name for name in names if get_node(conn, name) is None)
    known = [name for name in names if name not in unknown]
    refs = _expand_part_of(conn, known)
    files = {
        path
        for ref in refs
        for path, _hash in get_owned_code_files(conn, ref)
    }
    return BeadScope(
        bead_id=record.bead_id,
        refs=frozenset(refs),
        files=frozenset(files),
        unresolved=UNRESOLVED_UNKNOWN_REF if unknown else None,
        unknown_refs=unknown,
    )


def resolve_scopes(
    conn: sqlite3.Connection, records: Sequence[BeadRecord]
) -> tuple[BeadScope, ...]:
    """Resolve every record, in sorted bead order so the answer is stable."""
    return tuple(
        resolve_scope(conn, record)
        for record in sorted(records, key=lambda r: r.bead_id)
    )
