# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Rule loading: parse ``rules.yml`` into typed rules and validate against the DB.

This module owns the *ingestion* responsibility — turning the YAML rule schema
(versions 1-3) into the typed :mod:`beadloom.graph.rules.types` model, plus the
database-aware reference validation that produces advisory warnings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

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
    LayerRule,
    ModuleCoverageRule,
    NodeMatcher,
    NonBehaviouralNode,
    RequireRule,
    Rule,
    ScenarioCoverageRule,
    SummaryFactsRule,
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
) -> ImportExemption:
    """Parse one entry of ``forbid_import.exempt``.

    An exemption must name what it exempts (``from`` and/or ``to``), why, and
    when it goes away: an exclusion with no reason and no exit condition is how
    a gate is switched off without saying so (BDL-061 CONTEXT).
    """
    where = f"Rule '{name}': forbid_import.exempt[{index}]"
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

    exempt_raw = forbid_data.get("exempt", [])
    if not isinstance(exempt_raw, list):
        msg = f"Rule '{name}': forbid_import.exempt must be a list"
        raise ValueError(msg)
    exempt = tuple(
        _parse_import_exemption(name, i, entry) for i, entry in enumerate(exempt_raw)
    )

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

        has_unregistered = "unregistered_feature_candidate" in rule_data
        has_module_coverage = "module_coverage" in rule_data

        # Parse severity (v2 feature, defaults to "error" for v1 backward compat).
        # The advisory ``unregistered_feature_candidate`` and ``module_coverage``
        # checks default to "warn" when severity is omitted (they must never fail
        # the build until S3b classifies every module).
        has_scenario_coverage_block = "scenario_coverage" in rule_data
        has_doc_area_block = "doc_area_coherence" in rule_data
        default_severity = (
            "warn"
            if (
                has_unregistered
                or has_module_coverage
                or has_scenario_coverage_block
                or has_doc_area_block
            )
            else "error"
        )
        severity_raw = rule_data.get("severity", default_severity)
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
        has_scenario_coverage = "scenario_coverage" in rule_data
        has_doc_area = "doc_area_coherence" in rule_data
        has_summary_facts = "summary_facts" in rule_data

        rule_type_count = sum(
            [
                has_deny,
                has_require,
                has_forbid_cycles,
                has_forbid_import,
                has_forbid,
                has_layers,
                has_check,
                has_unregistered,
                has_module_coverage,
                has_scenario_coverage,
                has_doc_area,
                has_summary_facts,
            ]
        )
        if rule_type_count != 1:
            msg = (
                f"rules.yml: rule '{name}' must have exactly one of "
                f"'deny', 'require', 'forbid_cycles', 'forbid_import', "
                f"'forbid', 'layers', 'check', 'unregistered_feature_candidate', "
                f"'module_coverage', 'scenario_coverage', 'doc_area_coherence', "
                f"or 'summary_facts'"
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
        elif has_unregistered:
            ufc_data = rule_data["unregistered_feature_candidate"]
            if not isinstance(ufc_data, dict):
                msg = f"Rule '{name}': 'unregistered_feature_candidate' must be a mapping"
                raise ValueError(msg)
            rules.append(
                _parse_unregistered_feature_candidate_rule(
                    name, description, ufc_data, severity=severity
                )
            )
        elif has_module_coverage:
            mc_data = rule_data["module_coverage"]
            if not isinstance(mc_data, dict):
                msg = f"Rule '{name}': 'module_coverage' must be a mapping"
                raise ValueError(msg)
            rules.append(
                _parse_module_coverage_rule(name, description, mc_data, severity=severity)
            )
        elif has_scenario_coverage:
            sc_data = rule_data["scenario_coverage"]
            if not isinstance(sc_data, dict):
                msg = f"Rule '{name}': 'scenario_coverage' must be a mapping"
                raise ValueError(msg)
            rules.append(
                _parse_scenario_coverage_rule(name, description, sc_data, severity=severity)
            )
        elif has_doc_area:
            da_data = rule_data["doc_area_coherence"]
            if not isinstance(da_data, dict):
                msg = f"Rule '{name}': 'doc_area_coherence' must be a mapping"
                raise ValueError(msg)
            rules.append(
                _parse_doc_area_coherence_rule(name, description, da_data, severity=severity)
            )
        elif has_summary_facts:
            sf_data = rule_data["summary_facts"]
            if not isinstance(sf_data, dict):
                msg = f"Rule '{name}': 'summary_facts' must be a mapping"
                raise ValueError(msg)
            rules.append(
                _parse_summary_facts_rule(name, description, sf_data, severity=severity)
            )
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
        elif isinstance(rule, CardinalityRule) and rule.for_matcher.ref_id is not None:
            ref_ids.add(rule.for_matcher.ref_id)

    # Check each against the database
    for ref_id in sorted(ref_ids):
        row = conn.execute("SELECT 1 FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
        if row is None:
            warnings.append(
                f"Rule references unknown ref_id '{ref_id}' (not found in nodes table)"
            )

    return warnings
