# beadloom:domain=application
# beadloom:feature=ci-gate
"""What an unusable opt-in declaration costs a gate leg, in one place for both legs.

Two legs of ``beadloom ci`` are opt-in — ``issue-log`` reads ``issue_log:`` and
``readme-pair`` reads ``document_pairs:`` — and both face the same three
questions once :mod:`beadloom.doc_sync.declarations` has read the key: what does
a leg print when a declaration could not be used, what does it print when the
config itself could not be read, and what does one refusal look like as a
finding. One answer, here, because the two legs answering it separately is the
defect that produced BDL-UX #270 and its twin (``beadloom-rqma.7``).

**What tells "declared none" from "declared badly" is a count, not an adverb.**
A skip reworded to "possibly nothing was declared" would be the same defect in
softer words, so the number of entries declared and the number unusable are in
the line.

Nothing here reads a config or decides which leg runs. It renders what the
declaration reader refused, and the leg composes it (BDL-069,
``beadloom-rqma.8``, the first slice of ``beadloom-oew7``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.gate_step import Finding, GateStep

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beadloom.doc_sync.declarations import Refusal

#: How many refusals a verdict names before it stops listing. The counts in
#: front of the list are over ALL of them, as with the pairs a leg names.
NAMED_REFUSALS = 3


def unusable_phrase(entries_declared: int, refusals: Sequence[Refusal]) -> str:
    """``; N entr(ies) declared, M unusable: <where> (<why>)`` — or nothing.

    The two numbers are the whole point of this clause. "Declared none" and
    "declared badly" were one sentence in both opt-in legs until
    ``beadloom-rqma.7``, and a skip reworded to "possibly nothing was declared"
    would have been the same defect in softer words: what tells the two apart is
    a count, not an adverb.
    """
    if not refusals:
        return ""
    named = ", ".join(
        f"{refusal.where} ({refusal.why})" for refusal in refusals[:NAMED_REFUSALS]
    )
    line = (
        f"; {entries_declared} entr(ies) declared, {len(refusals)} unusable: {named}"
    )
    remaining = len(refusals) - NAMED_REFUSALS
    if remaining > 0:
        line += f", and {remaining} more not named here"
    return line


def unusable_declaration_step(
    name: str, entries_declared: int, refusals: Sequence[Refusal]
) -> GateStep:
    """A leg whose whole declaration could not be used: nothing ran, and it says so.

    It BLOCKS, for the reason a declaration pointing at a missing file already
    blocked: the project opted in, the leg it asked for did not run, and a green
    tree that silently skipped a check somebody switched on is the defect class
    this epic exists for. A project that opted OUT never reaches here.
    """
    return GateStep(
        name,
        passed=False,
        findings=[refusal_finding(name, refusal) for refusal in refusals],
        summary="0 leg(s) run" + unusable_phrase(entries_declared, refusals),
    )


def undetermined_declaration_step(
    name: str, subject: str, refusals: Sequence[Refusal]
) -> GateStep:
    """The config itself could not be read, so whether the project opted in is unknown.

    Neither of the other two answers is honest here. Reporting absence tells an
    adopter they opted out; reporting a broken declaration reddens a project
    that may never have written the key. So it skips, and it WARNs: the leg
    could not read the population it reports on.
    """
    return GateStep(
        name,
        skipped=True,
        not_verified=True,
        summary=(
            "skipped — "
            + "; ".join(refusal.why for refusal in refusals)
            + f", so whether this project declares {subject} is unknown"
        ),
    )


def refusal_finding(name: str, refusal: Refusal) -> Finding:
    """One unusable declaration, located at the config file that holds it."""
    return {
        "kind": name,
        "rule": "unusable-declaration",
        "severity": "error",
        "locations": [{"file": ".beadloom/config.yml"}],
        "why": f"{refusal.where}: {refusal.why}",
        "remediation": refusal.remediation,
    }
