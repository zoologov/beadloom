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
  source root is derived by :func:`_source_root`, which descends one segment for
  as long as there is exactly one **supported** way down — supported meaning at
  least ``min_support`` sources agree on the next segment. On a
  package-per-domain tree that root comes out as ``src/<package>`` and the area
  is the package; on a feature-sliced tree it is ``src`` and the area is
  ``features`` or ``entities``. Neither spelling is known to this module — both
  fall out of the descent.

  ``min_support`` here is the dial the dominant-mapping half below already
  declares, reused rather than doubled: a second threshold governing the same
  question in a different unit is a knob whose two settings can quietly
  disagree. A genuine fork — two or more supported next segments — ends the
  descent, which is the whole point of the test, because a fork is where the
  areas begin and that depth is exactly what is being looked for.

  **A root is not a majority. It is the level above where the areas begin.**
  Governing the descent by ``threshold`` instead was tried and rejected
  (BDL-062 ``.9``), and it is worth writing down because it reads like the
  obvious symmetry with the dominance test below. At the shipped ``0.60`` a
  modal segment covering 6 of 10 sources is accepted, so the descent walks INTO
  the largest area and the root settles one level below where the areas start;
  every pair is then compared on the wrong segment. Measured by swapping the
  descent for a ``0.60`` majority: 5 of the 21 tests in
  ``tests/integration/graph/rules/test_doc_area_coherence.py`` fail, among them the rule's founding
  ``test_a_node_documented_outside_its_area_is_named``. Support answers *is
  there one shared way down*; a majority answers *which way down is most
  popular*, and only the first question has a root for its answer.

  Two populations consequently do not compare, and neither is dropped. A source
  **too short** to have a segment below the root is ``rootless`` (see
  :attr:`Convention.rootless`) — a node whose source IS the root. A source lying
  **outside** the root altogether, a second source tree too small to establish
  one of its own, is excluded from the comparison and counted in
  :attr:`Convention.outside_root`, which is why the population clause every
  finding carries ends ``"; N sit outside the source root"``. Under the old
  unanimity rule either one held a veto over the entire derivation; now each
  holds a count.

  **A second source tree large enough to hold a convention is read as a tree**
  (BDL-076 K3, ``beadloom-5o48``). A frontend of two or more nodes beside a
  backend is a supported second way down, so the descent forks at the very top
  and the root comes out empty. Read as it stands, the areas are then the tree
  names, no document names a tree, and the rule checked none of the pairs — 126
  of 126 on this repository once its site became 17 slice nodes. A fork at the
  top is ambiguous: a repository of top-level packages has its AREAS begin there,
  a backend beside a frontend has its TREES begin there, and the sources alone
  cannot tell which. So :func:`_readings` derives both — one root for the whole
  graph, and one root per supported top-level segment — and
  :func:`derive_convention` keeps the reading under which more pairs fall under a
  dominant mapping, which is the reading the documents corroborate. A tie keeps
  the single reading, and a graph whose root is not empty never reaches the
  second one, so a project with one source tree is read exactly as before. In
  the per-tree reading each area is qualified by its tree (two trees' ``shared``
  stay two areas), and :class:`SourceTree` gives the population line one clause
  per tree, because a total over two trees can hide one of them checking nothing.
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
  :attr:`Convention.unnamed`), never treated as agreement. Read per tree, each
  tree votes with its own areas; a tree whose documents name none of them is
  read at the depth the whole docs tree votes for, because one docs tree serves
  every source tree.

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
    from collections.abc import Sequence

    from beadloom.graph.rules.types import DocAreaCoherenceRule

#: ``rule_type`` of every non-liveness finding this module produces.
DOC_AREA_RULE_TYPE = "doc_area_coherence"

#: One node/doc pair as the index holds it: ``(ref_id, source, doc_path)``.
Pair = tuple[str, str, str]

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


