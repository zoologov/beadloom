# BDL-017: Beadloom v1.6 — Plan (DAG)

## Metadata
- **Created:** 2026-02-16
- **Status:** Approved (2026-02-16)
- **Total beads:** 15
- **Estimated waves:** 3

---

## Wave 1: Core Analysis + Independent Infrastructure (parallel)

All tasks in Wave 1 are independent and can run in parallel.

### BEAD-01: API Route Extraction — Core Module [P0]
- **Type:** feature
- **Effort:** L
- **Files:** NEW `src/beadloom/context_oracle/route_extractor.py`, NEW `tests/test_route_extractor.py`
- **What:** Create `Route` dataclass + `extract_routes()` function. 12 framework patterns: FastAPI, Flask, Express, NestJS, Spring Boot, Gin, Echo, Fiber, GraphQL (schema + Python code-first + TS code-first), gRPC (.proto). Tree-sitter primary, regex fallback.
- **Tests:** Unit tests per framework with real code snippets. Min 24 test cases (2 per framework).
- **Done when:** `extract_routes("fastapi_app.py", "python")` returns correct Route objects.

### BEAD-02: Git History Analysis [P0]
- **Type:** feature
- **Effort:** M
- **Files:** NEW `src/beadloom/infrastructure/git_activity.py`, NEW `tests/test_git_activity.py`
- **What:** Create `GitActivity` dataclass + `analyze_git_activity()`. Single `git log` invocation, parse output, map files→dirs→nodes. Activity levels: hot/warm/cold/dormant. Graceful degradation if not git repo.
- **Tests:** Unit tests with mocked subprocess. Integration test with tmp git repo.
- **Done when:** `analyze_git_activity(project_root, source_dirs)` returns correct GitActivity per node.

### BEAD-03: Test Mapping [P1]
- **Type:** feature
- **Effort:** M
- **Files:** NEW `src/beadloom/context_oracle/test_mapper.py`, NEW `tests/test_test_mapper.py`
- **What:** Create `TestMapping` dataclass + `map_tests()`. 5 frameworks: pytest, jest, go test, JUnit, XCTest. Mapping by naming convention + import analysis. Coverage estimate: high/medium/low/none.
- **Tests:** Unit tests per framework with fixture dirs.
- **Done when:** `map_tests(project_root, source_dirs)` maps test files to correct source nodes.

### BEAD-04: Rule Severity Levels [P1]
- **Type:** feature
- **Effort:** S
- **Files:** `src/beadloom/graph/rule_engine.py`, `src/beadloom/graph/linter.py`, `src/beadloom/services/cli.py`
- **What:** Add `severity: error | warn` to rules.yml v2 format. Update `Violation` dataclass. Update `evaluate_rules()` to pass severity through. Update CLI lint output with severity icons. `--strict` exits 1 only on errors. Backward compat: v1 rules default to `severity: error`.
- **Tests:** Existing rule engine tests + new severity tests.
- **Done when:** `beadloom lint` shows `[ERROR]`/`[WARN]` markers. `--strict` ignores warnings.

### BEAD-05: MCP Tool — why [P1]
- **Type:** feature
- **Effort:** S
- **Files:** `src/beadloom/services/mcp_server.py`
- **What:** Add `why` tool to MCP server. Wraps existing `why` CLI logic. Returns JSON with upstream/downstream/impact_summary.
- **Tests:** MCP tool handler test with mock DB.
- **Done when:** MCP `why` tool returns structured JSON for any valid ref_id.

### BEAD-06: MCP Tool — diff [P1]
- **Type:** feature
- **Effort:** S
- **Files:** `src/beadloom/services/mcp_server.py`
- **What:** Add `diff` tool to MCP server. Wraps existing `diff` CLI logic. Returns JSON with added/removed/changed nodes and edges.
- **Tests:** MCP tool handler test.
- **Done when:** MCP `diff` tool returns graph changes since a git ref.

### BEAD-07: Deep Config Reading [P2]
- **Type:** feature
- **Effort:** S
- **Files:** NEW `src/beadloom/onboarding/config_reader.py`, NEW `tests/test_config_reader.py`
- **What:** `read_deep_config()` parses pyproject.toml (scripts, tool configs), package.json (scripts, workspaces, engines), tsconfig.json (paths, baseUrl), Cargo.toml (workspace, features), build.gradle (plugins, deps). Store in root `nodes.extra.config`.
- **Tests:** Unit tests with fixture config files.
- **Done when:** Config data appears in `nodes.extra` after reindex.

### BEAD-08: Context Cost Metrics [P2]
- **Type:** feature
- **Effort:** S
- **Files:** `src/beadloom/services/cli.py`, `src/beadloom/context_oracle/builder.py`
- **What:** Add token estimation to `beadloom status`. Calculate avg/max bundle sizes. Show "Beadloom context vs raw file size" comparison.
- **Tests:** Unit test for token estimation.
- **Done when:** `beadloom status` shows "Context Metrics:" section.

---

## Wave 2: Reindex Integration (depends on Wave 1 core modules)

