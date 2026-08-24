"""Wave planning: decide, from the graph, which beads may run at the same time.

``beadloom waves <bead>...`` DECIDES a shape; it does not advise one. An advisory
wave shape is the same failure this epic exists to remove — a statement in prose
that a model may or may not act on — so the answer is a plan with an exit code,
and a human who disagrees with it records an override that carries a reason and
an exit condition, exactly like every other stand-down in this codebase.

The guarantee the shape makes, stated once so the rest of the package can be read
against it: **for any two beads it places in the same wave, no medium they share
can carry one bead's in-progress state into the other's result — and where a
medium cannot give that guarantee, the wave says so and names the one bead that
measures the combined outcome.** Code independence (:mod:`.independence`) is the
half the graph can decide. The other half (:mod:`.media`) cannot be decided by
any shape at all and is therefore stated rather than assumed.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

from beadloom.application.waves.config import (
    OVERRIDE_KEYS,
    WaveConfigError,
    load_overrides,
)
from beadloom.application.waves.independence import conflict_between, conflicts_among
from beadloom.application.waves.media import (
    MEDIUM_COMMIT_GATE,
    MEDIUM_DOC_BASELINE,
    MEDIUM_TRACKER_IDS,
    MEDIUM_WORKING_TREE,
    SHARED_MEDIA,
    media_for,
)
from beadloom.application.waves.models import (
    DECISION_PARALLEL,
    DECISION_SERIAL,
    DECISIONS,
    REASON_BLOCKED_BY_BEAD,
    REASON_DEPENDENCY_EDGE,
    REASON_OVERRIDE_SERIAL,
    REASON_SHARED_FILE,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    UNRESOLVED_NO_DECLARATION,
    UNRESOLVED_UNKNOWN_REF,
    BeadRecord,
    BeadScope,
    Conflict,
    OverrideOutcome,
    SharedMedium,
    Wave,
    WaveOverride,
    WavePlan,
)
from beadloom.application.waves.planner import plan_waves
from beadloom.application.waves.scope import declared_refs, resolve_scope, resolve_scopes

__all__ = [
    "DECISIONS",
    "DECISION_PARALLEL",
    "DECISION_SERIAL",
    "MEDIUM_COMMIT_GATE",
    "MEDIUM_DOC_BASELINE",
    "MEDIUM_TRACKER_IDS",
    "MEDIUM_WORKING_TREE",
    "OVERRIDE_KEYS",
    "REASON_BLOCKED_BY_BEAD",
    "REASON_DEPENDENCY_EDGE",
    "REASON_OVERRIDE_SERIAL",
    "REASON_SHARED_FILE",
    "REASON_SHARED_NODE",
    "REASON_UNRESOLVED_SCOPE",
    "SHARED_MEDIA",
    "UNRESOLVED_NO_DECLARATION",
    "UNRESOLVED_UNKNOWN_REF",
    "BeadRecord",
    "BeadScope",
    "Conflict",
    "OverrideOutcome",
    "SharedMedium",
    "Wave",
    "WaveConfigError",
    "WaveOverride",
    "WavePlan",
    "conflict_between",
    "conflicts_among",
    "declared_refs",
    "load_overrides",
    "media_for",
    "plan_waves",
    "resolve_scope",
    "resolve_scopes",
]
