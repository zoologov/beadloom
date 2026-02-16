# beadloom:domain=graph
"""Architecture rule engine: parse rules.yml, validate, and evaluate against the graph DB."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_NODE_KINDS: frozenset[str] = frozenset({"domain", "feature", "service", "entity", "adr"})
VALID_EDGE_KINDS: frozenset[str] = frozenset(
    {"part_of", "depends_on", "uses", "implements", "touches_entity", "touches_code"}
)
VALID_RULE_SEVERITIES: frozenset[str] = frozenset({"error", "warn"})
SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1, 2})

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeMatcher:
    """Matches graph nodes by ref_id and/or kind."""

    ref_id: str | None = None
    kind: str | None = None

    def matches(self, node_ref_id: str, node_kind: str) -> bool:
        """Return True if this matcher matches the given node."""
        if self.ref_id is not None and self.ref_id != node_ref_id:
            return False
        return not (self.kind is not None and self.kind != node_kind)


@dataclass(frozen=True)
class DenyRule:
    """Forbid imports between matched nodes."""

    name: str
    description: str
    from_matcher: NodeMatcher
    to_matcher: NodeMatcher
    unless_edge: tuple[str, ...]  # edge kinds that exempt the import
    severity: str = "error"  # "error" | "warn"


@dataclass(frozen=True)
class RequireRule:
    """Require edges from matched nodes to target nodes."""

    name: str
    description: str
    for_matcher: NodeMatcher
    has_edge_to: NodeMatcher
    edge_kind: str | None = None
    severity: str = "error"  # "error" | "warn"


Rule = DenyRule | RequireRule


@dataclass(frozen=True)
class Violation:
    """A single rule violation."""

    rule_name: str
    rule_description: str
    rule_type: str  # "deny" | "require"
    severity: str  # "error" | "warn"
    file_path: str | None  # source file (for deny rules)
    line_number: int | None  # line number (for deny rules)
    from_ref_id: str | None  # source node
    to_ref_id: str | None  # target node
    message: str  # human-readable explanation


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------


def _parse_node_matcher(
    data: dict[str, object], context: str, *, allow_empty: bool = False
) -> NodeMatcher:
    """Parse a node matcher dict into a NodeMatcher, validating fields.

    When *allow_empty* is True an empty dict ``{}`` is accepted and produces
    a ``NodeMatcher(ref_id=None, kind=None)`` that matches **any** node.
    """
    ref_id = data.get("ref_id")
    kind = data.get("kind")

    if ref_id is None and kind is None and not allow_empty:
        msg = f"{context}: node matcher must have at least one of 'ref_id' or 'kind'"
        raise ValueError(msg)

    ref_id_str: str | None = str(ref_id) if ref_id is not None else None
    kind_str: str | None = str(kind) if kind is not None else None

    if kind_str is not None and kind_str not in VALID_NODE_KINDS:
        msg = f"{context}: invalid kind '{kind_str}', must be one of {sorted(VALID_NODE_KINDS)}"
        raise ValueError(msg)

    return NodeMatcher(ref_id=ref_id_str, kind=kind_str)


def _parse_deny_rule(
    name: str, description: str, deny_data: dict[str, object], *, severity: str = "error"
) -> DenyRule:
    """Parse the 'deny' block of a rule."""
    from_data = deny_data.get("from")
    to_data = deny_data.get("to")

    if not isinstance(from_data, dict):
        msg = f"Rule '{name}': deny.from must be a mapping"
        raise ValueError(msg)
    if not isinstance(to_data, dict):
        msg = f"Rule '{name}': deny.to must be a mapping"
        raise ValueError(msg)

    from_matcher = _parse_node_matcher(from_data, f"Rule '{name}' deny.from")
    to_matcher = _parse_node_matcher(to_data, f"Rule '{name}' deny.to")

    unless_edge_raw = deny_data.get("unless_edge", [])
    if not isinstance(unless_edge_raw, list):
        msg = f"Rule '{name}': deny.unless_edge must be a list"
        raise ValueError(msg)

    unless_edge_strs: list[str] = [str(e) for e in unless_edge_raw]
    for edge_kind in unless_edge_strs:
        if edge_kind not in VALID_EDGE_KINDS:
            msg = (
                f"Rule '{name}': invalid edge kind '{edge_kind}' in unless_edge, "
                f"must be one of {sorted(VALID_EDGE_KINDS)}"
            )
            raise ValueError(msg)

    return DenyRule(
        name=name,
        description=description,
        from_matcher=from_matcher,
        to_matcher=to_matcher,
        unless_edge=tuple(unless_edge_strs),
        severity=severity,
    )


def _parse_require_rule(
    name: str,
    description: str,
    require_data: dict[str, object],
    *,
    severity: str = "error",
) -> RequireRule:
    """Parse the 'require' block of a rule."""
    for_data = require_data.get("for")
    has_edge_to_data = require_data.get("has_edge_to")

    if not isinstance(for_data, dict):
        msg = f"Rule '{name}': require.for must be a mapping"
        raise ValueError(msg)
    if not isinstance(has_edge_to_data, dict):
        msg = f"Rule '{name}': require.has_edge_to must be a mapping"
        raise ValueError(msg)

    for_matcher = _parse_node_matcher(for_data, f"Rule '{name}' require.for")
    has_edge_to = _parse_node_matcher(
        has_edge_to_data, f"Rule '{name}' require.has_edge_to", allow_empty=True
    )

    edge_kind_raw = require_data.get("edge_kind")
    edge_kind: str | None = str(edge_kind_raw) if edge_kind_raw is not None else None

    if edge_kind is not None and edge_kind not in VALID_EDGE_KINDS:
        msg = (
            f"Rule '{name}': invalid edge_kind '{edge_kind}', "
            f"must be one of {sorted(VALID_EDGE_KINDS)}"
        )
        raise ValueError(msg)

    return RequireRule(
        name=name,
        description=description,
        for_matcher=for_matcher,
        has_edge_to=has_edge_to,
        edge_kind=edge_kind,
        severity=severity,
    )


def load_rules(rules_path: Path) -> list[Rule]:
    """Parse rules.yml and return validated Rule objects.

    Raises ``ValueError`` on schema errors (missing version, invalid kinds, etc.).
    """
    with rules_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        msg = "rules.yml must be a YAML mapping"
        raise ValueError(msg)

    # Validate version
    version = data.get("version")
    if version is None:
        msg = "rules.yml: missing required 'version' field"
        raise ValueError(msg)
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        expected = sorted(SUPPORTED_SCHEMA_VERSIONS)
        msg = f"rules.yml: unsupported version {version}, expected one of {expected}"
        raise ValueError(msg)

    rules_data = data.get("rules", [])
    if not isinstance(rules_data, list):
        msg = "rules.yml: 'rules' must be a list"
        raise ValueError(msg)

    seen_names: set[str] = set()
    rules: list[Rule] = []

    for idx, rule_data in enumerate(rules_data):
        if not isinstance(rule_data, dict):
            msg = f"rules.yml: rule at index {idx} must be a mapping"
            raise ValueError(msg)

        # Name is required
        name = rule_data.get("name")
        if name is None or not isinstance(name, str) or not name.strip():
            msg = f"rules.yml: rule at index {idx} missing required 'name' field"
            raise ValueError(msg)

        if name in seen_names:
            msg = f"rules.yml: Duplicate rule name '{name}'"
            raise ValueError(msg)
        seen_names.add(name)

        description = str(rule_data.get("description", ""))

        # Parse severity (v2 feature, defaults to "error" for v1 backward compat)
        severity_raw = rule_data.get("severity", "error")
        severity = str(severity_raw)
        if severity not in VALID_RULE_SEVERITIES:
            msg = (
                f"rules.yml: rule '{name}' has invalid severity '{severity}', "
                f"must be one of {sorted(VALID_RULE_SEVERITIES)}"
            )
            raise ValueError(msg)

        has_deny = "deny" in rule_data
        has_require = "require" in rule_data

        if has_deny == has_require:
            # Both present or neither present
            msg = f"rules.yml: rule '{name}' must have exactly one of 'deny' or 'require'"
            raise ValueError(msg)

        if has_deny:
            deny_data = rule_data["deny"]
            if not isinstance(deny_data, dict):
                msg = f"Rule '{name}': 'deny' must be a mapping"
                raise ValueError(msg)
            rules.append(_parse_deny_rule(name, description, deny_data, severity=severity))
        else:
            require_data = rule_data["require"]
            if not isinstance(require_data, dict):
                msg = f"Rule '{name}': 'require' must be a mapping"
                raise ValueError(msg)
            rules.append(
                _parse_require_rule(name, description, require_data, severity=severity)
            )

    return rules


# ---------------------------------------------------------------------------
# Database-aware validation (warnings, not errors)
# ---------------------------------------------------------------------------


def validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]:
    """Validate rules against the database, returning warning messages.

    Checks that ref_id values referenced in matchers actually exist in the
    nodes table.  Returns a list of warning strings (empty if all is well).
    """
    warnings: list[str] = []

    # Collect all ref_ids from matchers
    ref_ids: set[str] = set()
    for rule in rules:
        if isinstance(rule, DenyRule):
            if rule.from_matcher.ref_id is not None:
                ref_ids.add(rule.from_matcher.ref_id)
            if rule.to_matcher.ref_id is not None:
                ref_ids.add(rule.to_matcher.ref_id)
        elif isinstance(rule, RequireRule):
            if rule.for_matcher.ref_id is not None:
                ref_ids.add(rule.for_matcher.ref_id)
            if rule.has_edge_to.ref_id is not None:
                ref_ids.add(rule.has_edge_to.ref_id)

    # Check each against the database
    for ref_id in sorted(ref_ids):
        row = conn.execute("SELECT 1 FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
        if row is None:
            warnings.append(
                f"Rule references unknown ref_id '{ref_id}' (not found in nodes table)"
            )

    return warnings


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
    rule.
    """
    if not rules:
        return []

    violations: list[Violation] = []

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

        for rule in rules:
            if not rule.from_matcher.matches(source_id, source_kind):
                continue
            if not rule.to_matcher.matches(target_id, target_kind):
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
    restricted by ``edge_kind``).
    """
    if not rules:
        return []

    violations: list[Violation] = []

    # Fetch all nodes once
    all_nodes = conn.execute("SELECT ref_id, kind FROM nodes").fetchall()

    for rule in rules:
        for node_row in all_nodes:
            node_ref_id = str(node_row[0])
            node_kind = str(node_row[1])
            if not rule.for_matcher.matches(node_ref_id, node_kind):
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
                if rule.has_edge_to.matches(target_id, target_kind):
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
# Combined evaluation
# ---------------------------------------------------------------------------


def evaluate_all(conn: sqlite3.Connection, rules: list[Rule]) -> list[Violation]:
    """Evaluate all rules (deny + require) and return sorted violations."""
    deny_rules: list[DenyRule] = []
    require_rules: list[RequireRule] = []

    for rule in rules:
        if isinstance(rule, DenyRule):
            deny_rules.append(rule)
        elif isinstance(rule, RequireRule):
            require_rules.append(rule)

    violations = evaluate_deny_rules(conn, deny_rules) + evaluate_require_rules(
        conn, require_rules
    )

    # Sort by rule_name, then file_path (None sorts first)
    violations.sort(key=lambda v: (v.rule_name, v.file_path or ""))

    return violations
