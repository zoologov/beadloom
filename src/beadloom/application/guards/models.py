# beadloom:domain=application
# beadloom:feature=flow-guards
"""The guard verdict — the one shape every harness and every caller reads (BDL-061 S1).

A guard answers a *process* question ("is this edit covered by a claimed bead?")
and returns a :class:`GuardVerdict`. The verdict is the whole contract: an
adapter needs the exit code, an agent needs ``why`` + ``remediation``, and a
reviewer needs ``not_covered`` — the honest statement of what the guard did
**not** look at.

Two invariants are enforced at construction, because both are ways a gate goes
quietly dead:

* a ``skip`` always carries a reason — a guard that silently does not apply is
  indistinguishable from one that passed;
* a ``warn`` always names what it did not check — a warning nobody can act on
  trains the reader to ignore warnings.

Exit codes are part of the contract so a shell adapter needs no parsing:
``0`` for pass/skip, ``1`` for warn (visible, non-blocking), ``2`` for block.
``3`` is reserved by the CLI for a usage/configuration error, deliberately NOT
``2`` — Click's own ``UsageError`` exits 2 and would otherwise be
indistinguishable from a genuine block.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


class GuardOutcome(str, Enum):
    """The four outcomes a guard evaluation can produce."""

    PASS = "pass"  # noqa: S105 — an outcome name, not a credential
    WARN = "warn"
    BLOCK = "block"
    SKIP = "skip"


#: Outcome -> process exit code. See the module docstring for why 3 is reserved.
EXIT_CODE_BY_OUTCOME: Mapping[GuardOutcome, int] = {
    GuardOutcome.PASS: 0,
    GuardOutcome.SKIP: 0,
    GuardOutcome.WARN: 1,
    GuardOutcome.BLOCK: 2,
}

#: Exit code for a usage or configuration error (never a guard outcome).
EXIT_CODE_CONFIG_ERROR = 3


@dataclass(frozen=True)
class GuardVerdict:
    """One guard's answer about one situation.

    Attributes
    ----------
    guard:
        Registered guard name (``bead-claimed``).
    outcome:
        One of :class:`GuardOutcome`.
    why:
        One sentence stating what was observed — never a restatement of the
        outcome.
    not_covered:
        What this evaluation did NOT verify. Mandatory for ``warn``.
    remediation:
        The command or action that resolves a ``warn``/``block``.
    context:
        The evaluation context (path, tool, work kind) echoed back, so a
        recorded verdict can be re-read without the invocation.
    """

    guard: str
    outcome: GuardOutcome
    why: str
    not_covered: tuple[str, ...] = ()
    remediation: str = ""
    context: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome is GuardOutcome.SKIP and not self.why.strip():
            msg = f"guard {self.guard!r}: a skip must carry a reason"
            raise ValueError(msg)
        if not self.why.strip():
            msg = f"guard {self.guard!r}: a verdict must state why (outcome={self.outcome.value})"
            raise ValueError(msg)
        if self.outcome is GuardOutcome.WARN and not self.not_covered:
            msg = (
                f"guard {self.guard!r}: a warn must name what it did not check "
                "(not_covered is empty)"
            )
            raise ValueError(msg)

    @property
    def exit_code(self) -> int:
        """Process exit code carrying this outcome."""
        return EXIT_CODE_BY_OUTCOME[self.outcome]

    def to_dict(self) -> dict[str, object]:
        """JSON-ready mapping — the ``--json`` payload and the firing record."""
        return {
            "guard": self.guard,
            "outcome": self.outcome.value,
            "why": self.why,
            "not_covered": list(self.not_covered),
            "remediation": self.remediation,
            "context": dict(self.context),
        }
