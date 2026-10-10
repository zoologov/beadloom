# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Rule-engine model: constants, rule dataclasses, ``NodeMatcher``, and ``Violation``.

This module owns the *data* of the architecture rule engine — the typed shapes
that the loader produces and the evaluators consume. It holds no I/O and no
evaluation logic, only the immutable model and the constants that bound it.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from beadloom.graph.scenarios import DEFAULT_FEATURE_GLOB

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

#: ``rule_type`` of a finding that reports a rule which cannot fire, as opposed
#: to code that breaks one. Kept distinct so a consumer can tell "your
#: architecture is broken" from "your check is broken". It lives here, with the
#: model, because two modules produce it: :mod:`.liveness` for the eight
#: matcher/graph-based rule types, and :mod:`.evaluators` for ``forbid_import``
#: (whose dead-glob and dead-exemption findings fall out of the import scan the
#: rule evaluation already runs).
LIVENESS_RULE_TYPE = "rule_liveness"

#: ``rule_type`` of the statement each suite rule (``test_binding``,
#: ``test_import_boundary``, ``scenario_binding``) prints on every run: how much of
#: the suite it judged and how much it could not. It decides nothing, so it is an
#: advisory (:mod:`.advisories`) and ``--fail-on-warn`` does not exit on it.
SUITE_POPULATION_RULE_TYPE = "suite_population"


#: What each side of a ``forbid_import`` rule is matched against. Stated on every
#: liveness finding because the mismatch it describes is invisible otherwise: a
#: ``src/``-prefixed ``to:`` glob simply never matches, and the rule reads green
#: forever (BDL-UX #150). It lives with the model, beside the ``ImportBoundaryRule``
#: docstring that defines the two forms, because three modules now state them:
#: :mod:`.evaluators` (a dead glob), :mod:`.exemptions` (a dead exemption) and the
#: reference documentation generated from here.
MATCHING_FORM_HINT = (
    "`from:` is matched against the repo-relative source file path as indexed "
    "(e.g. `src/pkg/tui/app.py`); `to:` against the dotted import path with dots "
    "replaced by slashes (e.g. `pkg/infrastructure/db`) — no `src/` prefix, no file "
    "extension. Drop the source root from `to:`, or widen it to `**/infrastructure/**`"
)


def import_path_as_path(import_path: str) -> str:
    """Convert a dotted import path to the slash-separated form globs are matched against.

    Example: ``components.features.calendar.events`` becomes
    ``components/features/calendar/events``.
    """
    return import_path.replace(".", "/")


