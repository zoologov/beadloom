# beadloom:domain=application
# beadloom:feature=flow-guards
"""One invocation of a guard, from raw arguments to a verdict and a record (BDL-061.29).

Three fix cycles each closed a different place where an invocation ended with no
verdict and no firing record — a traversal spelling, a NUL, a crashing
evaluation, then argument parsing, an undecodable stdin, and a project root taken
from the working directory. Each was closed where it was found, which is why the
next entry path was a fresh place to forget the rule: the invariant was honoured
*case by case*, and a case-by-case invariant is one defect away from being false.

This module is that invariant made structural. Every invocation — however it
arrives, however it fails — comes back through :func:`run_invocation`, which
returns an :class:`InvocationResult` and never raises and never exits. A failure
anywhere inside, including in argument parsing and in the stdin read (i.e.
before a guard name is even known), becomes a recorded verdict of "I could not
tell". New failure modes will still appear; the requirement this module exists to
meet is that they appear in ``guard --liveness`` instead of in a traceback.

Two functions, and the split is the whole design:

* :func:`_answer` decides — it may fail in any way at all;
* :func:`_record` writes — it is the **only** place a firing is recorded, and it
  either records or names why it did not.

``run_invocation`` is ``_record(_answer(...))`` and has exactly one return, so a
new exit path that skips the record cannot be added without changing that line.

**Recording is one predicate, stated once**: a firing is written when a project
was located, a *registered* guard was named, and the invocation was an
evaluation rather than a report. Each of the three exceptions has a reason it
cannot be otherwise, and each is reported on the result rather than inferred
from an absent line:

* **no project** — there is nowhere to write it. Manufacturing a root was the
  measured failure (a stray ``.beadloom/`` inside the source tree that the real
  project's ``--liveness`` never reads), so the guard writes nothing and answers
  ``error``, which blocks.
* **an unregistered name** — there is no guard to attribute the row to, and an
  invented row is a lie in the one report whose product is honesty.
* **``--liveness``** — a report evaluates nothing; recording one would inflate
  the very count it prints.

**The handler of last resort is ``BaseException``, and that has a price.**
``SystemExit`` was caught from the first version because a lower layer that
terminates the process without a verdict is the shape of every hole this module
closed; ``KeyboardInterrupt`` is the other ``BaseException`` a running guard
actually meets, and catching only the first left it escaping to Click, which
turns it into exit ``1`` — the *warn* code the shipped adapter carries on past —
with no verdict and no record (BDL-061.30, finding A). The price of closing it,
stated because it is not free: an interrupt is now a recorded ``error`` at exit
``2``, so Ctrl-C during a guarded edit BLOCKS that edit rather than waving it
through. That is the right side to fail on. SIGINT is delivered to the whole
foreground process group, so the harness's own tool call is interrupted along
with the guard and there is usually no edit left to block; and where there is,
"the guard did not answer" must never be readable as "the guard passed" — which
is the one sentence this whole slice exists to keep true. The two named clauses
above it exist only to give a reader a cause they can act on; the wide one
exists so that the class nobody thought of is a verdict rather than an escape.

**Exit codes.** The code follows the verdict (``pass``/``skip`` 0, ``warn`` 1,
``block``/``error`` 2). ``3`` is overridden onto two classes and no others: a
defect in the project's own declared configuration (a ``guards:`` block that
will not parse, an exclusion with no reason, a guard name nobody registered) and
a command line the CLI could not use at all (no guard named, ``--liveness`` with
a name, a malformed ``--context`` pair, an unsupported ``--hook`` harness). Both
are stable defects a human fixes once, they are not about any particular edit,
and BDL-061.2 reserved ``3`` so that a broken ``flow.yml`` is never mistaken for
a guard that fired. Everything that goes wrong while trying to answer about
*this* edit — a payload that cannot be decoded or parsed, a project that cannot
be located, an exception anywhere — is an ``error`` verdict at exit ``2``,
because that is the one code the shipped adapter blocks on, and the harness
supplied the input that failed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.config import GuardConfigError
from beadloom.application.guards.contract import GuardProbes
from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.firing import record_firing
from beadloom.application.guards.hook_payload import (
    HookPayloadError,
    UnknownHarnessError,
    context_from_hook_payload,
)
from beadloom.application.guards.liveness import build_liveness
from beadloom.application.guards.models import (
    EXIT_CODE_CONFIG_ERROR,
    GuardOutcome,
    GuardVerdict,
)
from beadloom.application.guards.project_root import (
    ProjectLocation,
    locate_project_root,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from beadloom.application.guards.liveness import GuardLiveness

#: Stands in for the guard name when the invocation never named one.
UNNAMED_GUARD = "(no guard named)"

#: What an unanswered invocation did not check — one shape, filled per cause.
UNANSWERED_NOT_COVERED = "{scope}: {because}"

#: The scope an unanswered invocation left unchecked: one guard's, or every guard's.
SCOPE_ONE_GUARD = "everything guard {name!r} checks"
SCOPE_EVERY_GUARD = "everything every guard checks"

_BECAUSE_INCOMPLETE = "the evaluation did not complete"
_BECAUSE_NO_REPORT = "the liveness report could not be built"
_BECAUSE_NO_PROJECT = "the project could not be located, so nothing was evaluated"
_BECAUSE_NO_NAME = "no guard was named, so nothing was evaluated"
_BECAUSE_UNREADABLE_PAYLOAD = (
    "the harness payload could not be read, so no edit target was known"
)

#: Why a firing was not written. Reported, never left to be inferred.
NOT_RECORDED_LIVENESS = (
    "--liveness reports on evaluations; it performs none, so there is nothing to record"
)
NOT_RECORDED_NO_PROJECT = (
    "no project was located, and a guard does not create one to write into"
)
NOT_RECORDED_UNREGISTERED = (
    "{name!r} is not a registered guard, so there is nothing to record it against"
)
NOT_RECORDED_WRITE_FAILED = "the firing record could not be written ({detail})"

_NO_NAME_WHY = "no guard was named, and --liveness was not requested"
_NO_NAME_REMEDIATION = (
    "name a guard to evaluate (`beadloom guard <name>`), or pass --liveness"
)
_LIVENESS_WITH_NAME_WHY = (
    "--liveness reports every guard, so it cannot be given one to report on"
)
_LIVENESS_WITH_NAME_REMEDIATION = "drop the guard name, or drop --liveness"
_USAGE_REMEDIATION = (
    "fix the reported problem — in the command line or in .beadloom/flow.yml — "
    "then re-run the guard"
)
_CONTEXT_WHY = "--context expects KEY=VALUE, got {pair!r}"
_CONTEXT_REMEDIATION = (
    "pass each context item as KEY=VALUE (path=..., tool=..., work_kind=...)"
)
_PAYLOAD_WHY = "the {harness} hook payload could not be read as text: {detail}"
_PAYLOAD_REMEDIATION = (
    "the harness sent bytes this process cannot decode; re-run the guard with "
    "--context path=... to evaluate the edit directly"
)
_EXITED_WHY = "the evaluation terminated the process instead of answering (exit {code})"
_INTERRUPTED_WHY = (
    "the evaluation was interrupted before it could answer, so this edit is "
    "not covered by the guard"
)
_CRASHED_WHY = "the guard could not be evaluated: {detail}"
_CRASHED_REMEDIATION = (
    "fix the reported error, then re-run `beadloom guard {name}`; the edit is "
    "blocked until the guard can answer"
)
_NO_PROJECT_REMEDIATION = (
    "run the guard from inside the project (any directory under the one holding "
    ".beadloom/), or name the root with --project <dir>"
)


class GuardUsageError(ValueError):
    """A command line the CLI could not use — reported as a verdict, never a crash."""


def _no_payload() -> str:
    """The stdin a caller that passed no ``--hook`` supplies: none."""
    return ""


def _no_probes(_project_root: Path) -> GuardProbes:
    """Probes for a caller that wired none: every port reports "unavailable"."""
    return GuardProbes()


@dataclass(frozen=True)
class GuardInvocation:
    """What the caller asked for, before any of it has been validated.

    ``read_payload`` and ``probes_for`` are callables rather than values because
    both can fail, and both must fail *inside* the boundary: reading stdin was
    the last step still happening outside it (BDL-061.28, F7).
    """

    name: str | None = None
    declared_project: Path | None = None
    context_pairs: tuple[str, ...] = ()
    harness: str | None = None
    liveness: bool = False
    read_payload: Callable[[], str] = _no_payload
    probes_for: Callable[[Path], GuardProbes] = _no_probes
    start_dir: Path | None = None


@dataclass(frozen=True)
class InvocationResult:
    """What one invocation produced: something to print, a code, and the record.

    ``verdict`` is ``None`` only for a liveness report that succeeded — every
    other way out, including every failure, carries one.
    """

    exit_code: int
    verdict: GuardVerdict | None = None
    liveness: tuple[GuardLiveness, ...] = ()
    project_root: Path | None = None
    recorded_at: Path | None = None
    not_recorded_because: str = ""

    @property
    def recorded(self) -> bool:
        """True when this invocation left a firing record."""
        return self.recorded_at is not None


def run_invocation(invocation: GuardInvocation) -> InvocationResult:
    """Carry out *invocation* and come back with a verdict and, where due, a record.

    The only entry point, and the only place the two halves meet: it decides,
    then it records. It does not raise and it does not exit — the caller renders
    the result and exits once.
    """
    return _record(_answer(invocation))


def _answer(invocation: GuardInvocation) -> InvocationResult:
    """Decide what this invocation's verdict is, whatever goes wrong doing so.

    Locating the project happens *inside* the try, not before it: a step that
    runs before the handler is exactly the shape of every hole this boundary
    exists to close. ``location`` starts as "no project", so a failure to locate
    one still reaches the handler with something coherent to answer with.
    """
    location = ProjectLocation()
    try:
        location = locate_project_root(
            declared=invocation.declared_project, start=invocation.start_dir
        )
        return _decide(invocation, location)
    except SystemExit as exc:
        return _unanswerable(
            invocation, location, _EXITED_WHY.format(code=exc.code)
        )
    except KeyboardInterrupt:
        return _unanswerable(invocation, location, _INTERRUPTED_WHY)
    except BaseException as exc:  # the last resort; see the module docstring
        return _unanswerable(
            invocation, location, _CRASHED_WHY.format(detail=_detail(exc))
        )


def _record(result: InvocationResult) -> InvocationResult:
    """Write the firing, or state why this invocation could not leave one."""
    if result.verdict is None:
        return replace(result, not_recorded_because=NOT_RECORDED_LIVENESS)
    if result.project_root is None:
        return replace(result, not_recorded_because=NOT_RECORDED_NO_PROJECT)
    if result.verdict.guard not in BUILTIN_GUARDS:
        return replace(
            result,
            not_recorded_because=NOT_RECORDED_UNREGISTERED.format(
                name=result.verdict.guard
            ),
        )
    try:
        written = record_firing(result.project_root, result.verdict)
    except BaseException as exc:  # see the comment below
        # Writing the record is the last thing that can fail, and a failure to
        # record must not become a failure to answer: the verdict still reaches
        # the reader, carrying the reason the record is missing. The handler is
        # as wide as ``_answer``'s for the same reason it is wide there — an
        # interrupt landing on the write is a missing record either way, and the
        # difference is whether the reader is told (BDL-061.31, .30's asymmetry).
        return replace(
            result,
            not_recorded_because=NOT_RECORDED_WRITE_FAILED.format(
                detail=_detail(exc)
            ),
        )
    return replace(result, recorded_at=written)


def _decide(invocation: GuardInvocation, location: ProjectLocation) -> InvocationResult:
    """The evaluation itself — free to fail, because :func:`_answer` catches it."""
    root = location.root
    if root is None:
        return _failed(
            invocation.name,
            why=location.refusal,
            because=_BECAUSE_NO_PROJECT,
            remediation=_NO_PROJECT_REMEDIATION,
        )
    if invocation.liveness:
        return _report(invocation, root)
    if invocation.name is None:
        return _usage(
            None,
            root,
            why=_NO_NAME_WHY,
            because=_BECAUSE_NO_NAME,
            remediation=_NO_NAME_REMEDIATION,
        )
    return _evaluate(invocation, invocation.name, root)


def _report(invocation: GuardInvocation, root: Path) -> InvocationResult:
    """The liveness report: rows, or the configuration error that stopped them."""
    if invocation.name is not None:
        return _usage(
            invocation.name,
            root,
            why=_LIVENESS_WITH_NAME_WHY,
            because=_BECAUSE_INCOMPLETE,
            remediation=_LIVENESS_WITH_NAME_REMEDIATION,
        )
    try:
        rows = build_liveness(root)
    except GuardConfigError as exc:
        return _usage(
            None,
            root,
            why=str(exc),
            because=_BECAUSE_NO_REPORT,
            remediation=_USAGE_REMEDIATION,
        )
    return InvocationResult(exit_code=0, liveness=rows, project_root=root)


def _evaluate(
    invocation: GuardInvocation, name: str, root: Path
) -> InvocationResult:
    """Assemble the context and ask the evaluator, mapping each failure to a verdict."""
    try:
        context = _context(invocation)
    except GuardUsageError as exc:
        return _usage(
            name,
            root,
            why=str(exc),
            because=_BECAUSE_INCOMPLETE,
            remediation=_CONTEXT_REMEDIATION,
        )
    except UnknownHarnessError as exc:
        return _usage(
            name,
            root,
            why=str(exc),
            because=_BECAUSE_INCOMPLETE,
            remediation=_USAGE_REMEDIATION,
        )
    except HookPayloadError as exc:
        return _failed(
            name,
            root=root,
            why=str(exc),
            because=_BECAUSE_UNREADABLE_PAYLOAD,
            remediation=_PAYLOAD_REMEDIATION,
        )
    try:
        verdict = evaluate_guard(
            name,
            project_root=root,
            context=context,
            probes=invocation.probes_for(root),
        )
    except GuardConfigError as exc:
        return _usage(
            name,
            root,
            why=str(exc),
            because=_BECAUSE_INCOMPLETE,
            remediation=_USAGE_REMEDIATION,
        )
    return InvocationResult(
        exit_code=verdict.exit_code, verdict=verdict, project_root=root
    )


def _context(invocation: GuardInvocation) -> dict[str, str]:
    """The evaluation context: the hook payload first, explicit ``--context`` on top."""
    context = _parse_context(invocation.context_pairs)
    if invocation.harness is None:
        return context
    try:
        raw = invocation.read_payload()
    except (OSError, UnicodeDecodeError) as exc:
        msg = _PAYLOAD_WHY.format(harness=invocation.harness, detail=exc)
        raise HookPayloadError(msg) from exc
    return {**context_from_hook_payload(invocation.harness, raw), **context}


def _parse_context(pairs: tuple[str, ...]) -> dict[str, str]:
    """Parse repeated ``--context k=v`` flags into a mapping."""
    context: dict[str, str] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key.strip():
            raise GuardUsageError(_CONTEXT_WHY.format(pair=pair))
        context[key.strip()] = value
    return context


def _unanswerable(
    invocation: GuardInvocation, location: ProjectLocation, why: str
) -> InvocationResult:
    """The verdict for a failure nobody enumerated — recorded like any other."""
    name = _named(invocation.name)
    return _failed(
        invocation.name,
        root=location.root,
        why=why,
        because=_BECAUSE_INCOMPLETE,
        remediation=_CRASHED_REMEDIATION.format(name=name),
    )


def _failed(
    name: str | None,
    *,
    why: str,
    because: str,
    remediation: str,
    root: Path | None = None,
) -> InvocationResult:
    """An ``error`` verdict: the guard could not answer, so the edit stops."""
    verdict = _error_verdict(name, why=why, because=because, remediation=remediation)
    return InvocationResult(
        exit_code=verdict.exit_code, verdict=verdict, project_root=root
    )


def _usage(
    name: str | None,
    root: Path | None,
    *,
    why: str,
    because: str,
    remediation: str,
) -> InvocationResult:
    """A configuration or command-line defect: an ``error`` verdict on exit 3."""
    verdict = _error_verdict(name, why=why, because=because, remediation=remediation)
    return InvocationResult(
        exit_code=EXIT_CODE_CONFIG_ERROR, verdict=verdict, project_root=root
    )


def _named(name: str | None) -> str:
    """How a guard name reads back — including when the caller typed an empty one.

    ``name or UNNAMED_GUARD`` folded ``""`` into ``None``, so ``beadloom guard ""``
    reported "(no guard named)" as the guard it would not record, quoting a name
    the caller never typed while its own ``why`` said ``unknown guard ''``
    (BDL-061.30, section 4).
    """
    return UNNAMED_GUARD if name is None else name


def _detail(exc: BaseException) -> str:
    """An exception as one readable clause, with no empty tail when it carries none."""
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _error_verdict(
    name: str | None,
    *,
    why: str,
    because: str,
    remediation: str,
    context: Mapping[str, str] | None = None,
) -> GuardVerdict:
    """The one verdict shape every failure takes, so none of them is silent."""
    scope = (
        SCOPE_EVERY_GUARD if name is None else SCOPE_ONE_GUARD.format(name=name)
    )
    return GuardVerdict(
        guard=_named(name),
        outcome=GuardOutcome.ERROR,
        why=why,
        not_covered=(UNANSWERED_NOT_COVERED.format(scope=scope, because=because),),
        remediation=remediation,
        context=dict(context or {}),
    )
