# /test — Tester Role

> **When to invoke:** when writing tests, checking coverage
> **Focus:** pytest, test quality, coverage >= 80%, edge cases

---

## Test structure

Tests are in `tests/` (flat layout, no subdirectories). Discover test files:

```bash
ls tests/test_*.py               # all test files
beadloom ctx <domain> --json     # see source files → derive test file names
```

Naming conventions:
- Domain module: `src/beadloom/<domain>/<module>.py` → `tests/test_<module>.py`
- CLI commands: `tests/test_cli_<command>.py`
- Integration: `tests/test_integration*.py`

---

## AAA Pattern (Arrange-Act-Assert)

```python
def test_get_context_returns_bundle_for_valid_ref_id(db: Database) -> None:
    # Arrange
    db.insert_node(Node(ref_id="PROJ-123", kind="feature", summary="Test"))
    db.insert_edge(Edge(src_ref_id="PROJ-123", dst_ref_id="routing", kind="part_of"))
    oracle = ContextOracle(db)

    # Act
    bundle = oracle.get_context("PROJ-123")

    # Assert
    assert bundle.focus.ref_id == "PROJ-123"
    assert len(bundle.graph.nodes) >= 1
    assert any(e.kind == "part_of" for e in bundle.graph.edges)
```

---

## Test types

### Unit tests
- Test a single function/class in isolation
- Mocks for all dependencies
- Fast (< 10ms)

### Integration tests
- Test interaction between components (CLI -> Core -> SQLite)
- Real SQLite database (in-memory or tmp_path)
- Medium speed (< 1s)

---

## Fixtures (conftest.py)

```python
import pytest
import sqlite3
from pathlib import Path
from beadloom.infrastructure.db import open_db, create_schema

@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """Clean SQLite database for each test."""
    conn = open_db(tmp_path / "test.db")
    create_schema(conn)
    return conn

@pytest.fixture
def sample_graph(tmp_path: Path) -> Path:
    """Minimal YAML graph for tests."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "domains.yml").write_text(
        "nodes:\n"
        "  - ref_id: routing\n"
        "    kind: domain\n"
        "    summary: Test domain\n"
    )
    return tmp_path

@pytest.fixture
def sample_docs(tmp_path: Path) -> Path:
    """Minimal documentation for tests."""
    docs_dir = tmp_path / "docs" / "domains" / "routing"
    docs_dir.mkdir(parents=True)
    (docs_dir / "README.md").write_text(
        "# Routing\n\n## Invariants\nTest invariant.\n"
    )
    return tmp_path
```

---

## Edge Cases Checklist

### Input validation
- [ ] `None` / empty string
- [ ] Non-existent `ref_id`
- [ ] Duplicate `ref_id`
- [ ] Special characters and Unicode in `ref_id` / `summary`
- [ ] Very long `summary` (>10K characters)
- [ ] Empty YAML file
- [ ] Invalid YAML

### SQLite
- [ ] Empty database (no nodes)
- [ ] `ref_id` with SQL special characters (`'`, `"`, `;`)
- [ ] Broken foreign keys (orphaned edges)
- [ ] WAL mode with concurrent access

### File system
- [ ] Missing files (`docs/` does not exist)
- [ ] Empty Markdown files
- [ ] Markdown without H2 headings
- [ ] Files >1MB
- [ ] Symlinks

### Graph
- [ ] Circular dependencies
- [ ] Isolated nodes (no edges)
- [ ] depth=0
- [ ] max_chunks=0

---

## Commands

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src/beadloom --cov-report=term-missing

# Integration only
uv run pytest tests/test_integration*.py

# Single file
uv run pytest tests/test_graph_loader.py

# With verbose
uv run pytest -v

# Watch mode (pytest-watch)
uv run ptw
```

---

## Checking coverage

```bash
uv run pytest --cov=src/beadloom --cov-report=term-missing --cov-fail-under=80
```

Minimum thresholds:
- Statements: 80%
- Branches: 80%

---

## Mocking

### pytest.mock / monkeypatch

```python
from unittest.mock import MagicMock, patch

def test_sync_check_detects_stale(db: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock the file system
    monkeypatch.setattr(Path, "stat", lambda self: MagicMock(st_mtime=99999))

    sync = SyncEngine(db)
    result = sync.check()

    assert len(result.stale_docs) == 1


def test_cli_ctx_outputs_json(tmp_path: Path) -> None:
    """Integration test for CLI via CliRunner."""
    from click.testing import CliRunner
    from beadloom.services.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["ctx", "PROJ-123", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["focus"]["ref_id"] == "PROJ-123"
```

### Factory for test data

```python
# tests/helpers.py — factory helpers for test data
import sqlite3

def insert_node(
    conn: sqlite3.Connection,
    ref_id: str = "test-node",
    kind: str = "feature",
    summary: str = "Test node",
    source: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        (ref_id, kind, summary, source),
    )

def insert_edge(
    conn: sqlite3.Connection,
    src: str = "a",
    dst: str = "b",
    kind: str = "part_of",
) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src, dst, kind),
    )
```

---

## Testing result

```bash
bd comments add <bead-id> "$(cat <<'EOF'
TESTS:
- Unit: XX passed
- Integration: XX passed
- Coverage: XX%
- Edge cases: [list of checked cases]
- Known limitations: [if any]
EOF
)"
```

---

## Tester checklist

- [ ] Unit tests for all business logic
- [ ] Integration tests for CLI and indexer
- [ ] Edge cases covered (see checklist above)
- [ ] Coverage >= 80% (`--cov-fail-under=80`)
- [ ] Tests are independent (can be run in any order)
- [ ] Tests are fast (unit <10ms, integration <1s)
- [ ] Tests are readable (AAA pattern)
- [ ] Fixtures in `conftest.py`, using `tmp_path`
- [ ] No hardcoded paths (only `tmp_path` / `Path`)
