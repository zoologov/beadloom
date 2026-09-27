"""Golden tests for the TYPED GraphQL Tier-A surface (BDL-060 S2, G1a).

``graph/graphql_surface.py`` deepens the name-level surface of ``graph/sdl.py``
into a typed surface over Query / Mutation / Subscription operations: each
operation field carries its return ``type`` (with ``!`` nullability + ``[]`` list
wrapping preserved) and its ``args`` (each ``{name: type}``). Parsing uses the
OPTIONAL ``graphql-core`` extra; when the extra is absent, the typed surface
honestly degrades to the name-level surface (no fabricated fields, no hard fail).

Determinism: ``serialize_typed_surface`` produces a sorted/deduped, byte-stable
dict. The typed surface is the substrate for the native breaking verdict
(``graph/contracts.py``), tested separately.
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

import pytest

from beadloom.graph import graphql_surface as gqs

if TYPE_CHECKING:
    from collections.abc import Iterator

_SDL = """
\"\"\"Public API schema.\"\"\"
type Query {
  plan(id: ID!, limit: Int): Plan
  plans: [Plan!]!
}

type Mutation {
  createPlan(input: CreatePlanInput!): Plan
}

type Subscription {
  planUpdated: Plan!
}

type Plan {
  id: ID!
  name: String!
}

input CreatePlanInput {
  name: String!
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


class TestTypedSurfaceWithGraphqlCore:
    """The typed surface, when graphql-core is available."""

    @requires_graphql
    def test_extracts_operation_fields_with_types(self) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        fields = surface.fields
        assert "plan" in fields
        assert "plans" in fields
        assert "createPlan" in fields
        assert "planUpdated" in fields

    @requires_graphql
    def test_preserves_nullability_and_list_wrapping(self) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        # Nullable object return.
        assert surface.fields["plan"].type == "Plan"
        # Non-null list of non-null Plan.
        assert surface.fields["plans"].type == "[Plan!]!"
        # Non-null object (subscription).
        assert surface.fields["planUpdated"].type == "Plan!"

    @requires_graphql
    def test_args_carry_types_with_nullability(self) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        plan_args = surface.fields["plan"].args
        assert plan_args["id"] == "ID!"
        assert plan_args["limit"] == "Int"
        assert surface.fields["createPlan"].args["input"] == "CreatePlanInput!"

    @requires_graphql
    def test_subscription_fields_are_first_class(self) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        assert "planUpdated" in surface.fields
        assert surface.fields["planUpdated"].type == "Plan!"

    @requires_graphql
    def test_typed_flag_true_when_parsed(self) -> None:
        assert gqs.extract_typed_surface(_SDL).typed is True

    @requires_graphql
    def test_names_match_name_level_operation_fields(self) -> None:
        # The typed field names are a superset-compatible view of the
        # name-level operation fields (no fabricated names).
        from beadloom.graph.sdl import extract_surface

        typed_names = set(gqs.extract_typed_surface(_SDL).fields)
        name_level = extract_surface(_SDL)
        assert typed_names <= name_level

    @requires_graphql
    def test_malformed_sdl_degrades_to_name_level(self) -> None:
        # A syntax error must NOT raise — honest fallback to name-level, typed=False.
        surface = gqs.extract_typed_surface("this is not graphql {{{")
        assert surface.typed is False
        assert surface.fields == {}

    @requires_graphql
    def test_empty_sdl_is_empty_untyped(self) -> None:
        surface = gqs.extract_typed_surface("")
        assert surface.typed is False
        assert surface.fields == {}

    @requires_graphql
    def test_schema_without_operations_has_no_fields(self) -> None:
        surface = gqs.extract_typed_surface("type Plan { id: ID! }")
        # Parsed (typed) but no operation fields.
        assert surface.fields == {}


class TestHonestDegradationWithoutExtra:
    """Absent the extra, the typed surface falls back to name-level (typed=False)."""

    def test_fallback_yields_name_level_field_names(
        self, no_graphql_core: None
    ) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        assert surface.typed is False
        # Name-level operation fields are still surfaced (presence), but with no
        # type/arg depth (honest "unknown", never fabricated).
        names = set(surface.fields)
        assert {"plan", "plans", "createPlan", "planUpdated"} <= names

    def test_fallback_field_types_are_unknown(self, no_graphql_core: None) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        # No fabricated type — honest empty/unknown.
        assert surface.fields["plan"].type == ""
        assert surface.fields["plan"].args == {}

    def test_fallback_empty_sdl(self, no_graphql_core: None) -> None:
        surface = gqs.extract_typed_surface("")
        assert surface.fields == {}
        assert surface.typed is False


class TestDeterministicSerialization:
    """The typed surface serializes to a sorted/deduped, byte-stable dict."""

    @requires_graphql
    def test_serialize_is_sorted_by_field_name(self) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        data = gqs.serialize_typed_surface(surface)
        field_names = [entry["name"] for entry in data["fields"]]
        assert field_names == sorted(field_names)

    @requires_graphql
    def test_serialize_args_sorted(self) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        data = gqs.serialize_typed_surface(surface)
        plan = next(e for e in data["fields"] if e["name"] == "plan")
        arg_names = [a["name"] for a in plan["args"]]
        assert arg_names == sorted(arg_names)

    @requires_graphql
    def test_serialize_round_trips_through_parse(self) -> None:
        surface = gqs.extract_typed_surface(_SDL)
        data = gqs.serialize_typed_surface(surface)
        reparsed = gqs.parse_typed_surface(data)
        assert reparsed.fields == surface.fields

    @requires_graphql
    def test_serialize_is_deterministic(self) -> None:
        a = gqs.serialize_typed_surface(gqs.extract_typed_surface(_SDL))
        b = gqs.serialize_typed_surface(gqs.extract_typed_surface(_SDL))
        assert a == b

    def test_parse_empty_payload_yields_empty_surface(self) -> None:
        surface = gqs.parse_typed_surface({})
        assert surface.fields == {}
        assert surface.typed is False

    @requires_graphql
    def test_serialize_records_typed_flag(self) -> None:
        data = gqs.serialize_typed_surface(gqs.extract_typed_surface(_SDL))
        assert data["typed"] is True

    def test_parse_preserves_typed_flag(self) -> None:
        surface = gqs.parse_typed_surface(
            {"typed": True, "fields": [{"name": "x", "type": "Int", "args": []}]}
        )
        assert surface.typed is True
        assert surface.fields["x"].type == "Int"
