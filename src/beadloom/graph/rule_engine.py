# beadloom:domain=graph
"""Architecture rule engine: parse rules.yml, validate, and evaluate against the graph DB."""

from __future__ import annotations

import fnmatch
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
SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1, 2, 3})

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeMatcher:
    """Matches graph nodes by ref_id, kind, and/or tag."""

    ref_id: str | None = None
    kind: str | None = None
    tag: str | None = None
    exclude: tuple[str, ...] | None = None

    def matches(self, node_ref_id: str, node_kind: str, *, tags: set[str] | None = None) -> bool:
        """Return True if this matcher matches the given node.

        The *tags* parameter is optional for backward compatibility.
        When *tags* is ``None`` and ``self.tag`` is set, the tag check
        is skipped (i.e. old callers that do not pass tags are not broken).

        The *exclude* field, when set, causes ``matches()`` to return
        ``False`` for any ``node_ref_id`` listed in the tuple.
        """
        if self.exclude and node_ref_id in self.exclude:
            return False
        if self.ref_id is not None and self.ref_id != node_ref_id:
            return False
        if self.kind is not None and self.kind != node_kind:
            return False
        return not (self.tag is not None and tags is not None and self.tag not in tags)


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


@dataclass(frozen=True)
class CycleRule:
    """Forbid circular dependencies along specified edge kinds."""

    name: str
    description: str
    edge_kind: str | tuple[str, ...]  # which edge kinds to traverse
    max_depth: int = 10  # limit search depth
    severity: str = "error"  # "error" | "warn"


@dataclass(frozen=True)
class ImportBoundaryRule:
    """Forbid imports between file paths matched by glob patterns.

    Unlike DenyRule (which matches graph nodes via NodeMatcher), this rule
    operates directly on file paths using ``fnmatch`` glob patterns against
    the ``code_imports`` table.
    """

    name: str
    description: str
    from_glob: str  # source file path glob (e.g. "components/features/map/**")
    to_glob: str  # target path glob (matched against import_path after dot-to-slash)
    severity: str = "error"  # "error" | "warn"


@dataclass(frozen=True)
class ForbidEdgeRule:
    """Forbid graph edges between matched nodes.

    Unlike :class:`DenyRule` which checks ``code_imports``, this rule
    operates on the ``edges`` table directly.  Useful for enforcing
    architectural layering at the graph level.
    """

    name: str
    description: str
    from_matcher: NodeMatcher  # matches source node (by tag, kind, ref_id)
    to_matcher: NodeMatcher  # matches target node
    edge_kind: str | None = None  # optional: only check specific edge kind
    severity: str = "error"  # "error" | "warn"


@dataclass(frozen=True)
class LayerDef:
    """A single layer definition with a name and a tag for matching nodes."""

    name: str
    tag: str


@dataclass(frozen=True)
class LayerRule:
    """Enforce dependency direction between ordered architecture layers.

    Layers are ordered top (index 0) to bottom (index N).  For ``enforce:
    top-down``, upper layers may depend on lower layers but **not** the
    reverse.  When ``allow_skip`` is ``False``, a layer can only depend on
    the immediately adjacent layer below it.
    """

    name: str
    description: str
    layers: tuple[LayerDef, ...]  # ordered top-to-bottom
    enforce: str  # "top-down"
    allow_skip: bool = True  # can skip layers (presentation -> service)
    edge_kind: str = "uses"  # which edge kind to check
    severity: str = "error"  # "error" | "warn"


@dataclass(frozen=True)
class CardinalityRule:
    """Detect architectural smells via node-level cardinality checks.

    For each node matching ``for_matcher``, counts symbols, files, and/or
    doc-coverage under the node's ``source`` prefix.  Produces a violation
    when any threshold is exceeded.
    """

    name: str
    description: str
    for_matcher: NodeMatcher
    max_symbols: int | None = None
    max_files: int | None = None
    min_doc_coverage: float | None = None
    severity: str = "warn"


Rule = (
    DenyRule
    | RequireRule
    | CycleRule
    | ImportBoundaryRule
    | ForbidEdgeRule
    | LayerRule
    | CardinalityRule
)


