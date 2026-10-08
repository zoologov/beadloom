# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Rule loading: parse ``rules.yml`` into typed rules and validate against the DB.

This module owns the *ingestion* responsibility — turning the YAML rule schema
(versions 1-3) into the typed :mod:`beadloom.graph.rules.types` model, plus the
database-aware reference validation that produces advisory warnings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import yaml

from beadloom.graph.rules.layer_declaration import declaration_warnings
from beadloom.graph.rules.layer_reach import part_of_parents
from beadloom.graph.rules.layers import within_scope
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import (
    DEFAULT_DOC_AREA_MIN_SUPPORT,
    DEFAULT_DOC_AREA_THRESHOLD,
    SUPPORTED_SCHEMA_VERSIONS,
    VALID_EDGE_KINDS,
    VALID_NODE_KINDS,
    VALID_RULE_SEVERITIES,
    CardinalityRule,
    CycleRule,
    DenyRule,
    DocAreaCoherenceRule,
    ForbidEdgeRule,
    ImportBoundaryRule,
    ImportExemption,
    LayerDef,
    LayerExemption,
    LayerRule,
    ListedExemption,
    ModuleCoverageRule,
    NodeMatcher,
    NonBehaviouralNode,
    RequireRule,
    Rule,
    ScenarioBindingRule,
    ScenarioCoverageRule,
    SummaryFactsRule,
    TestBindingRule,
    TestImportBoundaryRule,
    UnregisteredFeatureCandidateRule,
)
from beadloom.graph.scenarios import DEFAULT_FEATURE_GLOB

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


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


def _parse_import_exemption(
    name: str,
    index: int,
    entry: object,
    *,
    key: str = "forbid_import",
) -> ImportExemption:
    """Parse one entry of ``forbid_import.exempt``.

    An exemption must name what it exempts (``from`` and/or ``to``), why, and
    when it goes away: an exclusion with no reason and no exit condition is how
    a gate is switched off without saying so (BDL-061 CONTEXT).
    """
    where = f"Rule '{name}': {key}.exempt[{index}]"
    if not isinstance(entry, dict):
        msg = f"{where} must be a mapping"
        raise ValueError(msg)

    from_glob = str(entry.get("from", "") or "").strip()
    to_glob = str(entry.get("to", "") or "").strip()
    if not from_glob and not to_glob:
        msg = f"{where} must set 'from' and/or 'to' — an entry matching both would exempt the rule"
        raise ValueError(msg)

    reason = str(entry.get("reason", "") or "").strip()
    if not reason:
        msg = f"{where} must carry a non-empty 'reason'"
        raise ValueError(msg)
    until = str(entry.get("until", "") or "").strip()
    if not until:
        msg = f"{where} must carry a non-empty 'until' (its exit condition)"
        raise ValueError(msg)

    return ImportExemption(
        to_glob=to_glob or "*",
        from_glob=from_glob or "*",
        reason=reason,
        until=until,
    )


def _parse_import_boundary(
    name: str, data: dict[str, object], *, key: str
) -> tuple[str, str, tuple[ImportExemption, ...]]:
    """The ``from``/``to`` globs and the exemptions of an import boundary, under *key*.

    Shared by ``forbid_import`` and ``test_import_boundary``, which judge one
    boundary over two import tables, so an entry means the same in both and each
    message names the block it came from.
    """
    from_glob = data.get("from")
    to_glob = data.get("to")

    if from_glob is None or not isinstance(from_glob, str) or not from_glob.strip():
        msg = f"Rule '{name}': {key}.from must be a non-empty string"
        raise ValueError(msg)
    if to_glob is None or not isinstance(to_glob, str) or not to_glob.strip():
        msg = f"Rule '{name}': {key}.to must be a non-empty string"
        raise ValueError(msg)

    exempt_raw = data.get("exempt", [])
    if not isinstance(exempt_raw, list):
        msg = f"Rule '{name}': {key}.exempt must be a list"
        raise ValueError(msg)
    exempt = tuple(
        _parse_import_exemption(name, i, entry, key=key) for i, entry in enumerate(exempt_raw)
    )
    return from_glob, to_glob, exempt


