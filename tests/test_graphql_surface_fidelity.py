"""Surface FIDELITY tests for the typed GraphQL Tier-A extraction (BDL-060 S2).

``test_graphql_surface.py`` proves the happy-path shape; this file proves the
extraction does not silently *flatten* or *lose* depth on a richer, nested
schema — the DATA-STRICTNESS requirement that a typed surface is only worth
trusting if the types it reports are faithful:

- nested INPUT types resolve as the arg's named type (``CreatePlanInput!``),
- nested OBJECT return types keep their list + nullability wrapping
  (``[Plan!]!``, ``Plan``, ``Plan!``),
- deeply-nested wrapping (``[[Plan!]!]!``) survives round-trip byte-for-byte,
- subscription-ONLY schemas extract with full depth (no Query required),
- the name-level FALLBACK (no ``graphql-core``) never fabricates a type/arg and
  still feeds a working name-presence verdict end-to-end.

The end-to-end seam (extract -> serialize -> reconcile-shape -> verdict) is
exercised so a fidelity loss anywhere along the wire surfaces as a wrong verdict.
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

import pytest

from beadloom.graph import graphql_surface as gqs
from beadloom.graph.graphql_breaking import breaking_field_descriptors

if TYPE_CHECKING:
    from collections.abc import Iterator

# A richer WebAPI-style producer surface: nested input + object types, list and
# nullability wrapping at several depths, across Query / Mutation / Subscription.
_NESTED_SDL = """
\"\"\"Public WebAPI schema (nested types).\"\"\"
type Query {
  plan(id: ID!, filter: PlanFilter): Plan
  plans(first: Int): [Plan!]!
  matrix: [[Plan!]!]!
}

type Mutation {
  createPlan(input: CreatePlanInput!): Plan!
  archivePlan(id: ID!, reason: String): Plan
}

type Subscription {
  planUpdated(channel: ID!): Plan!
  ticker: Quote!
}

type Plan {
  id: ID!
  name: String!
  owner: Account
}

type Account {
  id: ID!
}

type Quote {
  value: Float!
}

input PlanFilter {
  name: String
  active: Boolean
}

input CreatePlanInput {
  name: String!
  ownerId: ID!
}
"""


def _has_graphql_core() -> bool:
    try:
        import graphql  # noqa: F401
    except ImportError:
        return False
    return True


requires_graphql = pytest.mark.skipif(
    not _has_graphql_core(), reason="graphql-core extra not installed"
)


@pytest.fixture()
def no_graphql_core(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force the absent-extra path: ``import graphql`` raises ImportError."""
    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "graphql" or name.startswith("graphql."):
            raise ImportError("graphql-core not installed (simulated)")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    yield


class TestNestedTypeFidelity:
    """Nested input/object types resolve without flattening or nullability loss."""

    @requires_graphql
    def test_all_operations_across_three_roots_present(self) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        assert {
            "plan",
            "plans",
            "matrix",
            "createPlan",
            "archivePlan",
            "planUpdated",
            "ticker",
        } <= set(surface.fields)

    @requires_graphql
    def test_nested_input_type_resolves_as_arg_type(self) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        assert surface.fields["createPlan"].args["input"] == "CreatePlanInput!"
        # A nullable nested input arg keeps its nullability.
        assert surface.fields["plan"].args["filter"] == "PlanFilter"

    @requires_graphql
    def test_object_return_wrapping_preserved(self) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        assert surface.fields["plan"].type == "Plan"  # nullable object
        assert surface.fields["plans"].type == "[Plan!]!"  # non-null list non-null
        assert surface.fields["createPlan"].type == "Plan!"  # non-null object

    @requires_graphql
    def test_deeply_nested_list_wrapping_not_flattened(self) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        # The doubly-nested list must NOT collapse to ``[Plan!]!`` or ``Plan``.
        assert surface.fields["matrix"].type == "[[Plan!]!]!"

    @requires_graphql
    def test_subscription_args_carry_types(self) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        assert surface.fields["planUpdated"].args["channel"] == "ID!"
        assert surface.fields["ticker"].type == "Quote!"

    @requires_graphql
    def test_multiple_args_all_captured(self) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        args = surface.fields["plan"].args
        assert set(args) == {"id", "filter"}
        assert args["id"] == "ID!"


class TestDeepWrappingRoundTrip:
    """Deep wrapping survives serialize -> parse byte-identically (no loss)."""

    @requires_graphql
    def test_serialize_parse_preserves_deep_wrapping(self) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        reparsed = gqs.parse_typed_surface(gqs.serialize_typed_surface(surface))
        assert reparsed.fields["matrix"].type == "[[Plan!]!]!"
        assert reparsed.fields["createPlan"].args["input"] == "CreatePlanInput!"
        # Full equality: nothing was dropped, reordered-into-loss, or fabricated.
        assert reparsed.fields == surface.fields