def matches_import_target(target_as_path: str, glob: str) -> bool:
    """Match a ``to``-side glob against an indexed import target.

    A glob covering a package covers a bare import OF that package: Python records
    ``from pkg.infrastructure import db`` as the target ``pkg/infrastructure``, so
    a rule written ``pkg/infrastructure/**`` would otherwise miss the single most
    common way of reaching into the package it forbids (BDL-UX #150 — the probe
    injected to reproduce that bead fired under no glob form at all). Matching the
    target with a trailing slash appended covers it without widening anything else:
    ``pkg/infrastructure_docs`` still does not match ``pkg/infrastructure/**``.
    """
    return fnmatch.fnmatch(target_as_path, glob) or fnmatch.fnmatch(target_as_path + "/", glob)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeMatcher:
    """Matches graph nodes by ref_id, kind, tag and/or the beginning of a tag.

    ``tag_prefix`` (BDL-080 S2b) selects a node carrying ANY tag that begins with
    it, so one rule covers a family of tags: ``fsd-`` selects a slice of every
    Feature-Sliced layer, where ``tag`` would need one rule per layer.
    """

    ref_id: str | None = None
    kind: str | None = None
    tag: str | None = None
    exclude: tuple[str, ...] | None = None
    tag_prefix: str | None = None

    @property
    def reads_tags(self) -> bool:
        """Whether a node's tags decide the match, so an evaluator must load them."""
        return self.tag is not None or self.tag_prefix is not None

    def matches(self, node_ref_id: str, node_kind: str, *, tags: set[str] | None = None) -> bool:
        """Return True if this matcher matches the given node.

        The *tags* parameter is optional for backward compatibility.
        When *tags* is ``None`` and ``self.tag`` or ``self.tag_prefix`` is set,
        the tag check is skipped (i.e. old callers that do not pass tags are not
        broken); a caller that judges by tags reads :attr:`reads_tags`.

        The *exclude* field, when set, causes ``matches()`` to return
        ``False`` for any ``node_ref_id`` listed in the tuple.
        """
        if self.exclude and node_ref_id in self.exclude:
            return False
        if self.ref_id is not None and self.ref_id != node_ref_id:
            return False
        if self.kind is not None and self.kind != node_kind:
            return False
        if tags is None:
            return True
        if self.tag is not None and self.tag not in tags:
            return False
        prefix = self.tag_prefix
        return prefix is None or any(tag.startswith(prefix) for tag in tags)

    def describe(self) -> str:
        """How the matcher reads in a finding, so an author can see what selected nothing."""
        fields = (
            ("ref_id", self.ref_id),
            ("kind", self.kind),
            ("tag", self.tag),
            ("tag_prefix", self.tag_prefix),
        )
        parts = [f"{field}={value}" for field, value in fields if value is not None]
        return ", ".join(parts) if parts else "everything"


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
class ImportExemption:
    """One named, expiring exception to an :class:`ImportBoundaryRule`.

    An exemption records a pre-existing crossing instead of narrowing the rule
    that catches it: the boundary keeps its full scope (a NEW crossing still
    fails), while what is tolerated today is visible, attributed and dated.

    ``reason`` and ``until`` are mandatory (BDL-061 CONTEXT: *every exclusion
    carries a reason and an exit condition; one with neither is a config
    error*), and an exemption that suppresses nothing is reported — that report
    IS the exit condition firing.
    """

    to_glob: str = "*"  # matched like the rule's ``to``: dotted import path, dots -> slashes
    from_glob: str = "*"  # matched like the rule's ``from``: repo-relative source file path
    reason: str = ""
    until: str = ""


@dataclass(frozen=True)
class ImportBoundaryRule:
    """Forbid imports between file paths matched by glob patterns.

    Unlike DenyRule (which matches graph nodes via NodeMatcher), this rule
    operates directly on file paths using ``fnmatch`` glob patterns against
    the ``code_imports`` table.

    **The two globs are matched against two different vocabularies** — the
    single fact whose absence from the reference left four of this project's own
    rules inert for months (BDL-UX #150):

    - ``from_glob`` is matched against the **repo-relative source file path** as
      indexed, e.g. ``src/beadloom/tui/app.py`` (it carries the source root);
    - ``to_glob`` is matched against the **imported module path** with dots
      replaced by slashes, e.g. ``beadloom/infrastructure/db`` (it never
      carries a source root, and never a file extension).

    So a ``to_glob`` written as ``src/pkg/infra/**`` can never match anything.
    ``evaluate_import_boundary_rules`` reports exactly that instead of counting
    the rule as clean.
    """

    name: str
    description: str
    from_glob: str  # source file path glob (e.g. "src/pkg/features/map/**")
    to_glob: str  # target glob (matched against import_path after dot-to-slash)
    severity: str = "error"  # "error" | "warn"
    exempt: tuple[ImportExemption, ...] = ()  # named, expiring pre-existing crossings


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
class LayerExemption:
    """One same-layer crossing a layer rule excuses, why, and what retires it.

    The shape mirrors :class:`ImportExemption` and for the same reason: an
    exclusion with no reason and no exit condition is how a gate is switched off
    without saying so (BDL-061 CONTEXT). It differs in what it names — two node
    ``ref_id`` globs rather than a file path and an import target — because a
    same-layer crossing is an EDGE, and an entry that named only one of its two
    ends would excuse everything that touches that end.
    """

    from_glob: str
    to_glob: str
    reason: str
    until: str

    def covers(self, src_ref_id: str, dst_ref_id: str) -> bool:
        """True when this entry excuses that edge, in that direction.

        Direction is part of the match: ``a -> b`` and ``b -> a`` are two
        crossings and a project that excused one did not excuse the other.
        """
        return fnmatch.fnmatchcase(src_ref_id, self.from_glob) and fnmatch.fnmatchcase(
            dst_ref_id, self.to_glob
        )


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
    #: Same-layer crossings this rule excuses. Empty by default, and every entry
    #: carries a reason and an exit condition the loader refuses to do without
    #: (BDL-070 B2): a layer rule that can be switched off silently is a layer
    #: rule nobody can read the green of.
    exempt: tuple[LayerExemption, ...] = ()
    #: The node whose ``part_of`` subtree the rule judges inside (BDL-080 S1b),
    #: ``None`` for the whole graph. A frontend's layering declared beside a
    #: backend's names its own service here, so a node elsewhere that happens to
    #: carry one of its tags is not judged by it.
    scope: str | None = None
    #: The name the portal shows the rule by (BDL-080 S1e), ``None`` when the
    #: rule declares none and is shown by its ``name``. The name stays the
    #: rule's identifier — lint, an exemption and the portal's URL say it — so
    #: a reader's name ("DDD architecture") needs a key of its own.
    title: str | None = None


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


