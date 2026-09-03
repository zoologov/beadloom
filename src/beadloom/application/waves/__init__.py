"""Wave planning: decide, from the graph, which beads may run at the same time.

``beadloom waves <bead>...`` DECIDES a shape; it does not advise one. An advisory
wave shape is the same failure this epic exists to remove — a statement in prose
that a model may or may not act on — so the answer is a plan with an exit code,
and a human who disagrees with it records an override that carries a reason and
an exit condition, exactly like every other stand-down in this codebase.

The guarantee the shape makes, stated once so the rest of the package can be read
against it: **for any two beads it places in the same wave, no medium they share
can carry one bead's in-progress state into the other's result — and where a
medium cannot give that guarantee, the wave says so, names the one bead that
measures the combined outcome, and CHECKS the medium's plan-time precondition.**
Code independence (:mod:`.independence`) is the half the graph can decide. The
other half cannot be decided by any shape at all, so it is stated
(:mod:`.media`) and then checked (:mod:`.media_checks`).

**The split the sentence names, because the second half is not symmetrical with
the first.** What is checked is a PRECONDITION, measured before the wave runs:
the tree it starts from, the hook that will judge its commits, the doc baseline
it inherits, and the ids its beads already carry. What is NOT checked — and
cannot be, by anything holding a plan — is the wave's conduct afterwards: no
check here can know that the gate owner ran the combined tree. Until BDL-061.22
the second half was a constant tuple that could not fail at all, which is worse
than claiming less, because the prose is what a reader trusts.
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
    ROOM_PREFIX,
    SHARED_MEDIA,
    room_for,
)
from beadloom.application.waves.media_checks import (
    check_media,
    finding_for,
    title_id_mismatches,
)
from beadloom.application.waves.models import (
    DECISION_PARALLEL,
    DECISION_SERIAL,
    DECISIONS,
    GATE_ABSENT,
    GATE_COMMIT_SCOPED,
    GATE_WHOLE_TREE,
    REASON_BLOCKED_BY_BEAD,
    REASON_DEPENDENCY_EDGE,
    REASON_OVERRIDE_SERIAL,
    REASON_SHARED_FILE,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    STATUS_FAILED,
    STATUS_NOT_APPLICABLE,
    STATUS_PASSED,
    STATUS_UNMEASURED,
    UNRESOLVED_DROPPED_NODE,
    UNRESOLVED_NO_DECLARATION,
    UNRESOLVED_REMEDIES,
    UNRESOLVED_UNANCHORED,
    UNRESOLVED_UNKNOWN_REF,
    BeadRecord,
    BeadScope,
    Conflict,
    MediumCheck,
    OverrideOutcome,
    SharedMedium,
    Wave,
    WaveEnvironment,
    WaveOverride,
    WavePlan,
)
from beadloom.application.waves.planner import plan_waves
from beadloom.application.waves.scope import (
    DECLARATION_FIELDS,
    Declaration,
    compose_declaration,
    declared_refs,
    parse_declaration,
    resolve_scope,
    resolve_scopes,
)

__all__ = [
    "DECISIONS",
    "DECISION_PARALLEL",
    "DECISION_SERIAL",
    "DECLARATION_FIELDS",
    "GATE_ABSENT",
    "GATE_COMMIT_SCOPED",
    "GATE_WHOLE_TREE",
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
    "ROOM_PREFIX",
    "SHARED_MEDIA",
    "STATUS_FAILED",
    "STATUS_NOT_APPLICABLE",
    "STATUS_PASSED",
    "STATUS_UNMEASURED",
    "UNRESOLVED_DROPPED_NODE",
    "UNRESOLVED_NO_DECLARATION",
    "UNRESOLVED_REMEDIES",
    "UNRESOLVED_UNANCHORED",
    "UNRESOLVED_UNKNOWN_REF",
    "BeadRecord",
    "BeadScope",
    "Conflict",
    "Declaration",
    "MediumCheck",
    "OverrideOutcome",
    "SharedMedium",
    "Wave",
    "WaveConfigError",
    "WaveEnvironment",
    "WaveOverride",
    "WavePlan",
    "check_media",
    "compose_declaration",
    "conflict_between",
    "conflicts_among",
    "declared_refs",
    "finding_for",
    "load_overrides",
    "parse_declaration",
    "plan_waves",
    "resolve_scope",
    "resolve_scopes",
    "room_for",
    "title_id_mismatches",
]