def _parse_forbid_import_rule(
    name: str,
    description: str,
    forbid_data: dict[str, object],
    *,
    severity: str = "error",
) -> ImportBoundaryRule:
    """Parse the 'forbid_import' block of a rule."""
    from_glob, to_glob, exempt = _parse_import_boundary(name, forbid_data, key="forbid_import")

    return ImportBoundaryRule(
        name=name,
        description=description,
        from_glob=from_glob,
        to_glob=to_glob,
        severity=severity,
        exempt=exempt,
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


def _parse_layer_exemption(
    name: str,
    index: int,
    entry: object,
) -> LayerExemption:
    """Parse one entry of a layer rule's ``exempt`` list.

    An entry must name BOTH ends, why the crossing stands, and what retires it.
    Both ends, because a same-layer crossing is an edge and an entry naming one
    end would excuse every crossing that touches it. A reason and an exit
    condition, because a bare allow tells the next reader that somebody decided
    something and nothing about what (BDL-070 B2).
    """
    where = f"Rule '{name}': layers.exempt[{index}]"
    if not isinstance(entry, dict):
        msg = f"{where} must be a mapping"
        raise ValueError(msg)

    from_glob = str(entry.get("from", "") or "").strip()
    to_glob = str(entry.get("to", "") or "").strip()
    if not from_glob or not to_glob:
        msg = f"{where} must name both ends — set 'from' and 'to'"
        raise ValueError(msg)
    if from_glob == "*" and to_glob == "*":
        msg = f"{where} matches every edge, which would exempt the rule"
        raise ValueError(msg)

    reason = str(entry.get("reason", "") or "").strip()
    if not reason:
        msg = f"{where} must carry a non-empty 'reason'"
        raise ValueError(msg)
    until = str(entry.get("until", "") or "").strip()
    if not until:
        msg = f"{where} must carry a non-empty 'until' (its exit condition)"
        raise ValueError(msg)

    return LayerExemption(from_glob=from_glob, to_glob=to_glob, reason=reason, until=until)


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

    exempt_raw = rule_data.get("exempt", [])
    if not isinstance(exempt_raw, list):
        msg = f"Rule '{name}': layers.exempt must be a list"
        raise ValueError(msg)
    exempt = tuple(
        _parse_layer_exemption(name, i, entry) for i, entry in enumerate(exempt_raw)
    )

    return LayerRule(
        name=name,
        description=description,
        layers=tuple(layer_defs),
        enforce=enforce,
        allow_skip=allow_skip,
        edge_kind=edge_kind,
        severity=severity,
        exempt=exempt,
        scope=_parse_layer_scope(name, rule_data),
        title=_parse_layer_title(name, rule_data),
    )


def _parse_layer_title(name: str, rule_data: dict[str, object]) -> str | None:
    """The name the portal shows a layer rule by, or ``None`` when the rule declares none.

    A value that is not a non-empty string is refused rather than read as "no
    title": the portal would show the rule's name instead, and nobody would see
    that the title they wrote was dropped.
    """
    if "title" not in rule_data:
        return None
    title = rule_data["title"]
    if not isinstance(title, str) or not title.strip():
        msg = (
            f"Rule '{name}': 'title' must be a non-empty string, "
            "the name the portal shows the rule by"
        )
        raise ValueError(msg)
    return title.strip()


def _parse_layer_scope(name: str, rule_data: dict[str, object]) -> str | None:
    """The node a layer rule judges inside, or ``None`` when the rule names none.

    Whether the node EXISTS is a question about the graph, which the loader does
    not read: :func:`validate_rules` and the rule's liveness answer it. What is
    refused here is a value that cannot be a ref_id at all, because an empty
    scope read as "no scope" would widen the rule to the whole graph in silence.
    """
    if "scope" not in rule_data:
        return None
    scope = rule_data["scope"]
    if not isinstance(scope, str) or not scope.strip():
        msg = (
            f"Rule '{name}': 'scope' must name one node by its ref_id, "
            "the container the rule judges inside"
        )
        raise ValueError(msg)
    return scope.strip()


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


def _parse_unregistered_feature_candidate_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "warn",
) -> UnregisteredFeatureCandidateRule:
    """Parse the 'unregistered_feature_candidate' block of a rule.

    YAML example::

        - name: unregistered-feature-candidate
          unregistered_feature_candidate:
            for: { kind: domain }
            min_symbols: 5
            exclude:
              - "**/config_reader.py"
          severity: warn
    """
    for_data = data.get("for")
    if not isinstance(for_data, dict):
        msg = f"Rule '{name}': unregistered_feature_candidate.for must be a mapping"
        raise ValueError(msg)

    for_matcher = _parse_node_matcher(
        for_data, f"Rule '{name}' unregistered_feature_candidate.for"
    )

    min_symbols_raw = data.get("min_symbols", 5)
    min_symbols = int(min_symbols_raw)  # type: ignore[call-overload]
    if min_symbols < 0:
        msg = f"Rule '{name}': unregistered_feature_candidate.min_symbols must be non-negative"
        raise ValueError(msg)

    exclude_raw = data.get("exclude", [])
    if exclude_raw is None:
        exclude_raw = []
    if not isinstance(exclude_raw, list):
        msg = f"Rule '{name}': unregistered_feature_candidate.exclude must be a list"
        raise ValueError(msg)
    exclude = tuple(str(item) for item in exclude_raw)

    return UnregisteredFeatureCandidateRule(
        name=name,
        description=description,
        for_matcher=for_matcher,
        min_symbols=min_symbols,
        exclude=exclude,
        severity=severity,
    )


