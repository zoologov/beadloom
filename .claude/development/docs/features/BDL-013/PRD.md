# PRD: BDL-013 — Dogfood Beadloom + Agent Instructions + CI

> **Status:** Complete (delivered in v1.3.1)
> **Date:** 2026-02-14

---

## 1. Problem Statement

Beadloom v1.3.1 is a Context Oracle + Doc Sync Engine that helps AI agents maintain
documentation and enforce architectural boundaries. However, the project does not
use its own capabilities during development:

1. **No Beadloom in CI** — `beadloom lint --strict` and `beadloom sync-check` are
   never run in GitHub Actions. Architecture violations and stale docs can be merged.
2. **Agent instructions are Beads-only** — `.claude/CLAUDE.md` and all 7 skill files
   in `.claude/commands/` contain zero Beadloom CLI instructions. After `/compact`,
   agents lose all context about running `beadloom reindex`, `sync-check`, or `lint`.
3. **AGENTS.md is redundant** — Duplicates information that should live in
   `.claude/CLAUDE.md` + skills. Not auto-loaded, doesn't survive `/compact`,
   already outdated (references flat file structure instead of actual DDD layout).
4. **Skills contain fictional package structure** — `/dev` and `/test` describe
   `src/beadloom/cli/main.py`, `core/graph.py`, `storage/database.py` etc. that
   don't exist. Actual layout is DDD-based: `services/cli.py`, `graph/loader.py`,
   `infrastructure/db.py`. Agents following these skills look for nonexistent files.
5. **Pre-commit hooks not installed** — `beadloom install-hooks` has never been run
   on the project itself.
6. **Missing architecture rules** — Only 2 require rules exist (`domain-needs-parent`,
   `feature-needs-domain`). No `service-needs-parent`, no deny rules for cross-boundary
   imports.
7. **No `.beadloom/README.md`** — Beads generates `.beads/README.md` during init to
   explain the tool to new contributors. Beadloom has no equivalent — new agents or
   developers opening `.beadloom/` see raw YAML/DB files with no guidance.

**Impact:** We cannot credibly recommend Beadloom to users if we don't use it ourselves.
Bugs in the dogfood workflow surface real UX issues before users encounter them.

---

## 2. Goals

| # | Goal | Success Metric |
|---|------|----------------|
| G1 | Beadloom validates itself in CI | `beadloom lint --strict` + `sync-check` pass in GH Actions |
| G2 | Agents use Beadloom after `/compact` | CLAUDE.md and skills contain Beadloom workflows |
| G3 | Single source of truth for agent instructions | AGENTS.md deleted, content in `.claude/` only |
| G4 | Skills use dynamic structure from Beadloom | No hardcoded file trees; agents run `beadloom graph`/`ctx` |
| G5 | Pre-commit warns on stale docs | `beadloom install-hooks --mode warn` active |
| G6 | Architecture rules cover all node kinds | ≥4 require rules + ≥1 deny rule |
| G7 | CI is optimized | Tests skip on docs-only changes, AaC lint runs always |
| G8 | `.beadloom/README.md` exists for all projects | Generated during `beadloom init`, AI Agent Native messaging |
| G9 | Consistent terminology | "Architecture graph" everywhere, not "knowledge graph" |

---

## 3. User Stories

### US-1: CI catches architecture violations
**As** a developer pushing to main,
**I want** CI to run `beadloom lint --strict`,
**So that** cross-boundary imports are caught before merge.

### US-2: CI catches stale documentation
**As** a developer changing code,
**I want** CI to run `beadloom sync-check`,
**So that** documentation stays in sync with code.

### US-3: Agent knows Beadloom workflow after compact
**As** an AI agent resuming after `/compact`,
**I want** Beadloom CLI instructions in `.claude/CLAUDE.md`,
**So that** I run `reindex`, `sync-check`, and `lint` at the right time.

### US-4: Agent discovers project structure dynamically
**As** an AI agent following `/dev` instructions,
**I want** to run `beadloom graph` and `beadloom ctx <domain>` for project structure,
**So that** I always work with actual file paths, not stale hardcoded trees.

### US-5: Pre-commit catches stale docs locally
**As** a developer committing changes,
**I want** a pre-commit warning when docs are stale,
**So that** I update documentation before pushing.

### US-6: CI doesn't waste resources
**As** a maintainer,
**I want** tests to skip on docs-only changes,
**So that** CI minutes are not wasted on irrelevant runs.

### US-7: New contributors understand .beadloom/
**As** a developer or AI agent encountering `.beadloom/` for the first time,
**I want** a README.md explaining what Beadloom is and how to use it,
**So that** I can start using the architecture graph without external docs.

---

## 4. Scope

### In Scope

| # | Deliverable | Package |
|---|-------------|---------|
| D1 | `beadloom-aac-lint.yml` GitHub Actions workflow | C: CI |
| D2 | Optimized `tests.yml` with path filters | C: CI |
| D3 | Updated `.claude/CLAUDE.md` with Beadloom section | B: Agent |
| D4 | Updated `.claude/commands/dev.md` — add Beadloom workflow, replace static structure with dynamic `beadloom graph`/`ctx` commands | B: Agent |
| D5 | Updated `.claude/commands/review.md` with Beadloom checks | B: Agent |
| D6 | Updated `.claude/commands/test.md` — replace static structure with dynamic discovery | B: Agent |
| D7 | Updated `.claude/commands/coordinator.md` — add Beadloom validation to wave checklist | B: Agent |
| D8 | Delete `AGENTS.md` — migrate unique content to `.claude/CLAUDE.md` + skills | B: Agent |
| D9 | Pre-commit hook installed (`--mode warn`) | A: Dogfood |
| D10 | Expanded `rules.yml` (service-needs-parent + deny rules) | A: Dogfood |
| D11 | Verify and fix any issues found by new rules/checks | A: Dogfood |
| D12 | Generate `.beadloom/README.md` during `beadloom init` + create for own project | A: Dogfood |
| D13 | Rename "knowledge graph" → "architecture graph" across codebase | A: Dogfood |

### Out of Scope

- New Beadloom features (semantic search, new languages, etc.) — that's STRATEGY-2
- Changes to the graph structure (adding/removing nodes)
- TUI improvements
- MCP server changes

---

## 5. Design Principle: Dynamic over Static

Skills should separate **methodology** (static, rarely changes) from
**project structure** (dynamic, queried from Beadloom at runtime):

| Content type | Where it lives | Example |
|-------------|----------------|---------|
| **HOW** — methodology | Static in skill file | TDD workflow, AAA pattern, code restrictions |
| **WHAT** — project structure | Dynamic from Beadloom | `beadloom graph`, `beadloom ctx <domain>`, `beadloom status` |

This is the first real use case of Beadloom on itself: agents navigate
the codebase using the tool they are building.

---

## 6. Dependencies

- No external dependencies. All work uses existing v1.3.1 capabilities.
- Beads CLI for task tracking (already installed).

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| New lint rules expose existing violations | Fix violations as part of D11 before enabling `--strict` |
| CI workflow adds latency | AaC lint is fast (~2s), run on single Python version |
| Pre-commit hook annoys developers | Use `--mode warn` (advisory), not `block` |
| Deleting AGENTS.md breaks external tools | Content migrated to `.claude/`; Beadloom still generates AGENTS.md for other projects |
| Agent overhead from running `beadloom` commands | Commands are fast (<1s); one-time cost per session vs permanent stale data |
