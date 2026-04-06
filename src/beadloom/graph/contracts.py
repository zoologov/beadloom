"""First-class cross-service contract model + protocol-agnostic reconciliation.

F2 (BDL-038) promotes the cross-service contract out of the edge-buried
``extra.contract`` blob (F1) into a first-class object computed at the hub. This
module owns the :class:`Contract` model, the language-neutral
:func:`contract_key` derivation, the :class:`ContractVerdict` enum, and
:func:`reconcile_contracts` (which ``federation.py`` delegates to).

BEAD-01 scope: AMQP only, with **byte-identical** F1 federation output (the
``Contract`` projects back to F1's flat ``{message_type, directions, repos,
confirmed}`` shape via :meth:`Contract.to_report_dict`). Later beads enrich the
key (BEAD-02: AMQP exchange/routing), add GraphQL (BEAD-03), and assign verdicts
(BEAD-04). The :class:`ContractVerdict` values are defined here as a stable
skeleton; the ``classify`` logic that selects among them lands in BEAD-04.
"""

# beadloom:domain=graph

from __future__ import annotations

import enum
from dataclasses import dataclass, field

_AMQP = "amqp"
_GRAPHQL = "graphql"
_WILDCARD = "*"


class ContractVerdict(enum.Enum):
    """Contract-level intent-vs-reality verdict (skeleton; classify in BEAD-04).

    - :attr:`CONFIRMED`           — producers and consumers present, compatible.
    - :attr:`DRIFT`               — declared active, present on only one side.
    - :attr:`ORPHANED_CONSUMER`   — consumes a contract nobody produces.
    - :attr:`UNDECLARED_PRODUCER` — produces a contract nobody consumes.
    - :attr:`BREAKING`            — GraphQL consumer references a surface the
      producer's current SDL no longer exposes.
    - :attr:`EXPECTED`            — lifecycle planned / deprecated-and-gone.
    - :attr:`EXTERNAL`            — target is an external/unmapped node.
    - :attr:`DEAD`                — declared dead.
    """

    CONFIRMED = "confirmed"
    DRIFT = "drift"
    ORPHANED_CONSUMER = "orphaned_consumer"
    UNDECLARED_PRODUCER = "undeclared_producer"
    BREAKING = "breaking"
    EXPECTED = "expected"
    EXTERNAL = "external"
    DEAD = "dead"


@dataclass(frozen=True)
class ContractEndpoint:
    """One side of a contract: which repo/node, and which direction.

    ``direction`` is the raw declared value (``"produces"`` / ``"consumes"``;
    may be empty for a malformed declaration — kept verbatim so the projection
    back to F1's shape is lossless).
    """

    repo: str
    ref_id: str
    direction: str
    source_file: str | None = None


@dataclass
class Contract:
    """A reconciled cross-service contract (first-class, protocol-agnostic).

    Every contract-bearing edge that shares a :attr:`contract_key` contributes
    one :class:`ContractEndpoint`. ``producers`` / ``consumers`` are derived
    views over :attr:`endpoints` so no endpoint is ever lost.
    """

    contract_key: str
    protocol: str
    name: str
    endpoints: list[ContractEndpoint] = field(default_factory=list)
    lifecycle: str = "active"
    verdict: ContractVerdict | None = None

    @property
    def producers(self) -> list[ContractEndpoint]:
        return [e for e in self.endpoints if e.direction == "produces"]

    @property
    def consumers(self) -> list[ContractEndpoint]:
        return [e for e in self.endpoints if e.direction == "consumes"]

    def to_report_dict(self) -> dict[str, object]:
        """Project to F1's flat contract shape (byte-identical back-compat).

        F1 surfaced AMQP contracts as ``{message_type, directions (sorted),
        repos (sorted), confirmed}``. Preserved verbatim so ``_mark_undeclared``
        and the report/JSON rendering are unchanged in BEAD-01.
        """
        directions = sorted({e.direction for e in self.endpoints})
        repos = sorted({e.repo for e in self.endpoints})
        confirmed = "produces" in directions and "consumes" in directions
        return {
            "message_type": self.name,
            "directions": directions,
            "repos": repos,
            "confirmed": confirmed,
        }


def contract_key(payload: dict[str, object]) -> str:
    """Derive a protocol-prefixed, language-neutral contract identity.

    The key resolves on contract *names*, never a code symbol, so a cross-language
    edge (e.g. a TS client vs a backend) reconciles across the boundary.

    - AMQP: ``amqp:<exchange>/<routing_key>:<message_type>``. A missing exchange
      or routing falls back to ``*``, so a v1 export (message_type only) yields
      ``amqp:*/*:<message_type>`` and still reconciles (F1 back-compat). The
      exchange/routing fields are populated by BEAD-02; until then they are
      wildcards.
    - GraphQL: ``graphql:<schema_name>`` (BEAD-03 wires the producer/consumer
      surface; this is the identity hook).
    - Any other protocol: ``<protocol>:<message_type-or-name>`` (stable, namespaced).
    """
    protocol = str(payload.get("protocol", ""))
    if protocol == _GRAPHQL:
        schema = str(payload.get("schema") or payload.get("name") or "")
        return f"{_GRAPHQL}:{schema}"
    if protocol == _AMQP:
        message_type = str(payload.get("message_type", ""))
        exchange = str(payload.get("exchange") or _WILDCARD)
        routing = str(payload.get("routing_key") or _WILDCARD)
        return f"{_AMQP}:{exchange}/{routing}:{message_type}"
    discriminator = payload.get("message_type") or payload.get("name") or ""
    return f"{protocol}:{discriminator}"


def reconcile_contracts(edges: list[dict[str, object]]) -> list[Contract]:
    """Group contract-bearing edges by :func:`contract_key` into Contracts.

    BEAD-01: AMQP only (matching F1); GraphQL grouping arrives in BEAD-03.
    Insertion order is preserved (a key first appears in the order its edges are
    traversed) — this keeps F1's contract ordering byte-identical, since F1
    reconciled over the unsorted edge union. Deterministic key-sorting is a
    deliberate BEAD-04 output change (FEDERATION_SCHEMA_VERSION 1 -> 2).
    """
    by_key: dict[str, Contract] = {}
    for edge in edges:
        payload = _edge_contract(edge)
        if payload is None or payload.get("protocol") != _AMQP:
            continue
        key = contract_key(payload)
        contract = by_key.get(key)
        if contract is None:
            contract = Contract(
                contract_key=key,
                protocol=_AMQP,
                name=str(payload.get("message_type", "")),
            )
            by_key[key] = contract
        contract.endpoints.append(
            ContractEndpoint(
                repo=str(edge.get("repo", "")),
                ref_id=str(edge.get("src", "")),
                direction=str(payload.get("direction", "")),
            )
        )
    return list(by_key.values())


def _edge_contract(edge: dict[str, object]) -> dict[str, object] | None:
    """Return the edge's contract payload dict, or ``None`` for a plain edge."""
    contract = edge.get("contract")
    return contract if isinstance(contract, dict) else None
