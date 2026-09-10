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
* a ``warn``, an ``error`` or an ``unresolved`` always names what it did not
  check — a warning nobody can act on trains the reader to ignore warnings, and
  an ``unresolved`` that does not say so is a permitted edit reported as a
  shrug.

``error`` and ``unresolved`` both mean "the guard did not answer", and the
difference between them is **what the guard could not answer about**. Both exist
because "I could not tell" was previously spelled as a traceback, which the
process reported as exit 1 — the *warn* code, which a harness reads as
non-blocking (BDL-061.27, F2). Both are verdicts rather than exceptions so that
they are recorded like every other firing: an evaluation missing from
``guard-firings.jsonl`` is invisible to ``--liveness``, the one report whose whole
product is honesty about dead gates.

* ``error`` — the guard ran and refuses to interpret the **edit** it was handed:
  a target whose shape it will not resolve, a harness payload it cannot decode.
  That is a real answer about this edit, the next edit is unaffected, and a
  different target clears it, so it stops the edit at :data:`EXIT_CODE_BLOCK`.
* ``unresolved`` — the guard could not evaluate **itself**: its own code would
  not import, its configuration would not parse, the evaluation crashed or was
  interrupted. It has no answer about anything, and the repair for it is almost
  always a file write — which is what the guard is refusing (BDL-UX #254).
  Measured live in BDL-068 S5: a package half-moved by ``git mv`` made
  ``services/guard_probes.py:79`` unimportable, every bound tool returned the
  same ``ImportError`` at the blocking code, and the remediation read "fix the
  reported error, then re-run" — asking for the write it had just disabled. Only
  ``Read`` was outside the surface, and a read repairs nothing. So an unresolved
  guard **warns and permits, saying that it checked nothing**: a gate that blocks
  on its own inability is not strict, it is unavailable.

The fix is deliberately NOT a narrower surface. ``Bash`` belongs on the matcher
(BDL-UX #170, closed by ``beadloom-0mdo.31``) and removing it would restore the
shell escape by reopening a real coverage hole. The defect is the verdict on
inability, never the coverage.

Exit codes are part of the contract so a shell adapter needs no parsing:
``0`` for pass/skip, ``1`` for warn (visible, non-blocking), ``2`` for block.
``error`` also exits ``2``: the shipped Claude Code adapter blocks on 2 and on
nothing else, so an outcome that must stop work has exactly one code available.

``unresolved`` is the one outcome whose code depends on the **caller**, and
:func:`unresolved_exit_code` holds both halves. A shell or CI caller gets ``3``,
deliberately NOT ``2`` — Click's own ``UsageError`` exits 2 and would otherwise
be indistinguishable from a genuine block. A caller bound to a harness gets
``1``, which that harness shows and carries past, because the alternative was
measured: the blocking code there made every repair for the class impossible
from inside the session (BDL-UX #254).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


class GuardOutcome(str, Enum):
    """The six outcomes a guard evaluation can produce."""

    PASS = "pass"  # noqa: S105 — an outcome name, not a credential
    WARN = "warn"
    BLOCK = "block"
    SKIP = "skip"
    ERROR = "error"
    UNRESOLVED = "unresolved"


#: The code that stops work. Named once because two things must agree on it: the
#: ``block`` outcome and the ``error`` outcome.
EXIT_CODE_BLOCK = 2

#: The code that is seen and carried past. The shipped adapter blocks on
#: :data:`EXIT_CODE_BLOCK` and on nothing else, so this is the code an
#: ``unresolved`` verdict reports to a harness: visible, and not a block.
EXIT_CODE_WARN = 1

#: Outcome -> process exit code. See the module docstring for why 3 is reserved.
#: ``unresolved`` maps to the warn code because that is what a harness must
#: receive; a shell caller gets :data:`EXIT_CODE_UNRESOLVED` instead, which is
#: the one place the code depends on the caller (see :func:`unresolved_exit_code`).
EXIT_CODE_BY_OUTCOME: Mapping[GuardOutcome, int] = {
    GuardOutcome.PASS: 0,
    GuardOutcome.SKIP: 0,
    GuardOutcome.WARN: EXIT_CODE_WARN,
    GuardOutcome.BLOCK: EXIT_CODE_BLOCK,
    GuardOutcome.ERROR: EXIT_CODE_BLOCK,
    GuardOutcome.UNRESOLVED: EXIT_CODE_WARN,
}

#: Exit code an ``unresolved`` verdict reports to a **shell or CI** caller.
#: Reserved by BDL-061.2 for a usage or configuration defect and widened by
#: BDL-UX #254 to every inability a guard has about itself, which is the class
#: that name always described: neither is about any particular edit, both fail
#: identically until a human changes a file, and Click's own usage error exits 2.
EXIT_CODE_UNRESOLVED = 3

#: What an ``unresolved`` verdict says happened to the edit, in the words a
#: reader needs to see beside "the guard could not answer". It lives here rather
#: than in the CLI renderer so that a second harness prints the same sentence.
PERMITTED_UNGUARDED = (
    "this edit was NOT checked and was allowed through — a guard that cannot "
    "evaluate itself does not block the write that would repair it"
)


#: The recorded outcomes that are not answers. Both mean "no verdict was
#: reached"; they differ only in what the guard could not reach one about.
_UNANSWERED_OUTCOMES = frozenset(
    {GuardOutcome.ERROR.value, GuardOutcome.UNRESOLVED.value}
)


def is_unanswered(outcome: str) -> bool:
    """True when a recorded outcome is evidence the guard ran and did not answer.

    One predicate rather than two comparisons, because two places must agree on
    it — :mod:`beadloom.application.guards.firing` folds it into the carried
    summary and :mod:`beadloom.application.guards.liveness` decides
    ``never-fired`` with it — and an outcome added to one of them and not the
    other makes a guard that has never reached a verdict read as a live gate.

    *outcome* is the recorded **string**, not the enum: a firing file written by
    an older version can carry a value this build does not know, and an unknown
    value is treated as an answer for the same reason ``--liveness`` errs quiet
    on evidence rather than loud on a guess.
    """
    return outcome in _UNANSWERED_OUTCOMES


def unresolved_exit_code(harness: str | None) -> int:
    """The code an ``unresolved`` verdict exits with (BDL-061.33, BDL-UX #254).

    ``3`` was the whole answer until BDL-061.33, and it was fail-open where it
    mattered most: ``3`` blocks nothing in the harness the emitted adapter binds
    to, so a ``.beadloom/flow.yml`` that would not parse — the single file of
    this feature an adopter edits by hand — switched every bound guard off while
    each invocation announced that it could not answer. That entry sent the class
    to the blocking code under a harness, and BDL-UX #254 measured what the
    blocking code costs. Both are answered by asking *who is calling*:

    * **A shell or CI caller** (*harness* is ``None``) gets ``3``. A defect in the
      project's declared configuration is not a failure about any particular
      edit, it fails identically until a human edits a file, and Click's own
      usage error already exits ``2`` — collapsing the two would make a broken
      ``flow.yml`` indistinguishable from a genuine block.
    * **An invocation bound to a harness** (``--hook`` names one) gets
      :data:`EXIT_CODE_WARN`, because there the only question the exit code
      answers is "does this edit proceed?" — and BDL-UX #254 measured what
      answering "no" costs. The blocking code was right about the danger and
      wrong about the remedy: every inability in this class is repaired by a
      file write, the guard is bound to every tool that writes one, so blocking
      made the tree unrepairable by anything inside the session. The edit
      proceeds and the verdict says, on the stream and in the firing record,
      that nothing was checked.

    **This is not the fail-open BDL-061.33 closed, and the difference is what
    the reader is told.** ``3`` was fail-open because it was silent about being
    open: it reported "I could not answer" in a vocabulary the harness had no
    entry for, and an adopter saw a green session. ``unresolved`` is a named
    outcome with its own line, its own firing record and its own liveness
    consequence — it does not clear ``never-fired``, so a guard that keeps
    failing to run keeps reading as a dead gate in the one report whose product
    is honesty about dead gates.

    The decision lives here rather than in the emitted shell script for the
    reason the whole epic rests on: an adapter that maps codes contains logic,
    logic in an adapter exists only inside one tool, and every future harness
    would have to re-derive it — which is the same fail-open, one harness later.
    The adapter already declares its harness; that declaration is enough.

    *harness* is the name the caller passed, not a member of a supported set: a
    harness Beadloom cannot translate is a wiring defect in the binding itself,
    and Beadloom has no way to learn the exit vocabulary of a tool it does not
    support, so it uses the one code it knows is seen and not blocking. There is
    deliberately no per-harness table today. Every harness Beadloom supports
    blocks on ``2`` and carries on past ``1``, and a one-entry table with a
    default reads as a capability that exists — the shape standing rule 8 names.
    The day a harness disagrees, its non-blocking code becomes an entry beside
    its payload translator.
    """
    return EXIT_CODE_UNRESOLVED if harness is None else EXIT_CODE_WARN


def exception_detail(exc: BaseException) -> str:
    """An exception as one readable clause that names its class.

    Shared rather than written twice, because two layers phrase the same fact
    and a reader compares them: the boundary reports "the guard could not be
    evaluated: <detail>" and the path resolver reports "it could not be
    resolved (<detail>)". The class belongs in the clause —
    ``RuntimeError: Symlink loop from '/p/a'`` and
    ``OSError: [Errno 40] Too many levels of symbolic links`` are the same
    condition reported by the interpreter and by the filesystem, and which one
    spoke is what tells the reader where to look. The empty-message case is
    handled because ``str(SomeError())`` is ``""``, which would otherwise print
    a bare colon with nothing after it.
    """
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


@dataclass(frozen=True)
class GuardVerdict:
    """One guard's answer about one situation.

    Attributes
    ----------
    guard:
        Registered guard name (``bead-claimed``).
    outcome:
        One of :class:`GuardOutcome`. ``error`` and ``unresolved`` both mean the
        guard did not answer — never that the guarded condition was met.
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
        if (
            self.outcome
            in (GuardOutcome.WARN, GuardOutcome.ERROR, GuardOutcome.UNRESOLVED)
            and not self.not_covered
        ):
            msg = (
                f"guard {self.guard!r}: a {self.outcome.value} must name what it "
                "did not check (not_covered is empty)"
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
