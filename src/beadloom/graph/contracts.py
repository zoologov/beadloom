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
    # GraphQL surface (BEAD-03, G2). ``exposed`` is the producer's declared SDL
    # surface; ``references`` is the union of consumer-referenced names. Both are
    # sorted + deduped. Empty for AMQP (and for GraphQL with no surface) — the
    # presence-based ``BREAKING`` check that consumes them lands in BEAD-04.
    exposed: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

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


_RECONCILED_PROTOCOLS = frozenset({_AMQP, _GRAPHQL})


def reconcile_contracts(edges: list[dict[str, object]]) -> list[Contract]:
    """Group contract-bearing edges by :func:`contract_key` into Contracts.

    BEAD-03: AMQP **and** GraphQL (grouping by the protocol-prefixed key, so a
    ``graphql:<schema>`` producer and consumer resolve across the language
    boundary by name — G3). The producer's ``exposed`` SDL surface and the
    consumers' ``references`` accumulate onto the :class:`Contract` (sorted +
    deduped) for BEAD-04's presence-based ``BREAKING`` check. AMQP behavior is
    byte-identical to BEAD-02 (empty exposed/references).

    Insertion order is preserved (a key first appears in the order its edges are
    traversed) — this keeps F1's contract ordering byte-identical, since F1
    reconciled over the unsorted edge union. Deterministic key-sorting is a
    deliberate BEAD-04 output change (FEDERATION_SCHEMA_VERSION 1 -> 2).
    """
    by_key: dict[str, Contract] = {}
    for edge in edges:
        payload = _edge_contract(edge)
        if payload is None:
            continue
        protocol = str(payload.get("protocol", ""))
        if protocol not in _RECONCILED_PROTOCOLS:
            continue
        key = contract_key(payload)
        contract = by_key.get(key)
        if contract is None:
            contract = Contract(
                contract_key=key,
                protocol=protocol,
                name=_contract_name(protocol, payload),
            )
            by_key[key] = contract
        contract.endpoints.append(
            ContractEndpoint(
                repo=str(edge.get("repo", "")),
                ref_id=str(edge.get("src", "")),
                direction=str(payload.get("direction", "")),
            )
        )
        _accumulate_surface(contract, payload)
    return list(by_key.values())


def _contract_name(protocol: str, payload: dict[str, object]) -> str:
    """Human label for a contract: schema name for GraphQL, message_type for AMQP."""
    if protocol == _GRAPHQL:
        return str(payload.get("schema") or payload.get("name") or "")
    return str(payload.get("message_type", ""))


def _accumulate_surface(contract: Contract, payload: dict[str, object]) -> None:
    """Fold a GraphQL edge's ``exposed`` / ``references`` into the Contract.

    Both are kept sorted + deduped so identical input serializes byte-identically
    (the F2 determinism invariant). AMQP payloads carry neither, so this is a
    no-op for them.
    """
    exposed = _str_list(payload.get("exposed"))
    if exposed:
        contract.exposed = sorted(set(contract.exposed) | set(exposed))
    references = _str_list(payload.get("references"))
    if references:
        contract.references = sorted(set(contract.references) | set(references))


def _str_list(raw: object) -> list[str]:
    """Coerce a payload value into a list of strings (empty for anything else)."""
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def _edge_contract(edge: dict[str, object]) -> dict[str, object] | None:
    """Return the edge's contract payload dict, or ``None`` for a plain edge."""
    contract = edge.get("contract")
    return contract if isinstance(contract, dict) else None
