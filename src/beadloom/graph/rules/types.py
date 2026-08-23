# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Rule-engine model: constants, rule dataclasses, ``NodeMatcher``, and ``Violation``.

This module owns the *data* of the architecture rule engine — the typed shapes
that the loader produces and the evaluators consume. It holds no I/O and no
evaluation logic, only the immutable model and the constants that bound it.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from datetime import date

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

#: The one spelling of a deadline an exit condition may lead with, pinned as a
#: pattern rather than delegated to ``date.fromisoformat``: that parser widened
#: in Python 3.11 (``20260101`` and week dates parse there and raise on 3.10),
#: so leaning on it would make the same ``until:`` enforceable on one supported
#: interpreter and prose on another.
_ISO_DATE_PREFIX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:\b|$)")


def exit_condition_deadline(until: str) -> date | None:
    """The calendar date an exit condition names, or ``None`` when it names an event.

    ``until`` answers one question — *what retires this exclusion* — and there are
    two honest answers: a **date** (``2026-09-01``, optionally followed by the
    prose that explains it) and an **event** (``the repository read seam lands``).
    Only the first is checkable, and this function is the single definition of
    which is which: both surfaces that require an exit condition —
    ``forbid_import.exempt[].until`` in ``rules.yml`` and
    ``guards.<name>.exclusions[].until`` in ``flow.yml`` — read it here rather
    than restating it, so the two cannot promise different things.

    A date must LEAD the string: a deadline is the first thing an exit condition
    says, or it is not one. ``some time after 2026-01-01`` is an event.
    """
    match = _ISO_DATE_PREFIX.match(until.strip())
    if match is None:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:  # a well-formed spelling of a day that does not exist
        return None

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


def liveness_finding(
    *,
    rule_name: str,
    rule_description: str,
    message: str,
    remediation: str,
) -> Violation:
    """Build one advisory finding about a rule being unable to do its job.

    The named constructor lives beside :class:`Violation` because **two** modules
    produce liveness findings — :mod:`.liveness` for the eight matcher/graph-based
    rule types and :mod:`.evaluators` for ``forbid_import`` — and the two must not
    drift in shape.

    Always ``warn``, whatever the rule's own severity: an inert rule is a
    configuration smell, not a boundary breach, and promoting it to ``error``
    would turn an adopter's green pipeline red on upgrade (BDL-061 CONTEXT).
    """
    return Violation(
        rule_name=rule_name,
        rule_description=rule_description,
        rule_type=LIVENESS_RULE_TYPE,
        severity="warn",
        file_path=None,
        line_number=None,
        from_ref_id=None,
        to_ref_id=None,
        message=message,
        remediation=remediation,
    )
