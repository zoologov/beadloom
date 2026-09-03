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

from beadloom.application.mutation_scope.scope import (
    MUTATION_KEY,
    MUTATION_OUTSIDE_SOURCE,
    MUTATION_TARGET_MISSING,
    MUTATION_ZERO_MUTANTS,
    MutationScopeFinding,
    check_mutation_scope,
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

__all__ = [
    "MUTATION_COUNTERS_MISSING",
    "MUTATION_KEY",
    "MUTATION_OUTSIDE_SOURCE",
    "MUTATION_RUN_ZERO_MUTANTS",
    "MUTATION_TARGET_MISSING",
    "MUTATION_TARGET_UNMEASURED",
    "MUTATION_ZERO_MUTANTS",
    "MutationCounters",
    "MutationReport",
    "MutationRun",
    "MutationScopeFinding",
    "check_mutation_scope",
    "describe_room",
    "load_mutation_targets",
    "read_run_counters",
    "report_mutation_score",
]