def _parse_module_coverage_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "warn",
) -> ModuleCoverageRule:
    """Parse the 'module_coverage' block of a rule.

    YAML example::

        - name: module-coverage
          module_coverage:
            source_root: src/beadloom/
            min_symbols: 1
            exempt:
              - "**/__init__.py"
          severity: warn
    """
    source_root_raw = data.get("source_root", "src/beadloom/")
    source_root = str(source_root_raw)

    min_symbols_raw = data.get("min_symbols", 1)
    min_symbols = int(min_symbols_raw)  # type: ignore[call-overload]
    if min_symbols < 0:
        msg = f"Rule '{name}': module_coverage.min_symbols must be non-negative"
        raise ValueError(msg)

    exempt_raw = data.get("exempt", [])
    if exempt_raw is None:
        exempt_raw = []
    if not isinstance(exempt_raw, list):
        msg = f"Rule '{name}': module_coverage.exempt must be a list"
        raise ValueError(msg)
    exempt = tuple(str(item) for item in exempt_raw)

    return ModuleCoverageRule(
        name=name,
        description=description,
        source_root=source_root,
        min_symbols=min_symbols,
        exempt=exempt,
        severity=severity,
    )


def _parse_scenario_coverage_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "warn",
) -> ScenarioCoverageRule:
    """Parse the 'scenario_coverage' block of a rule.

    YAML example::

        - name: scenario-coverage
          description: "behaviour carries an executable claim"
          scenario_coverage:
            for: { kind: feature }
            features: "tests/acceptance/features/**/*.feature"
            references:
              - "docs/**/PRD.md"
            non_behavioural:
              - node: rule-types
                reason: "frozen dataclasses; the behaviour is the evaluator's"

    ``reason`` is mandatory on every declaration: an unnamed exclusion is how a
    gate is quietly switched off (BDL-061 CONTEXT), so a declaration without one
    is a configuration error rather than a silent pass.

    For the same reason there is exactly ONE way to take a node out of this
    rule's population, and ``for.exclude`` is not it. An ``exclude`` entry
    carries no reason, is never reported and never expires, and
    ``_matcher_description`` does not even print it — so a matcher excluded down
    to nothing reports only that it selects no node. The error below routes the
    author to ``non_behavioural``, which requires the reason and reports the
    declaration when it stops excusing anything.

    Scoped to this rule type deliberately: ``exclude`` is shared by every rule
    type, and requiring a reason everywhere would turn an adopter's green project
    red on upgrade for rules this epic never touched. That widening is its own
    decision with its own migration; this rule type ships in the same release as
    the requirement, so no adopter has written one yet.
    """
    for_data = data.get("for", {"kind": "feature"})
    if not isinstance(for_data, dict):
        msg = f"Rule '{name}': scenario_coverage.for must be a mapping"
        raise ValueError(msg)
    excluded = for_data.get("exclude")
    if excluded is not None:
        listed = excluded if isinstance(excluded, list) else [excluded]
        names = ", ".join(str(item) for item in listed)
        msg = (
            f"Rule '{name}': scenario_coverage.for.exclude ({names}) carries no "
            f"reason and is never reported — declare each node under "
            f"scenario_coverage.non_behavioural with a 'reason' instead, which is "
            f"reported when it stops excusing anything"
        )
        raise ValueError(msg)
    for_matcher = _parse_node_matcher(for_data, f"Rule '{name}' scenario_coverage.for")

    features = str(data.get("features", DEFAULT_FEATURE_GLOB))

    references_raw = data.get("references", [])
    if references_raw is None:
        references_raw = []
    if not isinstance(references_raw, list):
        msg = f"Rule '{name}': scenario_coverage.references must be a list"
        raise ValueError(msg)
    references = tuple(str(item) for item in references_raw)

    declarations_raw = data.get("non_behavioural", [])
    if declarations_raw is None:
        declarations_raw = []
    if not isinstance(declarations_raw, list):
        msg = f"Rule '{name}': scenario_coverage.non_behavioural must be a list"
        raise ValueError(msg)
    declarations = tuple(
        _parse_non_behavioural(name, index, entry)
        for index, entry in enumerate(declarations_raw)
    )

    return ScenarioCoverageRule(
        name=name,
        description=description,
        for_matcher=for_matcher,
        features=features,
        references=references,
        non_behavioural=declarations,
        severity=severity,
    )