@dataclass(frozen=True)
class NonBehaviouralNode:
    """One node declared to carry no behaviour, with the reason it does not.

    The counterpart of :class:`ImportExemption` for
    :class:`ScenarioCoverageRule`: a chore, a data model or a pure vocabulary
    module has no user-observable behaviour, and demanding a scenario for it
    produces ceremony rather than a check. So the absence becomes a **stated
    decision** instead of a silent gap (PRD G7).

    ``reason`` is mandatory — an unnamed exclusion is how a gate is quietly
    switched off (BDL-061 CONTEXT). There is deliberately no ``until``: unlike
    an import exemption, this is not a debt that expires but a classification
    that is either true or false. What keeps it honest instead is that a dead
    declaration — one naming a node outside the rule's population, or one that
    turns out to HAVE a scenario — is itself reported.
    """

    node: str
    reason: str


@dataclass(frozen=True)
class ScenarioCoverageRule:
    """Bind behaviour-bearing nodes to executable scenarios, both ways.

    The ``.feature`` file is the source of truth (BDL-061 CONTEXT, option (b));
    this rule reports where the binding is missing, in three directions:

    - a node matched by ``for_matcher`` that **no scenario names**;
    - a scenario that names **no bead**, or names a node that is not in the
      graph, or a file in the suite that could not be read or declares nothing;
    - a scenario a document under ``references`` claims exists and the suite
      does not contain.

    ``features`` is a glob, defaulting to the layout Q3 chose
    (``tests/acceptance/features/**/*.feature``) and configurable from the
    start, because the flow ships to projects with their own conventions.

    ``severity`` defaults to ``warn`` and is meant to stay there. A finding here
    is about declared *intent* — that a behaviour was specified — and an
    ``error`` would turn every adopter's green project red on the upgrade that
    ships the rule (BDL-061 CONTEXT). Loudness replaces blocking: the finding
    prints by default and every message carries the population it is a fraction
    of.
    """

    name: str
    description: str
    #: The population. Defaults to ``kind: feature`` — the node kind that models
    #: a unit of user-observable behaviour in every methodology Beadloom ships an
    #: overlay for — so ``scenario_coverage: {}`` is a working rule rather than a
    #: configuration error.
    for_matcher: NodeMatcher = NodeMatcher(kind="feature")
    features: str = DEFAULT_FEATURE_GLOB
    references: tuple[str, ...] = ()
    non_behavioural: tuple[NonBehaviouralNode, ...] = ()
    severity: str = "warn"


#: Default share of a source area's pairs a mapping must cover to be dominant.
#: 0.6 rather than a bare majority: a convention that only just outvotes its
#: alternative is a migration in progress, and reporting the losing half of one
#: as violations is how a rule earns a blanket disable.
DEFAULT_DOC_AREA_THRESHOLD = 0.6

#: Default number of agreeing pairs a dominant mapping must rest on. Two, because
#: one observation is not a convention — it is a single fact that cannot disagree
#: with itself, and a graph of areas holding one node each would otherwise report
#: unanimous agreement having verified nothing.
DEFAULT_DOC_AREA_MIN_SUPPORT = 2


