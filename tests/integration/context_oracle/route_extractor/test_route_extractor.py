"""Tests for beadloom.context_oracle.route_extractor — API route extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.route_extractor import Route, extract_routes

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _routes_by_framework(routes: list[Route], framework: str) -> list[Route]:
    return [r for r in routes if r.framework == framework]


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------


class TestFastAPI:
    def test_basic_get(self, tmp_path: Path) -> None:
        f = tmp_path / "main.py"
        f.write_text(
            "from fastapi import FastAPI\n"
            "\n"
            "app = FastAPI()\n"
            "\n"
            '@app.get("/users")\n'
            "async def list_users():\n"
            "    return []\n"
        )
        routes = extract_routes(f, "python")
        assert len(routes) >= 1
        r = routes[0]
        assert r.method == "GET"
        assert r.path == "/users"
        assert r.handler == "list_users"
        assert r.framework == "fastapi"
        assert r.line > 0

    def test_multiple_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "api.py"
        f.write_text(
            "from fastapi import FastAPI\n"
            "\n"
            "app = FastAPI()\n"
            "\n"
            '@app.get("/items")\n'
            "def get_items():\n"
            "    pass\n"
            "\n"
            '@app.post("/items")\n'
            "def create_item():\n"
            "    pass\n"
            "\n"
            '@app.put("/items/{item_id}")\n'
            "def update_item():\n"
            "    pass\n"
            "\n"
            '@app.delete("/items/{item_id}")\n'
            "def delete_item():\n"
            "    pass\n"
        )
        routes = extract_routes(f, "python")
        methods = {r.method for r in routes}
        assert methods == {"GET", "POST", "PUT", "DELETE"}
        assert len(routes) == 4

    def test_router_prefix(self, tmp_path: Path) -> None:
        f = tmp_path / "routes.py"
        f.write_text(
            "from fastapi import APIRouter\n"
            "\n"
            "router = APIRouter()\n"
            "\n"
            '@router.get("/health")\n'
            "def health_check():\n"
            '    return {"status": "ok"}\n'
        )
        routes = extract_routes(f, "python")
        assert len(routes) >= 1
        assert routes[0].path == "/health"
        assert routes[0].framework == "fastapi"


# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------


class TestFlask:
    def test_app_route(self, tmp_path: Path) -> None:
        f = tmp_path / "app.py"
        f.write_text(
            "from flask import Flask\n"
            "\n"
            "app = Flask(__name__)\n"
            "\n"
            '@app.route("/login", methods=["POST"])\n'
            "def login():\n"
            "    pass\n"
        )
        routes = extract_routes(f, "python")
        assert len(routes) >= 1
        r = routes[0]
        assert r.path == "/login"
        assert r.handler == "login"
        assert r.framework == "flask"

    def test_blueprint_route(self, tmp_path: Path) -> None:
        f = tmp_path / "views.py"
        f.write_text(
            "from flask import Blueprint\n"
            "\n"
            'bp = Blueprint("auth", __name__)\n'
            "\n"
            '@bp.route("/register", methods=["POST"])\n'
            "def register():\n"
            "    pass\n"
        )
        routes = extract_routes(f, "python")
        assert len(routes) >= 1
        assert routes[0].path == "/register"
        assert routes[0].framework == "flask"

    def test_flask_methods_list(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        f.write_text(
            "from flask import Flask\n"
            "\n"
            "app = Flask(__name__)\n"
            "\n"
            '@app.route("/data", methods=["GET", "POST"])\n'
            "def handle_data():\n"
            "    pass\n"
        )
        routes = extract_routes(f, "python")
        assert len(routes) >= 1
        # Should capture at least GET or POST
        methods = {r.method for r in routes}
        assert methods & {"GET", "POST"}


# ---------------------------------------------------------------------------
# Express
# ---------------------------------------------------------------------------


class TestExpress:
    def test_router_get(self, tmp_path: Path) -> None:
        f = tmp_path / "routes.ts"
        f.write_text(
            'import { Router } from "express";\n'
            "\n"
            "const router = Router();\n"
            "\n"
            'router.get("/api/users", getUsers);\n'
        )
        routes = extract_routes(f, "typescript")
        assert len(routes) >= 1
        r = routes[0]
        assert r.method == "GET"
        assert r.path == "/api/users"
        assert r.framework == "express"

    def test_app_post(self, tmp_path: Path) -> None:
        f = tmp_path / "server.ts"
        f.write_text(
            'import express from "express";\n'
            "\n"
            "const app = express();\n"
            "\n"
            'app.post("/api/login", handleLogin);\n'
        )
        routes = extract_routes(f, "typescript")
        assert len(routes) >= 1
        assert routes[0].method == "POST"
        assert routes[0].path == "/api/login"

    def test_express_js_file(self, tmp_path: Path) -> None:
        f = tmp_path / "routes.js"
        f.write_text(
            'const router = require("express").Router();\n'
            "\n"
            'router.get("/health", (req, res) => res.json({ ok: true }));\n'
        )
        routes = extract_routes(f, "javascript")
        assert len(routes) >= 1
        assert routes[0].path == "/health"


# ---------------------------------------------------------------------------
# NestJS
# ---------------------------------------------------------------------------


class TestNestJS:
    def test_get_decorator(self, tmp_path: Path) -> None:
        f = tmp_path / "users.controller.ts"
        f.write_text(
            'import { Controller, Get, Post } from "@nestjs/common";\n'
            "\n"
            '@Controller("users")\n'
            "export class UsersController {\n"
            "  @Get()\n"
            "  findAll() {\n"
            "    return [];\n"
            "  }\n"
            "\n"
            "  @Post()\n"
            "  create() {\n"
            "    return {};\n"
            "  }\n"
            "}\n"
        )
        routes = extract_routes(f, "typescript")
        nest_routes = _routes_by_framework(routes, "nestjs")
        assert len(nest_routes) >= 2
        methods = {r.method for r in nest_routes}
        assert "GET" in methods
        assert "POST" in methods

    def test_get_with_path(self, tmp_path: Path) -> None:
        f = tmp_path / "cats.controller.ts"
        f.write_text(
            'import { Controller, Get } from "@nestjs/common";\n'
            "\n"
            '@Controller("cats")\n'
            "export class CatsController {\n"
            '  @Get(":id")\n'
            "  findOne() {\n"
            "    return {};\n"
            "  }\n"
            "}\n"
        )
        routes = extract_routes(f, "typescript")
        nest_routes = _routes_by_framework(routes, "nestjs")
        assert len(nest_routes) >= 1
        assert nest_routes[0].method == "GET"


# ---------------------------------------------------------------------------
# Spring Boot
# ---------------------------------------------------------------------------


class TestSpringBoot:
    def test_get_mapping(self, tmp_path: Path) -> None:
        f = tmp_path / "UserController.java"
        f.write_text(
            "package com.example.demo;\n"
            "\n"
            "import org.springframework.web.bind.annotation.*;\n"
            "\n"
            "@RestController\n"
            '@RequestMapping("/api/users")\n'
            "public class UserController {\n"
            "\n"
            "    @GetMapping\n"
            "    public List<User> getUsers() {\n"
            "        return userService.findAll();\n"
            "    }\n"
            "\n"
            "    @PostMapping\n"
            "    public User createUser(@RequestBody User user) {\n"
            "        return userService.save(user);\n"
            "    }\n"
            "}\n"
        )
        routes = extract_routes(f, "java")
        spring_routes = _routes_by_framework(routes, "spring")
        assert len(spring_routes) >= 2
        methods = {r.method for r in spring_routes}
        assert "GET" in methods
        assert "POST" in methods

    def test_request_mapping_with_method(self, tmp_path: Path) -> None:
        f = tmp_path / "ApiController.java"
        f.write_text(
            "package com.example;\n"
            "\n"
            "import org.springframework.web.bind.annotation.*;\n"
            "\n"
            "@RestController\n"
            "public class ApiController {\n"
            "\n"
            '    @RequestMapping(value = "/status", method = RequestMethod.GET)\n'
            "    public String status() {\n"
            '        return "ok";\n'
            "    }\n"
            "}\n"
        )
        routes = extract_routes(f, "java")
        spring_routes = _routes_by_framework(routes, "spring")
        assert len(spring_routes) >= 1
        assert spring_routes[0].path == "/status"


# ---------------------------------------------------------------------------
# Gin (Go)
# ---------------------------------------------------------------------------


class TestGin:
    def test_gin_get(self, tmp_path: Path) -> None:
        f = tmp_path / "main.go"
        f.write_text(
            "package main\n"
            "\n"
            'import "github.com/gin-gonic/gin"\n'
            "\n"
            "func main() {\n"
            "    r := gin.Default()\n"
            '    r.GET("/ping", pingHandler)\n'
            '    r.POST("/users", createUser)\n'
            "    r.Run()\n"
            "}\n"
        )
        routes = extract_routes(f, "go")
        gin_routes = _routes_by_framework(routes, "gin")
        assert len(gin_routes) >= 2
        methods = {r.method for r in gin_routes}
        assert "GET" in methods
        assert "POST" in methods

    def test_gin_group(self, tmp_path: Path) -> None:
        f = tmp_path / "routes.go"
        f.write_text(
            "package main\n"
            "\n"
            'import "github.com/gin-gonic/gin"\n'
            "\n"
            "func setupRoutes(r *gin.Engine) {\n"
            '    r.GET("/health", healthCheck)\n'
            "}\n"
        )
        routes = extract_routes(f, "go")
        gin_routes = _routes_by_framework(routes, "gin")
        assert len(gin_routes) >= 1
        assert gin_routes[0].path == "/health"


# ---------------------------------------------------------------------------
# Echo (Go)
# ---------------------------------------------------------------------------


class TestEcho:
    def test_echo_get(self, tmp_path: Path) -> None:
        f = tmp_path / "server.go"
        f.write_text(
            "package main\n"
            "\n"
            'import "github.com/labstack/echo/v4"\n'
            "\n"
            "func main() {\n"
            "    e := echo.New()\n"
            '    e.GET("/users", getUsers)\n'
            '    e.POST("/users", createUser)\n'
            '    e.Start(":8080")\n'
            "}\n"
        )
        routes = extract_routes(f, "go")
        echo_routes = _routes_by_framework(routes, "echo")
        assert len(echo_routes) >= 2

    def test_echo_delete(self, tmp_path: Path) -> None:
        f = tmp_path / "api.go"
        f.write_text(
            "package main\n"
            "\n"
            'import "github.com/labstack/echo/v4"\n'
            "\n"
            "func setup(e *echo.Echo) {\n"
            '    e.DELETE("/users/:id", deleteUser)\n'
            "}\n"
        )
        routes = extract_routes(f, "go")
        echo_routes = _routes_by_framework(routes, "echo")
        assert len(echo_routes) >= 1
        assert echo_routes[0].method == "DELETE"


# ---------------------------------------------------------------------------
# Fiber (Go)
# ---------------------------------------------------------------------------


class TestFiber:
    def test_fiber_get(self, tmp_path: Path) -> None:
        f = tmp_path / "main.go"
        f.write_text(
            "package main\n"
            "\n"
            'import "github.com/gofiber/fiber/v2"\n'
            "\n"
            "func main() {\n"
            "    app := fiber.New()\n"
            '    app.Get("/api/items", getItems)\n'
            '    app.Post("/api/items", createItem)\n'
            '    app.Listen(":3000")\n'
            "}\n"
        )
        routes = extract_routes(f, "go")
        fiber_routes = _routes_by_framework(routes, "fiber")
        assert len(fiber_routes) >= 2

    def test_fiber_put(self, tmp_path: Path) -> None:
        f = tmp_path / "routes.go"
        f.write_text(
            "package main\n"
            "\n"
            'import "github.com/gofiber/fiber/v2"\n'
            "\n"
            "func setup(app *fiber.App) {\n"
            '    app.Put("/items/:id", updateItem)\n'
            "}\n"
        )
        routes = extract_routes(f, "go")
        fiber_routes = _routes_by_framework(routes, "fiber")
        assert len(fiber_routes) >= 1
        assert fiber_routes[0].method == "PUT"


# ---------------------------------------------------------------------------
# GraphQL schema (.graphql / .gql)
# ---------------------------------------------------------------------------


class TestGraphQLSchema:
    def test_query_fields(self, tmp_path: Path) -> None:
        f = tmp_path / "schema.graphql"
        f.write_text(
            "type Query {\n"
            "  users: [User!]!\n"
            "  user(id: ID!): User\n"
            "}\n"
            "\n"
            "type Mutation {\n"
            "  createUser(input: CreateUserInput!): User!\n"
            "}\n"
        )
        routes = extract_routes(f, "graphql")
        assert len(routes) >= 3
        queries = [r for r in routes if r.method == "QUERY"]
        mutations = [r for r in routes if r.method == "MUTATION"]
        assert len(queries) >= 2
        assert len(mutations) >= 1
        assert routes[0].framework == "graphql_schema"

    def test_subscription(self, tmp_path: Path) -> None:
        f = tmp_path / "schema.gql"
        f.write_text("type Subscription {\n  messageAdded(channelId: ID!): Message!\n}\n")
        routes = extract_routes(f, "graphql")
        subs = [r for r in routes if r.method == "SUBSCRIPTION"]
        assert len(subs) >= 1
        assert subs[0].path == "messageAdded"

    def test_gql_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "api.gql"
        f.write_text("type Query {\n  hello: String!\n}\n")
        routes = extract_routes(f, "graphql")
        assert len(routes) >= 1


# ---------------------------------------------------------------------------
# GraphQL code-first Python (Strawberry, Ariadne)
# ---------------------------------------------------------------------------


class TestGraphQLPython:
    def test_strawberry_query(self, tmp_path: Path) -> None:
        f = tmp_path / "schema.py"
        f.write_text(
            "import strawberry\n"
            "\n"
            "@strawberry.type\n"
            "class Query:\n"
            "    @strawberry.field\n"
            "    def users(self) -> list[User]:\n"
            "        return []\n"
        )
        routes = extract_routes(f, "python")
        gql_routes = _routes_by_framework(routes, "graphql_python")
        assert len(gql_routes) >= 1

    def test_ariadne_query_type(self, tmp_path: Path) -> None:
        f = tmp_path / "resolvers.py"
        f.write_text(
            "from ariadne import QueryType\n"
            "\n"
            "query = QueryType()\n"
            "\n"
            '@query.field("users")\n'
            "def resolve_users(_, info):\n"
            "    return []\n"
        )
        routes = extract_routes(f, "python")
        gql_routes = _routes_by_framework(routes, "graphql_python")
        assert len(gql_routes) >= 1


# ---------------------------------------------------------------------------
# GraphQL code-first TypeScript (TypeGraphQL)
# ---------------------------------------------------------------------------


class TestGraphQLTypeScript:
    def test_typegraphql_query(self, tmp_path: Path) -> None:
        f = tmp_path / "resolver.ts"
        f.write_text(
            'import { Resolver, Query, Mutation } from "type-graphql";\n'
            "\n"
            "@Resolver()\n"
            "class UserResolver {\n"
            "  @Query(() => [User])\n"
            "  async users() {\n"
            "    return [];\n"
            "  }\n"
            "\n"
            "  @Mutation(() => User)\n"
            "  async createUser() {\n"
            "    return {};\n"
            "  }\n"
            "}\n"
        )
        routes = extract_routes(f, "typescript")
        gql_routes = _routes_by_framework(routes, "graphql_ts")
        assert len(gql_routes) >= 2

    def test_typegraphql_resolver_decorator(self, tmp_path: Path) -> None:
        f = tmp_path / "posts.resolver.ts"
        f.write_text(
            'import { Resolver, Query } from "type-graphql";\n'
            "\n"
            "@Resolver()\n"
            "class PostResolver {\n"
            "  @Query(() => [Post])\n"
            "  async posts() {\n"
            "    return [];\n"
            "  }\n"
            "}\n"
        )
        routes = extract_routes(f, "typescript")
        gql_routes = _routes_by_framework(routes, "graphql_ts")
        assert len(gql_routes) >= 1


# ---------------------------------------------------------------------------
# gRPC (.proto)
# ---------------------------------------------------------------------------


class TestGRPC:
    def test_service_rpc(self, tmp_path: Path) -> None:
        f = tmp_path / "auth.proto"
        f.write_text(
            'syntax = "proto3";\n'
            "\n"
            "package auth;\n"
            "\n"
            "service AuthService {\n"
            "  rpc Login(LoginRequest) returns (LoginResponse);\n"
            "  rpc Register(RegisterRequest) returns (RegisterResponse);\n"
            "}\n"
        )
        routes = extract_routes(f, "protobuf")
        grpc_routes = _routes_by_framework(routes, "grpc")
        assert len(grpc_routes) >= 2
        assert grpc_routes[0].method == "RPC"
        assert "AuthService" in grpc_routes[0].path

    def test_multiple_services(self, tmp_path: Path) -> None:
        f = tmp_path / "api.proto"
        f.write_text(
            'syntax = "proto3";\n'
            "\n"
            "service UserService {\n"
            "  rpc GetUser(GetUserRequest) returns (User);\n"
            "}\n"
            "\n"
            "service OrderService {\n"
            "  rpc CreateOrder(CreateOrderRequest) returns (Order);\n"
            "}\n"
        )
        routes = extract_routes(f, "protobuf")
        grpc_routes = _routes_by_framework(routes, "grpc")
        assert len(grpc_routes) >= 2
        paths = {r.path for r in grpc_routes}
        assert any("UserService" in p for p in paths)
        assert any("OrderService" in p for p in paths)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        routes = extract_routes(f, "python")
        assert routes == []

    def test_no_routes(self, tmp_path: Path) -> None:
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 42\n\nclass Config:\n    pass\n")
        routes = extract_routes(f, "python")
        assert routes == []

    def test_100_route_cap(self, tmp_path: Path) -> None:
        """Safety limit: at most 100 routes per file."""
        lines = ["from fastapi import FastAPI\n", "app = FastAPI()\n"]
        for i in range(120):
            lines.append(f'@app.get("/route{i}")\n')
            lines.append(f"def handler_{i}():\n")
            lines.append("    pass\n\n")
        f = tmp_path / "many_routes.py"
        f.write_text("".join(lines))
        routes = extract_routes(f, "python")
        assert len(routes) <= 100

    def test_file_path_stored(self, tmp_path: Path) -> None:
        f = tmp_path / "api.py"
        f.write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "\n"
            '@app.get("/test")\n'
            "def test_endpoint():\n"
            "    pass\n"
        )
        routes = extract_routes(f, "python")
        assert len(routes) >= 1
        assert routes[0].file_path == str(f)

    def test_graceful_fallback_unknown_language(self, tmp_path: Path) -> None:
        """Unknown language should return empty list, not raise."""
        f = tmp_path / "unknown.xyz"
        f.write_text("some content\n")
        routes = extract_routes(f, "unknown")
        assert routes == []

    def test_route_dataclass_is_frozen(self) -> None:
        r = Route(
            method="GET",
            path="/test",
            handler="handler",
            file_path="test.py",
            line=1,
            framework="fastapi",
        )
        with pytest.raises(AttributeError):
            r.method = "POST"  # type: ignore[misc]

    def test_graphql_empty_schema(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.graphql"
        f.write_text("# Just a comment\n")
        routes = extract_routes(f, "graphql")
        assert routes == []

    def test_proto_no_service(self, tmp_path: Path) -> None:
        f = tmp_path / "messages.proto"
        f.write_text(
            'syntax = "proto3";\n\nmessage User {\n  string name = 1;\n  int32 age = 2;\n}\n'
        )
        routes = extract_routes(f, "protobuf")
        assert routes == []


# ---------------------------------------------------------------------------
# Self-exclusion (Issue #29 part 1)
# ---------------------------------------------------------------------------


class TestSelfExclusion:
    """Route extractor should skip its own module files."""

    def test_skip_route_extractor_file(self, tmp_path: Path) -> None:
        """Files with 'route_extractor' in the path should return empty."""
        # The actual route_extractor.py has comment examples like:
        #   # Ariadne @query.field("name")
        # which match the Ariadne regex and produce false positives
        pkg = tmp_path / "context_oracle"
        pkg.mkdir()
        f = pkg / "route_extractor.py"
        f.write_text(
            "import re\n"
            "\n"
            '# Ariadne @query.field("name")\n'
            "# These trigger GraphQL detection:\n"
            "if 'QueryType' in content or 'MutationType' in content:\n"
            "    pass\n"
            "\n"
            "def extract_routes(file_path, language):\n"
            "    pass\n"
        )
        routes = extract_routes(f, "python")
        assert routes == []

    def test_non_route_extractor_file_not_skipped(self, tmp_path: Path) -> None:
        """Normal files should still have routes extracted."""
        f = tmp_path / "api.py"
        f.write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "\n"
            '@app.get("/health")\n'
            "def health():\n"
            "    pass\n"
        )
        routes = extract_routes(f, "python")
        assert len(routes) >= 1


# ---------------------------------------------------------------------------
# Route formatting (Issue #30)
# ---------------------------------------------------------------------------


class TestRouteFormatting:
    """Test route formatting helpers."""

    def test_format_routes_separates_graphql(self) -> None:
        """GraphQL routes should be in a separate section from HTTP routes."""
        from beadloom.context_oracle.route_extractor import format_routes_for_display

        routes_data = [
            {
                "method": "GET", "path": "/api/users",
                "handler": "list_users", "framework": "fastapi",
            },
            {
                "method": "POST", "path": "/api/users",
                "handler": "create_user", "framework": "fastapi",
            },
            {
                "method": "QUERY", "path": "users",
                "handler": "users", "framework": "graphql_schema",
            },
            {
                "method": "MUTATION", "path": "createUser",
                "handler": "createUser", "framework": "graphql_schema",
            },
        ]
        result = format_routes_for_display(routes_data)
        # HTTP and GraphQL should be in separate sections
        assert "HTTP" in result or "Routes" in result
        assert "GraphQL" in result

    def test_format_routes_empty(self) -> None:
        """Empty routes list returns empty string."""
        from beadloom.context_oracle.route_extractor import format_routes_for_display

        result = format_routes_for_display([])
        assert result == ""

    def test_format_routes_only_graphql(self) -> None:
        """Only GraphQL routes should show GraphQL section only."""
        from beadloom.context_oracle.route_extractor import format_routes_for_display

        routes_data = [
            {
                "method": "QUERY", "path": "users",
                "handler": "users", "framework": "graphql_schema",
            },
        ]
        result = format_routes_for_display(routes_data)
        assert "GraphQL" in result
        # Should not have an HTTP section header
        assert "HTTP" not in result

    def test_format_routes_wider_path_column(self) -> None:
        """Long paths should not be truncated (wider column)."""
        from beadloom.context_oracle.route_extractor import format_routes_for_display

        routes_data = [
            {
                "method": "GET",
                "path": "/api/v2/organizations/{org_id}/projects/{proj_id}/settings",
                "handler": "get_settings",
                "framework": "fastapi",
            },
        ]
        result = format_routes_for_display(routes_data)
        assert "/api/v2/organizations/{org_id}/projects/{proj_id}/settings" in result