def _source_root(
    sources: Sequence[tuple[str, ...]], *, min_support: int
) -> tuple[str, ...]:
    """The prefix the project's sources share, tolerating a minority that does not.

    This used to be the longest prefix EVERY source shares. That is a unanimity
    rule, and unanimity hands each individual source a veto over the whole
    derivation: one node whose source is ``site/`` — a committed asset tree
    beside the code — collapsed the root from ``src/beadloom`` to nothing for all
    85 other pairs of this repository, and the rule then either invented findings
    against a bogus convention or compared nothing at all (BDL-062 ``.9``,
    BDL-UX #195). Any project with a second source tree meets it on first contact.

    The descent takes one step for as long as there is **exactly one supported
    way down**, where supported means ``min_support`` sources agree on the next
    segment. That reuses the dial the dominant-mapping half already declares
    rather than inventing a second threshold, and it reads the same way there:
    *a fact resting on fewer than min_support observations is not a convention.*

    Three things end the descent, and each is the right answer to a different
    graph. **A genuine fork** — two or more supported next segments — is where
    the areas begin, which is precisely the depth being looked for. **No
    supported segment at all** means every candidate is a minority, so there is
    no shared root to speak of. And a source **too short to have this depth** is
    simply not counted here; it is a node whose source IS the root, and it is
    reported as ``rootless`` rather than allowed to stop the descent, because
    stopping on it would be the same veto in a different costume.

    A source that falls outside the returned root is never silently discarded:
    :func:`_tree` counts it, and :meth:`Convention.population` states it.
    """
    root: list[str] = []
    cluster = [segments for segments in sources if segments]
    depth = 0
    while True:
        counts = Counter(segments[depth] for segments in cluster if len(segments) > depth)
        supported = [segment for segment, count in counts.items() if count >= min_support]
        if len(supported) != 1:
            return tuple(root)
        segment = supported[0]
        root.append(segment)
        cluster = [
            segments
            for segments in cluster
            if len(segments) > depth and segments[depth] == segment
        ]
        depth += 1


@dataclass(frozen=True)
class Placement:
    """One node/doc pair reduced to the two segments the rule compares."""

    ref_id: str
    source: str
    doc_path: str
    source_area: str
    docs_area: str
    #: The source tree the pair was read in, by its root; empty when the graph
    #: was read as one tree.
    tree: str = ""


@dataclass(frozen=True)
class SourceTree:
    """One top-level source tree's share of the pairs, for the population line.

    Only the pairs it was handed are stored; what compared, what fell under a
    dominant mapping and what agreed are read off the convention's placements, so
    the per-tree clause and the totals cannot disagree.
    """

    root: str
    examined: int


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
    #: Pairs whose source lies OUTSIDE the derived source root — a second source
    #: tree too small to establish one of its own. They are excluded from the
    #: comparison and counted here rather than dropped, because a reader cannot
    #: otherwise tell a graph with no outliers from one whose outliers vanished
    #: (BDL-062 `.9`).
    outside_root: int = 0
    #: The source trees the graph was read as, when it was read as more than one.
    #: Empty for a graph with one source tree, whose population reads as it did.
    trees: tuple[SourceTree, ...] = ()

    @property
    def sampled(self) -> int:
        """Pairs that yielded a comparable segment on both sides."""
        return len(self.placements)

    @property
    def examined(self) -> int:
        """Every node/doc pair the graph offered, compared or not."""
        return self.sampled + self.rootless + self.unnamed + self.outside_root

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
            f"observations) and {agreeing} of those agree; "
            f"{self.outside_root} sit outside the source root"
        ) + self._per_tree()

    def _per_tree(self) -> str:
        """The population of each source tree, or nothing for a single-tree graph.

        A total over two trees can hide one of them checking nothing — which is
        the shape this rule had on this repository once its site became a tree —
        so each tree states its own share beside the total.
        """
        if not self.trees:
            return ""
        shares = []
        for tree in self.trees:
            compared = [p for p in self.placements if p.tree == tree.root]
            checked = [p for p in compared if p.source_area in self.dominant]
            agreeing = [
                p for p in checked if self.dominant[p.source_area].docs_area == p.docs_area
            ]
            shares.append(
                f"`{tree.root}`: {len(compared)} of {tree.examined} pairs compare, "
                f"{len(checked)} under a dominant mapping, {len(agreeing)} agree"
            )
        return "; per source tree, " + "; ".join(shares)

    def unverifiable_reason(self) -> str:
        """Why nothing could be checked, stated in the terms that would change it."""
        if not self.placements:
            return (
                f"no node/doc pair yields a comparable area — of "
                f"{self.examined} pairs, {self.rootless} have no source area below "
                f"the source root, {self.outside_root} sit outside it, and "
                f"{self.unnamed} have a doc path with no segment "
                f"at the depth this project names areas"
            ) + self._per_tree()
        areas = len({p.source_area for p in self.placements})
        return (
            f"no source area reaches a {self.threshold:.2f} majority over at least "
            f"{self.min_support} observations ({self.sampled} pairs across "
            f"{areas} source areas)"
        ) + self._per_tree()