@dataclass(frozen=True)
class DocAreaCoherenceRule:
    """Hold every node to the docs placement the rest of the graph already keeps.

    The convention is **derived from the graph under test**, never declared here:
    :mod:`.doc_area` reads the source area of each node and the docs area of each
    of its documents, counts the agreements, and calls a mapping dominant when it
    covers ``threshold`` of that area's pairs over at least ``min_support`` of
    them. A node contradicting a dominant mapping is a violation; a node under no
    dominant mapping is not, and a graph with no dominant mapping at all makes the
    rule report that it checked nothing rather than that everything is fine.

    Both knobs are configurable because "how much agreement is a convention" is a
    property of a project's size and history, not of Beadloom. Neither has a
    layout in it, which is the point: no directory name appears in this rule, in
    its defaults, or in the module that evaluates it.

    ``severity`` defaults to ``warn`` and is meant to stay there for an adopter.
    A finding here is about house style, and an ``error`` would fail a green
    project's first run on a convention it never agreed to; a project that has
    settled its layout raises it in its own ``rules.yml``.
    """

    name: str
    description: str
    threshold: float = DEFAULT_DOC_AREA_THRESHOLD
    min_support: int = DEFAULT_DOC_AREA_MIN_SUPPORT
    severity: str = "warn"


@dataclass(frozen=True)
class SummaryFactsRule:
    """Hold every node summary to the numbers the project computes about itself.

    :mod:`.summary_facts` reads each node's ``summary`` with the documentation
    audit's own extractor and compares what it finds against the audit's own fact
    registry. There is nothing to configure: what counts as a version, what
    counts as a claim about a count, and how close a count has to be are all
    decided by the audit, and a knob here would be a second answer to a question
    already answered once.

    ``severity`` defaults to ``error`` rather than the ``warn`` a convention
    check ships with. A summary that contradicts the project it describes is
    wrong in every house style, so there is no adopter preference to respect —
    and the value is in the graph the adopter wrote, so it is theirs to fix.
    """

    name: str
    description: str
    severity: str = "error"


@dataclass(frozen=True)
class ListedExemption:
    """Named test files, feature files or nodes a suite rule excuses, why, and what retires them.

    The counterpart of :class:`ImportExemption` for the rules that judge the test
    suite (BDL-074 C3), and required the same way: ``reason`` and ``until`` are
    mandatory, because an exclusion with neither is how a gate is switched off
    without saying so (BDL-061 CONTEXT).

    It LISTS its entries rather than holding one glob, so each entry is judged on
    its own: an entry that excuses nothing is reported by name. That per-entry
    report is the exit condition firing — a test file listed as not yet split is
    reported the run after it moves to its node's folder, and a glob covering a
    whole folder could not say which of its files had moved.
    """

    #: Path globs (``fnmatch``) over repository-relative files, or node ``ref_id``
    #: values — which of the two is decided by the key the rule read them from.
    entries: tuple[str, ...]
    reason: str
    until: str


@dataclass(frozen=True)
class TestBindingRule:
    """A test file bound to no node, and a node bound to no test file (BDL-074 C3).

    The binding is the one the reindex records in ``test_files``: a test file's
    node follows from the mirror of its path or from a node's ``tests:`` list.
    Two legs, each run only when declared:

    - ``files`` (a path glob) — every indexed test file it matches that binds to
      no node is reported. A file a kind folder places is outside the judged
      population and counted by its recorded kind: an acceptance step file, whose
      scenarios bind by their ``@node:`` tags, and a self-check, which tests the
      project's own files and binds to no node by design.
    - ``for`` (a node matcher) — every matched node with no bound test file, its
      own or a ``part_of`` descendant's, is reported.

    ``severity`` defaults to ``warn``: a project's tests are unplaced until it
    adopts the mirrored layout, and an ``error`` would turn every adopter red on
    the upgrade that ships the rule.
    """

    __test__ = False  # a product type, not a pytest test class

    name: str
    description: str
    for_matcher: NodeMatcher | None = None
    files: str | None = None
    exempt_files: tuple[ListedExemption, ...] = ()
    exempt_nodes: tuple[ListedExemption, ...] = ()
    severity: str = "warn"


