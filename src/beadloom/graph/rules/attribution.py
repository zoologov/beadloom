# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Which node an indexed source FILE is attributed to, and what it cost to say.

One responsibility: **answer "whose file is this?" for the linter**, and count
the files for which there is no answer.

Before BDL-061.50 a ``deny`` rule resolved the SOURCE node of an import through
``code_symbols.annotations`` alone and took the FIRST annotation value that
happened to name a node.  Two defects followed from that, and both are silent:

* a file whose annotation the extractor could not read — or that carries none at
  all — was invisible to **every** deny rule.  Measured on this repository
  before the fix: 22 of 128 import-source files (17%), among them
  ``services/cli.py`` and two TUI widgets.  The ``depends_on`` edge for those
  imports EXISTS, because :mod:`beadloom.graph.import_resolver` derives it from
  ownership; only the rule that polices the edge used a different key.  This is
  BDL-UX #146's disease in the linter.
* "the first annotation that names a node" is dictionary order.  A module
  annotated ``domain=app`` **and** ``component=alpha`` resolved to whichever key
  came first, so a rule written against the specific node quietly stopped
  matching when a coarser one was listed earlier.

The answer here is a ranked list rather than a single ref, because both keys are
legitimate: an annotation is a per-file declaration, ownership is the same
most-specific-source rule the ``depends_on`` edges already use
(:func:`beadloom.infrastructure.repository.get_owning_ref_id`).  A rule matches
against the most specific candidate first, so nothing gets less specific than it
was, and nothing that is genuinely attributable stays invisible.

What remains unattributable — a file under no node's source and carrying no
annotation — is **counted and reported** on the lint header rather than skipped
in a loop: a deny rule that never saw a file did not clear it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.infrastructure.repository import covering_prefix, source_covers

if TYPE_CHECKING:
    import sqlite3

#: Rank given to an annotated node that declares no ``source`` of its own.
#: An annotation is written INSIDE the file, so it is at least as specific as
#: any directory that contains it; a feature node without a source exists
#: precisely to name a slice finer than the directory it lives in.
_PER_FILE_RANK = 1 << 30



@dataclass(frozen=True)
class _NodeSource:
    """The two node facts attribution needs: what it is, and what it covers."""

    kind: str
    source: str


class FileAttribution:
    """Ranked node candidates for a source file, built once per lint run.

    Built as a snapshot rather than queried per import: the previous shape ran
    one query per file plus one per annotation value, and the ranking needs the
    whole node table anyway.
    """

    def __init__(
        self,
        nodes: dict[str, _NodeSource],
        annotations_by_file: dict[str, set[str]],
    ) -> None:
        self._nodes = nodes
        self._annotations = annotations_by_file

    @classmethod
    def build(cls, conn: sqlite3.Connection) -> FileAttribution:
        """Snapshot the node table and the per-file annotation values."""
        nodes: dict[str, _NodeSource] = {}
        for row in conn.execute("SELECT ref_id, kind, source FROM nodes"):
            nodes[str(row[0])] = _NodeSource(kind=str(row[1] or ""), source=str(row[2] or ""))

        annotations: dict[str, set[str]] = {}
        for row in conn.execute("SELECT file_path, annotations FROM code_symbols"):
            raw = row[1]
            if raw is None:
                continue
            try:
                parsed: dict[str, object] = json.loads(str(raw))
            except (json.JSONDecodeError, TypeError):
                continue
            values = {value for value in parsed.values() if isinstance(value, str)}
            if values:
                annotations.setdefault(str(row[0]), set()).update(values)
        return cls(nodes, annotations)

    def kind_of(self, ref_id: str) -> str:
        """The node kind for *ref_id*, or ``""`` when it is not a node."""
        node = self._nodes.get(ref_id)
        return node.kind if node is not None else ""

    def candidates(self, file_path: str) -> tuple[str, ...]:
        """Every node that CONTAINS *file_path*, most specific first.

        Containment, not mere mention: an annotation naming a node whose own
        ``source`` lies elsewhere is a cross-reference, and treating it as
        containment produces a false RED. Measured on this repository:
        ``services/commands/setup.py`` annotates individual commands
        ``domain=onboarding``; matching a ``deny from: {kind: domain}`` rule
        against that label reported the CLI's own ``mcp-server`` import as a
        domain-to-service breach, when the file is a service module and the
        derived ``depends_on`` edge says so.

        A node with no ``source`` of its own is always a candidate for a file
        that annotates it: that is what a feature node IS — a slice named finer
        than the directory holding it.

        Empty when the file lies under no node's source and annotates no
        source-less node — the state that must be counted, not skipped.
        """
        ranked: dict[str, int] = {}
        for ref_id in self._annotations.get(file_path, ()):
            node = self._nodes.get(ref_id)
            if node is None:
                continue
            if not node.source:
                ranked[ref_id] = _PER_FILE_RANK
            elif source_covers(node.source, file_path):
                ranked[ref_id] = len(covering_prefix(node.source))
        for ref_id, node in self._nodes.items():
            if not node.source or not source_covers(node.source, file_path):
                continue
            ranked.setdefault(ref_id, len(covering_prefix(node.source)))
        return tuple(sorted(ranked, key=lambda ref: (-ranked[ref], ref)))


def count_unattributed_import_files(conn: sqlite3.Connection) -> int:
    """How many scanned files belong to no node, and so pass every deny rule.

    Reported beside ``files_scanned`` because the two together are the honest
    statement: a scanned count alone reads the same whether the rules could look
    at those files or not (standing rule A GREEN COUNT IS NOT A CHECKED COUNT).
    """
    attribution = FileAttribution.build(conn)
    rows = conn.execute("SELECT DISTINCT file_path FROM code_imports").fetchall()
    return sum(1 for row in rows if not attribution.candidates(str(row[0])))
