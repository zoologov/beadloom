"""Unit tests for the minimal GraphQL SDL surface extractor (BDL-038 BEAD-03).

``extract_surface`` returns the producer's exposed names — the field names of the
top-level ``Query``/``Mutation``/``Subscription`` types PLUS the top-level
``type``/``input``/``enum``/``interface`` type names. Name-presence only; a
malformed or empty SDL yields ``set()`` (recorded honestly as ``exposed: []``,
never faked). Output is order-independent (a ``set``); callers sort it.
"""

from __future__ import annotations

from beadloom.graph.sdl import extract_surface

_SDL = """
\"\"\"Public API schema.\"\"\"
type Query {
  plan(id: ID!): Plan
  plans: [Plan!]!
}

type Mutation {
  createPlan(input: CreatePlanInput!): Plan
}

type Subscription {
  planUpdated: Plan
}

type Plan {
  id: ID!
  name: String!
}

input CreatePlanInput {
  name: String!
}

enum PlanStatus {
  DRAFT
  PUBLISHED
}

interface Node {
  id: ID!
}
"""


class TestExtractSurface:
    def test_query_field_names(self) -> None:
        surface = extract_surface(_SDL)
        assert "plan" in surface
        assert "plans" in surface

    def test_mutation_field_names(self) -> None:
        assert "createPlan" in extract_surface(_SDL)

    def test_subscription_field_names(self) -> None:
        assert "planUpdated" in extract_surface(_SDL)

    def test_top_level_type_names(self) -> None:
        surface = extract_surface(_SDL)
        assert "Plan" in surface

    def test_input_enum_interface_type_names(self) -> None:
        surface = extract_surface(_SDL)
        assert {"CreatePlanInput", "PlanStatus", "Node"} <= surface

    def test_root_type_names_also_present(self) -> None:
        # The root operation types are themselves exposed type names.
        surface = extract_surface(_SDL)
        assert {"Query", "Mutation", "Subscription"} <= surface

    def test_nested_field_names_not_leaked_as_top_level(self) -> None:
        # ``id``/``name`` are fields of object types, not Query/Mutation/
        # Subscription operations — they are NOT part of the exposed operation
        # surface. (They appear only if a type named ``id`` existed, which it
        # does not.)
        surface = extract_surface(_SDL)
        assert "name" not in surface
        assert "id" not in surface

    def test_empty_string_returns_empty_set(self) -> None:
        assert extract_surface("") == set()

    def test_whitespace_only_returns_empty_set(self) -> None:
        assert extract_surface("   \n\t  ") == set()

    def test_malformed_sdl_returns_empty_set(self) -> None:
        # No recognizable type/operation definitions — honest empty, never faked.
        assert extract_surface("this is not graphql {{{ ") == set()

    def test_garbage_braces_do_not_crash(self) -> None:
        assert extract_surface("} } } type") == set()

    def test_deterministic_same_input_same_output(self) -> None:
        a = extract_surface(_SDL)
        b = extract_surface(_SDL)
        assert a == b

    def test_returns_a_set(self) -> None:
        assert isinstance(extract_surface(_SDL), set)

    def test_type_with_no_fields(self) -> None:
        surface = extract_surface("type Empty {\n}\n")
        assert surface == {"Empty"}

    def test_extend_type_not_treated_as_definition(self) -> None:
        # ``extend type`` is a modification, not a new top-level surface name.
        surface = extract_surface("extend type Query {\n  extra: Int\n}\n")
        assert "extra" in surface
        # The extended root's own name is still its own; we do not invent one.
        assert "extend" not in surface