@dataclass(frozen=True)
class TestImportBoundaryRule:
    """``forbid_import`` over the imports of TEST files, narrowed by their binding.

    ``from_glob`` and ``to_glob`` are matched exactly as :class:`ImportBoundaryRule`
    matches them — the repository-relative file path and the dotted import path
    with dots turned into slashes — against the ``test_imports`` the reindex
    records rather than ``code_imports``, which holds no test file. ``of_matcher``,
    when set, keeps only the test files bound to a node it matches, that node or
    one of its ``part_of`` containers: "a unit test OF a domain node".
    """

    __test__ = False  # a product type, not a pytest test class

    name: str
    description: str
    from_glob: str
    to_glob: str
    of_matcher: NodeMatcher | None = None
    severity: str = "error"
    exempt: tuple[ImportExemption, ...] = ()

    def as_import_rule(self) -> ImportBoundaryRule:
        """The same boundary as the rule ``forbid_import``'s evaluator reads."""
        return ImportBoundaryRule(
            name=self.name,
            description=self.description,
            from_glob=self.from_glob,
            to_glob=self.to_glob,
            severity=self.severity,
            exempt=self.exempt,
        )


@dataclass(frozen=True)
class ScenarioBindingRule:
    """A scenario's ``@node:`` tag names the folder its feature file sits in (BDL-074 C3).

    The suite is laid out one folder per node, so the folder that holds a feature
    file names the node its scenarios bind to, and a folder above it that names a
    node names one of that node's ``part_of`` containers. Whether a scenario's
    steps EXECUTE its node is the other half of the binding, and it is not judged:
    it needs a runtime trace this rule does not have (see :mod:`.scenario_binding`).

    ``severity`` defaults to ``warn``, for the reason :class:`TestBindingRule`'s does.
    """

    name: str
    description: str
    features: str = DEFAULT_FEATURE_GLOB
    exempt: tuple[ListedExemption, ...] = ()
    severity: str = "warn"


#: The standard segments of a Feature-Sliced Design slice, in FSD's own order: what a
#: slice's top may hold besides its ``index`` (BDL-080 S3c).
DEFAULT_SLICE_SEGMENTS: tuple[str, ...] = ("ui", "model", "lib", "api", "config")


@dataclass(frozen=True)
class SlicePublicApiRule:
    """An import into a slice from outside it lands on the slice's ``index`` (BDL-080 S3c).

    Feature-Sliced Design enters a slice through its public API, the ``index`` file at
    the top of its folder; Steiger's ``fsd/no-public-api-sidestep`` reports reaching
    past it (its ``public-api`` reports a slice with no ``index`` at all). A *slice*
    is a node carrying one of ``tags`` whose ``source`` is a folder.

    **Over resolved imports, not import paths.** ``forbid_import`` matches globs
    against import paths, and no glob says "inside this slice but not its index":
    ``@/features/auth`` and ``@/features/auth/model/session`` differ by a suffix only an
    alias table can interpret. So the rule reads ``code_imports``, where the reindex has
    already decided which node each import reached, and asks only where inside that
    slice's folder the imported file is: a relative specifier is completed from the
    importing file's folder, any other is matched against the slice's folder by its
    longest trailing path that names a file there. A file other than the slice's
    ``index`` is a finding; so is an import into a slice that has no ``index`` at all,
    which has no public API to enter. An import from inside the slice is not judged.

    YAML::

        - name: fsd-public-api
          severity: error
          slice_public_api:
            tags: [fsd-pages, fsd-widgets, fsd-features, fsd-entities]
    """

    name: str
    description: str
    tags: tuple[str, ...]
    severity: str = "error"


@dataclass(frozen=True)
class SliceShapeRule:
    """A slice's top holds its segments and its ``index`` (BDL-080 S3c).

    FSD gives a slice its shape rather than a size: the standard segments
    (:data:`DEFAULT_SLICE_SEGMENTS`) and a public API in ``index``. For each slice — a
    node carrying one of ``tags`` whose ``source`` is a folder on disk — a folder at
    its top whose name is not in ``segments`` is a finding, and so is a code file
    there that is not its ``index``. Hidden entries and files that are not code
    (``README.md``) are not judged.

    YAML::

        - name: fsd-slice-shape
          severity: warn
          slice_shape:
            tags: [fsd-pages, fsd-widgets, fsd-features, fsd-entities]
            segments: [ui, model, lib, api, config]   # optional; these five by default
    """

    name: str
    description: str
    tags: tuple[str, ...]
    segments: tuple[str, ...] = DEFAULT_SLICE_SEGMENTS
    severity: str = "error"


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
    | ScenarioCoverageRule
    | DocAreaCoherenceRule
    | SummaryFactsRule
    | TestBindingRule
    | TestImportBoundaryRule
    | ScenarioBindingRule
    | SlicePublicApiRule
    | SliceShapeRule
)


