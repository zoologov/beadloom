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
from beadloom.application.waves.derivation import (
    compare_declarations,
    derivation_findings,
    unguarded_axes,
)
from beadloom.application.waves.independence import conflict_between, conflicts_among
from beadloom.application.waves.landing import (
    DEFECT_ANONYMOUS_HOLDER,
    DEFECT_QUEUE_ONLY_WAIT,
    DEFECT_UNGUARDED_RELEASE,
    DEFECT_UNKNOWN_FORM,
    DEFECTS,
    HOLDER_FLAG,
    LOCK_COMMAND,
    WAIT_FLAG,
    LockInvocation,
    LockSite,
    defect_detail,
    lock_sites,
)
from beadloom.application.waves.media import (
    MEDIUM_COMMIT_GATE,
    MEDIUM_DOC_BASELINE,
    MEDIUM_LANDING_ORDER,
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
    title_references,
)
from beadloom.application.waves.models import (
    AXES_NOT_GATHERED,
    AXIS_AGREES,
    AXIS_NOT_ATTRIBUTED,
    AXIS_NOT_DERIVED,
    AXIS_RULED_OUT,
    AXIS_UNDECIDED,
    DECISION_PARALLEL,
    DECISION_SERIAL,
    DECISIONS,
    FINDING_DECLARED_OUTSIDE,
    FINDING_NOT_COMPARED,
    FINDING_UNGUARDED_AXIS,
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
    UNKNOWN_REMEDY,
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
    ScopeAgreement,
    SharedMedium,
    UnguardedAxis,
    Wave,
    WaveEnvironment,
    WaveOverride,
    WavePlan,
    WorkItemAxes,
    remedy_for,
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
    "AXES_NOT_GATHERED",
    "AXIS_AGREES",
    "AXIS_NOT_ATTRIBUTED",
    "AXIS_NOT_DERIVED",
    "AXIS_RULED_OUT",
    "AXIS_UNDECIDED",
    "DECISIONS",
    "DECISION_PARALLEL",
    "DECISION_SERIAL",
    "DECLARATION_FIELDS",
    "DEFECTS",
    "DEFECT_ANONYMOUS_HOLDER",
    "DEFECT_QUEUE_ONLY_WAIT",
    "DEFECT_UNGUARDED_RELEASE",
    "DEFECT_UNKNOWN_FORM",
    "FINDING_DECLARED_OUTSIDE",
    "FINDING_NOT_COMPARED",
    "FINDING_UNGUARDED_AXIS",
    "GATE_ABSENT",
    "GATE_COMMIT_SCOPED",
    "GATE_WHOLE_TREE",
    "HOLDER_FLAG",
    "LOCK_COMMAND",
    "MEDIUM_COMMIT_GATE",
    "MEDIUM_DOC_BASELINE",
    "MEDIUM_LANDING_ORDER",
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
    "UNKNOWN_REMEDY",
    "UNRESOLVED_DROPPED_NODE",
    "UNRESOLVED_NO_DECLARATION",
    "UNRESOLVED_REMEDIES",
    "UNRESOLVED_UNANCHORED",
    "UNRESOLVED_UNKNOWN_REF",
    "WAIT_FLAG",
    "BeadRecord",
    "BeadScope",
    "Conflict",
    "Declaration",
    "LockInvocation",
    "LockSite",
    "MediumCheck",
    "OverrideOutcome",
    "ScopeAgreement",
    "SharedMedium",
    "UnguardedAxis",
    "Wave",
    "WaveConfigError",
    "WaveEnvironment",
    "WaveOverride",
    "WavePlan",
    "WorkItemAxes",
    "check_media",
    "compare_declarations",
    "compose_declaration",
    "conflict_between",
    "conflicts_among",
    "declared_refs",
    "defect_detail",
    "derivation_findings",
    "finding_for",
    "load_overrides",
    "lock_sites",
    "parse_declaration",
    "plan_waves",
    "remedy_for",
    "resolve_scope",
    "resolve_scopes",
    "room_for",
    "title_id_mismatches",
    "title_references",
    "unguarded_axes",
]
