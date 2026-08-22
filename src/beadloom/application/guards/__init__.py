"""Flow guards — the named-guard primitive the enforced agentic flow binds to.

A guard answers one process question about one situation and returns a verdict a
harness can act on from the exit code alone. Guards are declared in
``.beadloom/flow.yml``, evaluated here, and bound to a tool by an adapter that
contains no logic — so no behaviour exists only inside one harness.

Start at :func:`~beadloom.application.guards.invocation.run_invocation` for a
whole invocation (it decides and then records, and it neither raises nor exits)
or at :func:`~beadloom.application.guards.evaluation.evaluate_guard` for the
decision alone; the verdict shape is
:class:`~beadloom.application.guards.models.GuardVerdict`.
"""

from beadloom.application.guards.checks import BUILTIN_GUARDS, GUARD_NAMES
from beadloom.application.guards.config import GuardConfigError, load_guards_config
from beadloom.application.guards.evaluation import UnknownGuardError, evaluate_guard
from beadloom.application.guards.firing import read_firings, record_firing
from beadloom.application.guards.invocation import (
    GuardInvocation,
    InvocationResult,
    run_invocation,
)
from beadloom.application.guards.liveness import build_liveness
from beadloom.application.guards.models import GuardOutcome, GuardVerdict

__all__ = [
    "BUILTIN_GUARDS",
    "GUARD_NAMES",
    "GuardConfigError",
    "GuardInvocation",
    "GuardOutcome",
    "GuardVerdict",
    "InvocationResult",
    "UnknownGuardError",
    "build_liveness",
    "evaluate_guard",
    "load_guards_config",
    "read_firings",
    "record_firing",
    "run_invocation",
]