#: The ``rule_type`` a layer rule's finding about ONE EDGE carries — a
#: dependency pointing up through the layers, one skipping a layer, or one
#: crossing between peers inside a layer. It lives here rather than beside
#: either emitter because :mod:`.evaluators` and :mod:`.layer_crossings` both
#: produce it and :mod:`.layer_edges` selects on it, and a token written down
#: in three places is a set that can drift into disagreement without anything
#: going red. A layer rule's OTHER findings — the population it judged, a
#: declared layer no node is in, an exemption that excuses nothing — are about
#: the rule rather than about an edge and carry their own types.
LAYER_EDGE_RULE_TYPE = "layer"


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


def liveness_finding(
    *,
    rule_name: str,
    rule_description: str,
    message: str,
    remediation: str,
    severity: str = "warn",
    from_ref_id: str | None = None,
) -> Violation:
    """Build one advisory finding about a rule being unable to do its job.

    The named constructor lives beside :class:`Violation` because **two** modules
    produce liveness findings — :mod:`.liveness` for the eight matcher/graph-based
    rule types and :mod:`.evaluators` for ``forbid_import`` — and the two must not
    drift in shape.

    ``warn`` by default, and that default is the right answer for a PARTIAL
    inertness — a dead glob, an exemption that excuses nothing, a matcher
    selecting no node while the rule's other legs still fire. Such a rule is a
    configuration smell, not a boundary breach, and promoting it would turn an
    adopter's green pipeline red on upgrade (BDL-061 CONTEXT).

    A **total** stand-down is a different thing and callers may say so by passing
    *severity*. When a rule could check NONE of its population, "the rule found
    nothing wrong" and "the rule never ran" are the same output, and a project
    that deliberately escalated that rule to ``error`` has had its escalation
    quietly evaporate at exactly the moment it mattered (BDL-062 ``.9``,
    BDL-UX #195). Passing the rule's declared severity costs an adopter nothing:
    a rule that ships ``warn`` still reports ``warn``, so nobody's first
    ``beadloom ci`` goes red on a graph that is merely small.

    *from_ref_id* names the node the finding is about, for the callers that have
    one. Most do not: a liveness finding is usually about a RULE that could not
    run, and a node id would be an invention. ``graph-summary-facts`` is the
    exception — it reports per node, and its two states were reaching consumers
    differently, a disagreement carrying ``claim.ref_id`` and an unverifiable
    claim carrying nothing, from the same rule about the same node (BDL-062.10,
    m1). Added the same way *severity* was, and for the same reason: a default
    that preserves every existing caller's output byte for byte.
    """
    return Violation(
        rule_name=rule_name,
        rule_description=rule_description,
        rule_type=LIVENESS_RULE_TYPE,
        severity=severity,
        file_path=None,
        line_number=None,
        from_ref_id=from_ref_id,
        to_ref_id=None,
        message=message,
        remediation=remediation,
    )


def population_finding(*, rule_name: str, rule_description: str, message: str) -> Violation:
    """The statement a suite rule prints of what it judged — always ``warn``, never a verdict.

    Printed on every run, clean or not, because a green count is not a checked
    count: "0 test files bound to no node" means something only beside the number
    of files the rule looked at and the number it could not.
    """
    return Violation(
        rule_name=rule_name,
        rule_description=rule_description,
        rule_type=SUITE_POPULATION_RULE_TYPE,
        severity="warn",
        file_path=None,
        line_number=None,
        from_ref_id=None,
        to_ref_id=None,
        message=message,
        remediation=(
            "nothing to fix: this states the rule's reach, so a count of findings "
            "can be read as a fraction of what was judged"
        ),
    )
