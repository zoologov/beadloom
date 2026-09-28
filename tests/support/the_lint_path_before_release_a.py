"""The lint path exactly as it stood before Release A of BDL-070, and how to compare it.

BDL-070 A7 (`beadloom-cfkk`). Release A of this epic must move no verdict, and
the only comparison that can show it is a differential against the code as it
stood — run in the same process, against the same index, so both sides always
see the same graph. A recorded baseline would not do it: this repository's
`scenario-coverage` findings state `N scenarios in M files`, so the very
`.feature` files A7 adds rewrite about forty of the messages a baseline would
hold, and a baseline that has to be regenerated to stay green is a baseline
nobody reads.

The transcription lives here rather than inside one test module because TWO
modules need it and two transcriptions of one function are two things that can
drift: A2 (`beadloom-1ylk`) compares the evaluator on graphs, and A7 compares
the whole `lint()` run on a project that is not this repository. It is kept as
source rather than read out of git, because a test that skips on a shallow
clone is a test that does not run in CI.

Everything here is transcribed from `a8c306d8`, the commit Release A starts at.
Nothing in this module imports the code it is the oracle for.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.cycles import _live_lifecycle_clause
from beadloom.graph.rules.layer_declaration import LAYER_DECLARATION_RULE_TYPE
from beadloom.graph.rules.layer_reach import LAYER_POPULATION_RULE_TYPE
from beadloom.graph.rules.types import Violation

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules.types import LayerRule


def layer_findings_before_release_a(
    conn: sqlite3.Connection, rules: list[LayerRule]
) -> list[Violation]:
    """`evaluate_layer_rules` transcribed verbatim from `a8c306d8`.

    The oracle is the pre-change function itself, message strings included, so a
    comparison against it is a comparison of decisions AND of what those
    decisions say — not of a summary somebody wrote down afterwards. It is kept
    here rather than read from git because a test that skips on a shallow clone
    is a test that does not run in CI, which is the shape this project has
    measured itself getting wrong.

    One property of the transcription is checked rather than assumed: the old
    body iterated a node's tag `set` and took the first declared tag it met, so
    on a node carrying two declared layer tags its answer depended on hash
    order. A2's `test_no_node_carries_two_declared_layer_tags` holds the
    condition under which that ambiguity is unreachable on this repository's
    graph, and A7's fixture project carries no node with two either.
    """
    if not rules:
        return []

    from beadloom.graph.loader import get_node_tags

    violations: list[Violation] = []
    tags_cache: dict[str, set[str]] = {}

    def _cached_tags(ref_id: str) -> set[str]:
        if ref_id not in tags_cache:
            tags_cache[ref_id] = get_node_tags(conn, ref_id)
        return tags_cache[ref_id]

    for rule in rules:
        tag_to_index: dict[str, int] = {}
        for idx, layer_def in enumerate(rule.layers):
            tag_to_index[layer_def.tag] = idx

        life_clause, life_params = _live_lifecycle_clause(conn)
        all_edges = conn.execute(
            f"SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = ?{life_clause}",  # noqa: S608
            (rule.edge_kind, *life_params),
        ).fetchall()

        for edge_row in all_edges:
            src_ref_id = str(edge_row[0])
            dst_ref_id = str(edge_row[1])

            src_tags = _cached_tags(src_ref_id)
            dst_tags = _cached_tags(dst_ref_id)

            src_layer_idx: int | None = None
            dst_layer_idx: int | None = None

            for tag in src_tags:
                if tag in tag_to_index:
                    src_layer_idx = tag_to_index[tag]
                    break

            for tag in dst_tags:
                if tag in tag_to_index:
                    dst_layer_idx = tag_to_index[tag]
                    break

            if src_layer_idx is None or dst_layer_idx is None:
                continue
            if src_layer_idx == dst_layer_idx:
                continue

            if rule.enforce == "top-down" and src_layer_idx > dst_layer_idx:
                src_layer_name = rule.layers[src_layer_idx].name
                dst_layer_name = rule.layers[dst_layer_idx].name
                violations.append(
                    Violation(
                        rule_name=rule.name,
                        rule_description=rule.description,
                        rule_type="layer",
                        severity=rule.severity,
                        file_path=None,
                        line_number=None,
                        from_ref_id=src_ref_id,
                        to_ref_id=dst_ref_id,
                        message=(
                            f"Layer violation: '{src_ref_id}' (layer '{src_layer_name}', "
                            f"index {src_layer_idx}) depends on '{dst_ref_id}' "
                            f"(layer '{dst_layer_name}', index {dst_layer_idx}). "
                            f"Lower layers must not depend on upper layers "
                            f"(rule '{rule.name}')."
                        ),
                    )
                )
                continue

            if not rule.allow_skip and (dst_layer_idx - src_layer_idx) > 1:
                src_layer_name = rule.layers[src_layer_idx].name
                dst_layer_name = rule.layers[dst_layer_idx].name
                violations.append(
                    Violation(
                        rule_name=rule.name,
                        rule_description=rule.description,
                        rule_type="layer",
                        severity=rule.severity,
                        file_path=None,
                        line_number=None,
                        from_ref_id=src_ref_id,
                        to_ref_id=dst_ref_id,
                        message=(
                            f"Layer skip violation: '{src_ref_id}' (layer '{src_layer_name}', "
                            f"index {src_layer_idx}) depends on '{dst_ref_id}' "
                            f"(layer '{dst_layer_name}', index {dst_layer_idx}). "
                            f"Skipping layers is not allowed "
                            f"(rule '{rule.name}')."
                        ),
                    )
                )

    return violations


class ClosureTags:
    """The tag cache each of the five evaluators kept, transcribed from `a8c306d8`.

    The shared lookup is compared against this rather than against a description
    of it, so "the closures were identical and the replacement is equivalent" is
    a measurement over this repository's real rules instead of a claim about a
    diff.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._cache: dict[str, set[str]] = {}

    def of(self, ref_id: str) -> set[str]:
        from beadloom.graph.loader import get_node_tags

        if ref_id not in self._cache:
            self._cache[ref_id] = get_node_tags(self._conn, ref_id)
        return self._cache[ref_id]


def comparable(violations: list[Violation]) -> set[tuple[str | None, ...]]:
    """A findings list as a set, carrying everything a reader would see."""
    return {
        (
            v.rule_name,
            v.rule_type,
            v.severity,
            v.file_path,
            None if v.line_number is None else str(v.line_number),
            v.from_ref_id,
            v.to_ref_id,
            v.message,
        )
        for v in violations
    }


#: The advisories Release A adds beside the rule's decisions. Each is `warn`,
#: neither judges an edge, and the differential is about what the rule DECIDES
#: — so both are subtracted before the comparison rather than one.
#: `layer_declaration` (BDL-070 A6) joined the set when `validate_rules` gained
#: its `LayerRule` case: a fixture that declares four layers over a graph
#: populating two is exactly the finding that check exists to make, and it
#: fires on such a fixture by design.
THE_ADVISORY_TYPES = frozenset({LAYER_POPULATION_RULE_TYPE, LAYER_DECLARATION_RULE_TYPE})


def decisions(violations: list[Violation]) -> set[tuple[str | None, ...]]:
    """The findings that are not one of Release A's advisories."""
    return comparable([v for v in violations if v.rule_type not in THE_ADVISORY_TYPES])
