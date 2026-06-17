# beadloom:domain=graph
# beadloom:component=contracts
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

from beadloom.graph.graphql_breaking import breaking_field_descriptors

_AMQP = "amqp"
_GRAPHQL = "graphql"
_WILDCARD = "*"
# Marker that introduces a foreign (cross-repo) reference in a namespaced
# federated id (``@<repo>:<ref>``) — mirrors federation._FOREIGN_MARKER.
_FOREIGN_MARKER = "@"

# Lifecycle significance for folding several contract edges into one declared
# intent: a louder (more terminal) declaration on any endpoint wins. ``dead`` >
# ``deprecated`` > ``planned`` > ``active``. ``external`` ranks above all so a
# single external endpoint marks the whole contract external (BEAD-05 wires its
# trigger; ``classify`` already honours it defensively). Unknown values rank 0.
_LIFECYCLE_SIGNIFICANCE: dict[str, int] = {
    "active": 1,
    "planned": 2,
    "deprecated": 3,
    "dead": 4,
    "external": 5,
}


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
    # Typed GraphQL Tier-A surface (BDL-060 S2, G1a). ``exposed_fields`` is the
    # producer's typed operation surface; ``referenced_fields`` is the consumer's.
    # Each maps an operation field name to ``{"type": str, "args": {name: type}}``
    # (the serialized shape of ``graphql_surface.FieldType``). Empty when the
    # ``graphql-core`` extra was absent (honest name-level fallback) or for AMQP —
    # the verdict then degrades to the presence-based ``missing_references`` check.
    exposed_fields: dict[str, dict[str, object]] = field(default_factory=dict)
    referenced_fields: dict[str, dict[str, object]] = field(default_factory=dict)

    @property
    def producers(self) -> list[ContractEndpoint]:
        return [e for e in self.endpoints if e.direction == "produces"]

    @property
    def consumers(self) -> list[ContractEndpoint]:
        return [e for e in self.endpoints if e.direction == "consumes"]

    @property
    def _has_typed_surface(self) -> bool:
        """True when BOTH sides carry a typed GraphQL surface (BDL-060 S2).

        The typed verdict may only reason about field/arg types when both the
        producer and the consumer parsed their SDL (the ``graphql-core`` extra was
        present on both). Absent that depth, the verdict honestly degrades to the
        name-presence check (DATA-STRICTNESS — a verdict only as strong as data).
        """
        return (
            self.protocol == _GRAPHQL
            and bool(self.exposed_fields)
            and bool(self.referenced_fields)
        )

    @property
    def breaking_fields(self) -> list[str]:
        """Typed break descriptors: field/arg refs the producer breaks (S2, G1a).

        When both sides are typed, names every consumer reference that is absent,
        type-narrowed, nullability-broken, or has a broken arg (``"<field>"`` or
        ``"<field>(<arg>)"``). Empty when not typed (use ``missing_references``),
        for AMQP, or when every reference is satisfied (additive changes benign).
        Sorted + deduped.
        """
        if not self._has_typed_surface:
            return []
        return breaking_field_descriptors(self.exposed_fields, self.referenced_fields)

    @property
    def missing_references(self) -> list[str]:
        """Consumer-referenced surface the producer breaks (G5 / S2 G1a).

        The ``BREAKING`` signal: a non-empty result means a consumer relies on a
        field/arg the producer no longer satisfies. When both sides are typed
        (BDL-060 S2) this is the typed analysis (absence + type-narrowing +
        nullability + arg breaks, naming the offending field/arg); otherwise it
        degrades to the name-presence check (BDL-038). Sorted + deduped. Always
        empty for AMQP (no GraphQL surface).
        """
        if self.protocol != _GRAPHQL:
            return []
        if self._has_typed_surface:
            return self.breaking_fields
        if not self.references:
            return []
        return sorted(set(self.references) - set(self.exposed))

    def to_report_dict(self) -> dict[str, object]:
        """Project to a verdict-enriched contract dict (BEAD-04, G5).

        Keeps F1's flat keys verbatim (``message_type``/``directions``/``repos``/
        ``confirmed``) so nothing downstream (``_mark_undeclared``, the report,
        existing tests) breaks, and adds the F2 enrichment: ``verdict``,
        ``protocol``, ``contract_key``, and — for GraphQL — ``exposed`` /
        ``references`` / the ``missing`` names that triggered ``BREAKING``.
        """
        directions = sorted({e.direction for e in self.endpoints})
        repos = sorted({e.repo for e in self.endpoints})
        confirmed = "produces" in directions and "consumes" in directions
        verdict = self.verdict if self.verdict is not None else classify(self)
        report: dict[str, object] = {
            "message_type": self.name,
            "directions": directions,
            "repos": repos,
            "confirmed": confirmed,
            "verdict": verdict.value,
            "protocol": self.protocol,
            "contract_key": self.contract_key,
            "lifecycle": self.lifecycle,
        }
        if self.protocol == _GRAPHQL:
            report["exposed"] = list(self.exposed)
            report["references"] = list(self.references)
            report["missing"] = self.missing_references
        return report


