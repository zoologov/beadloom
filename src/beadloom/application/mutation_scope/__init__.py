# beadloom:domain=application
# beadloom:component=mutation-scope
"""The declared mutation scope, and the score a run over it produced.

Two halves of one question, and they shipped eleven weeks apart.

``scope`` (BDL-061 S4b) answers **could this declared target run a single
mutant** -- a target naming a moved package or an empty directory produces the
strongest possible ratio over an empty denominator, which reads as evidence of
test strength and is evidence of nothing.

``score`` (BDL-068 S3.1) answers **and what did a run over it produce**. Without
it the duty BDL-061 S4 put into every composed role core had no instrument: four
beads in BDL-067 each reported "mutation checking" by a different hand method,
every result prose in a bead comment, and one of them -- sent to audit another
-- found a reported "all 20 assertions red before the fix" was eleven guards
that cannot fail.

**Beadloom still owns no runner.** The tool is the project's choice, because
owning one would break tool-agnosticism and put a Python-only dependency inside
a product whose adopters are not all Python projects. What ships is the declared SCOPE, this
REPORT over whatever counters a run left behind, and a counter vocabulary that
is a set of NAMES rather than a tool. This repository runs ``mutmut`` over
``src/beadloom/graph/rules/`` as its own dev dependency; an adopter running
anything that can write ``killed`` and ``survived`` gets the same report.

This lives in ``application`` rather than beside the rest of the flow
configuration because it joins two sources -- ``flow.yml``'s declaration and
``config.yml``'s scan paths, the second of which is read through the
infrastructure seam that ``onboarding`` may not import. Reading ``flow.yml``
directly here follows the precedent set by ``application.guards.config``, which
owns the ``guards:`` block the same way.
"""

from __future__ import annotations

from beadloom.application.mutation_scope.acceptance import acceptance_files_by_node
from beadloom.application.mutation_scope.change import (
    ChangedFunction,
    ChangePlan,
    MutationChangeError,
    NodeSelection,
    change_payload,
    describe_change,
    diff_since,
    plan_change,
)
from beadloom.application.mutation_scope.sample import (
    SampleInterval,
    describe_sample,
    sample_interval,
    sample_payload,
    wilson_interval,
)
from beadloom.application.mutation_scope.scope import (
    MUTATION_KEY,
    MUTATION_OUTSIDE_SOURCE,
    MUTATION_TARGET_MISSING,
    MUTATION_ZERO_MUTANTS,
    MutationScopeFinding,
    check_mutation_scope,
    lies_within,
    load_mutation_targets,
)
from beadloom.application.mutation_scope.score import (
    MUTATION_COUNTERS_MISSING,
    MUTATION_RUN_ZERO_MUTANTS,
    MUTATION_TARGET_UNMEASURED,
    MutationCounters,
    MutationReport,
    MutationRun,
    describe_room,
    read_run_counters,
    report_mutation_score,
)
from beadloom.application.mutation_scope.survivors import (
    Survivor,
    describe_survivors,
    read_survivors,
    survivors_by_node,
    survivors_payload,
)
from beadloom.application.mutation_scope.touched import (
    TouchedFunctions,
    changed_lines,
    touched_functions,
)

__all__ = [
    "MUTATION_COUNTERS_MISSING",
    "MUTATION_KEY",
    "MUTATION_OUTSIDE_SOURCE",
    "MUTATION_RUN_ZERO_MUTANTS",
    "MUTATION_TARGET_MISSING",
    "MUTATION_TARGET_UNMEASURED",
    "MUTATION_ZERO_MUTANTS",
    "ChangePlan",
    "ChangedFunction",
    "MutationChangeError",
    "MutationCounters",
    "MutationReport",
    "MutationRun",
    "MutationScopeFinding",
    "NodeSelection",
    "SampleInterval",
    "Survivor",
    "TouchedFunctions",
    "acceptance_files_by_node",
    "change_payload",
    "changed_lines",
    "check_mutation_scope",
    "describe_change",
    "describe_room",
    "describe_sample",
    "describe_survivors",
    "diff_since",
    "lies_within",
    "load_mutation_targets",
    "plan_change",
    "read_run_counters",
    "read_survivors",
    "report_mutation_score",
    "sample_interval",
    "sample_payload",
    "survivors_by_node",
    "survivors_payload",
    "touched_functions",
    "wilson_interval",
]