class TestSubscriptionOnlySchema:
    """A schema with ONLY a Subscription root extracts with full depth."""

    _SUB_ONLY = """
    type Subscription {
      ticker(symbol: ID!): Quote!
      book: [Level!]!
    }
    type Quote { value: Float! }
    type Level { price: Float! }
    """

    @requires_graphql
    def test_subscription_only_extracts_typed(self) -> None:
        surface = gqs.extract_typed_surface(self._SUB_ONLY)
        assert surface.typed is True
        assert surface.fields["ticker"].type == "Quote!"
        assert surface.fields["ticker"].args["symbol"] == "ID!"
        assert surface.fields["book"].type == "[Level!]!"

    @requires_graphql
    def test_subscription_only_feeds_verdict(self) -> None:
        # End-to-end: a dropped subscription field is BREAKING through the wire.
        producer = gqs.extract_typed_surface(self._SUB_ONLY)
        consumer = gqs.extract_typed_surface(
            self._SUB_ONLY.replace("book: [Level!]!", "book: [Level!]!\n  depth: Int!")
        )
        exposed = {
            f["name"]: {"type": f["type"], "args": {a["name"]: a["type"] for a in f["args"]}}
            for f in gqs.serialize_typed_surface(producer)["fields"]
        }
        referenced = {
            f["name"]: {"type": f["type"], "args": {a["name"]: a["type"] for a in f["args"]}}
            for f in gqs.serialize_typed_surface(consumer)["fields"]
        }
        assert "depth" in breaking_field_descriptors(exposed, referenced)


class TestEndToEndExtractToVerdict:
    """A producer-vs-consumer SDL diff yields the right break through the wire."""

    @requires_graphql
    def _serialized(self, sdl: str) -> dict[str, dict[str, object]]:
        surface = gqs.serialize_typed_surface(gqs.extract_typed_surface(sdl))
        return {
            f["name"]: {
                "type": f["type"],
                "args": {a["name"]: a["type"] for a in f["args"]},
            }
            for f in surface["fields"]
        }

    @requires_graphql
    def test_removed_field_breaks_end_to_end(self) -> None:
        # Producer drops ``archivePlan`` that the consumer still references.
        producer_sdl = _NESTED_SDL.replace(
            "  archivePlan(id: ID!, reason: String): Plan\n", ""
        )
        exposed = self._serialized(producer_sdl)
        referenced = self._serialized(_NESTED_SDL)
        assert "archivePlan" in breaking_field_descriptors(exposed, referenced)

    @requires_graphql
    def test_unchanged_schema_is_no_break_end_to_end(self) -> None:
        surface = self._serialized(_NESTED_SDL)
        assert breaking_field_descriptors(surface, surface) == []

    @requires_graphql
    def test_nested_input_arg_added_required_breaks(self) -> None:
        # Producer adds a required arg ``audit: ID!`` to ``createPlan``.
        producer_sdl = _NESTED_SDL.replace(
            "createPlan(input: CreatePlanInput!): Plan!",
            "createPlan(input: CreatePlanInput!, audit: ID!): Plan!",
        )
        exposed = self._serialized(producer_sdl)
        referenced = self._serialized(_NESTED_SDL)
        assert "createPlan(audit)" in breaking_field_descriptors(exposed, referenced)


class TestFallbackFidelity:
    """Absent the extra, fidelity degrades HONESTLY (no fabricated depth)."""

    def test_fallback_names_present_no_types(self, no_graphql_core: None) -> None:
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        assert surface.typed is False
        # Every operation field name surfaces (presence) ...
        assert {"plan", "plans", "createPlan", "planUpdated", "ticker"} <= set(
            surface.fields
        )
        # ... but with NO fabricated type or arg depth.
        for ft in surface.fields.values():
            assert ft.type == ""
            assert ft.args == {}

    def test_fallback_never_raises_on_nested_schema(
        self, no_graphql_core: None
    ) -> None:
        # The honest degradation path must not crash on a complex nested schema.
        surface = gqs.extract_typed_surface(_NESTED_SDL)
        assert isinstance(surface.fields, dict)

    def test_fallback_serialized_carries_no_typed_depth(
        self, no_graphql_core: None
    ) -> None:
        data = gqs.serialize_typed_surface(gqs.extract_typed_surface(_NESTED_SDL))
        assert data["typed"] is False
        assert all(entry["type"] == "" and entry["args"] == [] for entry in data["fields"])

    def test_fallback_verdict_works_at_name_level(self, no_graphql_core: None) -> None:
        # Without the extra both sides are untyped -> the contract layer would use
        # name-presence. Here at the surface level we still get HONEST field names
        # that a name-presence check can compare (no fabricated types to mislead).
        producer = gqs.extract_typed_surface(
            "type Query {\n  a: Int\n  b: Int\n}"
        )
        consumer = gqs.extract_typed_surface(
            "type Query {\n  a: Int\n  gone: Int\n}"
        )
        prod_names = set(producer.fields)
        cons_names = set(consumer.fields)
        assert prod_names == {"a", "b"}
        # Name-level: ``gone`` referenced but not exposed -> a name-presence break.
        assert "gone" in (cons_names - prod_names)