def _area_votes(doc_segments: Sequence[tuple[str, ...]], vocabulary: set[str]) -> Counter[int]:
    """Where in each doc path a source area is named, tallied by depth.

    The first of the two passes described in the module docstring. Each doc path
    is asked where in it a source area is named; :func:`_area_depth` turns the
    tally into the one depth the second pass reads for every path.
    """
    depths: Counter[int] = Counter()
    for segments in doc_segments:
        match = next(
            (index for index, seg in enumerate(segments) if _normalise(seg) in vocabulary),
            None,
        )
        if match is not None:
            depths[match] += 1
    return depths


def _area_depth(votes: Counter[int]) -> int | None:
    """The depth that won the vote, or ``None`` when no doc path named an area.

    Ties break to the shallower depth, which is the one a project that names an
    area twice means.
    """
    if not votes:
        return None
    return min(votes, key=lambda index: (-votes[index], index))


def _pairs(conn: sqlite3.Connection) -> list[Pair]:
    """Every node/doc pair the index holds, as ``(ref_id, source, doc_path)``."""
    rows = conn.execute(
        "SELECT n.ref_id, n.source, d.path FROM nodes n "
        "JOIN docs d ON d.ref_id = n.ref_id "
        "WHERE n.source IS NOT NULL AND n.source != '' "
        "AND d.path IS NOT NULL AND d.path != '' "
        "ORDER BY n.ref_id, d.path"
    ).fetchall()
    return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]


@dataclass(frozen=True)
class _Tree:
    """One set of pairs, split against the source root derived from them alone."""

    #: The tree as the population line names it; empty in the single reading.
    label: str
    root: tuple[str, ...]
    #: Pairs whose source has a segment below the root, so an area to compare.
    rooted: tuple[Pair, ...]
    rootless: int
    outside_root: int

    def area_of(self, source_segments: tuple[str, ...]) -> str:
        """The area a rooted source belongs to, spelled the way doc paths compare."""
        return _normalise(source_segments[len(self.root)])

    def key_of(self, source_segments: tuple[str, ...]) -> str:
        """The area qualified by its tree, so two trees' ``shared`` stay two areas."""
        area = self.area_of(source_segments)
        return f"{self.label}/{area}" if self.label else area


def _tree(
    pairs: Sequence[Pair],
    sources: dict[str, tuple[str, ...]],
    *,
    min_support: int,
    named: bool,
) -> _Tree:
    """Derive the source root of *pairs* and sort every pair by where its source sits.

    The root is derived over the DISTINCT sources, as it always was, so a node
    documented twice does not count twice towards a way down. A *named* tree is
    labelled by its root; the single reading is not named, so nothing it prints
    changes.
    """
    distinct = dict.fromkeys(source for _, source, _ in pairs)
    root = _source_root(sorted(sources[source] for source in distinct), min_support=min_support)
    depth = len(root)
    rooted: list[Pair] = []
    outside_root = 0
    rootless = 0
    for pair in pairs:
        segments = sources[pair[1]]
        if segments[:depth] != root:
            outside_root += 1
        elif len(segments) > depth:
            rooted.append(pair)
        else:
            rootless += 1
    label = "/".join(root) if named else ""
    return _Tree(label, root, tuple(rooted), rootless, outside_root)


@dataclass(frozen=True)
class _Reading:
    """One way of cutting the sources into areas, and every pair accounted for."""

    placements: tuple[Placement, ...]
    rootless: int
    unnamed: int
    outside_root: int
    trees: tuple[SourceTree, ...] = ()


