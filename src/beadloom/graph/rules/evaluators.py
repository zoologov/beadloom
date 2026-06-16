# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Per-rule-type evaluation against the graph DB.

This module owns the *evaluation* responsibility: given typed rules and a graph
connection, it produces :class:`Violation` objects for every rule kind except
cycles (which live in :mod:`beadloom.graph.rules.cycles`). It groups the shared
node/edge lookup helpers and the deny / require / import-boundary / forbid-edge
/ layer / cardinality / unregistered-feature / module-coverage evaluators.
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.graph.rules.cycles import _live_lifecycle_clause
from beadloom.graph.rules.types import (
    CardinalityRule,
    DenyRule,
    ForbidEdgeRule,
    ImportBoundaryRule,
    LayerRule,
    ModuleCoverageRule,
    RequireRule,
    UnregisteredFeatureCandidateRule,
    Violation,
)

if TYPE_CHECKING:
    import sqlite3


# ---------------------------------------------------------------------------
# Helpers for evaluation
# ---------------------------------------------------------------------------


def _get_file_node(file_path: str, conn: sqlite3.Connection) -> str | None:
    """Look up the node ref_id for a source file via code_symbols annotations.

    Checks the ``annotations`` JSON column for keys like ``domain``, ``service``,
    etc. that match a node's ``ref_id``.  Returns the first matching ref_id,
    or ``None`` if no annotation or no matching node is found.
    """
    rows = conn.execute(
        "SELECT annotations FROM code_symbols WHERE file_path = ?",
        (file_path,),
    ).fetchall()

    for row in rows:
        annotations_raw = row[0]
        if annotations_raw is None:
            continue
        try:
            annotations: dict[str, object] = json.loads(str(annotations_raw))
        except (json.JSONDecodeError, TypeError):
            continue

        for _key, value in annotations.items():
            if not isinstance(value, str):
                continue
            # Check if this annotation value corresponds to a known node
            node_row = conn.execute(
                "SELECT ref_id FROM nodes WHERE ref_id = ?", (value,)
            ).fetchone()
            if node_row is not None:
                return str(node_row[0])

    return None