def _parse_doc_area_coherence_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "warn",
) -> DocAreaCoherenceRule:
    """Parse the 'doc_area_coherence' block of a rule.

    YAML example::

        - name: doc-area-coherence
          description: "a node documents itself where its graph says it should"
          doc_area_coherence:
            threshold: 0.6
            min_support: 2

    Both keys are optional and neither names a directory: the convention the rule
    enforces is read off the graph, so there is nothing about a layout to
    configure. What IS configurable is how much agreement counts as a convention,
    which depends on the project's size rather than on Beadloom.
    """
    threshold = _parse_threshold(name, data.get("threshold", DEFAULT_DOC_AREA_THRESHOLD))
    min_support = _parse_min_support(
        name, data.get("min_support", DEFAULT_DOC_AREA_MIN_SUPPORT)
    )
    return DocAreaCoherenceRule(
        name=name,
        description=description,
        threshold=threshold,
        min_support=min_support,
        severity=severity,
    )


def _parse_threshold(rule_name: str, raw: object) -> float:
    """The majority share, rejected unless it is a fraction that can be a majority.

    A threshold at or below 0.5 is not a majority and a threshold above 1 can
    never be met, so both are configuration that reads as a rule and behaves as a
    silence — the class of defect this rule exists to refuse.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        msg = f"Rule '{rule_name}': doc_area_coherence.threshold must be a number"
        raise ValueError(msg)
    threshold = float(raw)
    if not (0.5 < threshold <= 1.0):
        msg = (
            f"Rule '{rule_name}': doc_area_coherence.threshold must be greater than "
            f"0.5 and at most 1.0, got {threshold}"
        )
        raise ValueError(msg)
    return threshold


def _parse_min_support(rule_name: str, raw: object) -> int:
    """The number of agreeing pairs a convention must rest on, at least two.

    One observation cannot disagree with itself, so a ``min_support`` of 1 would
    make every area holding a single documented node unanimous and let a graph too
    small to hold a convention report a clean sweep.
    """
    if isinstance(raw, bool) or not isinstance(raw, int):
        msg = f"Rule '{rule_name}': doc_area_coherence.min_support must be an integer"
        raise ValueError(msg)
    if raw < 2:
        msg = (
            f"Rule '{rule_name}': doc_area_coherence.min_support must be at least 2, "
            f"got {raw} — one observation is not a convention"
        )
        raise ValueError(msg)
    return raw


def _parse_summary_facts_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "error",
) -> SummaryFactsRule:
    """Parse the 'summary_facts' block of a rule.

    YAML example::

        - name: graph-summary-facts
          description: "a number in a node summary agrees with the project"
          severity: error
          summary_facts: {}

    The block takes no keys, and the empty mapping is the whole configuration
    surface on purpose: what counts as a version, what counts as a claim about a
    count and how close a count has to be are decided once by the documentation
    audit, and a knob here would be a second answer to a question already
    answered. An unknown key is REJECTED rather than ignored — a setting that
    looks configured and does nothing is the failure this rule family exists to
    catch.
    """
    unknown = sorted(data)
    if unknown:
        msg = (
            f"Rule '{name}': 'summary_facts' takes no keys, got {unknown}. The "
            f"extraction and the comparison come from the documentation audit, so "
            f"there is nothing here to tune"
        )
        raise ValueError(msg)
    return SummaryFactsRule(name=name, description=description, severity=severity)


def _parse_non_behavioural(
    rule_name: str, index: int, entry: object
) -> NonBehaviouralNode:
    """Parse one ``non_behavioural`` declaration, both fields mandatory."""
    where = f"Rule '{rule_name}': scenario_coverage.non_behavioural[{index}]"
    if not isinstance(entry, dict):
        msg = f"{where} must be a mapping with 'node' and 'reason'"
        raise ValueError(msg)
    node = str(entry.get("node", "")).strip()
    reason = str(entry.get("reason", "")).strip()
    if not node:
        msg = f"{where} must name a 'node'"
        raise ValueError(msg)
    if not reason:
        msg = (
            f"{where} (node '{node}') must carry a 'reason' — a node excused from "
            f"scenario coverage without a stated reason is a check switched off "
            f"without saying so"
        )
        raise ValueError(msg)
    return NonBehaviouralNode(node=node, reason=reason)


def _parse_listed_exemptions(
    name: str, key: str, raw: object, *, kinds: tuple[str, ...]
) -> dict[str, tuple[ListedExemption, ...]]:
    """Parse ``<key>.exempt``: each entry lists ONE of *kinds*, with a reason and an exit.

    *kinds* are the keys an entry may list its subjects under (``files``, and for
    ``test_binding`` also ``nodes``). An entry must name exactly one, so a reader
    never has to guess whether ``billing`` is a path or a node.
    """
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        msg = f"Rule '{name}': {key}.exempt must be a list"
        raise ValueError(msg)
    parsed: dict[str, list[ListedExemption]] = {kind: [] for kind in kinds}
    for index, entry in enumerate(raw):
        where = f"Rule '{name}': {key}.exempt[{index}]"
        if not isinstance(entry, dict):
            msg = f"{where} must be a mapping"
            raise ValueError(msg)
        listed = [kind for kind in kinds if kind in entry]
        if len(listed) != 1:
            allowed = ", ".join(f"'{kind}'" for kind in kinds)
            msg = f"{where} must list exactly one of {allowed}"
            raise ValueError(msg)
        (kind,) = listed
        values = entry[kind]
        if not isinstance(values, list) or not values:
            msg = f"{where}.{kind} must be a non-empty list"
            raise ValueError(msg)
        reason = str(entry.get("reason", "") or "").strip()
        until = str(entry.get("until", "") or "").strip()
        if not reason:
            msg = f"{where} must carry a non-empty 'reason'"
            raise ValueError(msg)
        if not until:
            msg = f"{where} must carry a non-empty 'until' (its exit condition)"
            raise ValueError(msg)
        parsed[kind].append(
            ListedExemption(entries=tuple(str(v) for v in values), reason=reason, until=until)
        )
    return {kind: tuple(entries) for kind, entries in parsed.items()}


def _parse_test_binding_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "warn",
) -> TestBindingRule:
    """Parse the 'test_binding' block of a rule.

    YAML example::

        - name: test-binding
          test_binding:
            files: "tests/**"          # the file leg: a test file binds to a node
            for: { kind: feature }     # the node leg: a node has a bound test file
            exempt:
              - files: [tests/test_mixed.py]
                reason: "tests several nodes; not yet split"
                until: "split by node and placed by the mirror"

    Each leg runs only when declared, so one rule can hold a file leg at
    ``error`` and another a node leg at ``warn``. A block naming neither is
    refused, and so is an exemption for a leg the rule does not run.
    """
    for_data = data.get("for")
    files_raw = data.get("files")
    if for_data is None and files_raw is None:
        msg = f"Rule '{name}': test_binding names neither 'for' (nodes) nor 'files' (test files)"
        raise ValueError(msg)
    for_matcher: NodeMatcher | None = None
    if for_data is not None:
        if not isinstance(for_data, dict):
            msg = f"Rule '{name}': test_binding.for must be a mapping"
            raise ValueError(msg)
        for_matcher = _parse_node_matcher(for_data, f"Rule '{name}' test_binding.for")
    files = None if files_raw is None else str(files_raw)
    exempt = _parse_listed_exemptions(
        name, "test_binding", data.get("exempt"), kinds=("files", "nodes")
    )
    if exempt["nodes"] and for_matcher is None:
        msg = f"Rule '{name}': test_binding exempts nodes but declares no 'for' node leg"
        raise ValueError(msg)
    if exempt["files"] and files is None:
        msg = f"Rule '{name}': test_binding exempts files but declares no 'files' leg"
        raise ValueError(msg)
    return TestBindingRule(
        name=name,
        description=description,
        for_matcher=for_matcher,
        files=files,
        exempt_files=exempt["files"],
        exempt_nodes=exempt["nodes"],
        severity=severity,
    )


def _parse_test_import_boundary_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "error",
) -> TestImportBoundaryRule:
    """Parse the 'test_import_boundary' block: ``forbid_import``'s keys, plus ``of``.

    YAML example::

        - name: domain-unit-tests-no-infra
          test_import_boundary:
            from: "tests/unit/**"
            to: "pkg/infrastructure/**"
            of: { tag: layer-domain }   # the test's node, or a container of it
    """
    from_glob, to_glob, exempt = _parse_import_boundary(name, data, key="test_import_boundary")
    of_data = data.get("of")
    of_matcher: NodeMatcher | None = None
    if of_data is not None:
        if not isinstance(of_data, dict):
            msg = f"Rule '{name}': test_import_boundary.of must be a mapping"
            raise ValueError(msg)
        of_matcher = _parse_node_matcher(of_data, f"Rule '{name}' test_import_boundary.of")
    return TestImportBoundaryRule(
        name=name,
        description=description,
        from_glob=from_glob,
        to_glob=to_glob,
        of_matcher=of_matcher,
        severity=severity,
        exempt=exempt,
    )


def _parse_scenario_binding_rule(
    name: str,
    description: str,
    data: dict[str, object],
    *,
    severity: str = "warn",
) -> ScenarioBindingRule:
    """Parse the 'scenario_binding' block of a rule.

    YAML example::

        - name: scenario-binding
          scenario_binding:
            features: "tests/acceptance/**/*.feature"
            exempt:
              - files: [tests/acceptance/features/checkout.feature]
                reason: "its tag names the node its steps run through, not the folder's"
                until: "the feature is rewritten against its node"
    """
    features = str(data.get("features", DEFAULT_FEATURE_GLOB))
    exempt = _parse_listed_exemptions(
        name, "scenario_binding", data.get("exempt"), kinds=("files",)
    )
    return ScenarioBindingRule(
        name=name,
        description=description,
        features=features,
        exempt=exempt["files"],
        severity=severity,
    )


class _MappingParser(Protocol):
    """Read one rule type's mapping into its typed rule, severity already resolved."""

    def __call__(
        self, name: str, description: str, data: dict[str, object], /, *, severity: str
    ) -> Rule: ...