### BEAD-09: Integrate Routes into Reindex [P0]
- **Type:** feature
- **Effort:** M
- **Depends on:** BEAD-01
- **Files:** `src/beadloom/infrastructure/reindex.py`, `src/beadloom/context_oracle/builder.py`
- **What:** Call `extract_routes()` during `_index_code_symbols()`. Store routes in `nodes.extra`. Update `build_context_bundle()` to render routes section. Update context JSON output.
- **Tests:** Integration test: reindex → ctx shows routes.
- **Done when:** `beadloom ctx AUTH` shows "API Routes:" section with extracted routes.

### BEAD-10: Integrate Git Activity into Reindex [P0]
- **Type:** feature
- **Effort:** S
- **Depends on:** BEAD-02
- **Files:** `src/beadloom/infrastructure/reindex.py`, `src/beadloom/context_oracle/builder.py`
- **What:** Call `analyze_git_activity()` during reindex. Store in `nodes.extra`. Update context bundle to show activity. Update prime output.
- **Tests:** Integration test: reindex → ctx shows activity.
- **Done when:** `beadloom ctx AUTH` shows "Activity: hot (45 commits/30d)".

### BEAD-11: Integrate Test Mapping into Reindex [P1]
- **Type:** feature
- **Effort:** S
- **Depends on:** BEAD-03
- **Files:** `src/beadloom/infrastructure/reindex.py`, `src/beadloom/context_oracle/builder.py`
- **What:** Call `map_tests()` during reindex. Store in `nodes.extra`. Update context bundle.
- **Tests:** Integration test: reindex → ctx shows test info.
- **Done when:** `beadloom ctx AUTH` shows "Tests: pytest, 15 tests in 3 files".

### BEAD-12: MCP Tool — lint [P0]
- **Type:** feature
- **Effort:** M
- **Depends on:** BEAD-04
- **Files:** `src/beadloom/services/mcp_server.py`
- **What:** Add `lint` tool to MCP server. Uses updated linter with severity. Returns JSON violations with severity field. Filter by severity parameter.
- **Tests:** MCP lint tool tests with mock rules + violations.
- **Done when:** MCP `lint` tool returns `{violations: [...], summary: {errors: N, warnings: M}}`.

### BEAD-13: Integrate Deep Config into Bootstrap [P2]
- **Type:** feature
- **Effort:** S
- **Depends on:** BEAD-07
- **Files:** `src/beadloom/onboarding/scanner.py`, `src/beadloom/infrastructure/reindex.py`
- **What:** Call `read_deep_config()` during bootstrap and reindex. Store in root `nodes.extra`.
- **Tests:** Integration test.
- **Done when:** Config data appears in context bundle for root node.

---

## Wave 3: Polish Enrichment (depends on Wave 2)

### BEAD-14: Smart Docs Polish with Deep Data [P1]
- **Type:** feature
- **Effort:** M
- **Depends on:** BEAD-09, BEAD-10, BEAD-11
- **Files:** `src/beadloom/onboarding/doc_generator.py`
- **What:** Extend `generate_polish_data()` to include routes, activity, tests from `nodes.extra`. Update `format_polish_text()` with enriched output.
- **Tests:** Unit test verifying polish data includes new fields.
- **Done when:** `beadloom docs polish` shows routes, activity, and test info per node.

### BEAD-15: E2E Validation + AGENTS.md Update [P0]
- **Type:** task
- **Effort:** M
- **Depends on:** BEAD-09, BEAD-10, BEAD-11, BEAD-12, BEAD-14
- **Files:** `src/beadloom/onboarding/agents_md.py`, tests
- **What:** Full E2E test: init → reindex → ctx → lint → polish → MCP tools. Update AGENTS.md generator with new MCP tools count. Dogfood on beadloom itself. Collect UX feedback.
- **Done when:** All E2E tests pass. Beadloom's own graph enriched with routes + activity + tests.

---

## DAG Visualization

```
Wave 1 (all parallel):
  BEAD-01 (Routes core)        ──→ BEAD-09 (Routes reindex)  ──→ BEAD-14 (Smart polish) ──→ BEAD-15 (E2E)
  BEAD-02 (Git activity core)  ──→ BEAD-10 (Activity reindex) ──→ BEAD-14
  BEAD-03 (Test mapping core)  ──→ BEAD-11 (Test reindex)     ──→ BEAD-14
  BEAD-04 (Rule severity)      ──→ BEAD-12 (MCP lint)         ──→ BEAD-15
  BEAD-05 (MCP why)            ──→ BEAD-15
  BEAD-06 (MCP diff)           ──→ BEAD-15
  BEAD-07 (Deep config core)   ──→ BEAD-13 (Config reindex)   ──→ BEAD-15
  BEAD-08 (Cost metrics)       ──→ BEAD-15
```

## Critical Path
```
BEAD-01 → BEAD-09 → BEAD-14 → BEAD-15
```
(Longest chain: route extraction → reindex integration → polish enrichment → E2E)

## Parallelism Opportunities

**Max parallelism in Wave 1:** 8 independent beads
- **Agent 1:** BEAD-01 (Routes — largest, P0)
- **Agent 2:** BEAD-02 (Git) + BEAD-08 (Metrics)
- **Agent 3:** BEAD-03 (Tests) + BEAD-07 (Config)
- **Agent 4:** BEAD-04 (Severity) + BEAD-05 (MCP why) + BEAD-06 (MCP diff)

**Max parallelism in Wave 2:** 5 beads (BEAD-09, 10, 11, 12, 13)
**Wave 3:** 2 sequential beads (BEAD-14 → BEAD-15)
