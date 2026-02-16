# RFC: BDL-017 — Beadloom v1.6 Technical Specification

**Status:** Approved (2026-02-16)
**Created:** 2026-02-16
**Reference:** STRATEGY-2.md §4-5, PRD BDL-017

---

## 1. Overview

Two parallel phases delivering v1.6:
- **Phase 10** — Deep Code Analysis: API routes, git activity, test mapping, rule severity, enriched polish
- **Phase 11** — Agent Infrastructure: MCP lint/why/diff, context cost metrics, deep config reading

Phase 10 and 11 are largely independent. Within Phase 10, tasks 10.1-10.4 are independent; 10.5 depends on 10.1-10.3.

---

## 2. Phase 10: Deep Code Analysis

### 2.1 API Surface Extraction (10.1)

**Current state:**
- `code_indexer.py` extracts symbols via tree-sitter (13 languages)
- `scanner.py:_detect_framework_summary()` detects 18+ frameworks
- `code_symbols.kind` already includes `'route'` in the schema
- `nodes.extra` JSON stores `entry_points`, `tech_stack` — integration point for routes

**Implementation:**

New module: `src/beadloom/context_oracle/route_extractor.py`

```python
@dataclass(frozen=True)
class Route:
    method: str          # GET, POST, PUT, DELETE, PATCH, *
    path: str            # /api/login, /users/{id}
    handler: str         # function name
    file_path: str       # relative path
    line: int            # line number
    framework: str       # fastapi, flask, express, nestjs, spring, gin, echo, fiber

def extract_routes(file_path: Path, language: str) -> list[Route]:
    """Extract API routes from source file using tree-sitter + regex."""
```

**Framework-specific patterns:**

| Framework | Language | Pattern | Example |
|-----------|----------|---------|---------|
| FastAPI | Python | `@app.get/post/put/delete("/path")` | `@app.post("/api/login")` |
| Flask | Python | `@app.route("/path", methods=[...])` | `@bp.route("/users", methods=["GET"])` |
| Express | TS/JS | `router.get/post("/path", handler)` | `app.get("/api/me", getMe)` |
| NestJS | TS | `@Get/@Post/@Put/@Delete("/path")` | `@Post("login")` |
| Spring Boot | Java/Kt | `@GetMapping/@PostMapping("/path")` | `@GetMapping("/api/users")` |
| Gin | Go | `r.GET/POST("/path", handler)` | `r.POST("/api/login", loginHandler)` |
| Echo | Go | `e.GET/POST("/path", handler)` | `e.GET("/users/:id", getUser)` |
| Fiber | Go | `app.Get/Post("/path", handler)` | `app.Post("/auth", authHandler)` |
| GraphQL (schema) | `.graphql`/`.gql` | `type Query/Mutation { field(...) }` | `type Query { user(id: ID!): User }` |
| GraphQL (code-first) | Python | `@strawberry.type/mutation`, Ariadne `QueryType` | `@strawberry.mutation` |
| GraphQL (code-first) | TS | `@Query()/@Mutation()/@Resolver()` | TypeGraphQL, Apollo Server |
| gRPC | `.proto` | `service X { rpc Y(Req) returns (Resp) }` | `service Auth { rpc Login(...) }` |

**Method types for non-REST:**
- GraphQL: `QUERY`, `MUTATION`, `SUBSCRIPTION`
- gRPC: `RPC`

**Extraction approach:** Two-pass:
1. **tree-sitter AST** — find decorator/call nodes matching framework patterns
2. **Regex fallback** — for frameworks where tree-sitter queries are complex (Spring annotations, `.proto`/`.graphql` schema files)

**Storage:** Routes stored in `nodes.extra` JSON:
```json
{
  "routes": [
    {"method": "POST", "path": "/api/login", "handler": "login", "file": "auth/routes.py", "line": 42},
    {"method": "GET", "path": "/api/me", "handler": "get_me", "file": "auth/routes.py", "line": 58},
    {"method": "QUERY", "path": "user", "handler": "resolve_user", "file": "schema.graphql", "line": 5},
    {"method": "MUTATION", "path": "createUser", "handler": "create_user", "file": "auth/resolvers.py", "line": 12},
    {"method": "RPC", "path": "Auth/Login", "handler": "Login", "file": "auth.proto", "line": 8}
  ]
}
```