#: The authoring key read from the rule itself rather than from a mapping under
#: it: a layer rule's ``layers`` is a list, and its ``enforce``, ``allow_skip``,
#: ``edge_kind`` and ``exempt`` sit beside it, so ``_parse_layer_rule`` is handed
#: the whole rule. It is the one key the table below cannot hold.
_KEY_READ_FROM_THE_RULE = "layers"

#: Every authoring key whose value is a mapping, and the parser that reads it.
#: ``load_rules`` checks the value is a mapping, with one message for every key,
#: and hands it on — the check and the message were written out eleven times
#: before BDL-073 B3, identically but for the key. ``forbid_cycles`` is an entry
#: like any other: it was the chain's ``else`` arm only because the exactly-one
#: check above the chain made it the one key left.
_MAPPING_PARSERS: dict[str, _MappingParser] = {
    "deny": _parse_deny_rule,
    "require": _parse_require_rule,
    "forbid_cycles": _parse_cycle_rule,
    "forbid_import": _parse_forbid_import_rule,
    "forbid": _parse_forbid_rule,
    "check": _parse_check_rule,
    "unregistered_feature_candidate": _parse_unregistered_feature_candidate_rule,
    "module_coverage": _parse_module_coverage_rule,
    "scenario_coverage": _parse_scenario_coverage_rule,
    "doc_area_coherence": _parse_doc_area_coherence_rule,
    "summary_facts": _parse_summary_facts_rule,
    "test_binding": _parse_test_binding_rule,
    "test_import_boundary": _parse_test_import_boundary_rule,
    "scenario_binding": _parse_scenario_binding_rule,
}

