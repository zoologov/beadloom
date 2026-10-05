# beadloom:domain=application
# beadloom:feature=site-generation
"""The node card of ``architecture.data.json``: what one node shows, beyond its place in the graph.

BDL-076 A1. The viewer is a static site, so the card and the impact mode can
show only what ``beadloom docs site`` wrote into the data file. Schema version 1
carried a symbol count, one aggregate doc status and a lint boolean. This module
reads the rest of what the index holds about a node, and carries the two
verdicts the site run computes outside the index: the lint findings and the
debt report.

**One responsibility:** project the card fields of one node. Where the node
sits — its layer, its lane, its parent, its edges — is
:mod:`beadloom.application.site.architecture_view`'s question, and that module merges
these fields into each node.

Honest degradation, as in the rest of the data file:

- ``tests`` is ``None`` for a node the test binding does not cover, which is a
  different fact from a covered node with no test file.
- ``tests`` lists a test file once, at the node it is bound to. A container
  counts its parts' files without repeating their paths: listed at every
  ancestor, the paths were the largest field of the file (BDL-076 K4).
- ``activity`` is ``None`` when the reindex recorded none, and carries only
  :data:`CARD_ACTIVITY_KEYS`: the reindex records the names of a node's most
  frequent committers as well, and the data file is published (BDL-076 R1
  finding M2).
- ``source_url`` is the finished link to the node's source, decided per forge
  by :class:`~beadloom.application.site.repository_link.RepositoryLink`, and
  ``""`` when there is none to give (BDL-076 R1 finding M1).
- ``findings`` and ``debt`` are omitted entirely when the site run did not
  compute them, never reported as clean.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.application.site.node_pages import public_symbol_names
from beadloom.application.site.repository_link import RepositoryLink
from beadloom.graph.rules.suite_tables import read_test_files

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Mapping, Sequence

    from beadloom.application.debt_report import NodeDebt

#: How many public symbol names a node carries. The rest are counted, not
#: listed: the node page lists every name, and the data file is fetched on every
#: page view.
PUBLIC_SYMBOL_CAP = 50

#: The activity keys the node card shows, and the only ones the data file carries.
#: A key the reindex adds reaches the published file by being listed here.
CARD_ACTIVITY_KEYS = ("commits_30d", "lines_30d", "level")

#: A doc the index holds with no sync pair: nothing has been checked against it.
DOC_UNPAIRED = "unpaired"

#: ``sync_state`` statuses, worst first. A doc paired with several code files
#: shows the worst of its pairs, as the aggregate ``doc_status`` does.
_PAIR_STATUS_SEVERITY = ("missing", "stale", "unverified", "ok")


@dataclass(frozen=True)
class NodeFinding:
    """One lint finding against a node: the rule, how loudly, and what it says."""

    rule: str
    severity: str
    message: str

    def as_dict(self) -> dict[str, object]:
        return {"rule": self.rule, "severity": self.severity, "message": self.message}


@dataclass(frozen=True)
class NodeVerdicts:
    """What the site run measured about each node outside the index.

    ``None`` for either field means it was not computed, and the data file then
    omits the key rather than reporting every node clean.
    """

    findings: Mapping[str, Sequence[NodeFinding]] | None = None
    debt: Mapping[str, NodeDebt] | None = None


@dataclass(frozen=True)
class CardSources:
    """The whole-graph reads the card needs, taken once per build."""

    tags: Mapping[str, Collection[str]]
    placements: Mapping[str, str]
    #: Test file path -> the node it is bound to, for owners the graph holds.
    test_owners: Mapping[str, str]
    verdicts: NodeVerdicts
    #: The repository a node's source links into.
    repository: RepositoryLink = field(default_factory=RepositoryLink)


def card_sources(
    conn: sqlite3.Connection,
    *,
    tags: Mapping[str, Collection[str]],
    verdicts: NodeVerdicts | None,
    repository: RepositoryLink | None = None,
) -> CardSources:
    """Read the per-build inputs of the card: the test placements and owners, once."""
    tests = read_test_files(conn) or []
    nodes = {str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes").fetchall()}
    return CardSources(
        tags=tags,
        placements={test.path: test.placement for test in tests},
        test_owners={
            test.path: test.ref_id
            for test in tests
            if test.ref_id is not None and test.ref_id in nodes
        },
        verdicts=verdicts or NodeVerdicts(),
        repository=repository or RepositoryLink(),
    )


def card_fields(
    conn: sqlite3.Connection,
    ref_id: str,
    *,
    source: str | None,
    lifecycle: str,
    raw_extra: object,
    sources: CardSources,
) -> dict[str, object]:
    """The card fields of one node, keyed as the data file carries them."""
    extra = _extra(raw_extra)
    card: dict[str, object] = {
        "source": source or "",
        "source_url": sources.repository.source_url(source or ""),
        "lifecycle": lifecycle,
        "tags": sorted(sources.tags.get(ref_id, ())),
        "docs": doc_pairs(conn, ref_id),
        "tests": bound_tests(extra, sources, ref_id),
        "public_symbols": capped_public_symbols(conn, ref_id),
        "activity": card_activity(extra.get("activity")),
    }
    verdicts = sources.verdicts
    if verdicts.findings is not None:
        card["findings"] = [
            finding.as_dict()
            for finding in sorted(
                verdicts.findings.get(ref_id, ()),
                key=lambda f: (f.rule, f.severity, f.message),
            )
        ]
    if verdicts.debt is not None:
        debt = verdicts.debt.get(ref_id)
        card["debt"] = (
            {"score": debt.score, "reasons": list(debt.reasons)}
            if debt is not None
            else {"score": 0.0, "reasons": []}
        )
    return card


def doc_pairs(conn: sqlite3.Connection, ref_id: str) -> list[dict[str, object]]:
    """Every doc of the node with the worst status of its sync pairs, by path.

    A doc with no pair is :data:`DOC_UNPAIRED`: the index holds it and nothing
    has been held against it, which is not the same as ``ok``.
    """
    paths = [
        str(row["path"])
        for row in conn.execute(
            "SELECT path FROM docs WHERE ref_id = ? ORDER BY path", (ref_id,)
        ).fetchall()
    ]
    statuses: dict[str, set[str]] = {}
    for row in conn.execute(
        "SELECT doc_path, status FROM sync_state WHERE ref_id = ?", (ref_id,)
    ).fetchall():
        statuses.setdefault(str(row["doc_path"]), set()).add(str(row["status"]))
    return [
        {"path": path, "status": _worst(statuses.get(path, set()))}
        for path in sorted(set(paths) | set(statuses))
    ]


def _worst(statuses: set[str]) -> str:
    for status in _PAIR_STATUS_SEVERITY:
        if status in statuses:
            return status
    return DOC_UNPAIRED


def bound_tests(
    extra: Mapping[str, object], sources: CardSources, ref_id: str
) -> dict[str, object] | None:
    """The node's own test files, and the counts over the node and its parts.

    Read from ``extra["tests"]``, which the reindex rebuilds from the BDL-074
    binding over the node and its ``part_of`` descendants — the same files
    ``beadloom ctx`` reports. ``file_count``, ``count`` and ``placement`` are
    taken over all of those files, ``placement`` by what ``test_files`` records
    for each. ``files`` lists only the ones bound to *ref_id* itself: a part's
    file is listed at the part. A file whose owner the graph does not hold stays
    listed here, since no other node would list it. ``None`` when the binding
    does not cover the node.
    """
    tests = extra.get("tests")
    if not isinstance(tests, dict):
        return None
    listed = tests.get("test_files")
    files = sorted(str(path) for path in listed) if isinstance(listed, list) else []
    placement: dict[str, int] = {}
    for path in files:
        where = sources.placements.get(path)
        if where is not None:
            placement[where] = placement.get(where, 0) + 1
    count = tests.get("test_count")
    return {
        "files": [path for path in files if sources.test_owners.get(path, ref_id) == ref_id],
        "file_count": len(files),
        "count": count if isinstance(count, int) else 0,
        "placement": dict(sorted(placement.items())),
    }


def capped_public_symbols(conn: sqlite3.Connection, ref_id: str) -> dict[str, object]:
    """The first :data:`PUBLIC_SYMBOL_CAP` public names the node owns, and how many more."""
    names = public_symbol_names(conn, ref_id)
    return {
        "names": names[:PUBLIC_SYMBOL_CAP],
        "omitted": max(0, len(names) - PUBLIC_SYMBOL_CAP),
    }


def _extra(raw: object) -> dict[str, object]:
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def card_activity(recorded: object) -> dict[str, object] | None:
    """The recorded activity narrowed to :data:`CARD_ACTIVITY_KEYS`; ``None`` when none."""
    if not isinstance(recorded, dict):
        return None
    return {key: recorded[key] for key in CARD_ACTIVITY_KEYS if key in recorded}
