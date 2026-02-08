# /dev — Developer Role

> **When to invoke:** when working on code, implementing a bead
> **Focus:** Python 3.10+, TDD, Clean Code, Beadloom modular architecture

---

## Work start protocol

```bash
# 1. Check available tasks
bd ready

# 2. Claim a task
bd update <bead-id> --status in_progress --claim

# 3. Read the context
# - docs/features/{ISSUE-KEY}/{ISSUE-KEY}.CONTEXT.md
# - docs/features/{ISSUE-KEY}/{ISSUE-KEY}.ACTIVE.md
```

**Confirm to the user:**
```
┌─────────────────────────────────────────┐
│ Context loaded: {ISSUE-KEY}             │
│ Bead: <bead-id> — [name]               │
│ Goal: [from CONTEXT]                    │
│ Plan: [from ACTIVE or create one]       │
│ Ready to proceed?                       │
└─────────────────────────────────────────┘
```

---

## TDD Workflow (MANDATORY)

```
RED      → Write a test → make sure it fails
GREEN    → Write minimal code → test passes
REFACTOR → Improve the code → tests stay green
REPEAT   → Next test case
```

**Rules:**
1. DO NOT write production code without a failing test
2. Write only enough test to make it fail
3. Write only enough code to make the test pass
4. Refactor only when tests are green

---

## Beadloom Architecture

### Layers

```
CLI (Click + Rich)  →  Core Logic  →  Storage (SQLite)
         ↓                 ↓                ↓
    commands/         graph.py         database.py
    formatters/       context.py       models.py
                      sync.py
                      chunker.py
                         ↓
                    Parsers (tree-sitter)
```

**Rule:** dependencies point inward. CLI depends on Core, Core depends on Storage. Reverse dependencies are forbidden.

### Package structure

```
src/beadloom/
├── __init__.py
├── __main__.py          # python -m beadloom
├── cli/                 # Click commands
│   ├── __init__.py
│   ├── main.py          # cli group
│   ├── init_cmd.py
│   ├── reindex_cmd.py
│   ├── ctx_cmd.py
│   └── ...
├── core/                # Business logic (no dependency on CLI/MCP)
│   ├── __init__.py
│   ├── graph.py         # BFS, subgraphs
│   ├── context.py       # Context Oracle — bundle assembly
│   ├── sync.py          # Doc Sync Engine
│   ├── chunker.py       # Markdown → chunks
│   ├── indexer.py       # YAML + docs + code → SQLite
│   └── doctor.py        # Integrity validation
├── storage/             # SQLite, schema, migrations
│   ├── __init__.py
│   ├── database.py      # Connection, WAL, PRAGMA
│   ├── schema.py        # CREATE TABLE
│   └── queries.py       # Named SQL queries
├── parsers/             # tree-sitter, annotations
│   ├── __init__.py
│   ├── symbols.py       # Symbol extraction
│   └── annotations.py   # beadloom: comments
├── mcp/                 # MCP server
│   ├── __init__.py
│   ├── server.py        # stdio transport
│   ├── tools.py         # get_context, get_graph, ...
│   └── cache.py         # L1 in-memory cache
└── models.py            # Dataclasses: Node, Edge, Bundle, ...
tests/
├── conftest.py          # Shared fixtures
├── unit/
│   ├── test_graph.py
│   ├── test_context.py
│   ├── test_chunker.py
│   └── ...
├── integration/
│   ├── test_indexer.py
│   ├── test_cli.py
│   └── ...
└── fixtures/            # Test YAML, MD files
    ├── sample_graph/
    └── sample_docs/
```

---

## Code Patterns (Python)

### Dataclasses for models

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Node:
    ref_id: str
    kind: str  # domain | feature | service | entity | adr
    summary: str
    source: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Edge:
    src_ref_id: str
    dst_ref_id: str
    kind: str  # part_of | depends_on | uses | ...
```

### Exceptions

```python
class BeadloomError(Exception):
    """Base Beadloom exception."""

class NodeNotFoundError(BeadloomError):
    def __init__(self, ref_id: str) -> None:
        self.ref_id = ref_id
        super().__init__(f"Node not found: {ref_id}")