#: Every key a rule may declare to select its type. A rule declares exactly one.
#:
#: Derived from the table rather than listed beside it, so a rule type cannot be
#: accepted by one and missing from the other. The validation message below is
#: built from it, and `onboarding.scanner.rules_gen` labels rules by it, because a
#: key it did not know became the word "unknown" in the generated agent
#: instructions and nothing failed (BDL-062 `.4`).
AUTHORING_KEYS: frozenset[str] = frozenset({*_MAPPING_PARSERS, _KEY_READ_FROM_THE_RULE})

#: The authoring keys whose rule defaults to ``warn`` when ``severity`` is
#: omitted: advisory checks that must not fail the build until a project has
#: classified what they report on. Every other rule defaults to ``error``.
_KEYS_THAT_DEFAULT_TO_WARN: frozenset[str] = frozenset(
    {
        "unregistered_feature_candidate",
        "module_coverage",
        "scenario_coverage",
        "doc_area_coherence",
        "test_binding",
        "scenario_binding",
    }
)


#: What :func:`load_rules` last parsed at each resolved path: the text it read and
#: the rules it returned. One ``beadloom init`` re-indexes and then lints, and both
#: read the same ``rules.yml``; one suite run made 1581 parses, 783 of them of a
#: file that had not changed (BDL-073). The entry is trusted only while the file
#: still holds the same TEXT. A path alone would serve old rules to the TUI, which
#: refreshes in one long process while its user edits the file; ``st_mtime_ns``
#: with ``st_size`` would do the same for an edit that keeps the size and lands in
#: one timestamp tick, which a coarse-clock filesystem makes milliseconds wide.
#: Reading the file costs microseconds; the parse is what is saved. The rules are
#: kept as a tuple and every caller gets a list of its own, so one caller's
#: ``append`` cannot change what the next caller is served. The rules themselves
#: are frozen dataclasses, and those are shared.
_PARSED: dict[Path, tuple[str, tuple[Rule, ...]]] = {}


