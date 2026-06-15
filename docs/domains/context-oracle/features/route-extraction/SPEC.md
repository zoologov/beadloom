# Route Extraction

API route extraction across web frameworks for the context-oracle domain.

**Source:** `src/beadloom/context_oracle/route_extractor.py`

---

## Specification

### Purpose

Discover the HTTP and RPC API routes a codebase exposes, so the graph and the
context bundle can describe a service's external surface. The extractor pairs
tree-sitter parsing with a regex fallback and recognises twelve frameworks
across Python, TypeScript/JavaScript, Go, Java/Kotlin, GraphQL, and Protobuf:
FastAPI, Flask, Strawberry/Ariadne (GraphQL-Python), Express, NestJS,
TypeGraphQL, Spring, Gin, Echo, Fiber, a GraphQL schema reader, and a gRPC
`.proto` reader.

### Data flow

`extract_routes(file_path, language)` selects an extraction path from the
language label: GraphQL and Protobuf are pure-regex; Python, TypeScript,
JavaScript, Go, and Java/Kotlin each route to a language-specific extractor.
Each match becomes a frozen `Route` record. A per-file safety cap of 100 routes
prevents a pathological file from flooding the graph; the extractor also skips
its own module to avoid matching the regex patterns it defines.

`format_routes_for_display` renders a collected list of route dicts for the CLI,
separating HTTP routes from GraphQL operations.

## Invariants

- Tree-sitter parsing is preferred; the regex fallback is used where no grammar
  is available for the language.
- Extraction never raises on unreadable, empty, or unsupported input — it
  returns an empty list and logs a warning, so it cannot break a reindex.
- At most 100 routes are returned per file (`_MAX_ROUTES_PER_FILE`).

## API

Module `src/beadloom/context_oracle/route_extractor.py`:

- `Route` — frozen dataclass: `method`, `path`, `handler`, `file_path`,
  `line`, `framework`.
- `extract_routes(file_path: Path, language: str) -> list[Route]` — extract
  routes from one source file; `language` is one of `python`, `typescript`,
  `javascript`, `go`, `java`, `kotlin`, `graphql`, `protobuf`.
- `format_routes_for_display(routes_data: list[dict[str, str]]) -> str` —
  format collected route data for human-readable display.

## Testing

Tests: `tests/test_route_extractor.py`, `tests/test_reindex_routes.py`
