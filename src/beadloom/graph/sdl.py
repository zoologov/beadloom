# beadloom:domain=graph
# beadloom:component=sdl
"""Minimal, dependency-free GraphQL SDL surface extractor (BDL-038 BEAD-03).

The cross-service contract graph needs only the *names* a GraphQL producer
exposes so a consumer's declared ``references`` can be checked for presence
(the F2 ``BREAKING`` signal is presence-based — BEAD-04). This module therefore
implements a tiny line/brace scanner over the SDL text rather than pulling in a
full GraphQL parser (``graphql-core`` is the documented upgrade path if
field-type/argument-level diffing is ever needed — F3+; see RFC §2).

:func:`extract_surface` returns the exposed surface as a ``set[str]``:

- the **field names** of the top-level ``Query`` / ``Mutation`` /
  ``Subscription`` operation types, AND
- the **type names** of every top-level ``type`` / ``input`` / ``enum`` /
  ``interface`` definition (including the operation types themselves).

Scope is name-presence only — there is **no** schema validation. Malformed or
empty SDL yields an empty set, which the loader records honestly as
``exposed: []`` (never a faked confirmation — RFC design principle 2).
"""

# beadloom:domain=graph

from __future__ import annotations

import re

# Top-level definition headers we extract a *name* from. ``extend`` is allowed
# as an optional prefix (``extend type Query { ... }``) — the extended members
# still contribute to the exposed surface, but ``extend`` itself is not a name.
_DEFINITION = re.compile(
    r"^\s*(?:extend\s+)?(?P<keyword>type|input|enum|interface)\s+(?P<name>[A-Za-z_]\w*)",
)

# A field declaration inside an operation body: ``fieldName(args): ReturnType``
# or ``fieldName: ReturnType``. We capture only the leading identifier.
_FIELD = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*[(:]")

_OPERATION_TYPES = frozenset({"Query", "Mutation", "Subscription"})


def extract_surface(sdl_text: str) -> set[str]:
    """Extract the exposed GraphQL surface (operation fields + type names).

    Returns an empty set for empty/whitespace-only/malformed input (honest, not
    faked). The result is a ``set`` so callers must sort it for deterministic
    serialization.
    """
    type_names, operation_fields = _scan(sdl_text)
    return type_names | operation_fields


def operation_field_names(sdl_text: str) -> set[str]:
    """Extract ONLY the Query/Mutation/Subscription operation field names.

    The name-level fallback substrate for the typed surface
    (:mod:`beadloom.graph.graphql_surface`): consumer ``references`` are operation
    field names, so the fallback keys its ``fields`` on these (not the top-level
    type names that :func:`extract_surface` also returns). Honest empty set for
    empty/malformed input.
    """
    _type_names, operation_fields = _scan(sdl_text)
    return operation_fields


def _scan(sdl_text: str) -> tuple[set[str], set[str]]:
    """Single-pass scan: ``(top-level type names, operation field names)``."""
    type_names: set[str] = set()
    operation_fields: set[str] = set()
    lines = sdl_text.splitlines()
    i = 0
    while i < len(lines):
        match = _DEFINITION.match(lines[i])
        if match is None:
            i += 1
            continue
        name = match.group("name")
        type_names.add(name)
        body, i = _consume_body(lines, i)
        if name in _OPERATION_TYPES:
            operation_fields.update(_field_names(body))
    return type_names, operation_fields


def _consume_body(lines: list[str], start: int) -> tuple[list[str], int]:
    """Return the lines inside the ``{ ... }`` body of the definition at *start*.

    Tracks brace depth so nested braces (e.g. inline default objects) are
    balanced. Returns ``([], start + 1)`` for a bodyless definition. The second
    element is the index of the line *after* the consumed definition.
    """
    depth = 0
    body: list[str] = []
    opened = False
    i = start
    while i < len(lines):
        line = lines[i]
        depth += line.count("{") - line.count("}")
        if "{" in line:
            opened = True
        if opened and depth <= 0:
            return body, i + 1
        if opened and depth > 0 and i != start:
            body.append(line)
        i += 1
    # No closing brace (or no body at all) — bodyless definition.
    return body, start + 1


def _field_names(body: list[str]) -> set[str]:
    """Collect leading field identifiers from an operation type body."""
    names: set[str] = set()
    for line in body:
        match = _FIELD.match(line)
        if match is not None:
            names.add(match.group("name"))
    return names