def forget_parsed_rules() -> None:
    """Forget every parse :func:`load_rules` remembers, so the next call parses."""
    _PARSED.clear()


def load_rules(rules_path: Path) -> list[Rule]:
    """Parse rules.yml and return validated Rule objects.

    A file whose text has not changed since the last call for its path is not
    parsed again: the rules parsed then are returned, in a new list per call.

    Raises ``ValueError`` on schema errors (missing version, invalid kinds, etc.).
    """
    with rules_path.open("r", encoding="utf-8") as fh:
        text = fh.read()
    memo_key = rules_path.resolve()
    remembered = _PARSED.get(memo_key)
    if remembered is not None and remembered[0] == text:
        return list(remembered[1])
    data = yaml.safe_load(text)

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

        # Severity is a v2 feature and defaults to "error" for v1 backward compat;
        # it is resolved before the rule type is, so a rule that is wrong in both
        # ways is reported for its severity.
        declared = AUTHORING_KEYS.intersection(rule_data)
        default_severity = "warn" if declared & _KEYS_THAT_DEFAULT_TO_WARN else "error"
        severity_raw = rule_data.get("severity", default_severity)
        severity = str(severity_raw)
        if severity not in VALID_RULE_SEVERITIES:
            msg = (
                f"rules.yml: rule '{name}' has invalid severity '{severity}', "
                f"must be one of {sorted(VALID_RULE_SEVERITIES)}"
            )
            raise ValueError(msg)

        if len(declared) != 1:
            listed = ", ".join(f"'{key}'" for key in sorted(AUTHORING_KEYS))
            msg = f"rules.yml: rule '{name}' must have exactly one of {listed}"
            raise ValueError(msg)
        (key,) = declared

        if key == _KEY_READ_FROM_THE_RULE:
            rules.append(_parse_layer_rule(name, description, rule_data, severity=severity))
            continue
        block = rule_data[key]
        if not isinstance(block, dict):
            msg = f"Rule '{name}': '{key}' must be a mapping"
            raise ValueError(msg)
        rules.append(_MAPPING_PARSERS[key](name, description, block, severity=severity))

    _PARSED[memo_key] = (text, tuple(rules))
    return rules


