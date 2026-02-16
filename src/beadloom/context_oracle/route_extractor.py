"""API route extraction: tree-sitter AST + regex fallback for 12 frameworks."""

# beadloom:domain=context-oracle

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Node as TSNode

logger = logging.getLogger(__name__)

# Safety cap: maximum routes extracted from a single file.
_MAX_ROUTES_PER_FILE = 100


@dataclass(frozen=True)
class Route:
    """A single API route extracted from a source file."""

    method: str  # GET, POST, PUT, DELETE, PATCH, * / QUERY, MUTATION, SUBSCRIPTION / RPC
    path: str  # /api/login, /users/{id}, user (GraphQL field), Auth/Login (gRPC)
    handler: str  # function name
    file_path: str  # absolute path to source file
    line: int  # 1-based line number
    framework: str  # fastapi, flask, express, nestjs, spring, gin, echo, fiber, ...


# ---------------------------------------------------------------------------
# Language -> extraction strategy mapping
# ---------------------------------------------------------------------------

# Map "language" label -> file extension for tree-sitter lookup.
_LANG_TO_EXT: dict[str, str] = {
    "python": ".py",
    "typescript": ".ts",
    "javascript": ".js",
    "go": ".go",
    "java": ".java",
    "kotlin": ".kt",
}

# Languages that use pure regex (no tree-sitter needed).
_REGEX_ONLY_LANGS: frozenset[str] = frozenset({"graphql", "protobuf"})


# ---------------------------------------------------------------------------
# Regex patterns (compiled once)
# ---------------------------------------------------------------------------