class StaleIndexError(BeadloomError):
    """Index is stale, reindex required."""
```

### Working with paths

```python
from pathlib import Path

# Always pathlib, never os.path
graph_dir = project_root / ".beadloom" / "_graph"
for yml_file in graph_dir.glob("*.yml"):
    ...
```

### Working with SQLite

```python
import sqlite3

# Always parameterized queries
cursor.execute(
    "SELECT * FROM nodes WHERE ref_id = ?",
    (ref_id,),
)

# Never f-strings in SQL
# cursor.execute(f"SELECT * FROM nodes WHERE ref_id = '{ref_id}'")  # FORBIDDEN
```

### YAML

```python
import yaml

# Always safe_load
with open(path) as f:
    data = yaml.safe_load(f)

# Never yaml.load(f, Loader=yaml.FullLoader)
```

### Clean Code Principles

| Principle | Rule |
|-----------|------|
| **SRP** | One module/function = one responsibility |
| **DRY** | Do not duplicate logic |
| **KISS** | A simple solution is better than a complex one |
| **YAGNI** | Do not write code "for the future" |

### Naming Conventions

| Element | Style | Example |
|---------|-------|---------|
| Files/modules | snake_case | `context_builder.py` |
| Classes | PascalCase | `ContextBuilder` |
| Functions/methods | snake_case | `get_context_bundle` |
| Constants | SCREAMING_SNAKE | `MAX_CHUNK_SIZE` |
| Private | `_prefix` | `_build_subgraph` |

---

## During work

### After each significant action:

1. **Update ACTIVE.md:**
   ```markdown
   - [x] Step N: description (completed HH:MM)
   ```

2. **Add checkpoint in beads (every 30 min or 5 steps):**
   ```bash
   bd comments add <bead-id> "CHECKPOINT: [what was done]"
   ```

3. **For architectural decisions:**
   - Update CONTEXT.md (decisions table)
   - Update RFC.md

---

## Completing a bead

```bash
# 1. Make sure tests pass
uv run pytest

# 2. Linter and types
uv run ruff check src/ tests/
uv run mypy src/

# 3. Add final checkpoint
bd comments add <bead-id> "$(cat <<'EOF'
COMPLETED:
- What was done: [list]
- Decisions: [if any]
- Tests: [result]
- TODO: [if any]
EOF
)"

# 4. Close the bead
bd close <bead-id>

# 5. Check what got unblocked
bd ready
```

---

## Code restrictions

| Forbidden | Alternative |
|-----------|-------------|
| `Any` without reason | Explicit types, `object`, generics |
| `# type: ignore` without comment | Fix the typing |
| `print()` / `breakpoint()` | `logging` module |
| Magic numbers | Named constants |
| Commented-out code | Delete or TODO |
| Hardcoded secrets | Environment variables |
| Nesting > 3 levels | Early return, extract function |
| Functions > 30 lines | Split into smaller ones |
| Bare `except:` | `except SpecificError:` |
| `import *` | Explicit imports |
| `def f(x=[]):` | `def f(x: list | None = None):` |
| `os.path` | `pathlib.Path` |
| f-strings in SQL | Parameterized queries `?` |
| `yaml.load()` | `yaml.safe_load()` |

---

## Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Reindex completed", extra={"nodes": count, "duration_ms": elapsed})
```

**Forbidden to log:** passwords, tokens, API keys, PII

---

## Developer checklist

### When starting a bead
- [ ] `bd ready` -> selected a task
- [ ] `bd update <id> --status in_progress --claim`
- [ ] Read CONTEXT.md and ACTIVE.md
- [ ] Confirmed understanding to the user

### During work
- [ ] Following TDD: RED -> GREEN -> REFACTOR
- [ ] Updating ACTIVE.md after each step
- [ ] Checkpoint in beads every 30 min
- [ ] Architectural decisions -> CONTEXT.md

### When completing
- [ ] `uv run pytest` — all tests pass
- [ ] `uv run ruff check` — linter is clean
- [ ] `uv run mypy src/` — typing is ok
- [ ] Final checkpoint in beads
- [ ] `bd close <bead-id>`
- [ ] ACTIVE.md cleared for the next bead