@dataclass(frozen=True)
class Violation:
    """A single rule violation."""

    rule_name: str
    rule_description: str
    rule_type: str  # "deny" | "require" | "cardinality" | ...
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
    a ``NodeMatcher(ref_id=None, kind=None, tag=None)`` that matches **any** node.

    The optional ``exclude`` field accepts a string or list of strings and
    is normalized to a tuple of ref_ids to exclude from matching.
    """
    ref_id = data.get("ref_id")
    kind = data.get("kind")
    tag = data.get("tag")

    if ref_id is None and kind is None and tag is None and not allow_empty:
        msg = f"{context}: node matcher must have at least one of 'ref_id', 'kind', or 'tag'"
        raise ValueError(msg)

    ref_id_str: str | None = str(ref_id) if ref_id is not None else None
    kind_str: str | None = str(kind) if kind is not None else None
    tag_str: str | None = str(tag) if tag is not None else None

    if kind_str is not None and kind_str not in VALID_NODE_KINDS:
        msg = f"{context}: invalid kind '{kind_str}', must be one of {sorted(VALID_NODE_KINDS)}"
        raise ValueError(msg)

    # Parse optional exclude field (string or list -> tuple)
    exclude_raw = data.get("exclude")
    exclude: tuple[str, ...] | None = None
    if exclude_raw is not None:
        if isinstance(exclude_raw, list):
            exclude = tuple(str(item) for item in exclude_raw)
        else:
            exclude = (str(exclude_raw),)

    return NodeMatcher(ref_id=ref_id_str, kind=kind_str, tag=tag_str, exclude=exclude)


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


def _parse_cycle_rule(
    name: str,
    description: str,
    cycle_data: dict[str, object],
    *,
    severity: str = "error",
) -> CycleRule:
    """Parse the 'forbid_cycles' block of a rule."""
    edge_kind_raw = cycle_data.get("edge_kind")
    if edge_kind_raw is None:
        msg = f"Rule '{name}': forbid_cycles.edge_kind is required"
        raise ValueError(msg)

    # edge_kind can be a string or a list of strings
    edge_kind: str | tuple[str, ...]
    if isinstance(edge_kind_raw, list):
        edge_kind_strs: list[str] = [str(ek) for ek in edge_kind_raw]
        for ek in edge_kind_strs:
            if ek not in VALID_EDGE_KINDS:
                msg = (
                    f"Rule '{name}': invalid edge kind '{ek}' in forbid_cycles.edge_kind, "
                    f"must be one of {sorted(VALID_EDGE_KINDS)}"
                )
                raise ValueError(msg)
        edge_kind = tuple(edge_kind_strs)
    else:
        edge_kind = str(edge_kind_raw)
        if edge_kind not in VALID_EDGE_KINDS:
            msg = (
                f"Rule '{name}': invalid edge kind '{edge_kind}' in forbid_cycles.edge_kind, "
                f"must be one of {sorted(VALID_EDGE_KINDS)}"
            )
            raise ValueError(msg)

    max_depth_raw = cycle_data.get("max_depth", 10)
    max_depth = int(max_depth_raw)  # type: ignore[call-overload]

    return CycleRule(
        name=name,
        description=description,
        edge_kind=edge_kind,
        max_depth=max_depth,
        severity=severity,
    )


def _parse_forbid_import_rule(
    name: str,
    description: str,
    forbid_data: dict[str, object],
    *,
    severity: str = "error",
) -> ImportBoundaryRule:
    """Parse the 'forbid_import' block of a rule."""
    from_glob = forbid_data.get("from")
    to_glob = forbid_data.get("to")

    if from_glob is None or not isinstance(from_glob, str) or not from_glob.strip():
        msg = f"Rule '{name}': forbid_import.from must be a non-empty string"
        raise ValueError(msg)
    if to_glob is None or not isinstance(to_glob, str) or not to_glob.strip():
        msg = f"Rule '{name}': forbid_import.to must be a non-empty string"
        raise ValueError(msg)

    return ImportBoundaryRule(
        name=name,
        description=description,
        from_glob=from_glob,
        to_glob=to_glob,
        severity=severity,
    )


def _parse_forbid_rule(
    name: str,
    description: str,
    forbid_data: dict[str, object],
    *,
    severity: str = "error",
) -> ForbidEdgeRule:
    """Parse the 'forbid' block of a rule (graph-level forbidden edges)."""
    from_data = forbid_data.get("from")
    to_data = forbid_data.get("to")

    if not isinstance(from_data, dict):
        msg = f"Rule '{name}': forbid.from must be a mapping"
        raise ValueError(msg)
    if not isinstance(to_data, dict):
        msg = f"Rule '{name}': forbid.to must be a mapping"
        raise ValueError(msg)

    from_matcher = _parse_node_matcher(from_data, f"Rule '{name}' forbid.from")
    to_matcher = _parse_node_matcher(to_data, f"Rule '{name}' forbid.to")

    edge_kind_raw = forbid_data.get("edge_kind")
    edge_kind: str | None = str(edge_kind_raw) if edge_kind_raw is not None else None

    if edge_kind is not None and edge_kind not in VALID_EDGE_KINDS:
        msg = (
            f"Rule '{name}': invalid edge_kind '{edge_kind}', "
            f"must be one of {sorted(VALID_EDGE_KINDS)}"
        )
        raise ValueError(msg)

    return ForbidEdgeRule(
        name=name,
        description=description,
        from_matcher=from_matcher,
        to_matcher=to_matcher,
        edge_kind=edge_kind,
        severity=severity,
    )


_VALID_LAYER_ENFORCEMENTS: frozenset[str] = frozenset({"top-down"})


def _parse_layer_rule(
    name: str,
    description: str,
    rule_data: dict[str, object],
    *,
    severity: str = "error",
) -> LayerRule:
    """Parse a layer rule from the top-level rule data.

    The ``layers`` key contains a list of ``{name, tag}`` dicts, and
    ``enforce`` specifies the direction policy (currently only ``top-down``).
    """
    layers_raw = rule_data.get("layers")
    if not isinstance(layers_raw, list):
        msg = f"Rule '{name}': 'layers' must be a list"
        raise ValueError(msg)

    if len(layers_raw) < 2:
        msg = f"Rule '{name}': 'layers' must contain at least 2 layer definitions"
        raise ValueError(msg)

    layer_defs: list[LayerDef] = []
    for idx, layer_data in enumerate(layers_raw):
        if not isinstance(layer_data, dict):
            msg = f"Rule '{name}': layer at index {idx} must be a mapping"
            raise ValueError(msg)

        layer_name = layer_data.get("name")
        if layer_name is None or not isinstance(layer_name, str) or not layer_name.strip():
            msg = f"Rule '{name}': layer at index {idx} missing required 'name' field"
            raise ValueError(msg)

        layer_tag = layer_data.get("tag")
        if layer_tag is None or not isinstance(layer_tag, str) or not layer_tag.strip():
            msg = f"Rule '{name}': layer at index {idx} missing required 'tag' field"
            raise ValueError(msg)

        layer_defs.append(LayerDef(name=str(layer_name), tag=str(layer_tag)))

    enforce_raw = rule_data.get("enforce")
    if enforce_raw is None:
        msg = f"Rule '{name}': 'enforce' is required for layer rules"
        raise ValueError(msg)

    enforce = str(enforce_raw)
    if enforce not in _VALID_LAYER_ENFORCEMENTS:
        msg = (
            f"Rule '{name}': invalid enforce value '{enforce}', "
            f"must be one of {sorted(_VALID_LAYER_ENFORCEMENTS)}"
        )
        raise ValueError(msg)

    allow_skip_raw = rule_data.get("allow_skip", True)
    allow_skip = bool(allow_skip_raw)

    edge_kind_raw = rule_data.get("edge_kind", "uses")
    edge_kind = str(edge_kind_raw)
    if edge_kind not in VALID_EDGE_KINDS:
        msg = (
            f"Rule '{name}': invalid edge_kind '{edge_kind}', "
            f"must be one of {sorted(VALID_EDGE_KINDS)}"
        )
        raise ValueError(msg)

    return LayerRule(
        name=name,
        description=description,
        layers=tuple(layer_defs),
        enforce=enforce,
        allow_skip=allow_skip,
        edge_kind=edge_kind,
        severity=severity,
    )


def _parse_check_rule(
    name: str,
    description: str,
    check_data: dict[str, object],
    *,
    severity: str = "warn",
) -> CardinalityRule:
    """Parse the 'check' block of a rule into a :class:`CardinalityRule`.

    YAML example::

        - name: domain-size
          check:
            for: { kind: domain }
            max_symbols: 200
            max_files: 30
            min_doc_coverage: 0.5
          severity: warn
    """
    for_data = check_data.get("for")
    if not isinstance(for_data, dict):
        msg = f"Rule '{name}': check.for must be a mapping"
        raise ValueError(msg)

    for_matcher = _parse_node_matcher(for_data, f"Rule '{name}' check.for")

    max_symbols_raw = check_data.get("max_symbols")
    max_symbols: int | None = None
    if max_symbols_raw is not None:
        max_symbols = int(max_symbols_raw)  # type: ignore[call-overload]
        if max_symbols < 0:
            msg = f"Rule '{name}': check.max_symbols must be non-negative"
            raise ValueError(msg)

    max_files_raw = check_data.get("max_files")
    max_files: int | None = None
    if max_files_raw is not None:
        max_files = int(max_files_raw)  # type: ignore[call-overload]
        if max_files < 0:
            msg = f"Rule '{name}': check.max_files must be non-negative"
            raise ValueError(msg)

    min_doc_coverage_raw = check_data.get("min_doc_coverage")
    min_doc_coverage: float | None = None
    if min_doc_coverage_raw is not None:
        min_doc_coverage = float(min_doc_coverage_raw)  # type: ignore[arg-type]
        if not (0.0 <= min_doc_coverage <= 1.0):
            msg = f"Rule '{name}': check.min_doc_coverage must be between 0.0 and 1.0"
            raise ValueError(msg)

    if max_symbols is None and max_files is None and min_doc_coverage is None:
        msg = (
            f"Rule '{name}': check must specify at least one of "
            f"'max_symbols', 'max_files', or 'min_doc_coverage'"
        )
        raise ValueError(msg)

    return CardinalityRule(
        name=name,
        description=description,
        for_matcher=for_matcher,
        max_symbols=max_symbols,
        max_files=max_files,
        min_doc_coverage=min_doc_coverage,
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
        has_forbid_cycles = "forbid_cycles" in rule_data
        has_forbid_import = "forbid_import" in rule_data
        has_forbid = "forbid" in rule_data
        has_layers = "layers" in rule_data
        has_check = "check" in rule_data

        rule_type_count = sum(
            [
                has_deny,
                has_require,
                has_forbid_cycles,
                has_forbid_import,
                has_forbid,
                has_layers,
                has_check,
            ]
        )
        if rule_type_count != 1:
            msg = (
                f"rules.yml: rule '{name}' must have exactly one of "
                f"'deny', 'require', 'forbid_cycles', 'forbid_import', "
                f"'forbid', 'layers', or 'check'"
            )
            raise ValueError(msg)

        if has_deny:
            deny_data = rule_data["deny"]
            if not isinstance(deny_data, dict):
                msg = f"Rule '{name}': 'deny' must be a mapping"
                raise ValueError(msg)
            rules.append(_parse_deny_rule(name, description, deny_data, severity=severity))
        elif has_require:
            require_data = rule_data["require"]
            if not isinstance(require_data, dict):
                msg = f"Rule '{name}': 'require' must be a mapping"
                raise ValueError(msg)
            rules.append(_parse_require_rule(name, description, require_data, severity=severity))
        elif has_forbid_import:
            forbid_import_data = rule_data["forbid_import"]
            if not isinstance(forbid_import_data, dict):
                msg = f"Rule '{name}': 'forbid_import' must be a mapping"
                raise ValueError(msg)
            rules.append(
                _parse_forbid_import_rule(name, description, forbid_import_data, severity=severity)
            )
        elif has_forbid:
            forbid_data = rule_data["forbid"]
            if not isinstance(forbid_data, dict):
                msg = f"Rule '{name}': 'forbid' must be a mapping"
                raise ValueError(msg)
            rules.append(_parse_forbid_rule(name, description, forbid_data, severity=severity))
        elif has_layers:
            rules.append(_parse_layer_rule(name, description, rule_data, severity=severity))
        elif has_check:
            check_data = rule_data["check"]
            if not isinstance(check_data, dict):
                msg = f"Rule '{name}': 'check' must be a mapping"
                raise ValueError(msg)
            rules.append(_parse_check_rule(name, description, check_data, severity=severity))
        else:
            cycle_data = rule_data["forbid_cycles"]
            if not isinstance(cycle_data, dict):
                msg = f"Rule '{name}': 'forbid_cycles' must be a mapping"
                raise ValueError(msg)
            rules.append(_parse_cycle_rule(name, description, cycle_data, severity=severity))

    return rules


def load_rules_with_tags(
    rules_path: Path,
) -> tuple[list[Rule], dict[str, list[str]]]:
    """Parse rules.yml returning both rules and tag assignments.

    The optional top-level ``tags:`` block (schema v3) maps tag names to
    lists of ref_ids for bulk tag assignment, e.g.::

        tags:
          ui-layer: [app-tabs, app-auth]
          feature-layer: [map, calendar]

    Returns a ``(rules, tag_assignments)`` tuple.  *tag_assignments* is
    an empty dict when no ``tags:`` block is present.
    """
    with rules_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        msg = "rules.yml must be a YAML mapping"
        raise ValueError(msg)

    # Extract tag assignments before delegating to load_rules
    tags_block = data.get("tags", {})
    tag_assignments: dict[str, list[str]] = {}
    if isinstance(tags_block, dict):
        for tag_name, ref_ids in tags_block.items():
            if isinstance(ref_ids, list):
                tag_assignments[str(tag_name)] = [str(r) for r in ref_ids]

    rules = load_rules(rules_path)
    return rules, tag_assignments


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
        elif isinstance(rule, ForbidEdgeRule):
            if rule.from_matcher.ref_id is not None:
                ref_ids.add(rule.from_matcher.ref_id)
            if rule.to_matcher.ref_id is not None:
                ref_ids.add(rule.to_matcher.ref_id)
        elif isinstance(rule, CardinalityRule):
            if rule.for_matcher.ref_id is not None:
                ref_ids.add(rule.for_matcher.ref_id)

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
# Cycle rule evaluation
# ---------------------------------------------------------------------------


def _normalize_cycle(path: list[str]) -> tuple[str, ...]:
    """Normalize a cycle path so that the smallest element is first.

    This ensures that cycle A->B->C->A is the same as B->C->A->B.
    The path should NOT include the repeated start node at the end.
    """
    if not path:
        return ()
    min_idx = path.index(min(path))
    rotated = path[min_idx:] + path[:min_idx]
    return tuple(rotated)


def _build_adjacency(
    conn: sqlite3.Connection,
    edge_kinds: tuple[str, ...],
) -> dict[str, list[str]]:
    """Build an adjacency list from the edges table for given edge kinds."""
    placeholders = ", ".join("?" for _ in edge_kinds)
    query = (
        f"SELECT src_ref_id, dst_ref_id FROM edges "  # noqa: S608
        f"WHERE kind IN ({placeholders})"
    )
    rows = conn.execute(query, edge_kinds).fetchall()
    adj: dict[str, list[str]] = {}
    for row in rows:
        src = str(row[0])
        dst = str(row[1])
        adj.setdefault(src, []).append(dst)
    return adj


def evaluate_cycle_rules(conn: sqlite3.Connection, rules: list[CycleRule]) -> list[Violation]:
    """Evaluate cycle rules against the edges table using iterative DFS.

    For each rule, walks outgoing edges of the specified kind(s) looking for
    cycles.  Reports each unique cycle once with the full path in the message.
    """
    if not rules:
        return []

    violations: list[Violation] = []

    for rule in rules:
        # Normalize edge_kind to a tuple
        if isinstance(rule.edge_kind, str):
            edge_kinds: tuple[str, ...] = (rule.edge_kind,)
        else:
            edge_kinds = rule.edge_kind

        # Build adjacency list once per rule
        adj = _build_adjacency(conn, edge_kinds)

        # Collect all nodes that participate in edges
        all_nodes: set[str] = set(adj.keys())
        for neighbors in adj.values():
            all_nodes.update(neighbors)

        # Track found cycles (normalized) to avoid duplicates
        seen_cycles: set[tuple[str, ...]] = set()

        # Iterative DFS from each node
        for start_node in sorted(all_nodes):
            # Stack entries: (current_node, path_from_start)
            stack: list[tuple[str, list[str]]] = [(start_node, [start_node])]

            while stack:
                current, path = stack.pop()

                neighbors = adj.get(current, [])
                for neighbor in neighbors:
                    if neighbor in path:
                        # Found a cycle -- extract the cycle portion
                        cycle_start_idx = path.index(neighbor)
                        cycle_path = path[cycle_start_idx:]

                        normalized = _normalize_cycle(cycle_path)
                        if normalized not in seen_cycles:
                            seen_cycles.add(normalized)
                            # Format: A -> B -> C -> A
                            display_path = " \u2192 ".join([*cycle_path, neighbor])
                            violations.append(
                                Violation(
                                    rule_name=rule.name,
                                    rule_description=rule.description,
                                    rule_type="cycle",
                                    severity=rule.severity,
                                    file_path=None,
                                    line_number=None,
                                    from_ref_id=cycle_path[0],
                                    to_ref_id=cycle_path[-1],
                                    message=(
                                        f"Circular dependency detected: {display_path} "
                                        f"(rule '{rule.name}')"
                                    ),
                                )
                            )
                    elif len(path) < rule.max_depth:
                        stack.append((neighbor, [*path, neighbor]))

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

        # Fetch edges of the specified kind
        all_edges = conn.execute(
            "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = ?",
            (rule.edge_kind,),
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
# Combined evaluation
# ---------------------------------------------------------------------------


def evaluate_all(conn: sqlite3.Connection, rules: list[Rule]) -> list[Violation]:
    """Evaluate all rules and return sorted violations.

    Supports deny, require, cycle, import boundary, forbid edge, layer,
    and cardinality rules.
    """
    deny_rules: list[DenyRule] = []
    require_rules: list[RequireRule] = []
    cycle_rules: list[CycleRule] = []
    import_boundary_rules: list[ImportBoundaryRule] = []
    forbid_edge_rules: list[ForbidEdgeRule] = []
    layer_rules: list[LayerRule] = []
    cardinality_rules: list[CardinalityRule] = []

    for rule in rules:
        if isinstance(rule, DenyRule):
            deny_rules.append(rule)
        elif isinstance(rule, RequireRule):
            require_rules.append(rule)
        elif isinstance(rule, CycleRule):
            cycle_rules.append(rule)
        elif isinstance(rule, ImportBoundaryRule):
            import_boundary_rules.append(rule)
        elif isinstance(rule, ForbidEdgeRule):
            forbid_edge_rules.append(rule)
        elif isinstance(rule, LayerRule):
            layer_rules.append(rule)
        elif isinstance(rule, CardinalityRule):
            cardinality_rules.append(rule)

    violations = (
        evaluate_deny_rules(conn, deny_rules)
        + evaluate_require_rules(conn, require_rules)
        + evaluate_cycle_rules(conn, cycle_rules)
        + evaluate_import_boundary_rules(conn, import_boundary_rules)
        + evaluate_forbid_edge_rules(conn, forbid_edge_rules)
        + evaluate_layer_rules(conn, layer_rules)
        + evaluate_cardinality_rules(conn, cardinality_rules)
    )

    # Sort by rule_name, then file_path (None sorts first)
    violations.sort(key=lambda v: (v.rule_name, v.file_path or ""))

    return violations
