# beadloom:domain=graph
# beadloom:feature=federation
"""Landscape gate: turn federated verdicts into block/pass findings (BDL-039 F3).

:func:`gate_failures` scans a reconciled
:class:`~beadloom.graph.federation.reconcile.FederatedGraph` for the verdicts in a
fail-set (the SAFE-DEFAULT being the actionable real-break verdicts) and returns
deterministic :class:`GateFailure` findings;
:func:`gate_failure_remediation` derives an agent-actionable "how to fix" hint.
``NEVER_FAIL_VERDICTS`` are the intentional/honest states a gate must never arm on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beadloom.graph.federation.reconcile import FederatedGraph

# The SAFE-DEFAULT fail-set for ``federate --fail-on`` (bare flag or ``default``
# token). These are the actionable, real-break verdicts: a cross-service
# ``DRIFT`` (edge or contract), a GraphQL ``BREAKING`` change, a consumer with no
# producer (``ORPHANED_CONSUMER``), and a producer nobody consumes
# (``UNDECLARED_PRODUCER``). The edge-level ``undeclared`` (the AMQP equivalent
# of ``undeclared_producer``) is included too — the same emitting-into-the-void
# signal carried on the edge.
SAFE_DEFAULT_FAIL_ON: frozenset[str] = frozenset(
    {
        "breaking",
        "drift",
        "orphaned_consumer",
        "undeclared_producer",
        "undeclared",
    }
)

# Verdicts a gate must NEVER fail on (principle 3 — a noisy gate gets disabled).
# ``external`` / ``expected`` / ``dead`` / ``unmapped`` are intentional or
# honest-unknown states; ``confirmed`` / ``ok`` are healthy; ``cleanup_candidate``
# is a warning, not a block. Passing one of these to ``--fail-on`` is rejected
# (see :func:`parse_fail_on`), so it can never silently arm a false gate.
NEVER_FAIL_VERDICTS: frozenset[str] = frozenset(
    {
        "external",
        "expected",
        "dead",
        "unmapped",
        "confirmed",
        "ok",
        "cleanup_candidate",
    }
)


@dataclass(frozen=True)
class GateFailure:
    """One verdict that armed the landscape gate (BDL-039 F3 BEAD-01).

    - ``kind``      — ``"edge"`` or ``"contract"`` (which side of the union).
    - ``identity``  — ``src --> dst`` for an edge, the ``contract_key`` for a
      contract (the human-actionable locator).
    - ``verdict``   — the lowercased verdict value that matched the fail-set.
    - ``missing``   — for a ``breaking`` contract, the consumer-referenced names
      absent from the producer's SDL (sorted; empty otherwise).
    """

    kind: str
    identity: str
    verdict: str
    missing: tuple[str, ...] = ()


def gate_failures(fed: FederatedGraph, fail_on: set[str]) -> list[GateFailure]:
    """Collect every edge/contract verdict in *fail_on* (pure, deterministic).

    Scans each edge's :class:`EdgeVerdict` and each contract's
    :class:`~beadloom.graph.contracts.ContractVerdict` (both already computed by
    :func:`aggregate_exports`); a finding is produced whenever the verdict —
    matched case-insensitively against its enum value — is in *fail_on*. The
    output is sorted by ``(kind, identity, verdict)`` so the gate is reproducible
    regardless of edge/contract ordering. An empty result means the landscape is
    clean for the requested fail-set (exit 0).
    """
    wanted = {v.strip().lower() for v in fail_on if v.strip()}
    failures: list[GateFailure] = []
    for edge in fed.edges:
        verdict = str(edge.get("verdict", "")).lower()
        if verdict and verdict in wanted:
            identity = f"{edge.get('src', '')} --> {edge.get('dst', '')}"
            failures.append(GateFailure("edge", identity, verdict))
    for contract in fed.contracts:
        verdict = str(contract.get("verdict", "")).lower()
        if verdict and verdict in wanted:
            failures.append(_contract_failure(contract, verdict))
    failures.sort(key=lambda f: (f.kind, f.identity, f.verdict))
    return failures


def _contract_failure(contract: dict[str, object], verdict: str) -> GateFailure:
    """Build a contract :class:`GateFailure`, carrying BREAKING missing names."""
    identity = str(
        contract.get("contract_key") or contract.get("message_type") or ""
    )
    raw_missing = contract.get("missing")
    missing = (
        tuple(sorted(str(m) for m in raw_missing))
        if isinstance(raw_missing, list)
        else ()
    )
    return GateFailure("contract", identity, verdict, missing)


def gate_failure_remediation(failure: GateFailure) -> str | None:
    """Derive an agent-actionable "how to fix" hint for a gate failure (G2).

    Mirrors :func:`~beadloom.graph.rule_engine._remediation_for` for the
    cross-service landscape gate: each contract/edge verdict that armed the
    gate gets a templated hint naming the concrete contract/edge so an agent
    (or human) can act without re-deriving the break. Returns ``None`` for
    verdicts that carry no specific remediation.
    """
    verdict = failure.verdict.lower()
    identity = failure.identity or "<contract>"
    if verdict == "breaking":
        names = ", ".join(failure.missing) if failure.missing else "the referenced surface"
        return (
            f"consumer references `{names}` absent from the producer SDL of "
            f"`{identity}`; align the client or restore the field"
        )
    if verdict == "orphaned_consumer":
        return f"no producer for `{identity}`; add a producer or drop the consumer"
    if verdict in {"undeclared_producer", "undeclared"}:
        return f"no consumer for `{identity}`; add a consumer or stop producing it"
    if verdict == "drift":
        return (
            f"`{identity}` is declared active but present on only one side; "
            f"add the missing side or mark it deprecated/planned"
        )
    return None