**Context bundle integration:**
- `build_context_bundle()` in `context_oracle/builder.py` reads `nodes.extra.routes`
- Renders as "API Routes:" section in Markdown output
- JSON output includes `routes` array

**Reindex integration:**
- `_index_code_symbols()` in `reindex.py` calls `extract_routes()` after symbol extraction
- Routes stored in `nodes.extra` via `_update_node_extra()` helper

---

### 2.2 Git History Analysis (10.2)

**Current state:** No git integration. Only file-level hashing in `file_index`.

**Implementation:**

New module: `src/beadloom/infrastructure/git_activity.py`

```python
@dataclass(frozen=True)
class GitActivity:
    commits_30d: int          # commits in last 30 days
    commits_90d: int          # commits in last 90 days
    last_commit_date: str     # ISO 8601
    top_contributors: list[str]  # top 3 by commit count
    activity_level: str       # hot | warm | cold | dormant

def analyze_git_activity(
    project_root: Path,
    source_dirs: dict[str, str],  # ref_id -> source_path
) -> dict[str, GitActivity]:
    """Analyze git history for each node's source directory."""
```

**Activity classification:**
| Level | Criteria |
|-------|----------|
| `hot` | >20 commits in 30 days |
| `warm` | 5-20 commits in 30 days |
| `cold` | 1-4 commits in 30 days |
| `dormant` | 0 commits in 90 days |

**Git command:**
```bash
git log --format="%H %aI" --name-only --since="90 days ago"
```
Single invocation, parse output to map files → directories → nodes.

**Storage:** In `nodes.extra`:
```json
{
  "activity": {
    "level": "hot",
    "commits_30d": 45,
    "commits_90d": 120,
    "last_commit": "2026-02-15",
    "top_contributors": ["alice", "bob", "charlie"]
  }
}
```

**Context bundle integration:**
- Rendered as "Activity: hot (45 commits/30d)" in Markdown
- JSON includes `activity` object

**Graceful degradation:** If not a git repo or git not available, skip silently. Activity = null.

---

### 2.3 Test Mapping (10.3)

**Current state:** Tests excluded from bootstrap entirely (`_RECURSIVE_SKIP` includes `.pytest_cache`; test dirs not scanned for symbols).

**Implementation:**

New module: `src/beadloom/context_oracle/test_mapper.py`

```python
@dataclass(frozen=True)
class TestMapping:
    framework: str              # pytest, jest, go_test, junit, xctest
    test_files: list[str]       # relative paths
    test_count: int             # number of test functions/methods
    coverage_estimate: str      # high | medium | low | none

def map_tests(
    project_root: Path,
    source_dirs: dict[str, str],  # ref_id -> source_path
) -> dict[str, TestMapping]:
    """Map test files to source nodes."""
```

**Framework detection:**

| Framework | Language | Detection |
|-----------|----------|-----------|
| pytest | Python | `conftest.py`, `test_*.py`, `*_test.py` |
| jest | TS/JS | `jest.config.*`, `*.test.ts`, `*.spec.ts`, `__tests__/` |
| go test | Go | `*_test.go` |
| JUnit | Java/Kt | `src/test/`, `*Test.java`, `*Test.kt` |
| XCTest | Swift | `*Tests.swift`, `*Tests/` |

**Mapping logic:**
1. Detect test framework from project root markers
2. Find test files matching framework patterns
3. Map test file → source module by:
   - **Naming convention:** `test_auth.py` → `auth/` module
   - **Import analysis:** test file imports from `auth.service` → `auth` node
   - **Directory proximity:** `tests/auth/` → `auth` node

**Coverage estimate:**
| Level | Criteria |
|-------|----------|
| `high` | >3 test files per module |
| `medium` | 1-3 test files |
| `low` | 0 test files, but framework detected |
| `none` | no framework detected |

