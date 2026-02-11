# PRD: BDL-007 — Architecture as Code & Ecosystem (v1.0)

> **Status:** Draft
> **Date:** 2026-02-11
> **Phase:** 6
> **Target version:** 1.0.0

---

## 1. Problem Statement

Beadloom v0.7 **describes** architecture (knowledge graph) and **delivers** context (Context Oracle + MCP). But it does not **enforce** architectural rules.

Today:
- Agents receive context about how the system works, but nothing prevents them from violating architectural boundaries
- Traditional AaC tools (ArchUnit, Deptrac) validate code but don't deliver context to agents
- There is no single tool that combines: architecture definition + validation + context delivery + doc sync

**Gap:** Developers define architecture in YAML, but can't verify that code actually respects those boundaries.

## 2. Vision

Beadloom evolves from "architecture documentation" to a full **Architecture as Code** platform:

> Architecture is not just described, but **validated**, **enforced**, and **delivered** to AI agents as executable constraints.

Beadloom becomes the first tool that closes the full loop:

```
describe (graph) → validate (lint) → deliver (MCP + constraints) → keep in sync (Sync Engine)
```

## 3. Target Users

| User | Pain | Solution |
|------|------|----------|
| **Tech Lead / Architect** | "We defined module boundaries, but PRs constantly violate them" | `beadloom lint` catches violations before merge |
| **AI Agent (via MCP)** | "I have context but no rules — I might create cross-boundary imports" | `get_context` returns constraints alongside context |
| **CI Pipeline** | "No automated architecture validation" | `beadloom lint --strict` as CI gate, exits non-zero on violations |
| **Individual Developer** | "I don't know which imports are allowed between modules" | Rules are explicit in `rules.yml`, lint gives clear violation messages |

## 4. Scope

### In scope (v1.0)

| # | Feature | Priority | Description |
|---|---------|----------|-------------|
| 6.1 | **Architecture rules & lint** | P0 | `beadloom lint` validates code imports against graph boundaries |
| 6.2 | **Constraint language** | P0 | Declarative YAML rules in `.beadloom/_graph/rules.yml` |
| 6.3 | **Agent-aware constraints** | P1 | MCP `get_context` includes active constraints for the requested node |
| 6.4 | **CI architecture gate** | P1 | `beadloom lint --strict` for CI, porcelain output, exit codes |

### Out of scope (deferred post-v1.0)

| # | Feature | Why deferred |
|---|---------|--------------|
| 6.5 | Multi-repo support | Adds federation complexity; focus on single-repo first |
| 6.6 | Plugin system | Needs stable API surface; premature before v1.0 stabilizes |
| 6.7 | Web dashboard | Nice-to-have; CLI + TUI + MCP cover the primary users |

## 5. User Stories

### US-1: Architect defines boundary rules
```
As a Tech Lead,
I want to define rules like "billing must not import from auth directly"
So that the team has explicit, enforceable architectural boundaries.
```

**Acceptance criteria:**
- Rules defined in `.beadloom/_graph/rules.yml` (YAML format)
- Rule types: `deny` (forbidden edges/imports), `require` (mandatory relationships)
- Rules reference graph nodes by `ref_id` and/or `kind`
- Rules are validated on load (schema errors reported clearly)

### US-2: Developer runs architecture lint locally
```
As a Developer,
I want to run `beadloom lint` and see which imports violate architecture rules
So that I can fix violations before pushing.
```

**Acceptance criteria:**
- `beadloom lint` scans source code for imports (using tree-sitter)
- Maps imports to graph nodes (via annotations + file paths)
- Evaluates each import against active rules
- Reports violations with: rule name, file path, line number, import target, explanation
- Exit code 0 = clean, exit code 1 = violations found
- `--format` flag: `rich` (default, human-readable), `json`, `porcelain`

### US-3: CI blocks PRs with architecture violations
```
As a CI Pipeline,
I want `beadloom lint --strict` to fail the build when architecture is violated
So that violations don't reach the main branch.
```

**Acceptance criteria:**
- `beadloom lint --strict` returns exit code 1 on any violation
- `--format porcelain` outputs machine-readable one-line-per-violation
- `--format json` outputs structured JSON for programmatic consumption
- Works in headless environment (no rich formatting when not a TTY)
- Documents GitHub Actions / GitLab CI integration recipe

### US-4: Agent receives constraints with context
```
As an AI Agent (via MCP),
I want `get_context` to include architectural constraints for the requested node
So that I can respect boundaries without needing a human reviewer.
```

**Acceptance criteria:**
- `get_context` response includes a `constraints` field
- Each constraint has: rule name, description, scope, what's denied/required
- Constraints are filtered to those relevant to the focus node
- No performance regression (constraints loaded from SQLite, not re-parsed from YAML)

### US-5: Import detection across languages
```
As a Developer using Python/TypeScript/Go,
I want `beadloom lint` to detect imports in my language
So that rules work regardless of the project's language.
```

**Acceptance criteria:**
- Python: `import X`, `from X import Y`
- TypeScript/JavaScript: `import ... from 'X'`, `require('X')`
- Go: `import "X"`, `import ( "X" )`
- Rust: `use X`, `mod X`
- Import paths mapped to graph nodes via file path → annotation → ref_id chain

## 6. Non-functional Requirements

| Requirement | Target |
|-------------|--------|
| Lint speed | < 2s for 1000-file project |
| Rule loading | < 50ms for 100 rules |
| No new required dependencies | tree-sitter already in stack |
| Backward compatible | Existing projects work without rules.yml |
| Test coverage | >= 80% for new modules |
| mypy --strict | Zero errors |
| ruff | Zero violations |

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| `beadloom lint` validates Python imports | Yes |
| `beadloom lint` validates TS/JS imports | Yes |
| `beadloom lint` validates Go imports | Yes |
| `beadloom lint` validates Rust imports | Yes |
| MCP `get_context` returns constraints | Yes |
| CI integration documented | Yes |
| All existing 541 tests still pass | Yes |
| New test count | >= 80 new tests |
| Total tests | >= 620 |

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Import resolution is complex (relative imports, aliases, re-exports) | Start with direct import paths only; skip re-exports in v1.0 |
| Mapping file paths to graph nodes may be ambiguous | Use annotations as primary mapping; file path as fallback heuristic |
| Performance of full-project import scan | Leverage existing tree-sitter infrastructure; incremental via file_index |
| Rules YAML schema may need evolution | Version the schema (`version: 1`); design for forward compatibility |
