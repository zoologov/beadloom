# RFC: BDL-030 — Agent Instructions Freshness

> **Status:** Approved
> **Created:** 2026-02-21

---

## Overview

Add automated detection and auto-fix of stale facts in agent instruction files (CLAUDE.md, AGENTS.md). Two-step delivery: (1) `beadloom doctor` check for drift detection, (2) `beadloom setup-rules --refresh` for auto-regeneration of dynamic sections.

## Motivation

### Problem
CLAUDE.md section 0.1 contains hardcoded facts: version "1.7.0", phase list "1-6 + 8, 8.5, ...", architecture packages, stack description. AGENTS.md contains MCP tool counts, CLI command references. These drift silently with every release. Manual audit found 2 issues in a well-maintained project.

### Solution
Introspect the project programmatically (Click CLI group, MCP `_TOOLS` list, `__version__`, graph YAML) and compare extracted facts against claims in CLAUDE.md/AGENTS.md. Report drift via `doctor`, auto-fix via `setup-rules --refresh` using section markers.

## Technical Context

### Constraints
- Python 3.10+
- SQLite (WAL mode)
- Reuse existing `doctor` infrastructure (`Check` dataclass, `Severity` enum, `run_checks()`)
- Reuse existing `setup-rules` infrastructure (`generate_agents_md()`, `setup_rules_auto()`)
- Must not break existing CLAUDE.md structure for projects that don't opt in to markers

### Affected Areas
- `infrastructure/doctor.py` — new check function
- `onboarding/scanner.py` — extended `setup-rules --refresh` + CLAUDE.md section regeneration
- `services/cli.py` — new `--refresh` flag on `setup-rules` command
- `.claude/CLAUDE.md` — add `<!-- beadloom:auto-start/end -->` markers around section 0.1

## Proposed Solution

### Approach

**Step 1 (12.12.1): Detection — new doctor check**

Add `_check_agent_instructions()` to `infrastructure/doctor.py` that:

1. Reads CLAUDE.md and AGENTS.md from project root
2. Extracts factual claims via regex patterns:
   - Version: `**Current version:** X.Y.Z`
   - Phase list: `Phases 1-6 + 8...`
   - Architecture packages: `infrastructure/, context_oracle/, ...`
   - CLI command count (from AGENTS.md)
   - MCP tool count (from AGENTS.md)
3. Compares with actual project state:
   - Version: `importlib.metadata.version("beadloom")` with fallback to `__version__`
   - CLI commands: Click group introspection via `main.commands` dict
   - MCP tools: import and count `_TOOLS` list length
   - Architecture packages: scan `src/beadloom/` for DDD package directories
   - Phase status: parse STRATEGY-2.md headers for `DONE` / `Planned` suffixes
4. Returns `list[Check]` with `Severity.WARNING` for each drift

**Fact sources registry:**

| Fact | Ground truth source | Extraction method |
|------|-------------------|-------------------|
| Version | `beadloom.__version__` | `importlib.metadata.version()` or direct import |
| CLI commands | `services/cli.py` | `main.commands.keys()` via Click introspection |
| MCP tool count | `services/mcp_server.py` | `len(_TOOLS)` |
| Architecture packages | `src/beadloom/` | Directory scan for `__init__.py` |
| Phase status | `STRATEGY-2.md` | Regex on section headers |
| Test framework | `pyproject.toml` | `[tool.pytest]` presence |
| Stack description | `pyproject.toml` | `requires-python`, dependencies |

**Step 2 (12.12.2): Auto-fix — setup-rules --refresh**

Extend `onboarding/scanner.py` with:

1. `refresh_claude_md(project_root: Path, *, dry_run: bool = False) -> list[str]`:
   - Reads CLAUDE.md
   - Finds `<!-- beadloom:auto-start SECTION -->` / `<!-- beadloom:auto-end -->` marker pairs
   - Regenerates content between markers using fact sources
   - Preserves everything outside markers (policy sections)
   - Returns list of changed sections
   - If `dry_run=True`: returns changes without writing

2. Section marker format in CLAUDE.md:
```markdown
<!-- beadloom:auto-start project-info -->
- **Stack:** Python 3.10+, SQLite (WAL), ...
- **Current version:** 1.8.0 (Phases 1-6 + 8, 8.5, ... done)
- **Architecture:** DDD packages — `infrastructure/`, `context_oracle/`, ...
<!-- beadloom:auto-end -->
```

3. CLI integration:
   - `beadloom setup-rules --refresh` calls `refresh_claude_md()` + `generate_agents_md()`
   - `beadloom setup-rules --refresh --dry-run` shows diff without writing

### Changes

| File / Module | Change |
|---------------|--------|
| `infrastructure/doctor.py` | Add `_check_agent_instructions(conn, project_root)` + fact extraction helpers |
| `onboarding/scanner.py` | Add `refresh_claude_md()`, `_render_project_info_section()`, marker parsing |
| `services/cli.py` | Add `--refresh` and `--dry-run` flags to `setup-rules` command |
| `.claude/CLAUDE.md` | Add `<!-- beadloom:auto-start/end -->` markers around section 0.1 facts |

### API Changes

**New doctor check** (internal, no public API change — doctor output gains a new section):
```
$ beadloom doctor
...
Agent Instructions
  ! CLAUDE.md: version "1.7.0" -> actual "1.8.0"
  ! CLAUDE.md: phases missing "12.7, 12.8"
  OK CLAUDE.md: architecture packages match
  OK AGENTS.md: MCP tools count matches (14)
```

**Extended CLI** (public):
```bash
beadloom setup-rules --refresh           # regenerate dynamic sections
beadloom setup-rules --refresh --dry-run  # preview changes
```

## Alternatives Considered

### Option A: Manual audit only
Keep current approach — developer manually checks CLAUDE.md after releases. Rejected: doesn't scale, misses drift.

### Option B: Detection only (no auto-fix)
Only add doctor check, no `--refresh`. Rejected as final state: detection without fix creates toil. But detection IS Step 1 in our incremental approach.

### Option C: Full template-based regeneration
Regenerate entire CLAUDE.md from a template. Rejected: CLAUDE.md is 90% policy content that agents/humans hand-craft. Replacing it all would lose valuable customization.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Regex extraction fragile for unusual CLAUDE.md formats | Medium | Low | Document expected format, add tests for edge cases |
| Marker-based approach requires manual initial setup | Low | Low | First `--refresh` can auto-insert markers if section 0.1 detected |
| Phase status parsing depends on STRATEGY-2.md format | Low | Medium | Graceful degradation: skip phase check if STRATEGY not found |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Should markers be auto-inserted on first `--refresh` run? | Decided: Yes, auto-insert if section 0.1 pattern detected |
| Q2 | Should phase parsing be optional (not all projects have STRATEGY.md)? | Decided: Yes, skip gracefully if not found |
| Q3 | Support custom fact sources via config.yml? | Deferred to v1.9+ |
