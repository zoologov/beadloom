# Agent Instructions

Guidelines for AI agents (Claude Code, Cursor, Codex, etc.) working on beadloom.

For project overview and installation, see [README.md](README.md).

## Project Overview

**Beadloom** is a local CLI + MCP server that provides a queryable knowledge graph over project documentation and code. It solves two problems: context window waste (agents searching for context) and documentation rot (docs going stale after code changes).

- **Stack:** Python 3.10+, SQLite (WAL), Click + Rich (CLI), tree-sitter, MCP (stdio)
- **Package manager:** [uv](https://docs.astral.sh/uv/)
- **Distribution:** PyPI (`uv tool install beadloom`)
- **License:** MIT

## File Organization

```
beadloom/
├── src/beadloom/
│   ├── __init__.py          # Version string
│   ├── cli.py               # Click CLI (13 commands)
│   ├── mcp_server.py        # MCP stdio server (8 tools: 6 read + 2 write)
│   ├── context_builder.py   # BFS traversal, context bundle assembly
│   ├── sync_engine.py       # Doc-code sync state management
│   ├── db.py                # SQLite schema and helpers
│   ├── graph_loader.py      # YAML graph parser + update_node_in_yaml
│   ├── doc_indexer.py       # Markdown chunker
│   ├── code_indexer.py      # tree-sitter symbol extractor
│   ├── reindex.py           # Full + incremental reindex pipeline
│   ├── search.py            # FTS5 keyword search engine
│   ├── doctor.py            # Graph validation checks
│   ├── onboarding.py        # init --bootstrap / --import
│   ├── cache.py             # L1 in-memory + L2 SQLite cache
│   ├── health.py            # Health snapshots and trend tracking
│   ├── import_resolver.py   # tree-sitter import extraction + resolution
│   ├── rule_engine.py       # YAML deny/require rule parser + evaluator
│   ├── linter.py            # Lint orchestrator + output formatters
│   ├── why.py               # Impact analysis (upstream/downstream)
│   ├── diff.py              # Graph diff against git refs
│   ├── tui.py               # Interactive terminal dashboard (Textual)
│   └── watcher.py           # File watcher for auto-reindex
├── tests/                   # pytest tests (646+ tests, ~5s)
├── docs/                    # Project documentation (7 files)
├── .beadloom/               # Project's own beadloom data
│   ├── _graph/services.yml  # Knowledge graph definition
│   ├── config.yml           # Project config
│   └── beadloom.db          # SQLite index (gitignored)
└── pyproject.toml           # Build config, tool settings
```

## Development Guidelines

### Code Standards

- **Python:** 3.10+ (no 3.9 syntax)
- **Typing:** `mypy --strict` — all public functions fully typed
- **Lint/format:** `ruff` (lint + format, config in pyproject.toml)
- **Tests:** `pytest` with `pytest-cov` (≥80% coverage required)
- **Imports:** `from __future__ import annotations` in every module
- **No bare `except:`** — always specify exception type
- **No `Any` / `# type: ignore`** without documented reason
- **No `print()` / `breakpoint()`** in production code
- **No mutable default arguments** (`def f(x=[]):`)
- **No `import *`**

### Quality Gates

Run all three before committing:

```bash
uv run pytest                    # Tests (464 tests, ~3s)
uv run ruff check src/ tests/   # Lint
uv run mypy                     # Type checking
```

### Testing Workflow

- Follow **TDD** when adding features: write test first, then implement
- Test files mirror source: `src/beadloom/foo.py` → `tests/test_foo.py`
- CLI tests use `click.testing.CliRunner`
- Use `tmp_path` fixture for filesystem tests
- Mock external calls (filesystem) — never hit real APIs in tests

### Before Committing

1. Run quality gates (all three above)
2. If you changed behavior, update the corresponding doc in `docs/`
3. Run `beadloom sync-check` — if stale pairs exist, update the doc

## Using Beadloom (Self-Hosted Context)

This project uses beadloom on itself. The knowledge graph is at `.beadloom/_graph/services.yml`.

### Getting Context

```bash
# Context bundle for a domain/service
beadloom ctx doc-sync              # Markdown
beadloom ctx doc-sync --json       # JSON

# Available nodes
beadloom status

# Graph visualization
beadloom graph
```

### Checking Doc Freshness

```bash
# Check all doc-code pairs
beadloom sync-check

# Porcelain output for scripts
beadloom sync-check --porcelain

# Check specific ref_id
beadloom sync-update doc-sync --check
```

### Agent Workflows (MCP Write Tools)

Beadloom exposes write tools via MCP — the agent reads context and makes
intelligent updates without requiring a separate LLM API.

**Update stale documentation:**

1. Call `sync_check()` → get list of stale ref_ids
2. Call `get_context(ref_id)` → get full context + stale details
3. Read the doc file and changed code file
4. Update the doc file (using your own intelligence)
5. Call `mark_synced(ref_id)` → sync state reset to "ok"

**Improve node summaries:**

1. Call `get_status()` → see nodes with empty summaries
2. Call `get_context(ref_id)` → read code and docs
3. Generate a summary
4. Call `update_node(ref_id, summary="...")` → YAML + SQLite updated

**Search for relevant context:**

```bash
beadloom search "payment processing"     # FTS5 keyword search
beadloom search "auth" --kind service    # Filter by kind
```

### Architecture Lint

Beadloom enforces architectural boundaries via `beadloom lint`. Rules are defined in
`.beadloom/_graph/rules.yml` (deny/require patterns).

```bash
# Run architecture lint
beadloom lint                     # Human-readable output
beadloom lint --format json       # JSON for scripts
beadloom lint --strict            # Exit 1 on violations (CI mode)
beadloom lint --no-reindex        # Skip reindex before lint

# Context bundles include constraints for the focus node
beadloom ctx AUTH-001 --json      # "constraints" field in v2 bundles
```

**CI integration** (add to your CI pipeline):

```bash
pip install beadloom
beadloom reindex
beadloom lint --strict --format json
```

### After Changing Code

If `sync-check` shows stale pairs after your changes:

1. Read the stale doc and the changed code
2. Update the doc to reflect the code changes
3. Run `beadloom reindex` to rebuild the index
4. Verify with `beadloom sync-check` — all pairs should be `[ok]`

## Agent Warning: Interactive Commands

**DO NOT use `bd edit`** — it opens an interactive editor ($EDITOR) which AI agents cannot use.

Use `bd update` with flags instead:

```bash
bd update <id> --description "new description"
bd update <id> --title "new title"
bd update <id> --design "design notes"
bd update <id> --notes "additional notes"
```

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) on some systems:

