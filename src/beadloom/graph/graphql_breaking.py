# beadloom:domain=graph
# beadloom:component=graphql_breaking
"""Native typed GraphQL breaking analysis (BDL-060 S2, G1a).

Pure comparison of a consumer's referenced typed fields against a producer's
exposed typed fields, naming the offending field/arg. The single responsibility:
*given two typed surfaces, which consumer references does the producer break?*

A reference breaks when it is, vs the producer surface:

- **absent** — the producer no longer exposes the field;
- **type-incompatible** — the producer's return type changed so the consumer's
  expected type is no longer satisfied. Types are compared as a STRUCTURED
  wrapping (a named leaf wrapped in zero or more list levels, each level carrying
  its own nullability), so the comparison is rigorous at full depth: a different
  leaf named type, a differing list-nesting depth, a list-vs-scalar mismatch, or a
  nullability *narrowing* at ANY level (producer became nullable where the
  consumer relied on non-null) all break;
- **arg-broken** — the producer requires a non-null arg the consumer does not
  supply, or narrowed an arg the consumer supplies (named type, list depth, or
  per-level nullability) — list-typed args inherit the same structured rigor.

Purely additive producer changes are benign: a new field the consumer doesn't
reference, a new *nullable* arg, or *widening* a return type from nullable to
non-null at any level (more guarantees still satisfy the consumer).

This is NATIVE rigor — Beadloom computes the verdict; it does not delegate to an
external GraphQL registry/tool. The depth is only as strong as the data: the
caller invokes this ONLY when both sides carry a real typed surface, and falls
back to name-presence otherwise (DATA-STRICTNESS).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

# A typed field is ``{"type": "<gql-type-string>", "args": {name: type}}`` — the
# serialized shape of :class:`beadloom.graph.graphql_surface.FieldType`.
TypedField = Mapping[str, object]


def breaking_field_descriptors(
    exposed_fields: Mapping[str, TypedField],
    referenced_fields: Mapping[str, TypedField],
) -> list[str]:
    """Return sorted descriptors of consumer references the producer breaks.

    Each descriptor names the offending field (and, for an arg break, the arg):
    ``"<field>"`` for an absent/retyped field, ``"<field>(<arg>)"`` for an arg
    break. Empty when every reference is satisfied (purely additive producer
    changes are benign). Deterministic (sorted + deduped).
    """
    breaks: set[str] = set()
    for name in referenced_fields:
        consumer = referenced_fields[name]
        producer = exposed_fields.get(name)
        if producer is None:
            breaks.add(name)
            continue
        if _return_type_broken(_type_of(producer), _type_of(consumer)):
            breaks.add(name)
        breaks.update(
            f"{name}({arg})" for arg in _broken_args(producer, consumer)
        )
    return sorted(breaks)


def _return_type_broken(producer_type: str, consumer_type: str) -> bool:
    """True when the producer's return type no longer satisfies the consumer.

    Compares the FULL structured wrapping (see :func:`_satisfies`): same leaf
    named type, same list-nesting depth, and producer at-least-as-non-null at
    EVERY level. Widening nullability anywhere is fine; any narrowing, a
    list-vs-scalar mismatch, or a differing depth breaks.
    """
    producer = _parse_wrapped(producer_type)
    consumer = _parse_wrapped(consumer_type)
    return not _satisfies(producer, consumer)


def _broken_args(producer: TypedField, consumer: TypedField) -> list[str]:
    """Arg names the producer broke for this consumer reference.

    - A producer arg that is **required (non-null) and absent** from the
      consumer's supplied args is a break (the consumer's query won't satisfy it).
    - A producer arg the consumer **does supply** but whose producer type is
      incompatible (different leaf named type, differing list depth, or narrowed
      nullability at any level) is a break — list-typed args go through the SAME
      structured comparison as return types.
    A new **nullable** producer arg the consumer doesn't supply is benign.

    Args are CONTRAVARIANT: the value the consumer supplies must satisfy the
    producer's *input requirement*, so the nullability direction is the inverse of
    a return type (producer narrowing an arg to non-null breaks; widening it to
    nullable is benign). We express this by swapping the roles into the SAME
    structured :func:`_satisfies` — the consumer's supplied wrapping must satisfy
    the producer's required wrapping.
    """
    producer_args = _args_of(producer)
    consumer_args = _args_of(consumer)
    broken: list[str] = []
    for arg, producer_type in producer_args.items():
        if arg not in consumer_args:
            if _parse_wrapped(producer_type).non_null:
                broken.append(arg)
            continue
        consumer_type = consumer_args[arg]
        if not _satisfies(_parse_wrapped(consumer_type), _parse_wrapped(producer_type)):
            broken.append(arg)
    return broken


@dataclass(frozen=True)
class _WrappedType:
    """A GraphQL type as a structured wrapping (one recursive node).

    A ``NAMED`` leaf carries ``name`` and no ``inner``; a ``LIST`` level carries
    an ``inner`` wrapped type and no ``name``. ``non_null`` is THIS level's
    nullability (the ``!`` that immediately suffixes it).
    """

    non_null: bool
    name: str = ""
    inner: _WrappedType | None = None

    @property
    def is_list(self) -> bool:
        return self.inner is not None


def _parse_wrapped(type_str: str) -> _WrappedType:
    """Parse a canonical GraphQL type string into a structured wrapping.

    Grammar (canonical ``str(GraphQLType)`` form): a NAMED leaf, or a ``[...]``
    list level wrapping an inner type, where either may be suffixed ``!`` for
    non-null. An empty/unknown string parses to a nullable unnamed leaf (honest
    "unknown" — never fabricated), so the name-level fallback degrades safely.
    """
    text = type_str.strip()
    non_null = text.endswith("!")
    if non_null:
        text = text[:-1].strip()
    if text.startswith("[") and text.endswith("]"):
        inner = _parse_wrapped(text[1:-1])
        return _WrappedType(non_null=non_null, inner=inner)
    return _WrappedType(non_null=non_null, name=text)


def _satisfies(producer: _WrappedType, consumer: _WrappedType) -> bool:
    """True when the producer wrapping still satisfies the consumer's expectation.

    Structurally identical shape (same list-nesting depth, same leaf named type)
    AND the producer at-least-as-non-null at EVERY level: a consumer that relied
    on ``T!`` is broken by a producer ``T`` (narrowing), but a consumer ``T``
    accepts a producer ``T!`` (widening). A list-vs-scalar mismatch or a differing
    depth is never satisfied.
    """
    if consumer.non_null and not producer.non_null:
        return False
    if producer.is_list != consumer.is_list:
        return False
    if producer.is_list:
        assert producer.inner is not None and consumer.inner is not None
        return _satisfies(producer.inner, consumer.inner)
    return producer.name == consumer.name


def _type_of(field: TypedField) -> str:
    value = field.get("type")
    return value if isinstance(value, str) else ""


def _args_of(field: TypedField) -> dict[str, str]:
    raw = field.get("args")
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(name): str(value)
        for name, value in raw.items()
        if isinstance(value, str)
    }
