# beadloom:domain=graph
# beadloom:component=graphql_surface
"""Typed GraphQL Tier-A surface extraction (BDL-060 S2, G1a).

Deepens the name-level surface of :mod:`beadloom.graph.sdl` into a TYPED surface
over the Query / Mutation / Subscription operations: each operation field carries
its return ``type`` (with ``!`` nullability + ``[]`` list wrapping preserved) and
its ``args`` (``{name: type}``). This is the substrate the native breaking
verdict (:mod:`beadloom.graph.contracts`) reasons over — a consumer-referenced
field/arg that is absent, type-narrowed, or nullability-broken vs the producer is
``BREAKING``; a purely additive producer change is benign.

Parsing uses the OPTIONAL ``graphql-core`` extra (``beadloom[graphql]``). When the
extra is absent — or the SDL is malformed/empty — extraction **degrades
honestly** to the name-level surface (operation field NAMES with empty type/args,
``typed=False``); it never raises and never fabricates a field or type. A verdict
is therefore only ever as strong as the data behind it (the Beadloom DATA-
STRICTNESS invariant): typed depth gives a typed verdict; the name-level fallback
gives the presence-based verdict (identical to BDL-038).

Subscriptions are FIRST-CLASS: a subscription operation field is extracted with
the same depth as a query/mutation field, so a dropped or retyped subscription is
caught.

Determinism: :func:`serialize_typed_surface` emits a sorted/deduped, byte-stable
dict (fields sorted by name, args sorted by name) for the federation export wire;
:func:`parse_typed_surface` reads it back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from beadloom.graph.sdl import operation_field_names

# The three GraphQL root operations, in canonical (deterministic) order.
_OPERATION_ATTRS = ("query_type", "mutation_type", "subscription_type")


@dataclass(frozen=True)
class FieldType:
    """One operation field's typed shape: return ``type`` + ordered ``args``.

    ``type`` is the canonical GraphQL type string with nullability (``!``) and
    list (``[...]``) wrapping preserved (e.g. ``[Plan!]!``); empty string in the
    name-level fallback (honest "unknown", never fabricated). ``args`` maps each
    argument name to its (likewise canonical) type string.
    """

    type: str = ""
    args: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TypedSurface:
    """A producer's typed GraphQL operation surface (one nameable responsibility).

    ``fields`` maps each operation field name (across Query/Mutation/Subscription)
    to its :class:`FieldType`. ``typed`` records whether the depth is real
    (``graphql-core`` parsed the SDL) or a name-level fallback — the verdict layer
    uses this to decide whether it may reason about types/args at all.
    """

    fields: dict[str, FieldType] = field(default_factory=dict)
    typed: bool = False


class _SerializedArg(TypedDict):
    name: str
    type: str


class _SerializedField(TypedDict):
    name: str
    type: str
    args: list[_SerializedArg]


class SerializedSurface(TypedDict):
    """The deterministic wire shape of a typed surface (federation export)."""

    typed: bool
    fields: list[_SerializedField]


def extract_typed_surface(sdl_text: str) -> TypedSurface:
    """Extract the typed operation surface from GraphQL SDL text.

    Uses ``graphql-core`` when installed; degrades honestly to the name-level
    surface (operation field names with empty type/args, ``typed=False``) when the
    extra is absent or the SDL cannot be parsed. Never raises; never fabricates.
    """
    parsed = _parse_with_graphql_core(sdl_text)
    if parsed is not None:
        return parsed
    return _name_level_fallback(sdl_text)


def _parse_with_graphql_core(sdl_text: str) -> TypedSurface | None:
    """Typed extraction via ``graphql-core``; ``None`` if unavailable/unparseable.

    Returns ``None`` (so the caller falls back to name-level) when the extra is
    absent OR the SDL is malformed/empty — both are honest degradation, never a
    hard fail.
    """
    if not sdl_text.strip():
        return None
    try:
        from graphql import build_schema
        from graphql.error import GraphQLError
    except ImportError:
        return None
    try:
        # ``assume_valid`` skips full validation (we only read the type surface),
        # so a schema missing a root Query type still parses.
        schema = build_schema(sdl_text, assume_valid=True)
    except GraphQLError:
        return None
    fields: dict[str, FieldType] = {}
    for attr in _OPERATION_ATTRS:
        operation = getattr(schema, attr, None)
        if operation is None:
            continue
        for field_name, definition in operation.fields.items():
            fields[field_name] = FieldType(
                type=str(definition.type),
                args={
                    arg_name: str(arg.type)
                    for arg_name, arg in definition.args.items()
                },
            )
    return TypedSurface(fields=fields, typed=True)


def _name_level_fallback(sdl_text: str) -> TypedSurface:
    """Name-level fallback: operation field names with empty type/args.

    Reuses the regex scanner of :mod:`beadloom.graph.sdl` so the fallback matches
    BDL-038's presence-based surface exactly — honest "unknown" depth, never a
    fabricated type. ``typed=False`` tells the verdict layer to stay
    presence-based.
    """
    names = operation_field_names(sdl_text)
    return TypedSurface(
        fields={name: FieldType() for name in names},
        typed=False,
    )


def serialize_typed_surface(surface: TypedSurface) -> SerializedSurface:
    """Serialize a :class:`TypedSurface` to a deterministic, sorted dict.

    Fields are sorted by name and each field's args by name, so an equivalent
    surface emitted in a different traversal order serializes byte-identically
    (the federation determinism invariant).
    """
    return SerializedSurface(
        typed=surface.typed,
        fields=[
            _SerializedField(
                name=name,
                type=surface.fields[name].type,
                args=[
                    _SerializedArg(name=arg_name, type=arg_type)
                    for arg_name, arg_type in sorted(
                        surface.fields[name].args.items()
                    )
                ],
            )
            for name in sorted(surface.fields)
        ],
    )


def parse_typed_surface(payload: object) -> TypedSurface:
    """Read a serialized typed surface back into a :class:`TypedSurface`.

    Tolerant of a missing/empty/foreign payload (older exports carry no ``fields``
    block) — yields an empty, untyped surface so an older reader degrades
    honestly. Never raises on a malformed payload.
    """
    if not isinstance(payload, dict):
        return TypedSurface()
    raw_fields = payload.get("fields")
    fields: dict[str, FieldType] = {}
    if isinstance(raw_fields, list):
        for entry in raw_fields:
            parsed = _parse_field_entry(entry)
            if parsed is not None:
                fields[parsed[0]] = parsed[1]
    typed = bool(payload.get("typed")) and bool(fields)
    return TypedSurface(fields=fields, typed=typed)


def _parse_field_entry(entry: object) -> tuple[str, FieldType] | None:
    """Parse one serialized field entry; ``None`` for a malformed entry."""
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        return None
    field_type = entry.get("type")
    args: dict[str, str] = {}
    raw_args = entry.get("args")
    if isinstance(raw_args, list):
        for arg in raw_args:
            if isinstance(arg, dict):
                arg_name = arg.get("name")
                arg_type = arg.get("type")
                if isinstance(arg_name, str) and arg_name:
                    args[arg_name] = arg_type if isinstance(arg_type, str) else ""
    return name, FieldType(
        type=field_type if isinstance(field_type, str) else "",
        args=args,
    )