**Storage:** In `nodes.extra`:
```json
{
  "tests": {
    "framework": "pytest",
    "test_files": ["tests/test_auth.py", "tests/test_auth_service.py"],
    "test_count": 15,
    "coverage_estimate": "high"
  }
}
```

---

### 2.4 Rule Severity Levels (10.4)

**Current state:**
- `rule_engine.py` has `DenyRule` and `RequireRule` — both binary (violation or not)
- `Violation` dataclass has `rule_type: str` but no severity
- `rules.yml` format v1 has no severity field
- `lint --strict` exits 1 on any violation

**Implementation:**

**Rules YAML v2:**
```yaml
version: 2
rules:
  - name: domain-needs-parent
    description: Every domain must be part_of the beadloom service
    severity: error          # NEW: error (default) | warn
    require:
      for: {kind: domain}
      has_edge_to: {}
      edge_kind: part_of

  - name: no-cross-domain-deps
    description: Domains should not depend on other domains directly
    severity: warn           # NEW: won't fail --strict
    deny:
      for: {kind: domain}
      has_edge_to: {kind: domain}
      edge_kind: depends_on
```

**Backward compatibility:** `version: 1` rules default to `severity: error`.

**Violation dataclass:**
```python
@dataclass(frozen=True)
class Violation:
    rule_name: str
    rule_description: str
    rule_type: str          # deny | require
    severity: str           # NEW: error | warn
    src_ref_id: str
    dst_ref_id: str | None
    message: str
```

**CLI behavior:**
- `beadloom lint` — shows all violations, exits 0
- `beadloom lint --strict` — exits 1 only if **error** violations exist
- `beadloom lint --strict --fail-on-warn` — exits 1 on any violation (old behavior)

**Output format:**
```
⛔ [ERROR] domain-needs-parent: auth has no part_of edge
⚠️  [WARN]  no-cross-domain-deps: auth depends_on billing

Errors: 1, Warnings: 1
```

---

### 2.5 Smart Docs Polish (10.5)

**Current state:**
- `generate_polish_data()` returns nodes with symbols, deps, used_by, doc_status, symbol drift
- No routes, activity, or test data included

**Implementation:**

Extend `generate_polish_data()` in `doc_generator.py`:

```python
def generate_polish_data(project_root: Path, ...) -> dict:
    # ... existing logic ...

    for node in nodes:
        # NEW: Add routes from nodes.extra
        extra = json.loads(node.get("extra", "{}"))
        if "routes" in extra:
            node_data["routes"] = extra["routes"]

        # NEW: Add activity from nodes.extra
        if "activity" in extra:
            node_data["activity"] = extra["activity"]

        # NEW: Add test mapping from nodes.extra
        if "tests" in extra:
            node_data["tests"] = extra["tests"]
```

**Text format enhancements:**
```
## AUTH (domain) — FastAPI service: JWT authentication
Activity: 🔥 hot (45 commits/30d, last: 2026-02-15)
Tests: pytest, 15 tests in 3 files (high coverage)
Routes:
  POST /api/login       → login()          auth/routes.py:42
  GET  /api/me          → get_me()         auth/routes.py:58
  PUT  /api/users/{id}  → update_user()    auth/routes.py:73
Symbols: 5 classes, 12 functions
  ⚠ Symbol drift: 2 added, 1 removed since last doc sync
Dependencies: billing, notification
```

---

## 3. Phase 11: Agent Infrastructure

### 3.1 MCP Tool: lint (11.1)

**Current state:** `lint` exists as CLI command (cli.py:1654). Not available via MCP.

**Implementation:** Add to `mcp_server.py`:

```python
mcp.Tool(
    name="lint",
    description="Run architecture lint rules. Returns violations as JSON.",
    inputSchema={
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["all", "error", "warn"],
                "description": "Filter by severity (default: all)",
            },
        },
    },
)
```