def classify(contract: Contract) -> ContractVerdict:
    """Assign a :class:`ContractVerdict` to a reconciled contract (RFC §5, G5).

    The truth table, in precedence order (lifecycle intent dominates the
    presence/shape check — a ``dead`` contract is ``DEAD`` even if its shape is
    broken):

    1. lifecycle ``external`` -> ``EXTERNAL`` (defensive; trigger wired in BEAD-05).
    2. lifecycle ``dead``     -> ``DEAD``.
    3. lifecycle ``planned``  -> ``EXPECTED`` (intentional, not built yet).
    4. lifecycle ``deprecated`` -> ``EXPECTED`` (intentional retirement).
    5. GraphQL with producers ∧ consumers and ``references ⊄ exposed`` -> ``BREAKING``.
    6. producers ∧ consumers (compatible) -> ``CONFIRMED``.
    7. consumers, no producers -> ``ORPHANED_CONSUMER``.
    8. producers, no consumers -> ``UNDECLARED_PRODUCER``.
    9. otherwise (no endpoints) -> ``UNDECLARED_PRODUCER`` (degenerate, never live).
    """
    if contract.lifecycle == "external":
        return ContractVerdict.EXTERNAL
    if contract.lifecycle == "dead":
        return ContractVerdict.DEAD
    if contract.lifecycle in ("planned", "deprecated"):
        return ContractVerdict.EXPECTED
    has_producers = bool(contract.producers)
    has_consumers = bool(contract.consumers)
    if has_producers and has_consumers:
        if contract.protocol == _GRAPHQL and contract.missing_references:
            return ContractVerdict.BREAKING
        return ContractVerdict.CONFIRMED
    if has_consumers:
        return ContractVerdict.ORPHANED_CONSUMER
    return ContractVerdict.UNDECLARED_PRODUCER


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
    """Group contract-bearing edges into Contracts, scoped by landscape (U5).

    BEAD-03: AMQP **and** GraphQL (grouping by the protocol-prefixed key, so a
    ``graphql:<schema>`` producer and consumer resolve across the language
    boundary by name — G3). The producer's ``exposed`` SDL surface and the
    consumers' ``references`` accumulate onto the :class:`Contract` (sorted +
    deduped) for BEAD-04's presence-based ``BREAKING`` check.

    BEAD-06 (U5, nested landscapes): the group key is ``(landscape,
    contract_key)``. **Implicit** same-key matching is scoped *within* a
    landscape — two unrelated products that share a coincidental message_type /
    schema name reconcile in separate groups and never auto-confirm or
    auto-DRIFT. An edge that declares an **explicit** cross-repo target
    (``@otherrepo:<ref>`` — its ``dst`` repo differs from its own ``repo``)
    promotes its ``contract_key`` to *cross-landscape*: every edge sharing that
    key collapses into one landscape-agnostic group, so a genuine declared
    cross-product contract resolves with a both-sides verdict regardless of
    landscape. Edges with no declared landscape (``None``) share one default
    group, keeping the F1 single-product path byte-identical.

    Insertion order is preserved (a key first appears in the order its edges are
    traversed) — this keeps F1's contract ordering byte-identical, since F1
    reconciled over the unsorted edge union. Deterministic key-sorting is a
    deliberate BEAD-04 output change (FEDERATION_SCHEMA_VERSION 1 -> 2).
    """
    cross_landscape_keys = _cross_landscape_keys(edges)
    by_group: dict[tuple[str | None, str], Contract] = {}
    for edge in edges:
        payload = _edge_contract(edge)
        if payload is None:
            continue
        protocol = str(payload.get("protocol", ""))
        if protocol not in _RECONCILED_PROTOCOLS:
            continue
        key = contract_key(payload)
        group = _group_key(edge, key, cross_landscape_keys)
        contract = by_group.get(group)
        if contract is None:
            contract = Contract(
                contract_key=key,
                protocol=protocol,
                name=_contract_name(protocol, payload),
            )
            by_group[group] = contract
        contract.endpoints.append(
            ContractEndpoint(
                repo=str(edge.get("repo", "")),
                ref_id=str(edge.get("src", "")),
                direction=str(payload.get("direction", "")),
            )
        )
        _accumulate_surface(contract, payload)
        contract.lifecycle = _more_significant(
            contract.lifecycle, str(edge.get("lifecycle", "active"))
        )
    contracts = list(by_group.values())
    for contract in contracts:
        contract.verdict = classify(contract)
    return contracts


