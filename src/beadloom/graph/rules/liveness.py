# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Rule liveness: report a rule whose candidate set is empty, for every rule type.

**One responsibility:** decide whether a rule *can* produce a verdict at all, and
say so when it cannot. Nothing here evaluates architecture — a finding from this
module is a statement about the **configuration**, never about the code.

Why it exists (BDL-UX #172, BDL-061.48): a rule that cannot match is
indistinguishable from a rule that passed. Two of this project's own twelve
rules were incapable of firing for months while ``lint --strict`` printed
``12 rules, 0 violations``. ``beadloom-mr2l.43`` closed that for
``forbid_import`` only; this module closes it for the other nine rule types, so
``N rules evaluated`` stops being a count of rules that looked at nothing.

**The finding and the COUNT are separable, and for two rule types they are
separated.** ``forbid_import`` and ``scenario_coverage`` state their own liveness
where the diagnosis is — which glob, which leg — and this module answers the
other question, *how many of my rules checked nothing*, for every type.
``scenario_coverage`` is therefore counted here and reported there.
``forbid_import`` is reported there and not counted here, because its liveness
channel also carries statements about individual ``exempt`` entries, which the
SPEC deliberately excludes from ``rules_inert``. That asymmetry is the limit this
module has not closed, stated rather than left to be discovered.

**What "cannot fire" means per rule type** — the same table appears in
``docs/domains/graph/features/rule-engine/SPEC.md``:

===============================  =========================================================
Rule type                        Inert when
===============================  =========================================================
``deny``                         ``from``/``to`` matcher selects 0 nodes
``require``                      ``for`` selects 0 nodes, or ``has_edge_to`` selects 0
                                 (then every matched node fails, which is equally broken)
``forbid_cycles``                0 live edges of the declared ``edge_kind``(s)
``forbid_import``                glob matches 0 indexed files / 0 indexed import paths
                                 (owned by :mod:`.evaluators` — see below)
``forbid``                       ``from``/``to`` selects 0 nodes, or 0 edges of ``edge_kind``
``layers``                       fewer than 2 layers are populated, or no live edge of
                                 ``edge_kind`` runs between two layered nodes
``check``                        ``for`` selects 0 nodes, or no threshold is set
``unregistered_feature_...``     ``for`` selects 0 nodes, or none of them declares a source
``module_coverage``              0 candidate modules under ``source_root``
``scenario_coverage``            the ``features`` glob matches 0 files, which stands the
                                 WHOLE rule down. A dead ``for`` matcher or ``references``
                                 glob stands ONE leg down and is not inertness. Counted
                                 here, reported by :mod:`.scenario_coverage`
``doc_area_coherence``           no source-to-docs mapping in the graph reaches the
                                 majority threshold over the minimum support, so the
                                 convention the rule enforces cannot be read off the graph
                                 at all. Counted here, reported by :mod:`.doc_area`
``summary_facts``                no node ``summary`` in the graph states a number or a
                                 version the project computes a fact for, so there is no
                                 claim to check. Counted here, reported by
                                 :mod:`.summary_facts`
===============================  =========================================================

Two deliberate boundaries, named rather than left to be discovered:

* ``forbid_import`` liveness stays in :mod:`.evaluators`: its dead-glob and
  dead-exemption findings are byproducts of the single scan of ``code_imports``
  that the rule evaluation already performs, and the dead-*exemption* half can
  only be known from which exemptions that scan used. Splitting the pair would
  cost a second scan and separate two halves of one diagnosis. This module owns
  the shared *shape* of a liveness finding (:func:`liveness_finding`) so the two
  channels cannot drift.
* ``doc_area_coherence`` liveness is REPORTED by :mod:`.doc_area`, for the same
  reason and by the same split: the finding must state the sample size and the
  threshold the graph failed to reach, which a generic "cannot fire" cannot, and
  the predicate counted with here is that module's own
  :func:`~beadloom.graph.rules.doc_area.doc_area_inert_reason`.
* ``summary_facts`` liveness is REPORTED by :mod:`.summary_facts`, by the same
  split again, and it carries a second kind of finding this module has no shape
  for: a claim naming a fact the project DECLINED to compute is unverifiable on
  its own, one node at a time, while the rule as a whole is still live.
* ``scenario_coverage`` liveness is REPORTED by :mod:`.scenario_coverage`, per
  leg, because the finding must name which of the four legs stood down and which
  glob or matcher did it — and because those legs are decided by files on disk
  that no index holds. The predicate counted with here is that module's own
  :func:`~beadloom.graph.rules.scenario_coverage.inert_reason`, not a second copy
  of it, so the count cannot drift from the control flow it describes.
* ``deny`` liveness is matcher-based only. An index with **no resolved imports**
  makes every ``deny`` rule inert too, but that is a property of the index, not
  of the rule, and ``lint``'s header already states it (``0 imports resolved``).
  The same reasoning keeps the whole pass silent on an empty graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.cycles import _live_lifecycle_clause
from beadloom.graph.rules.evaluators import _disk_modules
from beadloom.graph.rules.loader import validate_rules
from beadloom.graph.rules.types import (
    CardinalityRule,
    CycleRule,
    DenyRule,
    DocAreaCoherenceRule,
    ForbidEdgeRule,
    LayerRule,
    ModuleCoverageRule,
    NodeMatcher,
    RequireRule,
    ScenarioCoverageRule,
    SummaryFactsRule,
    UnregisteredFeatureCandidateRule,
    liveness_finding,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.rules.types import Rule, Violation

#: What to do about a rule that cannot fire. Carried as the ``remediation`` of
#: every finding here, because the alternative to fixing it is not "ignore it" —
#: it is deleting a check that has been reporting green without looking.
INERT_RULE_HINT = (
    "make the rule name something that exists — a node, a tag, an edge kind, a "
    "threshold, a source root — or delete it: a rule that cannot fire is counted "
    "in `N rules evaluated` and checks nothing"
)


# ---------------------------------------------------------------------------
# The graph inventory every check below asks questions of
# ---------------------------------------------------------------------------


class _GraphFacts:
    """The few facts about the index that decide whether a rule can fire.

    Loaded once per lint run and queried per rule, so adding liveness costs a
    handful of aggregate queries rather than one per rule.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        from beadloom.graph.loader import get_node_tags

        self._conn = conn
        rows = conn.execute("SELECT ref_id, kind, source FROM nodes").fetchall()
        self.nodes: list[tuple[str, str, str | None]] = [
            (str(r[0]), str(r[1]), None if r[2] is None else str(r[2])) for r in rows
        ]
        self.ref_ids: set[str] = {ref_id for ref_id, _, _ in self.nodes}
        self._tags_cache: dict[str, set[str]] = {}
        self._get_node_tags = get_node_tags

    @property
    def is_empty(self) -> bool:
        """True when the index holds no nodes at all (a clone before reindex)."""
        return not self.nodes

    def tags(self, ref_id: str) -> set[str]:
        """Tags of *ref_id*, cached across every rule in the run."""
        if ref_id not in self._tags_cache:
            self._tags_cache[ref_id] = self._get_node_tags(self._conn, ref_id)
        return self._tags_cache[ref_id]

    def matched(self, matcher: NodeMatcher) -> list[str]:
        """Every node ref_id *matcher* selects."""
        return [
            ref_id
            for ref_id, kind, _ in self.nodes
            if matcher.matches(ref_id, kind, tags=self.tags(ref_id))
        ]

    def sources(self, ref_ids: list[str]) -> list[str]:
        """The non-empty ``source`` values of the given nodes."""
        by_ref = {ref_id: source for ref_id, _, source in self.nodes}
        wanted = set(ref_ids)
        return [
            source for ref_id, source in by_ref.items() if ref_id in wanted and source
        ]

    def edge_kind_count(self, kind: str) -> int:
        """How many edges of *kind* exist, whatever their lifecycle."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM edges WHERE kind = ?", (kind,)
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def live_edges_of_kinds(self, kinds: tuple[str, ...]) -> list[tuple[str, str]]:
        """``(src, dst)`` of every LIVE edge whose kind is in *kinds*.

        Only ``active`` edges count, matching what the cycle and layer
        evaluators actually traverse (BDL-037 Principle 8) — a rule whose only
        edges are ``planned`` cannot fire on them either.
        """
        if not kinds:
            return []
        placeholders = ", ".join("?" for _ in kinds)
        life_clause, life_params = _live_lifecycle_clause(self._conn)
        rows = self._conn.execute(
            f"SELECT src_ref_id, dst_ref_id FROM edges WHERE kind IN ({placeholders})"  # noqa: S608
            f"{life_clause}",
            (*kinds, *life_params),
        ).fetchall()
        return [(str(r[0]), str(r[1])) for r in rows]

    def indexed_modules_under(self, source_root: str) -> int:
        """How many distinct indexed modules sit under *source_root*."""
        row = self._conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM code_symbols WHERE file_path LIKE ?",
            (source_root + "%",),
        ).fetchone()
        return int(row[0]) if row is not None else 0


# ---------------------------------------------------------------------------
# Per-matcher and per-rule-type reasons
# ---------------------------------------------------------------------------


def _matcher_reason(matcher: NodeMatcher, label: str, facts: _GraphFacts) -> str | None:
    """Why *matcher* selects nothing, or None when it selects at least one node.

    The unknown-``ref_id`` case is named specifically because it is the one the
    loader can diagnose exactly; the rest fall back to naming the tag or kind
    that no node carries.
    """
    if matcher.ref_id is not None and matcher.ref_id not in facts.ref_ids:
        return f"its `{label}` names ref_id '{matcher.ref_id}', which is not in the graph"
    if facts.matched(matcher):
        return None
    if matcher.tag is not None:
        return f"its `{label}` tag '{matcher.tag}' is carried by no node"
    if matcher.kind is not None:
        return (
            f"its `{label}` kind '{matcher.kind}' matches none of the "
            f"{len(facts.nodes)} nodes in the graph"
        )
    return f"its `{label}` matches none of the {len(facts.nodes)} nodes in the graph"


def _reasons_for_matchers(
    facts: _GraphFacts, *pairs: tuple[NodeMatcher, str]
) -> list[str]:
    """Collect the reasons for several matchers, in declaration order."""
    return [
        reason
        for matcher, label in pairs
        if (reason := _matcher_reason(matcher, label, facts)) is not None
    ]


def _deny_reasons(rule: DenyRule, facts: _GraphFacts) -> list[str]:
    return _reasons_for_matchers(facts, (rule.from_matcher, "from"), (rule.to_matcher, "to"))


def _require_reasons(rule: RequireRule, facts: _GraphFacts) -> list[str]:
    reasons = _reasons_for_matchers(facts, (rule.for_matcher, "for"))
    target = _matcher_reason(rule.has_edge_to, "has_edge_to", facts)
    if target is not None:
        # The mirror image of an empty subject: the rule CAN iterate, but no node
        # could ever satisfy it, so every match is a violation of the rule's
        # wording rather than of the architecture.
        reasons.append(f"{target} — every node it matches would fail")
    return reasons


def _cycle_reasons(rule: CycleRule, facts: _GraphFacts) -> list[str]:
    kinds = (rule.edge_kind,) if isinstance(rule.edge_kind, str) else rule.edge_kind
    if facts.live_edges_of_kinds(kinds):
        return []
    return [f"the graph holds no live '{', '.join(kinds)}' edge to search for cycles in"]


def _forbid_edge_reasons(rule: ForbidEdgeRule, facts: _GraphFacts) -> list[str]:
    reasons = _reasons_for_matchers(
        facts, (rule.from_matcher, "from"), (rule.to_matcher, "to")
    )
    if rule.edge_kind is not None and facts.edge_kind_count(rule.edge_kind) == 0:
        reasons.append(f"the graph holds no '{rule.edge_kind}' edge")
    return reasons


#: A layered rule needs two populated layers before "above" and "below" mean
#: anything: with one, there is no direction for an edge to violate.
_MIN_POPULATED_LAYERS = 2


def _layer_reasons(rule: LayerRule, facts: _GraphFacts) -> list[str]:
    tag_to_index = {layer.tag: idx for idx, layer in enumerate(rule.layers)}
    layer_of: dict[str, int] = {}
    for ref_id, _, _ in facts.nodes:
        for tag in sorted(facts.tags(ref_id)):
            if tag in tag_to_index:
                layer_of[ref_id] = tag_to_index[tag]
                break

    carried = set(layer_of.values())
    if len(carried) < _MIN_POPULATED_LAYERS:
        empty = sorted(tag for tag, idx in tag_to_index.items() if idx not in carried)
        return [
            "fewer than two of its layers are populated (no node carries "
            f"{', '.join(repr(tag) for tag in empty)})"
        ]
    if not any(
        src in layer_of and dst in layer_of
        for src, dst in facts.live_edges_of_kinds((rule.edge_kind,))
    ):
        return [f"no live '{rule.edge_kind}' edge runs between two of its layers"]
    return []


def _cardinality_reasons(rule: CardinalityRule, facts: _GraphFacts) -> list[str]:
    reasons = _reasons_for_matchers(facts, (rule.for_matcher, "for"))
    if rule.max_symbols is None and rule.max_files is None and rule.min_doc_coverage is None:
        reasons.append(
            "no threshold is set (max_symbols, max_files and min_doc_coverage are "
            "all unset), so nothing is compared"
        )
    return reasons


def _unregistered_reasons(
    rule: UnregisteredFeatureCandidateRule, facts: _GraphFacts
) -> list[str]:
    reasons = _reasons_for_matchers(facts, (rule.for_matcher, "for"))
    if reasons:
        return reasons
    matched = facts.matched(rule.for_matcher)
    if not facts.sources(matched):
        return [
            f"none of the {len(matched)} nodes its `for` matches declares a `source`, "
            "so it has no files to inspect"
        ]
    return []


def _module_coverage_reasons(
    rule: ModuleCoverageRule, facts: _GraphFacts, project_root: Path | None
) -> list[str]:
    on_disk = _disk_modules(project_root, rule.source_root) if project_root is not None else []
    if on_disk or facts.indexed_modules_under(rule.source_root):
        return []
    return [
        f"its source_root '{rule.source_root}' holds no module, on disk or in the index"
    ]


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def _scenario_coverage_reasons(
    rule: ScenarioCoverageRule, project_root: Path | None
) -> list[str]:
    """Whether the rule can check anything, asked of the module that owns it.

    The predicate is
    :func:`~beadloom.graph.rules.scenario_coverage.inert_reason` rather than a
    copy of it here: this rule's legs are decided by files on disk that no index
    holds, and a second implementation of "is there a suite" would be free to
    drift from the control flow it describes.

    Silent without a *project_root*: the globs are rooted at it, so there is
    nothing to decide rather than nothing to check.
    """
    if project_root is None:
        return []
    from beadloom.graph.rules.scenario_coverage import inert_reason

    reason = inert_reason(rule, project_root)
    return [reason] if reason is not None else []


def _doc_area_reasons(rule: DocAreaCoherenceRule, conn: sqlite3.Connection) -> list[str]:
    """Whether the rule can check anything, asked of the module that owns it.

    Delegated to :func:`~beadloom.graph.rules.doc_area.doc_area_inert_reason` for
    the same reason ``scenario_coverage`` is: the predicate IS the derivation, and
    a second implementation of "does this graph agree on anything" would be free
    to say the rule fired on a run where it stood down.
    """
    from beadloom.graph.rules.doc_area import doc_area_inert_reason

    reason = doc_area_inert_reason(conn, rule)
    return [reason] if reason is not None else []


def _summary_facts_reasons(conn: sqlite3.Connection, project_root: Path | None) -> list[str]:
    """Whether the rule can check anything, asked of the module that owns it.

    Delegated to
    :func:`~beadloom.graph.rules.summary_facts.summary_facts_inert_reason` for the
    same reason ``doc_area_coherence`` is: the predicate IS the extraction, and a
    second implementation of "does any summary here state a number" would be free
    to say the rule fired on a run where it stood down.
    """
    from beadloom.graph.rules.summary_facts import summary_facts_inert_reason

    reason = summary_facts_inert_reason(conn, project_root)
    return [reason] if reason is not None else []


def _reasons_for_rule(
    rule: Rule, facts: _GraphFacts, conn: sqlite3.Connection, project_root: Path | None
) -> list[str]:
    """Every reason *rule* cannot fire, or an empty list when it can.

    ``forbid_import`` is absent by design: :mod:`.evaluators` reports it from the
    import scan it already runs (see the module docstring). ``scenario_coverage``,
    ``doc_area_coherence`` and ``summary_facts`` are present for the COUNT and
    absent from :func:`evaluate_rule_liveness`, which is the other half of the
    same boundary.
    """
    if isinstance(rule, DenyRule):
        return _deny_reasons(rule, facts)
    if isinstance(rule, RequireRule):
        return _require_reasons(rule, facts)
    if isinstance(rule, CycleRule):
        return _cycle_reasons(rule, facts)
    if isinstance(rule, ForbidEdgeRule):
        return _forbid_edge_reasons(rule, facts)
    if isinstance(rule, LayerRule):
        return _layer_reasons(rule, facts)
    if isinstance(rule, CardinalityRule):
        return _cardinality_reasons(rule, facts)
    if isinstance(rule, UnregisteredFeatureCandidateRule):
        return _unregistered_reasons(rule, facts)
    if isinstance(rule, ModuleCoverageRule):
        return _module_coverage_reasons(rule, facts, project_root)
    if isinstance(rule, ScenarioCoverageRule):
        return _scenario_coverage_reasons(rule, project_root)
    if isinstance(rule, DocAreaCoherenceRule):
        return _doc_area_reasons(rule, conn)
    if isinstance(rule, SummaryFactsRule):
        return _summary_facts_reasons(conn, project_root)
    # An unknown-ref_id diagnosis the loader can make about a rule kind this
    # module does not model yet is still worth printing: `validate_rules`
    # computes it, and dropping its return value is how #172 stayed open.
    return validate_rules([rule], conn)


def inert_rules(
    conn: sqlite3.Connection,
    rules: list[Rule],
    *,
    project_root: Path | None = None,
) -> list[tuple[Rule, str]]:
    """Every rule that cannot fire, paired with the reason it cannot.

    Silent on an empty graph: a clone before its first reindex has nothing for
    any rule to match, which is a fact about the index, not about the rules —
    and ``lint``'s header already says ``0 files scanned``.
    """
    facts = _GraphFacts(conn)
    if facts.is_empty:
        return []
    found: list[tuple[Rule, str]] = []
    for rule in rules:
        reasons = _reasons_for_rule(rule, facts, conn, project_root)
        if reasons:
            found.append((rule, "; ".join(reasons)))
    return found


def inert_rule_names(
    conn: sqlite3.Connection,
    rules: list[Rule],
    *,
    project_root: Path | None = None,
) -> set[str]:
    """The names of the rules that cannot fire — the count ``lint`` reports."""
    return {rule.name for rule, _ in inert_rules(conn, rules, project_root=project_root)}


#: Rule types that report their own liveness, so this module counts them and does
#: not report them a second time. ``scenario_coverage`` states which LEG stood
#: down and names the glob that did it, which a generic "cannot fire" cannot; two
#: findings for one fact is the affirm-it-twice defect of BDL-UX #173, and it
#: would double the single finding a repointed ``features:`` path is measured
#: down to.
_SELF_REPORTING: tuple[type, ...] = (
    ScenarioCoverageRule,
    DocAreaCoherenceRule,
    SummaryFactsRule,
)


def evaluate_rule_liveness(
    conn: sqlite3.Connection,
    rules: list[Rule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Report every rule that cannot fire — one finding per rule, always ``warn``.

    A rule type that reports its own liveness is skipped here and still counted
    by :func:`inert_rules`: the count answers *how many of my rules checked
    nothing*, the finding answers *what exactly stood down*, and only the second
    is better said by the rule's own module.
    """
    reportable = [rule for rule in rules if not isinstance(rule, _SELF_REPORTING)]
    return [
        liveness_finding(
            rule_name=rule.name,
            rule_description=rule.description,
            message=(
                f"Rule '{rule.name}' cannot fire: {reason}. It is counted as "
                "evaluated but checks nothing"
            ),
            remediation=INERT_RULE_HINT,
        )
        for rule, reason in inert_rules(conn, reportable, project_root=project_root)
    ]