# ---------------------------------------------------------------------------
# Database-aware validation (warnings, not errors)
# ---------------------------------------------------------------------------


def validate_rules(rules: list[Rule], conn: sqlite3.Connection) -> list[str]:
    """Validate rules against the database, returning warning messages.

    Checks that ref_id values referenced in matchers actually exist in the
    nodes table.  Returns a list of warning strings (empty if all is well).

    A ``LayerRule`` mentions no ref_id — it names TAGS — so it was outside the
    ``isinstance`` chain below and a rule could declare a layer whose tag no node
    carries without anything saying so. That is the same class of mistake the
    ref_id check exists for, and it is answered by
    :func:`~beadloom.graph.rules.layer_declaration.declaration_warnings`, the one
    function the evaluator's finding is also derived from.
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
        elif isinstance(rule, CardinalityRule) and rule.for_matcher.ref_id is not None:
            ref_ids.add(rule.for_matcher.ref_id)
        elif isinstance(rule, LayerRule) and rule.scope is not None:
            ref_ids.add(rule.scope)

    # A layer rule references the graph through tags rather than ref_ids, so the
    # tag map is read only when one is present — `node_tags` defers its query
    # until the first question is asked.
    layer_rules = [rule for rule in rules if isinstance(rule, LayerRule)]
    if layer_rules:
        tags = node_tags(conn).as_mapping()
        parents = part_of_parents(conn)
        for rule in layer_rules:
            # A scoped rule's layers are populated by the nodes inside its scope
            # only, which is what the evaluator judges (BDL-080 S1b).
            _, scoped_tags = within_scope(rule.scope, (), parents, tags)
            warnings.extend(declaration_warnings(rule, scoped_tags))

    # Check each against the database
    for ref_id in sorted(ref_ids):
        row = conn.execute("SELECT 1 FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
        if row is None:
            warnings.append(
                f"Rule references unknown ref_id '{ref_id}' (not found in nodes table)"
            )

    return warnings