def edge_group_key(
    edge: dict[str, object], cross_landscape_keys: set[str]
) -> tuple[str | None, str] | None:
    """Reconciliation group of a contract-bearing edge (BEAD-06, U5), or ``None``.

    ``None`` when the edge carries no reconciled contract. Mirrors
    :func:`reconcile_contracts` grouping so callers (e.g. the hub's UNDECLARED
    sweep) can scope by landscape consistently. Pass the shared
    :func:`cross_landscape_keys` so an explicit cross-product key collapses to a
    landscape-agnostic group.
    """
    payload = _edge_contract(edge)
    if payload is None:
        return None
    if str(payload.get("protocol", "")) not in _RECONCILED_PROTOCOLS:
        return None
    return _group_key(edge, contract_key(payload), cross_landscape_keys)


def cross_landscape_keys(edges: list[dict[str, object]]) -> set[str]:
    """Public alias for the set of explicitly-declared cross-product keys (U5)."""
    return _cross_landscape_keys(edges)


def _cross_landscape_keys(edges: list[dict[str, object]]) -> set[str]:
    """Contract keys that an explicit cross-repo edge declares (U5).

    A contract whose key is declared by *any* explicit ``@otherrepo:`` edge is a
    genuine cross-product contract and must reconcile across landscapes — so its
    key is excluded from landscape scoping (one shared group for the key).
    """
    keys: set[str] = set()
    for edge in edges:
        payload = _edge_contract(edge)
        if payload is None:
            continue
        if str(payload.get("protocol", "")) not in _RECONCILED_PROTOCOLS:
            continue
        if _is_explicit_cross_repo(edge):
            keys.add(contract_key(payload))
    return keys


def _is_explicit_cross_repo(edge: dict[str, object]) -> bool:
    """True when the edge's resolved ``dst`` names a repo other than its own.

    The edge ``dst`` is the hub-namespaced ``@<repo>:<ref>`` form: a foreign dst
    whose repo differs from the edge's own ``repo`` is an *explicitly declared*
    cross-repo contract (the consumer wrote ``@otherrepo:ref``). A local dst (no
    ``@``) or a same-repo namespaced dst is implicit.
    """
    dst = str(edge.get("dst", ""))
    if not dst.startswith(_FOREIGN_MARKER):
        return False
    dst_repo = dst[len(_FOREIGN_MARKER) :].partition(":")[0]
    return bool(dst_repo) and dst_repo != str(edge.get("repo", ""))