def _get_node(ref_id: str, conn: sqlite3.Connection) -> tuple[str, str] | None:
    """Return (ref_id, kind) for a node, or None if not found."""
    row = conn.execute("SELECT ref_id, kind FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    if row is None:
        return None
    return (str(row[0]), str(row[1]))


def _edge_exists(
    src_ref_id: str,
    dst_ref_id: str,
    allowed_kinds: tuple[str, ...],
    conn: sqlite3.Connection,
) -> bool:
    """Return True if an edge of any of *allowed_kinds* exists between two nodes."""
    if not allowed_kinds:
        return False
    placeholders = ", ".join("?" for _ in allowed_kinds)
    query = (
        f"SELECT 1 FROM edges "  # noqa: S608
        f"WHERE src_ref_id = ? AND dst_ref_id = ? AND kind IN ({placeholders}) "
        f"LIMIT 1"
    )
    params: tuple[str, ...] = (src_ref_id, dst_ref_id, *allowed_kinds)
    row = conn.execute(query, params).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Deny rule evaluation
# ---------------------------------------------------------------------------


def evaluate_deny_rules(conn: sqlite3.Connection, rules: list[DenyRule]) -> list[Violation]:
    """Evaluate deny rules against the code_imports table.

    For each import with a resolved_ref_id, determines the source node from
    code_symbols annotations and checks whether the import violates any deny
    rule.  Tag-based matchers are supported: tags are lazily loaded from the
    node ``extra`` JSON column and cached per evaluation run.
    """
    if not rules:
        return []

    from beadloom.graph.loader import get_node_tags

    violations: list[Violation] = []

    # Cache for node tags to avoid repeated DB lookups
    tags_cache: dict[str, set[str]] = {}

    def _cached_tags(ref_id: str) -> set[str]:
        if ref_id not in tags_cache:
            tags_cache[ref_id] = get_node_tags(conn, ref_id)
        return tags_cache[ref_id]

    # Check whether any rule actually uses tag-based matching
    any_tag_rule = any(
        r.from_matcher.tag is not None or r.to_matcher.tag is not None for r in rules
    )

    # Fetch all code_imports with resolved ref_ids
    imports = conn.execute(
        "SELECT file_path, line_number, import_path, resolved_ref_id "
        "FROM code_imports WHERE resolved_ref_id IS NOT NULL"
    ).fetchall()

    for imp in imports:
        file_path = str(imp[0])
        line_number = int(imp[1])
        target_ref_id = str(imp[3])
        source_ref_id = _get_file_node(file_path, conn)
        if source_ref_id is None:
            continue

        # Skip self-references
        if source_ref_id == target_ref_id:
            continue

        source_node = _get_node(source_ref_id, conn)
        target_node = _get_node(target_ref_id, conn)

        if source_node is None or target_node is None:
            continue

        source_id, source_kind = source_node
        target_id, target_kind = target_node

        # Lazily load tags only when needed
        source_tags: set[str] | None = None
        target_tags: set[str] | None = None
        if any_tag_rule:
            source_tags = _cached_tags(source_id)
            target_tags = _cached_tags(target_id)

        for rule in rules:
            if not rule.from_matcher.matches(source_id, source_kind, tags=source_tags):
                continue
            if not rule.to_matcher.matches(target_id, target_kind, tags=target_tags):
                continue

            # Check exemption via unless_edge
            if rule.unless_edge and _edge_exists(
                source_ref_id, target_ref_id, rule.unless_edge, conn
            ):
                continue

            violations.append(
                Violation(
                    rule_name=rule.name,
                    rule_description=rule.description,
                    rule_type="deny",
                    severity=rule.severity,
                    file_path=file_path,
                    line_number=line_number,
                    from_ref_id=source_ref_id,
                    to_ref_id=target_ref_id,
                    message=(
                        f"Import from '{source_ref_id}' to '{target_ref_id}' "
                        f"violates deny rule '{rule.name}': {rule.description}"
                    ),
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Require rule evaluation
# ---------------------------------------------------------------------------


def evaluate_require_rules(conn: sqlite3.Connection, rules: list[RequireRule]) -> list[Violation]:
    """Evaluate require rules against the nodes and edges tables.

    For each node matching a rule's ``for_matcher``, verifies that at least
    one outgoing edge reaches a node matching ``has_edge_to`` (optionally
    restricted by ``edge_kind``).  Tag-based matchers are supported.
    """
    if not rules:
        return []

    from beadloom.graph.loader import get_node_tags

    violations: list[Violation] = []

    # Cache for node tags to avoid repeated DB lookups
    tags_cache: dict[str, set[str]] = {}

    def _cached_tags(ref_id: str) -> set[str]:
        if ref_id not in tags_cache:
            tags_cache[ref_id] = get_node_tags(conn, ref_id)
        return tags_cache[ref_id]

    # Check whether any rule actually uses tag-based matching
    any_tag_rule = any(
        r.for_matcher.tag is not None or r.has_edge_to.tag is not None for r in rules
    )

    # Fetch all nodes once
    all_nodes = conn.execute("SELECT ref_id, kind FROM nodes").fetchall()

    for rule in rules:
        for node_row in all_nodes:
            node_ref_id = str(node_row[0])
            node_kind = str(node_row[1])

            # Load tags for for_matcher if needed
            node_tags: set[str] | None = None
            if any_tag_rule:
                node_tags = _cached_tags(node_ref_id)

            if not rule.for_matcher.matches(node_ref_id, node_kind, tags=node_tags):
                continue

            # Check outgoing edges from this node
            edges = conn.execute(
                "SELECT dst_ref_id, kind FROM edges WHERE src_ref_id = ?",
                (node_ref_id,),
            ).fetchall()

            has_match = False
            for edge_row in edges:
                dst_ref_id = str(edge_row[0])
                edge_kind = str(edge_row[1])
                # If rule specifies edge_kind, check it
                if rule.edge_kind is not None and edge_kind != rule.edge_kind:
                    continue

                # Check if the target matches has_edge_to
                target = _get_node(dst_ref_id, conn)
                if target is None:
                    continue

                target_id, target_kind = target

                # Load tags for has_edge_to if needed
                target_tags: set[str] | None = None
                if any_tag_rule:
                    target_tags = _cached_tags(target_id)

                if rule.has_edge_to.matches(target_id, target_kind, tags=target_tags):
                    has_match = True
                    break

            if not has_match:
                violations.append(
                    Violation(
                        rule_name=rule.name,
                        rule_description=rule.description,
                        rule_type="require",
                        severity=rule.severity,
                        file_path=None,
                        line_number=None,
                        from_ref_id=node_ref_id,
                        to_ref_id=None,
                        message=(
                            f"Node '{node_ref_id}' (kind={node_kind}) "
                            f"violates require rule '{rule.name}': {rule.description}"
                        ),
                    )
                )

    return violations


# ---------------------------------------------------------------------------
# Import boundary rule evaluation
# ---------------------------------------------------------------------------


def _import_path_to_file_path(import_path: str) -> str:
    """Convert a dotted import path to a slash-separated file path for glob matching.

    Example: ``components.features.calendar.events`` becomes
    ``components/features/calendar/events``.
    """
    return import_path.replace(".", "/")


def evaluate_import_boundary_rules(
    conn: sqlite3.Connection, rules: list[ImportBoundaryRule]
) -> list[Violation]:
    """Evaluate import boundary rules against the code_imports table.

    For each import, checks whether the source file matches ``from_glob``
    and the import target (after dot-to-slash conversion) matches ``to_glob``
    using ``fnmatch.fnmatch``.  If both match, a violation is produced.
    """
    if not rules:
        return []

    violations: list[Violation] = []

    # Fetch all code_imports (check ALL imports, not just resolved ones)
    imports = conn.execute(
        "SELECT file_path, line_number, import_path FROM code_imports"
    ).fetchall()

    for imp in imports:
        file_path = str(imp[0])
        line_number = int(imp[1])
        import_path = str(imp[2])
        target_as_path = _import_path_to_file_path(import_path)

        for rule in rules:
            if not fnmatch.fnmatch(file_path, rule.from_glob):
                continue
            if not fnmatch.fnmatch(target_as_path, rule.to_glob):
                continue

            violations.append(
                Violation(
                    rule_name=rule.name,
                    rule_description=rule.description,
                    rule_type="forbid_import",
                    severity=rule.severity,
                    file_path=file_path,
                    line_number=line_number,
                    from_ref_id=None,
                    to_ref_id=None,
                    message=(
                        f"File '{file_path}' imports '{import_path}' "
                        f"which violates boundary rule '{rule.name}': "
                        f"{rule.description}"
                    ),
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Forbid edge rule evaluation
# ---------------------------------------------------------------------------


def evaluate_forbid_edge_rules(
    conn: sqlite3.Connection, rules: list[ForbidEdgeRule]
) -> list[Violation]:
    """Evaluate forbid edge rules against the edges table.

    For each edge, loads tags for the source and destination nodes (using
    ``get_node_tags()``) and checks whether the source matches
    ``from_matcher`` and the destination matches ``to_matcher``.  If
    ``edge_kind`` is specified on the rule, only edges of that kind are
    checked.  A match means the edge is forbidden and produces a violation.
    """
    if not rules:
        return []

    from beadloom.graph.loader import get_node_tags

    violations: list[Violation] = []

    # Cache for node tags to avoid repeated DB lookups
    tags_cache: dict[str, set[str]] = {}

    def _cached_tags(ref_id: str) -> set[str]:
        if ref_id not in tags_cache:
            tags_cache[ref_id] = get_node_tags(conn, ref_id)
        return tags_cache[ref_id]

    # Check whether any rule actually uses tag-based matching
    any_tag_rule = any(
        r.from_matcher.tag is not None or r.to_matcher.tag is not None for r in rules
    )

    # Fetch all edges once
    all_edges = conn.execute("SELECT src_ref_id, dst_ref_id, kind FROM edges").fetchall()

    for edge_row in all_edges:
        src_ref_id = str(edge_row[0])
        dst_ref_id = str(edge_row[1])
        edge_kind = str(edge_row[2])

        # Look up node kinds for matching
        src_node = _get_node(src_ref_id, conn)
        dst_node = _get_node(dst_ref_id, conn)

        if src_node is None or dst_node is None:
            continue

        src_id, src_kind = src_node
        dst_id, dst_kind = dst_node

        # Lazily load tags only when needed
        src_tags: set[str] | None = None
        dst_tags: set[str] | None = None
        if any_tag_rule:
            src_tags = _cached_tags(src_id)
            dst_tags = _cached_tags(dst_id)

        for rule in rules:
            # Check edge_kind filter first (cheapest check)
            if rule.edge_kind is not None and edge_kind != rule.edge_kind:
                continue

            if not rule.from_matcher.matches(src_id, src_kind, tags=src_tags):
                continue
            if not rule.to_matcher.matches(dst_id, dst_kind, tags=dst_tags):
                continue

            violations.append(
                Violation(
                    rule_name=rule.name,
                    rule_description=rule.description,
                    rule_type="forbid",
                    severity=rule.severity,
                    file_path=None,
                    line_number=None,
                    from_ref_id=src_ref_id,
                    to_ref_id=dst_ref_id,
                    message=(
                        f"Edge '{src_ref_id}' -> '{dst_ref_id}' (kind={edge_kind}) "
                        f"violates forbid rule '{rule.name}': {rule.description}"
                    ),
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Layer rule evaluation
# ---------------------------------------------------------------------------


def evaluate_layer_rules(conn: sqlite3.Connection, rules: list[LayerRule]) -> list[Violation]:
    """Evaluate layer rules against the edges table.

    For ``enforce: top-down``, layers are ordered from top (index 0) to
    bottom (index N).  Dependencies flow downward: if a node in layer[i]
    depends on a node in layer[j] where ``i > j`` (lower depends on upper),
    that is a violation.

    When ``allow_skip`` is ``False``, only edges to the immediately adjacent
    lower layer (``j == i + 1``) are permitted; skipping layers produces a
    violation.

    Nodes that do not belong to any layer are silently skipped.
    """
    if not rules:
        return []

    from beadloom.graph.loader import get_node_tags

    violations: list[Violation] = []

    # Cache for node tags to avoid repeated DB lookups
    tags_cache: dict[str, set[str]] = {}

    def _cached_tags(ref_id: str) -> set[str]:
        if ref_id not in tags_cache:
            tags_cache[ref_id] = get_node_tags(conn, ref_id)
        return tags_cache[ref_id]

    for rule in rules:
        # Build tag-to-layer-index mapping
        tag_to_index: dict[str, int] = {}
        for idx, layer_def in enumerate(rule.layers):
            tag_to_index[layer_def.tag] = idx

        # Fetch live edges of the specified kind (planned/deprecated/dead
        # edges are intent or history, not live layering violations).
        life_clause, life_params = _live_lifecycle_clause(conn)
        all_edges = conn.execute(
            f"SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = ?{life_clause}",  # noqa: S608
            (rule.edge_kind, *life_params),
        ).fetchall()

        for edge_row in all_edges:
            src_ref_id = str(edge_row[0])
            dst_ref_id = str(edge_row[1])

            # Determine which layer each node belongs to
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

            # Skip if either node is not in any layer
            if src_layer_idx is None or dst_layer_idx is None:
                continue

            # Same layer -- always OK
            if src_layer_idx == dst_layer_idx:
                continue

            # Check direction violation: lower layer -> upper layer
            # src_layer_idx > dst_layer_idx means src is lower, dst is upper
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

            # Check skip violation (only when allow_skip=False)
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


# ---------------------------------------------------------------------------
# Cardinality rule evaluation
# ---------------------------------------------------------------------------


def evaluate_cardinality_rules(
    conn: sqlite3.Connection, rules: list[CardinalityRule]
) -> list[Violation]:
    """Evaluate cardinality rules against nodes, code_symbols, file_index, and sync_state.

    For each node matching a rule's ``for_matcher``, counts:
    - **symbols**: rows in ``code_symbols`` whose ``file_path`` starts with the
      node's ``source`` prefix.
    - **files**: rows in ``file_index`` whose ``path`` starts with the node's
      ``source`` prefix.
    - **doc coverage**: ratio of ``sync_state`` rows with ``status = 'ok'``
      to total ``sync_state`` rows for the node's ``ref_id``.

    A violation is produced when any threshold is exceeded (or not met, for
    ``min_doc_coverage``).
    """
    if not rules:
        return []

    from beadloom.graph.loader import get_node_tags

    violations: list[Violation] = []

    # Cache for node tags
    tags_cache: dict[str, set[str]] = {}

    def _cached_tags(ref_id: str) -> set[str]:
        if ref_id not in tags_cache:
            tags_cache[ref_id] = get_node_tags(conn, ref_id)
        return tags_cache[ref_id]

    # Check whether any rule uses tag-based matching
    any_tag_rule = any(r.for_matcher.tag is not None for r in rules)

    # Fetch all nodes once (ref_id, kind, source)
    all_nodes = conn.execute("SELECT ref_id, kind, source FROM nodes").fetchall()

    for rule in rules:
        for node_row in all_nodes:
            node_ref_id = str(node_row[0])
            node_kind = str(node_row[1])
            node_source: str | None = str(node_row[2]) if node_row[2] is not None else None

            # Load tags if needed
            node_tags: set[str] | None = None
            if any_tag_rule:
                node_tags = _cached_tags(node_ref_id)

            if not rule.for_matcher.matches(node_ref_id, node_kind, tags=node_tags):
                continue

            # --- max_symbols check ---
            if rule.max_symbols is not None and node_source is not None:
                prefix = node_source.rstrip("/") + "/"
                row = conn.execute(
                    "SELECT COUNT(*) FROM code_symbols WHERE file_path LIKE ?",
                    (prefix + "%",),
                ).fetchone()
                symbol_count = int(row[0]) if row is not None else 0

                if symbol_count > rule.max_symbols:
                    violations.append(
                        Violation(
                            rule_name=rule.name,
                            rule_description=rule.description,
                            rule_type="cardinality",
                            severity=rule.severity,
                            file_path=None,
                            line_number=None,
                            from_ref_id=node_ref_id,
                            to_ref_id=None,
                            message=(
                                f"Node '{node_ref_id}' has {symbol_count} symbols "
                                f"(max {rule.max_symbols}): "
                                f"rule '{rule.name}'"
                            ),
                        )
                    )

            # --- max_files check ---
            if rule.max_files is not None and node_source is not None:
                prefix = node_source.rstrip("/") + "/"
                row = conn.execute(
                    "SELECT COUNT(*) FROM file_index WHERE path LIKE ?",
                    (prefix + "%",),
                ).fetchone()
                file_count = int(row[0]) if row is not None else 0

                if file_count > rule.max_files:
                    violations.append(
                        Violation(
                            rule_name=rule.name,
                            rule_description=rule.description,
                            rule_type="cardinality",
                            severity=rule.severity,
                            file_path=None,
                            line_number=None,
                            from_ref_id=node_ref_id,
                            to_ref_id=None,
                            message=(
                                f"Node '{node_ref_id}' has {file_count} files "
                                f"(max {rule.max_files}): "
                                f"rule '{rule.name}'"
                            ),
                        )
                    )

            # --- min_doc_coverage check ---
            if rule.min_doc_coverage is not None:
                total_row = conn.execute(
                    "SELECT COUNT(*) FROM sync_state WHERE ref_id = ?",
                    (node_ref_id,),
                ).fetchone()
                total = int(total_row[0]) if total_row is not None else 0

                if total > 0:
                    ok_row = conn.execute(
                        "SELECT COUNT(*) FROM sync_state WHERE ref_id = ? AND status = 'ok'",
                        (node_ref_id,),
                    ).fetchone()
                    ok_count = int(ok_row[0]) if ok_row is not None else 0
                    coverage = ok_count / total
                else:
                    coverage = 0.0

                if coverage < rule.min_doc_coverage:
                    violations.append(
                        Violation(
                            rule_name=rule.name,
                            rule_description=rule.description,
                            rule_type="cardinality",
                            severity=rule.severity,
                            file_path=None,
                            line_number=None,
                            from_ref_id=node_ref_id,
                            to_ref_id=None,
                            message=(
                                f"Node '{node_ref_id}' has doc coverage "
                                f"{coverage:.0%} "
                                f"(min {rule.min_doc_coverage:.0%}): "
                                f"rule '{rule.name}'"
                            ),
                        )
                    )

    return violations


# ---------------------------------------------------------------------------
# Unregistered-feature-candidate rule evaluation
# ---------------------------------------------------------------------------


def _file_annotations(annotations_raw: object) -> dict[str, object] | None:
    """Parse a code_symbols ``annotations`` JSON value into a dict, or None."""
    if annotations_raw is None:
        return None
    try:
        parsed = json.loads(str(annotations_raw))
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _candidate_files_for_domain(
    conn: sqlite3.Connection, domain_ref_id: str, source_prefix: str
) -> dict[str, int]:
    """Group indexed symbols under *source_prefix* into per-file candidate counts.

    A file qualifies as a candidate (and appears in the returned mapping) when
    its annotations carry a ``domain`` key equal to *domain_ref_id* and carry
    **no** ``feature`` key. The mapped value is the file's indexed-symbol count.
    """
    rows = conn.execute(
        "SELECT file_path, annotations FROM code_symbols WHERE file_path LIKE ?",
        (source_prefix + "%",),
    ).fetchall()

    counts: dict[str, int] = {}
    domain_only: dict[str, bool] = {}
    has_feature: dict[str, bool] = {}

    for row in rows:
        file_path = str(row[0])
        counts[file_path] = counts.get(file_path, 0) + 1
        annotations = _file_annotations(row[1])
        if annotations is None:
            continue
        if annotations.get("domain") == domain_ref_id:
            domain_only[file_path] = True
        if "feature" in annotations:
            has_feature[file_path] = True

    return {
        path: count
        for path, count in counts.items()
        if domain_only.get(path, False) and not has_feature.get(path, False)
    }


def evaluate_unregistered_feature_candidate_rules(
    conn: sqlite3.Connection, rules: list[UnregisteredFeatureCandidateRule]
) -> list[Violation]:
    """Flag substantial domain-only modules that model no feature (BDL-051 S1).

    For each node matching a rule's ``for_matcher``, finds source files that are
    attributed to the node's domain (``annotations.domain == ref_id``), carry no
    ``feature`` annotation, and have at least ``min_symbols`` indexed symbols.
    Files matching any ``exclude`` glob are skipped. Each candidate produces one
    advisory (``warn``) finding naming the file and its symbol count.
    """
    if not rules:
        return []

    violations: list[Violation] = []

    all_nodes = conn.execute("SELECT ref_id, kind, source FROM nodes").fetchall()

    for rule in rules:
        for node_row in all_nodes:
            node_ref_id = str(node_row[0])
            node_kind = str(node_row[1])
            node_source: str | None = str(node_row[2]) if node_row[2] is not None else None

            if not rule.for_matcher.matches(node_ref_id, node_kind):
                continue
            if node_source is None:
                continue

            prefix = node_source.rstrip("/") + "/"
            candidates = _candidate_files_for_domain(conn, node_ref_id, prefix)

            for file_path, symbol_count in sorted(candidates.items()):
                if symbol_count < rule.min_symbols:
                    continue
                if any(fnmatch.fnmatch(file_path, pat) for pat in rule.exclude):
                    continue

                rel = file_path
                if rel.startswith(prefix):
                    rel = node_ref_id + "/" + rel[len(prefix) :]
                violations.append(
                    Violation(
                        rule_name=rule.name,
                        rule_description=rule.description,
                        rule_type="unregistered_feature_candidate",
                        severity=rule.severity,
                        file_path=file_path,
                        line_number=None,
                        from_ref_id=node_ref_id,
                        to_ref_id=None,
                        message=(
                            f"{rel} ({symbol_count} symbols): domain-only, no feature "
                            f"— candidate unregistered feature (rule '{rule.name}')."
                        ),
                    )
                )

    return violations


# ---------------------------------------------------------------------------
# Module-coverage rule evaluation
# ---------------------------------------------------------------------------


def _node_source_paths(conn: sqlite3.Connection) -> set[str]:
    """Return the set of node ``source`` values that point at a single module file.

    A module is *covered by being a node's source* when its path equals a node's
    ``source``. Directory sources (ending in ``/``) are not single files and are
    handled separately by :func:`_node_dir_source_prefixes`.
    """
    rows = conn.execute("SELECT source FROM nodes WHERE source IS NOT NULL").fetchall()
    sources: set[str] = set()
    for row in rows:
        source = str(row[0])
        if source and not source.endswith("/"):
            sources.add(source)
    return sources


def _node_dir_source_prefixes(conn: sqlite3.Connection, source_root: str) -> set[str]:
    """Return directory ``source`` prefixes that COVER every module beneath them.

    Owner choice (BDL-051 / BEAD-14): a node whose ``source`` is a directory may
    stand for its whole subtree as a single node — e.g. the ``tui`` *service*
    node covers all of ``src/beadloom/tui/`` (no per-widget nodes).

    Two kinds are deliberately excluded so the lint is not trivially satisfied:

    * ``domain`` nodes — a domain directory is *coarse ownership*, not coverage;
      modules under it must still carry a ``feature``/``component`` annotation
      (the architecture-model policy), and
    * any node whose source equals ``source_root`` itself (the root service
      ``src/beadloom/``) — it spans the entire tree, so it can never be coverage.
    """
    rows = conn.execute(
        "SELECT kind, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()
    root_norm = source_root.rstrip("/") + "/"
    prefixes: set[str] = set()
    for row in rows:
        kind = str(row[0])
        source = str(row[1])
        if not source.endswith("/") or kind == "domain":
            continue
        if source.rstrip("/") + "/" == root_norm:
            continue
        prefixes.add(source.rstrip("/") + "/")
    return prefixes


def _module_coverage_state(
    conn: sqlite3.Connection, source_root: str
) -> dict[str, tuple[int, bool]]:
    """Group indexed symbols under *source_root* into per-module coverage state.

    Returns ``{file_path: (symbol_count, has_feature_or_component_annotation)}``
    for every module with at least one indexed symbol.
    """
    rows = conn.execute(
        "SELECT file_path, annotations FROM code_symbols WHERE file_path LIKE ?",
        (source_root + "%",),
    ).fetchall()

    counts: dict[str, int] = {}
    annotated: dict[str, bool] = {}
    for row in rows:
        file_path = str(row[0])
        counts[file_path] = counts.get(file_path, 0) + 1
        annotations = _file_annotations(row[1])
        if annotations is not None and ("feature" in annotations or "component" in annotations):
            annotated[file_path] = True

    return {path: (count, annotated.get(path, False)) for path, count in counts.items()}


def _disk_modules(project_root: Path, source_root: str) -> list[str]:
    """Enumerate ``.py`` modules on DISK under ``project_root / source_root``.

    Returns repo-relative, forward-slash file paths (matching how
    ``code_symbols.file_path`` and node ``source`` values are stored), sorted
    deterministically. This is the candidate enumeration that closes the
    zero-symbol false-negative: a real module with no indexed ``def``/``class``
    symbol produces no ``code_symbols`` row, yet it is still a real module and
    must be a coverage candidate (BDL-051 S3a / BEAD-17).
    """
    base = (project_root / source_root).resolve()
    if not base.is_dir():
        return []
    rel_root = source_root.rstrip("/")
    modules: list[str] = []
    for path in base.rglob("*.py"):
        if not path.is_file():
            continue
        rel = path.resolve().relative_to(base).as_posix()
        modules.append(f"{rel_root}/{rel}")
    return sorted(modules)


def evaluate_module_coverage_rules(
    conn: sqlite3.Connection,
    rules: list[ModuleCoverageRule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Flag every ``src/`` module that is neither a tracked node nor exempt (S3a).

    The candidate set is enumerated from **disk** (every ``.py`` under
    ``project_root / source_root``) unioned with any module that has indexed
    ``code_symbols`` rows. Disk enumeration closes the zero-symbol false-negative:
    a real module with no top-level ``def``/``class`` produces no symbol row, yet
    it is a real module and must be a candidate (BDL-051 S3a / BEAD-17, review .9).

    A module is *covered* when it carries a ``feature``/``component`` annotation
    (read from ``code_symbols.annotations`` where available), equals a node's
    ``source``, or matches an ``exempt`` glob. An uncovered module produces one
    finding naming the file and its symbol count (severity per the rule —
    ``error`` since BDL-051 S3b).

    *project_root* defaults to the current working directory.
    """
    if not rules:
        return []

    root = project_root if project_root is not None else Path.cwd()

    violations: list[Violation] = []
    node_sources = _node_source_paths(conn)

    for rule in rules:
        coverage = _module_coverage_state(conn, rule.source_root)
        dir_prefixes = _node_dir_source_prefixes(conn, rule.source_root)
        # Union: every disk module is a candidate even with zero indexed symbols.
        candidates = dict(coverage)
        for disk_path in _disk_modules(root, rule.source_root):
            if disk_path not in candidates:
                candidates[disk_path] = (0, False)
        for file_path, (symbol_count, annotated) in sorted(candidates.items()):
            if symbol_count < rule.min_symbols and file_path in coverage:
                continue
            if annotated or file_path in node_sources:
                continue
            if any(file_path.startswith(prefix) for prefix in dir_prefixes):
                continue
            if any(fnmatch.fnmatch(file_path, pat) for pat in rule.exempt):
                continue

            violations.append(
                Violation(
                    rule_name=rule.name,
                    rule_description=rule.description,
                    rule_type="module_coverage",
                    severity=rule.severity,
                    file_path=file_path,
                    line_number=None,
                    from_ref_id=None,
                    to_ref_id=None,
                    message=(
                        f"{file_path} ({symbol_count} symbols): not covered by any node "
                        f"and not exempt — classify as a feature/component or add to exempt."
                    ),
                )
            )

    return violations
