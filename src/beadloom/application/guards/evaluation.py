# beadloom:domain=application
# beadloom:feature=flow-guards
"""Evaluating one guard: check outcome + strictness + exclusions -> verdict (BDL-061 S1).

This is the single decision point every caller shares — the CLI, the harness
hook adapter, and (from S2) the Gate. Keeping it here rather than in the CLI is
what makes "the hook and the CLI produce identical verdicts" true by
construction instead of by discipline.

Order of resolution, and why:

1. **Unknown name** -> :class:`UnknownGuardError`. A typo must not read as "no
   findings".
2. **Strictness ``off``** -> ``skip`` naming the work kind. Turning a guard off
   is legitimate; hiding that it is off is not.
3. **A malformed edit path** -> ``error``, which blocks. It is decided *after*
   ``off`` (an opt-out is a human decision recorded in flow.yml, and a guard that
   is off never looks at the path) and *before* exclusions (matching a pattern
   against a string the guard has refused to interpret is the bypass this order
   removes).
4. **Path exclusion** -> ``skip`` quoting the declared reason and ``until``, so
   the record shows who exempted this path and when the exemption expires.
5. **The check itself** -> ``pass``, or the configured ``warn``/``block``. A
   check that cannot apply returns its own skip reason, which is passed through
   verbatim.

The function performs no writes: recording the firing is the caller's step
(:mod:`beadloom.application.guards.firing`), which keeps the decision path
read-only and therefore trustworthy about what it inspected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.config import GuardConfigError, load_guards_config
from beadloom.application.guards.contract import GuardProbes, GuardRequest
from beadloom.application.guards.models import GuardOutcome, GuardVerdict
from beadloom.application.guards.paths import (
    MALFORMED_REMEDIATION,
    MALFORMED_WHY,
    PathScope,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from beadloom.application.guards.config import GuardsConfig
    from beadloom.application.guards.contract import Guard, GuardFinding

#: Strictness -> the outcome a violation produces under it.
_VIOLATION_OUTCOME: Mapping[str, GuardOutcome] = {
    "warn": GuardOutcome.WARN,
    "block": GuardOutcome.BLOCK,
}


class UnknownGuardError(GuardConfigError):
    """A guard name that is not registered — named, never silently ignored."""


def _not_covered(
    finding: GuardFinding, guard: Guard, request: GuardRequest
) -> tuple[str, ...]:
    """What the evaluation did not check, never empty.

    A warning with nothing in this field is one the reader cannot act on, so the
    guard's own scope is stated when the check offered nothing more specific.

    The path caveat is added here rather than in each check because it is a
    property of the *evaluation* — the evaluator is what decided not to apply
    any exclusion to a target outside the project root — and a check has no way
    to know that decision was made.
    """
    items = list(finding.not_covered) or [
        f"anything beyond this guard's single condition: {guard.summary}"
    ]
    note = request.resolved_path.not_covered_note
    if note:
        items.append(note)
    return tuple(items)


def evaluate_guard(
    name: str,
    *,
    project_root: Path,
    context: Mapping[str, str] | None = None,
    probes: GuardProbes | None = None,
    config: GuardsConfig | None = None,
) -> GuardVerdict:
    """Evaluate the guard *name* for *context* and return its verdict.

    Raises :class:`UnknownGuardError` for an unregistered name and
    :class:`~beadloom.application.guards.config.GuardConfigError` for a
    malformed ``guards:`` block.
    """
    guard = BUILTIN_GUARDS.get(name)
    if guard is None:
        msg = (
            f"unknown guard {name!r} — registered guards: {sorted(BUILTIN_GUARDS)}"
        )
        raise UnknownGuardError(msg)

    guards = config if config is not None else load_guards_config(project_root)
    spec = guards.spec_for(name)
    request = GuardRequest(
        project_root=project_root,
        context=dict(context or {}),
        probes=probes if probes is not None else GuardProbes(),
        options=spec.options,
    )
    scope = (guard.summary,)

    strictness = spec.strictness_for(request.work_kind)
    if strictness == "off":
        kind = request.work_kind or "the default work kind"
        return GuardVerdict(
            guard=name,
            outcome=GuardOutcome.SKIP,
            why=f"strictness is 'off' for {kind} in flow.yml",
            not_covered=scope,
            context=request.context,
        )

    resolved = request.resolved_path
    if resolved.scope is PathScope.MALFORMED:
        return GuardVerdict(
            guard=name,
            outcome=GuardOutcome.ERROR,
            why=MALFORMED_WHY.format(rejection=resolved.rejection),
            not_covered=(resolved.not_covered_note,),
            remediation=MALFORMED_REMEDIATION,
            context=request.context,
        )

    exclusion = spec.exclusion_for(resolved.relative)
    if exclusion is not None:
        return GuardVerdict(
            guard=name,
            outcome=GuardOutcome.SKIP,
            why=exclusion.describe(),
            not_covered=scope,
            context=request.context,
        )

    finding = guard.check(request)
    not_covered = _not_covered(finding, guard, request)
    if finding.skipped_because is not None:
        return GuardVerdict(
            guard=name,
            outcome=GuardOutcome.SKIP,
            why=finding.skipped_because,
            not_covered=not_covered,
            context=request.context,
        )
    if finding.satisfied:
        return GuardVerdict(
            guard=name,
            outcome=GuardOutcome.PASS,
            why=finding.why,
            not_covered=not_covered,
            context=request.context,
        )
    return GuardVerdict(
        guard=name,
        outcome=_VIOLATION_OUTCOME[strictness],
        why=finding.why,
        not_covered=not_covered,
        remediation=finding.remediation,
        context=request.context,
    )