def _group_key(
    edge: dict[str, object], key: str, cross_landscape_keys: set[str]
) -> tuple[str | None, str]:
    """Reconciliation group: ``(None, key)`` for cross-product keys, else
    ``(landscape, key)`` so implicit same-key matching is landscape-scoped."""
    if key in cross_landscape_keys:
        return (None, key)
    landscape = edge.get("landscape")
    scoped = landscape if isinstance(landscape, str) and landscape else None
    return (scoped, key)


def _more_significant(current: str, candidate: str) -> str:
    """Return the louder (more terminal) of two lifecycle declarations.

    Folds several contract-edge lifecycles into one declared intent for the
    Contract: ``external`` > ``dead`` > ``deprecated`` > ``planned`` > ``active``
    (see :data:`_LIFECYCLE_SIGNIFICANCE`). Unknown values rank below ``active``
    so a typo never silently masks a real declaration.
    """
    if _LIFECYCLE_SIGNIFICANCE.get(candidate, 0) > _LIFECYCLE_SIGNIFICANCE.get(
        current, 0
    ):
        return candidate
    return current


def _contract_name(protocol: str, payload: dict[str, object]) -> str:
    """Human label for a contract: schema name for GraphQL, message_type for AMQP."""
    if protocol == _GRAPHQL:
        return str(payload.get("schema") or payload.get("name") or "")
    return str(payload.get("message_type", ""))


def _accumulate_surface(contract: Contract, payload: dict[str, object]) -> None:
    """Fold a GraphQL edge's surface (name-level + typed) into the Contract.

    Name-level ``exposed`` / ``references`` are kept sorted + deduped (the F2
    determinism invariant). The typed ``fields`` block (BDL-060 S2), when present,
    is folded into ``exposed_fields`` (producer edges) / ``referenced_fields``
    (consumer edges) keyed by operation field name. AMQP payloads carry none of
    these, so this is a no-op for them.
    """
    exposed = _str_list(payload.get("exposed"))
    if exposed:
        contract.exposed = sorted(set(contract.exposed) | set(exposed))
    references = _str_list(payload.get("references"))
    if references:
        contract.references = sorted(set(contract.references) | set(references))
    typed = _typed_fields(payload.get("fields"))
    if typed:
        direction = str(payload.get("direction", ""))
        target = (
            contract.exposed_fields
            if direction == "produces"
            else contract.referenced_fields
        )
        target.update(typed)


def _typed_fields(raw: object) -> dict[str, dict[str, object]]:
    """Coerce a serialized typed-``fields`` block into ``{name: {type,args}}``.

    Tolerant of older/foreign payloads (a list of ``{name,type,args}`` entries):
    a malformed entry is dropped (honest), never fabricated. Empty for anything
    that isn't the expected list-of-dicts shape.
    """
    if not isinstance(raw, list):
        return {}
    fields: dict[str, dict[str, object]] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        args = {
            str(a.get("name")): str(a.get("type", ""))
            for a in entry.get("args", [])
            if isinstance(a, dict) and isinstance(a.get("name"), str) and a.get("name")
        }
        field_type = entry.get("type")
        fields[name] = {
            "type": field_type if isinstance(field_type, str) else "",
            "args": args,
        }
    return fields


def _str_list(raw: object) -> list[str]:
    """Coerce a payload value into a list of strings (empty for anything else)."""
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def _edge_contract(edge: dict[str, object]) -> dict[str, object] | None:
    """Return the edge's contract payload dict, or ``None`` for a plain edge."""
    contract = edge.get("contract")
    return contract if isinstance(contract, dict) else None
