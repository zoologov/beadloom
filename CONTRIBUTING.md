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
git clone https://github.com/zoologov/beadloom
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
│   ├── context_oracle/    # BFS traversal, code indexer, cache, search
│   ├── doc_sync/          # Doc-code sync engine
│   ├── graph/             # YAML loader, rule engine, import resolver, diff
│   ├── infrastructure/    # SQLite DB, reindex, health snapshots
│   ├── onboarding/        # Bootstrap, doc generation, presets
│   ├── services/
│   │   ├── cli.py         # Click CLI (29 commands)
│   │   └── mcp_server.py  # MCP server (14 tools, stdio)
│   └── tui/               # Interactive terminal dashboard
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
uv run beadloom mcp-serve
```

## Public API

Beadloom follows [Semantic Versioning](https://semver.org/), and the
version number is a promise about this list and nothing else (owner's ruling, 2026-10-08):

1. the commands, their options and their exit codes;
2. the keys of `.beadloom/config.yml`;
3. the keys and the value vocabularies of the JSON outputs: `ctx --json`, `status --json`,
   the debt report (`status --debt-report --json`) and `export`, whose artifact is JSON with
   no option;
4. the MCP tools;
5. the portal data file's schema;
6. the files generated for an adopter.

**Python import paths are not public API.** Modules under `beadloom.*` move when the graph
decomposes them, and no release promises otherwise.

[`docs/guides/public-api.md`](docs/guides/public-api.md) holds the same list with the references
for each item, the stability promise, and the table that turns a change into MAJOR, MINOR or
PATCH. A change to this list is a change to the promise: it is the owner's decision, and the
release that makes it says so in its change log.

## Release Process

Releases are cut by a maintainer (trunk-based; `main` is always green):

1. **Decide the version from the public API.** Classify every change since the last
   release against the [Public API](#public-api) list above, by the table in
   [`docs/guides/public-api.md`](docs/guides/public-api.md#how-a-change-sets-the-version).
   The highest row any change reaches decides MAJOR, MINOR or PATCH. A precedent from an
   earlier release is not a reason.
2. **Bump the version** in `src/beadloom/__init__.py` (`__version__`) — the single
   source of truth, read by `[tool.hatch.version]` and `beadloom --version`. Run
   `beadloom version-surface` before the bump: it lists every place the project states
   its version and the instrument that checks each one. The `Current version` line in
   `.claude/CLAUDE.md` is regenerated by `beadloom setup-agentic-flow`, never edited by
   hand. The `(vX.Y.Z)` in the root node's `summary` in `.beadloom/_graph/beadloom.yml`
   is a CHECKED claim since BDL-062, so `beadloom lint --strict` fails on it rather than
   letting it fall two majors behind unnoticed, which is what it did.
3. **Update `CHANGELOG.md`** — move `[Unreleased]` into a dated `[X.Y.Z]` section,
   with *Breaking* first, then *Added*, *Changed* and *Fixed*, each line naming its pull
   request, and one sentence at the top saying which line made the version what it is.
   The CHANGELOG is where a release is NAMED. A domain document that says "until
   X.Y.Z ..." before X.Y.Z exists states a version nothing can hold it to, and
   `docs audit` reports it stale.
4. **Verify the built wheel on a project that is not this repository.** Build the wheel from
   a clean export of the branch into an empty directory outside the repository, here
   `<export>`, so the wheel lands in `<export>/dist/` and not in the repository's `dist/`.
   Run from the repository root:

   ```bash
   git archive HEAD | tar -x -C <export>
   uv build --wheel <export> --out-dir <export>/dist
   python3 tests/release/verify_the_release.py \
       <export>/dist/beadloom-X.Y.Z-py3-none-any.whl \
       --release X.Y.Z --node-bin <a Node 22+ bin directory>
   ```

   The script installs the artifact with its `languages` extra into a fresh environment with
   `UV_NO_CACHE=1`, writes a throwaway adopter project and runs the release's behaviour on it.
   Exit 0 means every check that ran holds. The three npm checks (`portal build`,
   `portal assets`, `portal lint:fsd`) need Node 22 or later and npm. Without `--node-bin`
   they run only when `PATH` holds both, and otherwise they are skipped: left out of the
   verdict, which then reads `VERDICT: N of N checks that ran hold (exit 0)`, and named under
   it as `Not run by this run: … (<reason>)`. Steps 4 and 7 pass `--node-bin`, which keeps the
   npm checks required in a release: a directory without a Node 22+ and npm stops the run with
   exit 2. Exit 3 means a version check failed; 4 means a behaviour check failed; 2 means the
   run could not start or a step could not run, so the checks it did not reach were not
   judged.
   When a run has more than one, the exit is the first of 3, 4, 2: a check that ran and failed
   already settles that the artifact is not the release. So an exit 2 means no check that ran
   failed, and the run is repeated once the step it names can run. Pass `--release`: its
   default is the release the script was last updated for.
5. **Open one PR to `main`** and merge when `beadloom ci` (the required check) is green.
6. **Create a GitHub Release** tagged `vX.Y.Z` — this triggers `.github/workflows/pypi-publish.yml`
   (build → TestPyPI → PyPI). The version is read from `__version__`.
7. **Verify the downloaded release**, the same way, on the pin rather than the wheel:

   ```bash
   python3 tests/release/verify_the_release.py beadloom==X.Y.Z \
       --release X.Y.Z --node-bin <a Node 22+ bin directory>
   ```

   This is the artifact adopters install, so a green step 4 does not stand in for it. Exit 3
   with "the index holds no beadloom==X.Y.Z" right after the upload is the index not serving
   the new version yet; run it again once it does.
8. **The portal** redeploys from `main` via `deploy-site.yml` (`beadloom docs site` + VitePress).

When removing a top-level directory, grep every `.github/workflows/*` and `.gitlab-ci.yml`
for stale path references before releasing.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

Be respectful and professional in all interactions. We're here to build something great together.

---

Thank you for contributing to Beadloom!
