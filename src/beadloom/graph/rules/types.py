# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Rule-engine model: constants, rule dataclasses, ``NodeMatcher``, and ``Violation``.

This module owns the *data* of the architecture rule engine — the typed shapes
that the loader produces and the evaluators consume. It holds no I/O and no
evaluation logic, only the immutable model and the constants that bound it.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_NODE_KINDS: frozenset[str] = frozenset(
    {"domain", "feature", "component", "service", "entity", "adr"}
)
VALID_EDGE_KINDS: frozenset[str] = frozenset(
    {"part_of", "depends_on", "uses", "implements", "touches_entity", "touches_code"}
)
VALID_RULE_SEVERITIES: frozenset[str] = frozenset({"error", "warn"})
SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1, 2, 3})

# Edge lifecycles that count as live reality for structural checks (BDL-037
# Principle 8). Only ``active`` edges are live: ``planned`` (intent, not yet
# built), ``deprecated`` (on the way out), and ``dead`` edges are not counted
# as live ``no-dependency-cycles`` / ``architecture-layers`` violations.
LIVE_EDGE_LIFECYCLES: frozenset[str] = frozenset({"active"})

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


@dataclass(frozen=True)
class UnregisteredFeatureCandidateRule:
    """Flag substantial domain-only modules that model no feature (BDL-051 S1).

    For each node matching ``for_matcher`` (typically ``kind: domain``), groups
    indexed ``code_symbols`` rows by ``file_path`` and inspects each file's
    ``annotations`` JSON. A file is a *candidate unregistered feature* when:

    - its annotations carry a ``domain`` key equal to the matched node's
      ``ref_id`` (it is attributed to this domain),
    - its annotations carry **no** ``feature`` key (it models no feature), and
    - its indexed-symbol count is ``>= min_symbols`` (it is substantial).

    Findings are advisory (``severity: warn``): they name a modeling candidate,
    they do not decide it. Known domain-level plumbing can be silenced via
    ``exclude`` (a tuple of ``fnmatch`` file-path globs).
    """

    name: str
    description: str
    for_matcher: NodeMatcher
    min_symbols: int = 5
    exclude: tuple[str, ...] = ()
    severity: str = "warn"


@dataclass(frozen=True)
class ModuleCoverageRule:
    """Require every ``src/`` module to be a tracked node or explicitly exempt.

    This is the BDL-051 S3a *coverage* lint — the stronger, complete-coverage
    successor to :class:`UnregisteredFeatureCandidateRule`. The goal is **no
    shadow code**: every source module is either tracked by a node or named on a
    visible exempt list.

    For each module under ``source_root`` that has at least ``min_symbols``
    indexed symbols, the module is **covered** when any of:

    - one of its symbols' ``annotations`` carries a ``feature`` key, or
    - one of its symbols' ``annotations`` carries a ``component`` key, or
    - the module's path equals a ``domain``/``service``/``component``/… node's
      ``source`` (it *is* a node), or
    - its path matches an entry in ``exempt`` (a tuple of ``fnmatch`` globs).

    An uncovered module produces one finding naming the file and its symbol
    count. Since BDL-051 S3b classified every module, the rule is promoted to
    ``severity: error`` — a new shadow module (uncovered + not exempt) fails
    ``lint --strict``, enforcing the no-shadow-code guarantee.

    The exempt criterion (documented in ``rules.yml`` and the architecture-model
    guide): a module may be exempt when it has ``< N`` public symbols **and**
    does not back a CLI command **and** is internal-only (docstring-only glue).
    The list lives in ``rules.yml`` — it is visible, not a silent escape hatch.
    """

    name: str
    description: str
    source_root: str = "src/beadloom/"
    min_symbols: int = 1
    exempt: tuple[str, ...] = ()
    severity: str = "warn"


Rule = (
    DenyRule
    | RequireRule
    | CycleRule
    | ImportBoundaryRule
    | ForbidEdgeRule
    | LayerRule
    | CardinalityRule
    | UnregisteredFeatureCandidateRule
    | ModuleCoverageRule
)


@dataclass(frozen=True)
class Violation:
    """A single rule violation.

    ``remediation`` (BDL-039 F3 BEAD-02) is an additive, agent-actionable
    "how to fix" hint derived per rule kind by ``_remediation_for``. It
    defaults to ``None`` so existing constructions (and their tests) are
    unaffected; :func:`evaluate_all` populates it as a deterministic post-pass.
    """

    rule_name: str
    rule_description: str
    rule_type: str  # "deny" | "require" | "cardinality" | ...
    severity: str  # "error" | "warn"
    file_path: str | None  # source file (for deny rules)
    line_number: int | None  # line number (for deny rules)
    from_ref_id: str | None  # source node
    to_ref_id: str | None  # target node
    message: str  # human-readable explanation
    remediation: str | None = None  # agent-actionable "how to fix" hint
