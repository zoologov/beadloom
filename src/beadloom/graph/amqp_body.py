# beadloom:domain=graph
# beadloom:component=amqp_body
"""Strict AMQP message-body JSON-Schema model + native body-diff (S3, G1b).

The name-level AMQP contract (F1/BDL-038) only knew a ``message_type`` flowed
between a producer and a consumer. This module deepens it with an optional
``body`` — a minimal JSON-Schema describing the message payload (``type``,
``properties``, ``required``, ``enum``, nested objects and array ``items``) — and
the NATIVE diff that decides whether a producer body breaks a consumer that reads
it. It is the AMQP sibling of :mod:`beadloom.graph.graphql_breaking`: a pure,
structured comparison that names the offending field path; Beadloom computes the
verdict itself (no external schema tool).

The single responsibility: *given a producer body schema and a consumer body
schema, which consumer-read fields does the producer break?* A consumer field
breaks when, vs the producer body:

- **absent** — the producer no longer declares the property;
- **type-incompatible** — the producer property's ``type`` (or its structural
  shape: object vs array vs scalar) no longer matches what the consumer reads;
- **required-by-consumer-but-now-optional/removed** — the consumer requires the
  field but the producer no longer requires it (or dropped it entirely);
- **enum-narrowed** — the producer dropped an enum value the consumer relies on.

Nested objects (``properties``) and array ``items`` recurse with the SAME rigor,
the path named ``parent.child`` / ``field[]`` / ``field[].child``. Additive
producer fields, a producer that *widens* requiredness (now requires a field the
consumer treated as optional), and an *enum-widened* producer are benign.

DATA-STRICTNESS: the model is the minimal honest JSON-Schema body — never a
fabricated field or type. Determinism: :func:`serialize_body` emits a
sorted/byte-stable payload (properties sorted by name, ``required`` sorted,
recursively) for the federation wire; :func:`parse_body` reads it back.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

_TYPE = "type"
_PROPERTIES = "properties"
_REQUIRED = "required"
_ENUM = "enum"
_ITEMS = "items"
_ARRAY = "array"
_OBJECT = "object"


@dataclass(frozen=True)
class BodySchema:
    """A JSON-Schema body node as a structured, recursive value.

    One node carries its JSON-Schema ``type`` string (``""`` = honest unknown,
    never fabricated), its ``properties`` (name → child :class:`BodySchema`), the
    sorted/deduped set of ``required`` property names, the sorted/deduped ``enum``
    values (as canonical strings), and, for an ``array`` node, its ``items``
    schema. The shape mirrors the minimal JSON-Schema subset we ingest.
    """

    type: str = ""
    properties: dict[str, BodySchema] = field(default_factory=dict)
    required: frozenset[str] = frozenset()
    enum: frozenset[str] = frozenset()
    items: BodySchema | None = None

    def to_payload(self) -> dict[str, object]:
        """Serialize this node to a deterministic JSON-Schema dict (sorted)."""
        payload: dict[str, object] = {
            _TYPE: self.type,
            _PROPERTIES: {
                name: self.properties[name].to_payload()
                for name in sorted(self.properties)
            },
            _REQUIRED: sorted(self.required),
        }
        if self.enum:
            payload[_ENUM] = sorted(self.enum)
        if self.items is not None:
            payload[_ITEMS] = self.items.to_payload()
        return payload


def parse_body(payload: object) -> BodySchema:
    """Parse a JSON-Schema body payload into a :class:`BodySchema`.

    Tolerant of a missing/foreign payload (older AMQP exports carry no ``body``):
    a non-mapping yields an empty unknown node so an older reader degrades
    honestly. Never raises; never fabricates a property or type.
    """
    if not isinstance(payload, Mapping):
        return BodySchema()
    raw_type = payload.get(_TYPE)
    type_str = raw_type if isinstance(raw_type, str) else ""
    properties: dict[str, BodySchema] = {}
    raw_props = payload.get(_PROPERTIES)
    if isinstance(raw_props, Mapping):
        for name, child in raw_props.items():
            if isinstance(name, str) and name:
                properties[name] = parse_body(child)
    required = _str_set(payload.get(_REQUIRED))
    enum = _str_set(payload.get(_ENUM))
    raw_items = payload.get(_ITEMS)
    items = parse_body(raw_items) if isinstance(raw_items, Mapping) else None
    return BodySchema(
        type=type_str,
        properties=properties,
        required=required,
        enum=enum,
        items=items,
    )


def serialize_body(payload: object) -> dict[str, object]:
    """Serialize a JSON-Schema body to a deterministic, sorted dict.

    Accepts either a raw payload dict or a :class:`BodySchema`; routes both through
    :meth:`BodySchema.to_payload` so an equivalent body declared in a different
    property/required order serializes byte-identically (the federation
    determinism invariant).
    """
    if isinstance(payload, BodySchema):
        return payload.to_payload()
    return parse_body(payload).to_payload()


def breaking_body_descriptors(
    producer_body: object,
    consumer_body: object,
) -> list[str]:
    """Sorted field paths the producer body breaks for the consumer that reads it.

    Compares the consumer's read body against the producer's declared body: each
    descriptor names the offending path (``field``, ``parent.child``, ``field[]``
    for an array-item break, ``field[].child`` for a nested array-item field).
    Empty when every consumer-read field is satisfied (additive producer changes
    and widened requiredness are benign). Deterministic (sorted + deduped).
    """
    producer = parse_body(producer_body)
    consumer = parse_body(consumer_body)
    return sorted(set(_diff(producer, consumer, prefix="")))


def _diff(producer: BodySchema, consumer: BodySchema, *, prefix: str) -> list[str]:
    """Recurse the consumer schema against the producer, collecting break paths.

    At each property the consumer reads, the producer must declare a structurally
    compatible property; required-by-consumer fields must stay required; enums
    must not narrow; nested objects / array items recurse.
    """
    breaks: list[str] = []
    for name, consumer_child in consumer.properties.items():
        path = f"{prefix}{name}"
        producer_child = producer.properties.get(name)
        if producer_child is None:
            breaks.append(path)
            continue
        if name in consumer.required and name not in producer.required:
            # Consumer relies on the field's presence; producer no longer guarantees it.
            breaks.append(path)
            continue
        breaks.extend(_diff_node(producer_child, consumer_child, path=path))
    return breaks


def _diff_node(
    producer: BodySchema, consumer: BodySchema, *, path: str
) -> list[str]:
    """Compare one producer property against the consumer's at a given path.

    A scalar/structural type mismatch or an enum narrowing breaks at ``path``
    itself; an object recurses into its properties (``path.child``); an array
    recurses into its ``items`` (``path[]`` / ``path[].child``).
    """
    if not _types_compatible(producer, consumer):
        return [path]
    if _enum_narrowed(producer, consumer):
        return [path]
    if consumer.type == _OBJECT or consumer.properties:
        return _diff(producer, consumer, prefix=f"{path}.")
    if consumer.type == _ARRAY and consumer.items is not None:
        producer_items = producer.items or BodySchema()
        return _diff_items(producer_items, consumer.items, path=path)
    return []


def _diff_items(
    producer_items: BodySchema, consumer_items: BodySchema, *, path: str
) -> list[str]:
    """Compare array ``items`` schemas, naming breaks ``path[]`` / ``path[].child``."""
    if not _types_compatible(producer_items, consumer_items):
        return [f"{path}[]"]
    if _enum_narrowed(producer_items, consumer_items):
        return [f"{path}[]"]
    if consumer_items.type == _OBJECT or consumer_items.properties:
        return _diff(producer_items, consumer_items, prefix=f"{path}[].")
    return []


def _types_compatible(producer: BodySchema, consumer: BodySchema) -> bool:
    """True when the producer node's structural type still satisfies the consumer.

    An unknown (``""``) type on either side is treated as compatible (honest
    degradation — we never claim a break we cannot prove). Otherwise the JSON-
    Schema ``type`` strings must match: a scalar↔array, object↔scalar, or
    differently-named scalar mismatch breaks.
    """
    if not producer.type or not consumer.type:
        return True
    return producer.type == consumer.type


def _enum_narrowed(producer: BodySchema, consumer: BodySchema) -> bool:
    """True when the producer dropped an enum value the consumer relies on.

    The consumer's read enum values must all remain producible: the producer enum
    must be a SUPERSET of the consumer enum. A producer that widened its enum (or
    declares no enum at all — any value) is benign.
    """
    if not consumer.enum or not producer.enum:
        return False
    return not consumer.enum <= producer.enum


def _str_set(raw: object) -> frozenset[str]:
    """Coerce a JSON list value into a frozenset of strings (empty otherwise)."""
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        return frozenset()
    return frozenset(str(item) for item in raw)