# -- Python: FastAPI --
_FASTAPI_DECORATOR_RE = re.compile(
    r"@(?:\w+)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

# -- Python: Flask --
_FLASK_ROUTE_RE = re.compile(
    r"@(?:\w+)\.route\(\s*[\"']([^\"']+)[\"'](?:.*?methods\s*=\s*\[([^\]]+)\])?\s*\)",
    re.IGNORECASE,
)

# -- Python: GraphQL code-first (Strawberry / Ariadne) --
_STRAWBERRY_TYPE_RE = re.compile(r"@strawberry\.(type|mutation)")
_ARIADNE_FIELD_RE = re.compile(
    r"@\w+\.field\(\s*[\"']([^\"']+)[\"']\s*\)",
)
_ARIADNE_TYPE_RE = re.compile(r"(\w+)\s*=\s*(?:QueryType|MutationType|SubscriptionType)\(\)")

# -- TS/JS: Express --
_EXPRESS_ROUTE_RE = re.compile(
    r"(?:router|app)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

# -- TS: NestJS --
_NESTJS_DECORATOR_RE = re.compile(
    r"@(Get|Post|Put|Delete|Patch)\(\s*(?:[\"']([^\"']*)[\"'])?\s*\)",
)

# -- TS: TypeGraphQL --
_TYPEGRAPHQL_DECORATOR_RE = re.compile(
    r"@(Query|Mutation|Subscription)\(",
)

# -- Java/Kotlin: Spring Boot --
_SPRING_MAPPING_RE = re.compile(
    r"@(Get|Post|Put|Delete|Patch|Request)Mapping"
    r"(?:\(\s*(?:value\s*=\s*)?[\"']([^\"']*)[\"'])?",
)

# -- Go: Gin --
_GIN_ROUTE_RE = re.compile(
    r"\w+\.(GET|POST|PUT|DELETE|PATCH)\(\s*[\"']([^\"']+)[\"']",
)

# -- Go: Echo --
_ECHO_ROUTE_RE = re.compile(
    r"\w+\.(GET|POST|PUT|DELETE|PATCH)\(\s*[\"']([^\"']+)[\"']",
)

# -- Go: Fiber --
_FIBER_ROUTE_RE = re.compile(
    r"\w+\.(Get|Post|Put|Delete|Patch)\(\s*[\"']([^\"']+)[\"']",
)

# -- .graphql / .gql schema --
_GQL_TYPE_BLOCK_RE = re.compile(
    r"type\s+(Query|Mutation|Subscription)\s*\{([^}]+)\}",
    re.DOTALL,
)
_GQL_FIELD_RE = re.compile(r"^\s*(\w+)\s*(?:\([^)]*\))?\s*:", re.MULTILINE)

# -- .proto gRPC --
_PROTO_SERVICE_RE = re.compile(
    r"service\s+(\w+)\s*\{([^}]+)\}",
    re.DOTALL,
)
_PROTO_RPC_RE = re.compile(
    r"rpc\s+(\w+)\s*\(",
)


# ---------------------------------------------------------------------------
# Tree-sitter-based extraction helpers
# ---------------------------------------------------------------------------


def _get_node_text(node: TSNode) -> str:
    """Safely decode tree-sitter node text."""
    return node.text.decode("utf-8") if node.text else ""


def _find_function_after_line(
    lines: list[str],
    start_line: int,
) -> str:
    """Find function/method name on or after a given 0-based line index."""
    for i in range(start_line, min(start_line + 5, len(lines))):
        line = lines[i]
        # Python: def/async def
        m = re.search(r"(?:async\s+)?def\s+(\w+)", line)
        if m:
            return m.group(1)
        # TS/JS: function name(
        m = re.search(r"(?:async\s+)?(?:function\s+)?(\w+)\s*\(", line)
        if m and m.group(1) not in ("if", "for", "while", "return", "class"):
            return m.group(1)
    return "<anonymous>"


def _find_method_name_after(lines: list[str], start_line: int) -> str:
    """Find method name in class body after a decorator line (0-based)."""
    for i in range(start_line + 1, min(start_line + 5, len(lines))):
        line = lines[i].strip()
        # Skip empty/decorator lines
        if not line or line.startswith("@"):
            continue
        # TS/JS method: methodName( or async methodName(
        m = re.search(r"(?:async\s+)?(\w+)\s*\(", line)
        if m and m.group(1) not in ("if", "for", "while", "return", "class"):
            return m.group(1)
    return "<anonymous>"


# ---------------------------------------------------------------------------
# Framework-specific extraction via regex
# ---------------------------------------------------------------------------


def _extract_fastapi_regex(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract FastAPI routes from Python source using regex."""
    routes: list[Route] = []
    for m in _FASTAPI_DECORATOR_RE.finditer(content):
        method = m.group(1).upper()
        path = m.group(2)
        line_num = content[: m.start()].count("\n") + 1
        handler = _find_function_after_line(lines, line_num)  # 0-based after decorator
        routes.append(
            Route(
                method=method,
                path=path,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="fastapi",
            )
        )
    return routes


def _extract_flask_regex(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract Flask routes from Python source using regex."""
    routes: list[Route] = []
    for m in _FLASK_ROUTE_RE.finditer(content):
        path = m.group(1)
        methods_str = m.group(2)
        line_num = content[: m.start()].count("\n") + 1
        handler = _find_function_after_line(lines, line_num)

        if methods_str:
            # Parse methods=["GET", "POST"]
            parsed_methods = re.findall(r"[\"'](\w+)[\"']", methods_str)
            for method in parsed_methods:
                routes.append(
                    Route(
                        method=method.upper(),
                        path=path,
                        handler=handler,
                        file_path=file_path,
                        line=line_num,
                        framework="flask",
                    )
                )
        else:
            # Default to GET
            routes.append(
                Route(
                    method="GET",
                    path=path,
                    handler=handler,
                    file_path=file_path,
                    line=line_num,
                    framework="flask",
                )
            )
    return routes


def _extract_graphql_python_regex(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract GraphQL code-first routes from Python (Strawberry / Ariadne)."""
    routes: list[Route] = []

    # Strawberry @strawberry.type class with @strawberry.field methods
    if "strawberry" in content:
        # Find @strawberry.type or @strawberry.mutation decorators
        for m in _STRAWBERRY_TYPE_RE.finditer(content):
            kind = m.group(1).upper()  # "type" -> QUERY, "mutation" -> MUTATION
            gql_method = "MUTATION" if kind == "MUTATION" else "QUERY"
            line_num = content[: m.start()].count("\n") + 1
            # Find the class and its methods
            after = content[m.end() :]
            # Find method definitions inside the class
            for field_m in re.finditer(r"def\s+(\w+)\s*\(", after):
                field_name = field_m.group(1)
                if field_name.startswith("_"):
                    continue
                field_line = content[: m.end() + field_m.start()].count("\n") + 1
                routes.append(
                    Route(
                        method=gql_method,
                        path=field_name,
                        handler=field_name,
                        file_path=file_path,
                        line=field_line,
                        framework="graphql_python",
                    )
                )
                # Only get methods until the next class definition
                rest_after = after[field_m.end() :]
                if re.search(r"^class\s+", rest_after, re.MULTILINE):
                    # Check if there's a class definition between our field_m start and end
                    break

    # Ariadne @query.field("name")
    for m in _ARIADNE_FIELD_RE.finditer(content):
        field_name = m.group(1)
        line_num = content[: m.start()].count("\n") + 1
        handler = _find_function_after_line(lines, line_num)
        # Determine method from the variable name (query -> QUERY, mutation -> MUTATION)
        before = content[: m.start()]
        gql_method = "QUERY"  # default
        # Check what type the decorator object is
        for type_m in _ARIADNE_TYPE_RE.finditer(before):
            var_name = type_m.group(1)
            type_name = "QueryType"
            # Extract the actual type from the match
            type_match = re.search(
                rf"{re.escape(var_name)}\s*=\s*(QueryType|MutationType|SubscriptionType)",
                before,
            )
            if type_match:
                type_name = type_match.group(1)
            if type_name == "MutationType":
                gql_method = "MUTATION"
            elif type_name == "SubscriptionType":
                gql_method = "SUBSCRIPTION"
        routes.append(
            Route(
                method=gql_method,
                path=field_name,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="graphql_python",
            )
        )
    return routes


def _extract_express_regex(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract Express.js routes from TS/JS source using regex."""
    routes: list[Route] = []
    for m in _EXPRESS_ROUTE_RE.finditer(content):
        method = m.group(1).upper()
        path = m.group(2)
        line_num = content[: m.start()].count("\n") + 1
        # Try to find handler name from the call arguments
        rest_of_line = content[m.end() :]
        handler_m = re.match(r"\s*,\s*(\w+)", rest_of_line)
        handler = handler_m.group(1) if handler_m else "<anonymous>"
        routes.append(
            Route(
                method=method,
                path=path,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="express",
            )
        )
    return routes


def _extract_nestjs_regex(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract NestJS routes from TypeScript source using regex."""
    routes: list[Route] = []
    for m in _NESTJS_DECORATOR_RE.finditer(content):
        method = m.group(1).upper()
        path = m.group(2) if m.group(2) else ""
        line_num = content[: m.start()].count("\n") + 1
        handler = _find_method_name_after(lines, line_num - 1)
        routes.append(
            Route(
                method=method,
                path=path,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="nestjs",
            )
        )
    return routes


def _extract_typegraphql_regex(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract TypeGraphQL routes from TypeScript source using regex."""
    routes: list[Route] = []
    for m in _TYPEGRAPHQL_DECORATOR_RE.finditer(content):
        method = m.group(1).upper()
        line_num = content[: m.start()].count("\n") + 1
        handler = _find_method_name_after(lines, line_num - 1)
        routes.append(
            Route(
                method=method,
                path=handler,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="graphql_ts",
            )
        )
    return routes


def _extract_spring_regex(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract Spring Boot routes from Java/Kotlin source using regex."""
    routes: list[Route] = []
    for m in _SPRING_MAPPING_RE.finditer(content):
        mapping_type = m.group(1)
        path = m.group(2) if m.group(2) else ""
        line_num = content[: m.start()].count("\n") + 1

        method_map: dict[str, str] = {
            "Get": "GET",
            "Post": "POST",
            "Put": "PUT",
            "Delete": "DELETE",
            "Patch": "PATCH",
            "Request": "*",
        }
        method = method_map.get(mapping_type, "*")

        # For @RequestMapping, try to detect method from the annotation
        if mapping_type == "Request":
            method_match = re.search(r"method\s*=\s*RequestMethod\.(\w+)", content[m.start() :])
            if method_match:
                method = method_match.group(1).upper()

        handler = _find_method_after_annotation(lines, line_num - 1)
        routes.append(
            Route(
                method=method,
                path=path,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="spring",
            )
        )
    return routes


def _find_method_after_annotation(lines: list[str], start_line: int) -> str:
    """Find Java/Kotlin method name after an annotation (0-based line index)."""
    for i in range(start_line + 1, min(start_line + 5, len(lines))):
        line = lines[i].strip()
        if not line or line.startswith("@"):
            continue
        # Java: public ReturnType methodName(
        m = re.search(r"(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(", line)
        if m:
            return m.group(1)
        # Kotlin: fun methodName(
        m = re.search(r"fun\s+(\w+)\s*\(", line)
        if m:
            return m.group(1)
    return "<anonymous>"


def _extract_gin_regex(
    content: str,
    file_path: str,
) -> list[Route]:
    """Extract Gin routes from Go source using regex."""
    routes: list[Route] = []
    for m in _GIN_ROUTE_RE.finditer(content):
        method = m.group(1).upper()
        path = m.group(2)
        line_num = content[: m.start()].count("\n") + 1
        # Handler is typically the last argument
        rest = content[m.end() :]
        handler_m = re.match(r"\s*,\s*(\w+)", rest)
        handler = handler_m.group(1) if handler_m else "<anonymous>"
        routes.append(
            Route(
                method=method,
                path=path,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="gin",
            )
        )
    return routes


def _extract_echo_regex(
    content: str,
    file_path: str,
) -> list[Route]:
    """Extract Echo routes from Go source using regex."""
    routes: list[Route] = []
    for m in _ECHO_ROUTE_RE.finditer(content):
        method = m.group(1).upper()
        path = m.group(2)
        line_num = content[: m.start()].count("\n") + 1
        rest = content[m.end() :]
        handler_m = re.match(r"\s*,\s*(\w+)", rest)
        handler = handler_m.group(1) if handler_m else "<anonymous>"
        routes.append(
            Route(
                method=method,
                path=path,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="echo",
            )
        )
    return routes


def _extract_fiber_regex(
    content: str,
    file_path: str,
) -> list[Route]:
    """Extract Fiber routes from Go source using regex."""
    routes: list[Route] = []
    for m in _FIBER_ROUTE_RE.finditer(content):
        method = m.group(1).upper()
        path = m.group(2)
        line_num = content[: m.start()].count("\n") + 1
        rest = content[m.end() :]
        handler_m = re.match(r"\s*,\s*(\w+)", rest)
        handler = handler_m.group(1) if handler_m else "<anonymous>"
        routes.append(
            Route(
                method=method,
                path=path,
                handler=handler,
                file_path=file_path,
                line=line_num,
                framework="fiber",
            )
        )
    return routes


# ---------------------------------------------------------------------------
# Pure-regex extraction for schema files
# ---------------------------------------------------------------------------


def _extract_graphql_schema(
    content: str,
    file_path: str,
) -> list[Route]:
    """Extract routes from .graphql / .gql schema files (pure regex)."""
    routes: list[Route] = []
    method_map: dict[str, str] = {
        "Query": "QUERY",
        "Mutation": "MUTATION",
        "Subscription": "SUBSCRIPTION",
    }
    for block_m in _GQL_TYPE_BLOCK_RE.finditer(content):
        type_name = block_m.group(1)
        method = method_map.get(type_name, "QUERY")
        block_body = block_m.group(2)
        block_start_offset = block_m.start(2)

        for field_m in _GQL_FIELD_RE.finditer(block_body):
            field_name = field_m.group(1)
            # Calculate line number
            abs_offset = block_start_offset + field_m.start()
            line_num = content[:abs_offset].count("\n") + 1
            routes.append(
                Route(
                    method=method,
                    path=field_name,
                    handler=field_name,
                    file_path=file_path,
                    line=line_num,
                    framework="graphql_schema",
                )
            )
    return routes


def _extract_grpc_proto(
    content: str,
    file_path: str,
) -> list[Route]:
    """Extract routes from .proto gRPC service definitions (pure regex)."""
    routes: list[Route] = []
    for svc_m in _PROTO_SERVICE_RE.finditer(content):
        service_name = svc_m.group(1)
        svc_body = svc_m.group(2)
        svc_body_offset = svc_m.start(2)

        for rpc_m in _PROTO_RPC_RE.finditer(svc_body):
            rpc_name = rpc_m.group(1)
            abs_offset = svc_body_offset + rpc_m.start()
            line_num = content[:abs_offset].count("\n") + 1
            routes.append(
                Route(
                    method="RPC",
                    path=f"{service_name}/{rpc_name}",
                    handler=rpc_name,
                    file_path=file_path,
                    line=line_num,
                    framework="grpc",
                )
            )
    return routes


# ---------------------------------------------------------------------------
# Go framework disambiguation
# ---------------------------------------------------------------------------


def _detect_go_frameworks(content: str) -> set[str]:
    """Detect which Go web frameworks are imported in the source."""
    frameworks: set[str] = set()
    if "gin-gonic/gin" in content or '"github.com/gin-gonic' in content:
        frameworks.add("gin")
    if "labstack/echo" in content:
        frameworks.add("echo")
    if "gofiber/fiber" in content:
        frameworks.add("fiber")
    return frameworks


def _extract_go_routes(content: str, file_path: str) -> list[Route]:
    """Extract routes from Go source, disambiguating between Gin/Echo/Fiber."""
    frameworks = _detect_go_frameworks(content)
    routes: list[Route] = []

    if "gin" in frameworks:
        routes.extend(_extract_gin_regex(content, file_path))
    if "echo" in frameworks:
        # Avoid double-counting if gin regex also matched
        echo_routes = _extract_echo_regex(content, file_path)
        # Deduplicate by (line, path)
        existing = {(r.line, r.path) for r in routes}
        for r in echo_routes:
            if (r.line, r.path) not in existing:
                routes.append(r)
    if "fiber" in frameworks:
        routes.extend(_extract_fiber_regex(content, file_path))

    # If no specific framework detected, try all patterns
    if not frameworks:
        routes.extend(_extract_gin_regex(content, file_path))
        if not routes:
            routes.extend(_extract_echo_regex(content, file_path))
        if not routes:
            routes.extend(_extract_fiber_regex(content, file_path))

    return routes


# ---------------------------------------------------------------------------
# TypeScript/JS framework disambiguation
# ---------------------------------------------------------------------------


def _extract_ts_routes(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract routes from TypeScript/JavaScript source."""
    routes: list[Route] = []

    # NestJS detection: @Get/@Post etc. decorators
    if _NESTJS_DECORATOR_RE.search(content):
        routes.extend(_extract_nestjs_regex(content, file_path, lines))

    # TypeGraphQL detection: @Query/@Mutation decorators
    if _TYPEGRAPHQL_DECORATOR_RE.search(content):
        routes.extend(_extract_typegraphql_regex(content, file_path, lines))

    # Express detection: router.get/app.get pattern
    if _EXPRESS_ROUTE_RE.search(content):
        express_routes = _extract_express_regex(content, file_path, lines)
        # Deduplicate
        existing = {(r.line, r.path) for r in routes}
        for r in express_routes:
            if (r.line, r.path) not in existing:
                routes.append(r)

    return routes


# ---------------------------------------------------------------------------
# Python framework disambiguation
# ---------------------------------------------------------------------------


def _extract_python_routes(
    content: str,
    file_path: str,
    lines: list[str],
) -> list[Route]:
    """Extract routes from Python source."""
    routes: list[Route] = []

    # FastAPI detection
    if _FASTAPI_DECORATOR_RE.search(content):
        routes.extend(_extract_fastapi_regex(content, file_path, lines))

    # Flask detection
    if _FLASK_ROUTE_RE.search(content):
        flask_routes = _extract_flask_regex(content, file_path, lines)
        existing = {(r.line, r.path) for r in routes}
        for r in flask_routes:
            if (r.line, r.path) not in existing:
                routes.append(r)

    # GraphQL Python (Strawberry / Ariadne)
    if "strawberry" in content or "QueryType" in content or "MutationType" in content:
        gql_routes = _extract_graphql_python_regex(content, file_path, lines)
        existing = {(r.line, r.path) for r in routes}
        for r in gql_routes:
            if (r.line, r.path) not in existing:
                routes.append(r)

    return routes


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def extract_routes(file_path: Path, language: str) -> list[Route]:
    """Extract API routes from a source file using tree-sitter + regex.

    Parameters
    ----------
    file_path:
        Path to the source file to analyze.
    language:
        Language identifier: ``"python"``, ``"typescript"``, ``"javascript"``,
        ``"go"``, ``"java"``, ``"kotlin"``, ``"graphql"``, ``"protobuf"``.

    Returns
    -------
    list[Route]
        Extracted routes, capped at 100 per file.
    """
    file_path = Path(file_path)
    file_path_str = str(file_path)

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning("Cannot read file: %s", file_path)
        return []

    if not content.strip():
        return []

    lines = content.splitlines()
    routes: list[Route] = []

    # Pure regex languages (no tree-sitter needed).
    if language == "graphql":
        routes = _extract_graphql_schema(content, file_path_str)
    elif language == "protobuf":
        routes = _extract_grpc_proto(content, file_path_str)
    elif language in ("python",):
        routes = _extract_python_routes(content, file_path_str, lines)
    elif language in ("typescript", "javascript"):
        routes = _extract_ts_routes(content, file_path_str, lines)
    elif language == "go":
        routes = _extract_go_routes(content, file_path_str)
    elif language in ("java", "kotlin"):
        routes = _extract_spring_regex(content, file_path_str, lines)
    else:
        # Unknown language -- return empty gracefully.
        logger.debug("Unsupported language for route extraction: %s", language)
        return []

    # Apply safety cap.
    if len(routes) > _MAX_ROUTES_PER_FILE:
        logger.info(
            "Route cap hit: %d routes in %s, truncating to %d",
            len(routes),
            file_path,
            _MAX_ROUTES_PER_FILE,
        )
        routes = routes[:_MAX_ROUTES_PER_FILE]

    return routes
