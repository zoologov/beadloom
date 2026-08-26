# beadloom:domain=graph
# beadloom:feature=rule-engine
"""``doc-area-coherence`` — hold a graph to the docs placement it already keeps.

**One responsibility:** read the source-to-docs placement convention out of the
indexed graph, and name the nodes that contradict it.

**No layout is written down here, anywhere.** That was the flaw in the first
sketch of this rule: a literal such as ``docs/domains/<package>/`` ships one
project's tree as every adopter's, is wrong for a feature-sliced project the day
it is installed, and turns a check about the graph into a check about Beadloom.
Everything this module compares is derived from the graph it is handed.

How the two sides of a pair are reduced to one comparable segment:

* **The source area** is the segment directly below the *source root*, and the
  source root is the longest directory prefix every node source shares. On a
  package-per-domain tree that root is ``src/<package>`` and the area is the
  package; on a feature-sliced tree it is ``src`` and the area is ``features`` or
  ``entities``. Neither spelling is known to this module — both fall out of the
  common prefix.
* **The docs area** is the doc-path segment at the *area depth*, and the area
  depth is itself derived. It is NOT the segment below the common prefix of the
  doc paths, and the reason is measured: on this repository documents sit at
  three different depths, which collapses that common prefix to nothing and makes
  the "segment below the docs root" the ``domains``/``services`` bucket rather
  than the area inside it — precisely the segment that cannot disagree.

  So the area depth is found instead of assumed, in two passes. The first asks
  each doc path where in it a source area is named, using the vocabulary the
  source side already produced; the depth that answer lands at most often is the
  depth at which this project names areas. The second pass then reads EVERY doc
  path's segment at that depth, whatever it is called — which is what lets the
  rule see a document filed under a directory that names no source area at all,
  the commonest shape of the drift it exists to catch. A doc path too short to
  have a segment at that depth yields no comparison and is COUNTED as such (see
  :attr:`Convention.unnamed`), never treated as agreement.

A mapping ``source area -> docs area`` is **dominant** when it covers at least
``threshold`` of the pairs observed for that source area *and* rests on at least
``min_support`` of them. The second condition is not decoration: without it every
area holding a single documented node is "unanimous" at one observation, and a
graph of six nodes in six areas reports a clean sweep having verified nothing —
the exact failure this rule exists to refuse.

**When no mapping is dominant the rule reports that it checked nothing**, and is
counted among the rules ``lint`` says were unable to check anything. A flat docs
tree, a project mid-migration and a graph too small to hold a convention are all
legitimately unverifiable, and none of them is clean. ``unverifiable`` is a state
of its own here, never a quiet ``pass``.

Severity ships ``warn``. A convention check is a check about house style, and one
that fails an adopter's first ``beadloom ci`` on their own house style is a rule
they will switch off; a project that wants it enforced raises it to ``error`` in
its own ``rules.yml``, which is what this repository does.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.graph.rules.types import Violation, liveness_finding

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules.types import DocAreaCoherenceRule

#: ``rule_type`` of every non-liveness finding this module produces.
DOC_AREA_RULE_TYPE = "doc_area_coherence"

#: What to do about a node whose doc contradicts the graph's own convention.
DOC_AREA_HINT = (
    "move the document into the docs area the rest of the graph uses for this "
    "source area, or change the node's `docs:` to the area it genuinely belongs to"
)


def _normalise(segment: str) -> str:
    """One spelling for a path segment, so ``doc_sync`` and ``doc-sync`` compare equal.

    A source area is an import name and a docs area is a directory a human types,
    so the same area is routinely spelled with an underscore on one side and a
    hyphen on the other. Folding the two is not a layout assumption — it is the
    identifier rule the two naming conventions differ by.
    """
    return segment.replace("-", "_").casefold()


def _directory_segments(path: str) -> tuple[str, ...]:
    """The directory part of *path*, split into segments.

    A trailing segment carrying a suffix is treated as a file name and dropped, so
    ``a/b/c.py`` and ``a/b/c/`` both reduce to the directories that contain the
    thing. A directory whose own name carries a dot is misread as a file by this
    test; that costs one segment of depth and never invents one.
    """
    cleaned = path.strip().strip("/")
    if not cleaned:
        return ()
    segments = PurePosixPath(cleaned).parts
    if segments and PurePosixPath(segments[-1]).suffix:
        segments = segments[:-1]
    return tuple(segments)


def _common_prefix(paths: list[tuple[str, ...]]) -> tuple[str, ...]:
    """The longest leading run of segments every entry of *paths* shares."""
    if not paths:
        return ()
    shared: list[str] = []
    for column in zip(*paths, strict=False):
        first = column[0]
        if any(segment != first for segment in column):
            break
        shared.append(first)
    return tuple(shared)


@dataclass(frozen=True)
class Placement:
    """One node/doc pair reduced to the two segments the rule compares."""

    ref_id: str
    source: str
    doc_path: str
    source_area: str
    docs_area: str


@dataclass(frozen=True)
class DominantMapping:
    """The docs area a source area is agreed to use, and how strong the agreement is."""

    docs_area: str
    agreeing: int
    observed: int


@dataclass(frozen=True)
class Convention:
    """What the graph says about itself, and what it declined to say.

    The three counts that are *not* ``placements`` exist so a reader can judge the
    verdict rather than take it: a rule that compared 79 of 83 pairs has not
    checked 83, and saying "79" without saying which four were dropped is the
    green count that is not a checked count.
    """

    placements: tuple[Placement, ...]
    dominant: dict[str, DominantMapping]
    threshold: float
    min_support: int
    #: Pairs whose source sits at the source root itself, so there is no area
    #: below it to compare (the root node of a single-package tree).
    rootless: int
    #: Pairs whose doc path names no source area anywhere in it.
    unnamed: int

    @property
    def sampled(self) -> int:
        """Pairs that yielded a comparable segment on both sides."""
        return len(self.placements)

    @property
    def examined(self) -> int:
        """Every node/doc pair the graph offered, compared or not."""
        return self.sampled + self.rootless + self.unnamed

    @property
    def checked(self) -> tuple[Placement, ...]:
        """The sampled pairs that fall under a dominant mapping."""
        return tuple(p for p in self.placements if p.source_area in self.dominant)

    @property
    def contradicting(self) -> tuple[Placement, ...]:
        """The checked pairs whose docs area is not the one their area agreed on."""
        return tuple(
            p for p in self.checked if self.dominant[p.source_area].docs_area != p.docs_area
        )

    @property
    def is_derivable(self) -> bool:
        """Whether the graph agreed on anything at all."""
        return bool(self.dominant)

    def population(self) -> str:
        """The clause every finding carries, so no count over-claims on its own."""
        agreeing = len(self.checked) - len(self.contradicting)
        return (
            f"derived from {self.examined} node/doc pairs: {self.sampled} compare, "
            f"{len(self.checked)} fall under a dominant mapping "
            f"(majority {self.threshold:.2f} over at least {self.min_support} "
            f"observations) and {agreeing} of those agree"
        )

    def unverifiable_reason(self) -> str:
        """Why nothing could be checked, stated in the terms that would change it."""
        if not self.placements:
            return (
                f"no node/doc pair yields a comparable area — of "
                f"{self.examined} pairs, {self.rootless} have no source area below "
                f"the source root and {self.unnamed} have a doc path with no segment "
                f"at the depth this project names areas"
            )
        areas = len({p.source_area for p in self.placements})
        return (
            f"no source area reaches a {self.threshold:.2f} majority over at least "
            f"{self.min_support} observations ({self.sampled} pairs across "
            f"{areas} source areas)"
        )


def _area_depth(doc_segments: list[tuple[str, ...]], vocabulary: set[str]) -> int | None:
    """The depth at which this project's doc paths name an area, or ``None``.

    The first of the two passes described in the module docstring. Each doc path
    is asked where in it a source area is named; the depth that wins the vote is
    the one the second pass reads for every path. Ties break to the shallower
    depth, which is the one a project that names an area twice means.
    """
    depths: Counter[int] = Counter()
    for segments in doc_segments:
        match = next(
            (index for index, seg in enumerate(segments) if _normalise(seg) in vocabulary),
            None,
        )
        if match is not None:
            depths[match] += 1
    if not depths:
        return None
    return min(depths, key=lambda index: (-depths[index], index))


def _placements(conn: sqlite3.Connection) -> tuple[list[Placement], int, int]:
    """Every comparable node/doc pair in the index, plus what could not compare."""
    rows = conn.execute(
        "SELECT n.ref_id, n.source, d.path FROM nodes n "
        "JOIN docs d ON d.ref_id = n.ref_id "
        "WHERE n.source IS NOT NULL AND n.source != '' "
        "AND d.path IS NOT NULL AND d.path != '' "
        "ORDER BY n.ref_id, d.path"
    ).fetchall()
    pairs = [(str(row[0]), str(row[1]), str(row[2])) for row in rows]

    sources = {source: _directory_segments(source) for _, source, _ in pairs}
    source_depth = len(_common_prefix(sorted(sources.values())))
    vocabulary = {
        _normalise(segments[source_depth])
        for segments in sources.values()
        if len(segments) > source_depth
    }

    rooted = [
        (ref_id, source, doc_path)
        for ref_id, source, doc_path in pairs
        if len(sources[source]) > source_depth
    ]
    rootless = len(pairs) - len(rooted)

    docs = {doc_path: _directory_segments(doc_path) for _, _, doc_path in rooted}
    depth = _area_depth([docs[doc_path] for _, _, doc_path in rooted], vocabulary)
    if depth is None:
        # No doc path names any source area, so there is no depth at which this
        # project writes an area down. Nothing compares — which is a fact the
        # caller reports, not one it rounds down to "everything is fine".
        return [], rootless, len(rooted)

    placements: list[Placement] = []
    unnamed = 0
    for ref_id, source, doc_path in rooted:
        segments = docs[doc_path]
        if len(segments) <= depth:
            unnamed += 1
            continue
        placements.append(
            Placement(
                ref_id=ref_id,
                source=source,
                doc_path=doc_path,
                source_area=_normalise(sources[source][source_depth]),
                docs_area=_normalise(segments[depth]),
            )
        )
    return placements, rootless, unnamed


def derive_convention(
    conn: sqlite3.Connection, *, threshold: float, min_support: int
) -> Convention:
    """Read the graph's own source-to-docs convention out of the index.

    Pure derivation: nothing here knows a directory name, and the same call on a
    feature-sliced graph learns that graph's areas instead.
    """
    placements, rootless, unnamed = _placements(conn)

    observed: dict[str, Counter[str]] = {}
    for placement in placements:
        observed.setdefault(placement.source_area, Counter())[placement.docs_area] += 1

    dominant: dict[str, DominantMapping] = {}
    for source_area, counts in observed.items():
        docs_area, agreeing = max(sorted(counts.items()), key=lambda item: item[1])
        total = sum(counts.values())
        if agreeing < min_support or agreeing / total < threshold:
            continue
        dominant[source_area] = DominantMapping(
            docs_area=docs_area, agreeing=agreeing, observed=total
        )

    return Convention(
        placements=tuple(placements),
        dominant=dominant,
        threshold=threshold,
        min_support=min_support,
        rootless=rootless,
        unnamed=unnamed,
    )


def doc_area_inert_reason(conn: sqlite3.Connection, rule: DocAreaCoherenceRule) -> str | None:
    """Why *rule* can check nothing against this graph, or ``None`` when it can.

    Shared with :mod:`.liveness` so the count ``lint`` prints and the finding the
    rule writes cannot disagree about whether it stood down.
    """
    convention = derive_convention(
        conn, threshold=rule.threshold, min_support=rule.min_support
    )
    if convention.is_derivable:
        return None
    return convention.unverifiable_reason()


def _contradiction(rule: DocAreaCoherenceRule, convention: Convention, at: Placement) -> Violation:
    """One node whose doc sits outside the area its own graph agreed on."""
    agreed = convention.dominant[at.source_area]
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=DOC_AREA_RULE_TYPE,
        severity=rule.severity,
        file_path=at.doc_path,
        line_number=None,
        from_ref_id=at.ref_id,
        to_ref_id=None,
        message=(
            f"`{at.ref_id}` has its source under `{at.source_area}` but is documented "
            f"under `{at.docs_area}` ({at.doc_path}); this graph places "
            f"{agreed.agreeing} of {agreed.observed} `{at.source_area}` nodes under "
            f"`{agreed.docs_area}` — {convention.population()}"
        ),
        remediation=DOC_AREA_HINT,
    )


def evaluate_doc_area_coherence_rules(
    conn: sqlite3.Connection, rules: list[DocAreaCoherenceRule]
) -> list[Violation]:
    """Report every node documented outside its graph's own convention.

    A rule whose graph agrees on nothing reports **that**, as a ``rule_liveness``
    finding, instead of returning an empty list a reader would take for a pass.
    """
    violations: list[Violation] = []
    for rule in rules:
        convention = derive_convention(
            conn, threshold=rule.threshold, min_support=rule.min_support
        )
        if not convention.is_derivable:
            violations.append(
                liveness_finding(
                    rule_name=rule.name,
                    rule_description=rule.description,
                    message=(
                        f"Rule '{rule.name}' checked nothing: "
                        f"{convention.unverifiable_reason()}. No node was cleared — "
                        f"the convention this rule enforces could not be read off "
                        f"this graph"
                    ),
                    remediation=(
                        "place documents so that nodes from one source area share a "
                        "docs area, or lower `min_support`/`threshold` if the graph "
                        "is genuinely too small to hold a convention"
                    ),
                )
            )
            continue
        violations.extend(
            _contradiction(rule, convention, placement)
            for placement in convention.contradicting
        )
    return violations
