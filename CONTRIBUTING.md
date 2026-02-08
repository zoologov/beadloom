# Contributing to Beadloom

Thank you for your interest in contributing to Beadloom! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Getting Started

```bash
# Clone the repository
git clone https://github.com/your-org/beadloom
cd beadloom

# Install in development mode with all dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linter
uv run ruff check src/ tests/

# Run type checker
uv run mypy

# Install globally for CLI usage
uv tool install -e .
```

## Project Structure

```
beadloom/
├── src/beadloom/          # Main package
│   ├── cli.py             # Click CLI commands
│   ├── db.py              # SQLite schema and helpers
│   ├── graph_loader.py    # YAML graph loader
│   ├── doc_indexer.py     # Markdown documentation indexer
│   ├── code_indexer.py    # tree-sitter code indexer
│   ├── reindex.py         # Full reindex orchestrator
│   ├── context_builder.py # BFS context bundle builder
│   ├── sync_engine.py     # Doc-code sync engine
│   └── mcp_server.py      # MCP server (stdio)
├── tests/                 # pytest test suite
├── docs/                  # Project documentation (indexed by beadloom)
├── .beadloom/             # Beadloom data directory
│   └── _graph/            # YAML graph definitions
└── pyproject.toml         # Project configuration
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=beadloom --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_sync_engine.py -v

# Run tests matching a pattern
uv run pytest -k "test_stale" -v
```

## Code Style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for lint issues
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/
```

### Type Checking

We use mypy in strict mode:

```bash
uv run mypy
```

### Style Guidelines

- Follow PEP 8 conventions (enforced by ruff)
- Use type annotations for all function signatures
- Keep functions small and focused
- Write clear, descriptive variable names
- Add docstrings for public functions and classes
- Avoid `Any` / `# type: ignore` without a clear reason
- No bare `except:` — always specify exception types
- No mutable default arguments (`def f(x=[]):`)
- No `import *`
- No `print()` / `breakpoint()` in committed code

## Making Changes

### Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run tests, linter, and type checker locally
6. Commit your changes with clear messages
7. Push to your fork
8. Open a pull request

### Commit Messages

Write clear, concise commit messages:

```
feat: add cycle detection for dependency graphs

- Implement recursive CTE-based cycle detection
- Add tests for simple and complex cycles
- Update documentation with examples
```

Prefix types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.

### Important: Don't Include .beadloom/ Database Changes

The `.beadloom/beadloom.db` file is the local index database. It is gitignored and should never be committed. The `.beadloom/_graph/` YAML files are tracked — changes to these are welcome.

### Pull Requests

- Keep PRs focused on a single feature or fix
- Include tests for new functionality
- Update documentation as needed
- Ensure CI passes before requesting review
- Respond to review feedback promptly
- Maintain or improve test coverage (target: 80%+)

## Testing Guidelines

### Writing Tests

We follow the AAA (Arrange-Act-Assert) pattern:

```python
def test_build_sync_state_creates_pairs(conn, project):
    # Arrange
    _setup_linked_data(conn, project)

    # Act
    pairs = build_sync_state(conn)

    # Assert
    assert len(pairs) >= 1
    assert pairs[0].ref_id == "F1"
```

Guidelines:

- Use pytest fixtures for shared setup
- Use `tmp_path` for filesystem tests
- Write descriptive test names that explain what is being tested
- Use parametrize for testing multiple scenarios
- Clean up resources in fixtures (use `yield` for teardown)
- Test both success and error paths

## Documentation

- Update `docs/` for user-facing changes (these files are indexed by beadloom itself)
- Update `README.md` for installation or usage changes
- Add inline code comments for complex logic
- Include examples in documentation

## Feature Requests and Bug Reports

### Reporting Bugs

Include in your bug report:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Version of beadloom (`beadloom --version`)
- Python version and operating system

### Feature Requests

When proposing new features:
- Explain the use case
- Describe the proposed solution
- Consider backwards compatibility
- Discuss alternatives you've considered

## Code Review Process

All contributions go through code review:

1. Automated checks (tests, lint, type checking) must pass
2. At least one maintainer approval required
3. Address review feedback
4. Maintainer will merge when ready

## Development Tips

### Testing Locally

```bash
# Build and test your changes quickly
uv run beadloom init
uv run beadloom reindex
uv run beadloom status
uv run beadloom ctx <ref_id>
```

### Database Inspection

```bash
# Inspect the SQLite database directly
sqlite3 .beadloom/beadloom.db

# Useful queries
SELECT * FROM nodes;
SELECT * FROM edges;
SELECT ref_id, kind, summary FROM nodes WHERE kind = 'feature';
SELECT * FROM sync_state WHERE status = 'stale';
```

### MCP Server Testing

```bash
# Run the MCP server for testing
uv run beadloom mcp
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

Be respectful and professional in all interactions. We're here to build something great together.

---

Thank you for contributing to Beadloom!
