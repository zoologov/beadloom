# beadloom:domain=graph
# beadloom:component=graphql_breaking
"""Native typed GraphQL breaking analysis (BDL-060 S2, G1a).

Pure comparison of a consumer's referenced typed fields against a producer's
exposed typed fields, naming the offending field/arg. The single responsibility:
*given two typed surfaces, which consumer references does the producer break?*

A reference breaks when it is, vs the producer surface:

- **absent** — the producer no longer exposes the field;
- **type-incompatible** — the producer's return type changed so the consumer's
  expected type is no longer satisfied (a different named type, or a nullability
  *narrowing* — producer became nullable where the consumer relied on non-null);
- **arg-broken** — the producer requires a non-null arg the consumer does not
  supply, or narrowed an arg the consumer supplies to non-null.

Purely additive producer changes are benign: a new field the consumer doesn't
reference, a new *nullable* arg, or *widening* a return type from nullable to
non-null (more guarantees still satisfy the consumer).

This is NATIVE rigor — Beadloom computes the verdict; it does not delegate to an
external GraphQL registry/tool. The depth is only as strong as the data: the
caller invokes this ONLY when both sides carry a real typed surface, and falls
back to name-presence otherwise (DATA-STRICTNESS).
"""

from __future__ import annotations

from collections.abc import Mapping

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

    Compatible iff the underlying (unwrapped) named type is identical AND the
    producer is at least as non-null as the consumer relied on (widening
    nullable->non-null is fine; narrowing non-null->nullable breaks).
    """
    if _unwrap(producer_type) != _unwrap(consumer_type):
        return True
    # Nullability narrowing: consumer relied on non-null, producer is nullable.
    return _is_non_null(consumer_type) and not _is_non_null(producer_type)


def _broken_args(producer: TypedField, consumer: TypedField) -> list[str]:
    """Arg names the producer broke for this consumer reference.

    - A producer arg that is **required (non-null) and absent** from the
      consumer's supplied args is a break (the consumer's query won't satisfy it).
    - A producer arg the consumer **does supply** but whose producer type is
      incompatible (different named type, or narrowed to non-null where the
      consumer's value is nullable) is a break.
    A new **nullable** producer arg the consumer doesn't supply is benign.
    """
    producer_args = _args_of(producer)
    consumer_args = _args_of(consumer)
    broken: list[str] = []
    for arg, producer_type in producer_args.items():
        if arg not in consumer_args:
            if _is_non_null(producer_type):
                broken.append(arg)
            continue
        consumer_type = consumer_args[arg]
        type_changed = _unwrap(producer_type) != _unwrap(consumer_type)
        narrowed = _is_non_null(producer_type) and not _is_non_null(consumer_type)
        if type_changed or narrowed:
            broken.append(arg)
    return broken


def _unwrap(type_str: str) -> str:
    """Strip ``!`` and ``[]`` wrapping to the underlying named type."""
    return type_str.replace("!", "").replace("[", "").replace("]", "").strip()


def _is_non_null(type_str: str) -> bool:
    """True when the outermost type is non-null (ends in ``!``)."""
    return type_str.strip().endswith("!")


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