```bash
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file
rm -rf directory            # NOT: rm -r directory
```

## Issue Tracking with Beads

This project uses [beads](https://github.com/steveyegge/beads) (`bd` CLI) for issue tracking.

```bash
bd ready                    # Show issues ready to work (no blockers)
bd show <id>                # Issue details + dependencies
bd update <id> --status in_progress   # Claim work
bd close <id>               # Mark complete
bd sync                     # Sync with git remote
```

**Rules:**
- Create a bead **before** writing code
- Mark `in_progress` when starting
- Close with `bd close` when done
- Run `bd sync` at session end

## Session Completion Protocol

**When ending a work session**, complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues** for remaining work (`bd create`)
2. **Run quality gates** (if code changed): pytest, ruff, mypy
3. **Update issue status**: close finished work, update in-progress items
4. **Check doc sync**: `beadloom sync-check` — update stale docs if any
5. **Push to remote**:
   ```bash
   git add <files>
   git commit -m "descriptive message"
   bd sync
   git push
   git status   # MUST show "up to date with origin"
   ```
6. **Verify** all changes are committed AND pushed

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing — that leaves work stranded locally
- NEVER say "ready to push when you are" — YOU must push
- If push fails, resolve and retry until it succeeds

## Common Development Tasks

### Adding a New CLI Command

1. Add the command function in `src/beadloom/cli.py`
2. Register with `@main.command()`
3. Add `--project` option (standard pattern)
4. Add tests in `tests/test_cli_<name>.py`
5. Document in `docs/cli-reference.md`

### Adding a New MCP Tool

1. Add handler function in `src/beadloom/mcp_server.py` (`handle_<name>`)
2. Add tool definition to `_TOOLS` list
3. Add dispatch case in `_dispatch_tool()`
4. Add tests in `tests/test_mcp_server.py`
5. Document in `docs/mcp-server.md`

### Modifying the Knowledge Graph Schema

1. Update schema in `src/beadloom/db.py` (`_SCHEMA`)
2. Add migration logic if needed (or bump reindex)
3. Update `src/beadloom/graph_loader.py` if YAML format changes
4. Update `docs/graph-format.md`

### Adding Language Support

1. Add tree-sitter grammar to `pyproject.toml` dependencies
2. Add language config in `src/beadloom/code_indexer.py`
3. Add tests with sample code in that language
4. Update `docs/getting-started.md`

## Important Files

| File | Description |
|------|-------------|
| `README.md` | Main documentation — keep updated |
| `docs/architecture.md` | System design and data flow |
| `docs/context-oracle.md` | BFS algorithm and bundle format |
| `docs/sync-engine.md` | Doc-code synchronization |
| `docs/cli-reference.md` | CLI commands reference |
| `docs/mcp-server.md` | MCP tools reference |
| `docs/graph-format.md` | YAML graph format spec |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security policy |
| `pyproject.toml` | Build config, all tool settings |

## Questions?

```bash
# Check existing issues
bd list

# Project health
beadloom doctor
beadloom status

# Recent history
git log --oneline -20

# Create an issue if unsure
bd create --title "Question: ..." --type task --priority 3
```
