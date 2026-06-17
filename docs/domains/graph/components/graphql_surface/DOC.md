# GraphQL Surface (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/graphql_surface.py`

---

## Overview

The TYPED GraphQL Tier-A surface extractor (BDL-060 S2, G1a). It deepens the
name-level surface of the `sdl` component into a typed surface over the
`Query` / `Mutation` / `Subscription` operations: each operation field carries
its return `type` (with `!` nullability and `[]` list wrapping preserved) and its
`args` (`{name: type}`). Subscriptions are first-class — a subscription field is
extracted with the same depth as a query/mutation field.

Parsing uses the OPTIONAL `graphql-core` extra (`beadloom[graphql]`). When the
extra is absent — or the SDL is malformed/empty — extraction degrades honestly to
the name-level surface (operation field names with empty type/args,
`typed=False`); it never raises and never fabricates a field or type. A verdict is
therefore only ever as strong as the data behind it (the DATA-STRICTNESS
invariant).

## Public surface

- `extract_typed_surface(sdl_text) -> TypedSurface` — parse the typed operation
  surface (graphql-core); honest name-level fallback otherwise.
- `serialize_typed_surface(surface) -> SerializedSurface` — deterministic
  sorted/deduped wire dict (fields by name, args by name) for the federation
  export.
- `parse_typed_surface(payload) -> TypedSurface` — read a serialized surface back
  (tolerant of older/empty payloads).
- `TypedSurface` / `FieldType` — the typed dataclasses.

## Collaborators

Called by the graph-loader (`_fold_graphql_surface`) to emit a producer's typed
`contract.fields` block at load time, and consumed by the federation export +
`contracts` reconciliation. The `graphql_breaking` component computes the verdict
over two typed surfaces.

> Component doc (BDL-060 S2). Public surface verified against `graphql_surface.py`.