**Response format:**
```json
{
  "violations": [
    {
      "rule": "domain-needs-parent",
      "severity": "error",
      "src": "auth",
      "dst": null,
      "message": "auth has no part_of edge"
    }
  ],
  "summary": {"errors": 1, "warnings": 0, "rules_evaluated": 4}
}
```

### 3.2 MCP Tool: why (11.2)

**Current state:** `why` exists as CLI command (cli.py:1471). Returns upstream/downstream deps.

**Implementation:** Add to `mcp_server.py`:

```python
mcp.Tool(
    name="why",
    description="Impact analysis: show upstream dependencies and downstream dependents for a node.",
    inputSchema={
        "type": "object",
        "properties": {
            "ref_id": {"type": "string", "description": "Node reference ID"},
        },
        "required": ["ref_id"],
    },
)
```

**Response:** Structured JSON with `upstream`, `downstream`, `impact_summary`.

### 3.3 MCP Tool: diff (11.3)

**Current state:** `diff` exists as CLI command (cli.py:1512). Shows graph changes since commit.

**Implementation:** Add to `mcp_server.py`:

```python
mcp.Tool(
    name="diff",
    description="Show graph changes since a git ref (commit, branch, tag).",
    inputSchema={
        "type": "object",
        "properties": {
            "since": {"type": "string", "description": "Git ref (default: HEAD~1)"},
        },
    },
)
```

### 3.4 Context Cost Metrics (11.4)

**Current state:** No token counting. `beadloom status` shows node/edge/doc counts.

**Implementation:**

Add to `beadloom status`:
```
Context Metrics:
  Avg bundle size: ~1,200 tokens (vs ~150K raw grep)
  Largest bundle: AUTH — 2,400 tokens
  Total indexed: 274 symbols across 9 languages
```

Token estimation: `len(text) / 4` (rough tokens ≈ chars/4 for English/code).

### 3.5 Deep Config Reading (11.5)

**Current state:** `scan_project()` reads basic manifest info. No deep config extraction.

**Implementation:**

Extend `scanner.py` or new module `src/beadloom/onboarding/config_reader.py`:

```python
def read_deep_config(project_root: Path) -> dict[str, Any]:
    """Extract scripts, workspaces, path aliases from project configs."""
    # pyproject.toml → scripts, build-system, tool.pytest, tool.ruff
    # package.json → scripts, workspaces, engines
    # tsconfig.json → paths, baseUrl, compilerOptions
    # Cargo.toml → workspace members, features
    # build.gradle → plugins, dependencies
```

Store in `nodes.extra` on root node:
```json
{
  "config": {
    "scripts": {"test": "pytest", "lint": "ruff check ."},
    "workspaces": ["packages/*"],
    "path_aliases": {"@/": "src/"}
  }
}
```

---

## 4. Database Changes

**No new tables.** All new data stored in existing `nodes.extra` JSON column.

**Schema changes:**
- `rules.yml` format: `version: 1` → `version: 2` (backward compatible)
- `Violation` dataclass: add `severity: str` field

---

## 5. New Files

| File | Purpose |
|------|---------|
| `src/beadloom/context_oracle/route_extractor.py` | API route extraction |
| `src/beadloom/infrastructure/git_activity.py` | Git history analysis |
| `src/beadloom/context_oracle/test_mapper.py` | Test file ↔ module mapping |
| `src/beadloom/onboarding/config_reader.py` | Deep config reading |
| `tests/test_route_extractor.py` | Route extraction tests |
| `tests/test_git_activity.py` | Git activity tests |
| `tests/test_test_mapper.py` | Test mapping tests |
| `tests/test_config_reader.py` | Config reader tests |
| `tests/test_mcp_new_tools.py` | MCP lint/why/diff tests |

---

## 6. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| tree-sitter route queries fragile across frameworks | Regex fallback for each framework |
| Git subprocess slow on large repos | Limit to 90 days, single `git log` invocation |
| Test mapping false positives | Conservative naming + import-based mapping |
| Rule severity breaks existing CI | Default `severity: error`, backward compatible v1→v2 |
| `nodes.extra` JSON growing large | Cap routes at 100, activity is small, tests are small |