def _read(
    trees: Sequence[_Tree],
    sources: dict[str, tuple[str, ...]],
    docs: dict[str, tuple[str, ...]],
    *,
    outside_root: int,
) -> _Reading:
    """Place every rooted pair of *trees*, each tree read at its own area depth.

    A tree whose documents name none of its areas is read at the depth the
    project's documents as a whole name areas at: one docs tree serves every
    source tree, so the depth the other trees' documents establish is the
    project's own convention for it. This repository's site is that case — its
    slices are all documented in one directory named after no slice.
    """
    votes = [
        _area_votes(
            [docs[doc] for _, _, doc in tree.rooted],
            {tree.area_of(sources[source]) for _, source, _ in tree.rooted},
        )
        for tree in trees
    ]
    pooled = _area_depth(sum(votes, Counter()))
    placements: list[Placement] = []
    unnamed = 0
    shares: list[SourceTree] = []
    for tree, tree_votes in zip(trees, votes, strict=True):
        own = _area_depth(tree_votes)
        depth = own if own is not None else pooled
        placed = [
            Placement(
                ref_id=ref_id,
                source=source,
                doc_path=doc_path,
                source_area=tree.key_of(sources[source]),
                docs_area=_normalise(docs[doc_path][depth]),
                tree=tree.label,
            )
            for ref_id, source, doc_path in tree.rooted
            if depth is not None and len(docs[doc_path]) > depth
        ]
        # A doc path too short to have a segment at the depth, or a tree read at
        # no depth at all, compares nothing — counted, never taken for agreement.
        unnamed += len(tree.rooted) - len(placed)
        placements.extend(placed)
        examined = len(tree.rooted) + tree.rootless + tree.outside_root
        shares.append(SourceTree(root=tree.label, examined=examined))
    return _Reading(
        placements=tuple(placements),
        rootless=sum(tree.rootless for tree in trees),
        unnamed=unnamed,
        outside_root=outside_root + sum(tree.outside_root for tree in trees),
        # The single reading's one tree is unnamed and states no per-tree clause.
        trees=tuple(share for share in shares if share.root),
    )


def _readings(pairs: Sequence[Pair], *, min_support: int) -> list[_Reading]:
    """The one reading every graph gets, and the per-tree reading where it applies.

    The per-tree reading exists only when the descent forks at the very top —
    two or more top-level segments each carrying ``min_support`` sources. That
    fork is ambiguous: a repository of top-level packages has its AREAS begin
    there, and a backend beside a frontend has its SOURCE TREES begin there. The
    sources cannot tell the two apart, so both readings are derived and
    :func:`derive_convention` lets the documents decide. A graph whose root is
    not empty never reaches this second reading, and is read exactly as before.
    """
    sources = {source: _directory_segments(source) for _, source, _ in pairs}
    docs = {doc: _directory_segments(doc) for _, _, doc in pairs}
    single = _tree(pairs, sources, min_support=min_support, named=False)
    readings = [_read([single], sources, docs, outside_root=0)]
    if single.root:
        return readings

    by_top: dict[str, list[Pair]] = {}
    for pair in pairs:
        segments = sources[pair[1]]
        by_top.setdefault(segments[0] if segments else "", []).append(pair)
    supported = sorted(
        top
        for top, members in by_top.items()
        if top and len({source for _, source, _ in members}) >= min_support
    )
    if len(supported) < 2:
        return readings

    trees = [
        _tree(by_top[top], sources, min_support=min_support, named=True) for top in supported
    ]
    minority = sum(len(members) for top, members in by_top.items() if top not in supported)
    readings.append(_read(trees, sources, docs, outside_root=minority))
    return readings


def _convention(reading: _Reading, *, threshold: float, min_support: int) -> Convention:
    """The dominant mappings of one reading, and the reading's counts beside them."""
    observed: dict[str, Counter[str]] = {}
    for placement in reading.placements:
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
        placements=reading.placements,
        dominant=dominant,
        threshold=threshold,
        min_support=min_support,
        rootless=reading.rootless,
        unnamed=reading.unnamed,
        outside_root=reading.outside_root,
        trees=reading.trees,
    )


def derive_convention(
    conn: sqlite3.Connection, *, threshold: float, min_support: int
) -> Convention:
    """Read the graph's own source-to-docs convention out of the index.

    Pure derivation: nothing here knows a directory name, and the same call on a
    feature-sliced graph learns that graph's areas instead.

    Where :func:`_readings` offers two readings, the one under which more pairs
    fall under a dominant mapping is kept — the one the documents corroborate —
    and then the one under which more pairs compare. A tie keeps the single
    reading, which is how the rule read every graph before source trees existed.
    """
    conventions = [
        _convention(reading, threshold=threshold, min_support=min_support)
        for reading in _readings(_pairs(conn), min_support=min_support)
    ]
    # `max` returns the FIRST of equal candidates, and the single reading is first.
    return max(conventions, key=lambda convention: (len(convention.checked), convention.sampled))


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
                    # A TOTAL stand-down carries the severity the project
                    # declared. This rule ships `warn`, so an adopter is
                    # unaffected; a project that escalated it to `error` gets an
                    # escalation that does not evaporate the moment the rule
                    # stops working (BDL-062 `.9`).
                    severity=rule.severity,
                )
            )
            continue
        violations.extend(
            _contradiction(rule, convention, placement)
            for placement in convention.contradicting
        )
    return violations
