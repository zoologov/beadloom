# Documentation Audit

Zero-config detection of stale facts in project markdown documentation.

Source: `src/beadloom/doc_sync/audit.py`, `src/beadloom/doc_sync/scanner.py`

## Specification

### Purpose

The documentation audit feature detects stale numeric facts in markdown documentation by comparing mentioned values against ground-truth data extracted from the project. It uses a two-pass architecture: first collecting facts from project infrastructure (manifest files, graph DB, code symbols, MCP tools, CLI commands), then scanning documentation for keyword-proximate numbers and version strings, and finally comparing the two to produce stale/fresh findings.

### Architecture

The audit pipeline has three stages:

1. **FactRegistry** (`audit.py`) -- Collects ground-truth facts from multiple project data sources: `pyproject.toml` (version), graph DB (node/edge/test/framework/rule counts), MCP server introspection (tool count), Click CLI introspection (command count), and code_symbols (language count). Extra facts can be injected via `config.yml`.

2. **DocScanner** (`scanner.py`) -- Scans markdown files for numeric and version string mentions using keyword-proximity matching. Each mention is associated with a fact type based on nearby keywords within a configurable proximity window. False positives (dates, hex colors, issue IDs, line references, version pins) are masked before extraction.

3. **Comparator** (`compare_facts` in `audit.py`) -- Matches mentions against facts and applies configurable tolerances. Version strings require exact match; numeric facts support percentage-based tolerances (e.g., +/-10% for growing metrics like node_count).

### Fact Types

| Fact Name | Source | Default Tolerance | Description |
|-----------|--------|-------------------|-------------|
| `version` | `pyproject.toml` / `package.json` / `Cargo.toml` | 0.0 (exact) | Project version string |
| `node_count` | graph DB `nodes` table | 0.10 (+/-10%) | Total graph nodes |
| `edge_count` | graph DB `edges` table | 0.10 (+/-10%) | Total graph edges |
| `language_count` | `code_symbols` file extensions | 0.0 (exact) | Distinct programming languages |
| `test_count` | `nodes.extra` JSON `tests.test_count` | 0.05 (+/-5%) | Total test count |
| `framework_count` | `nodes.extra` JSON `tests.framework` | 0.0 (exact) | Nodes with detected test frameworks |
| `mcp_tool_count` | MCP server `_TOOLS` introspection | 0.0 (exact) | Number of MCP tools |
| `cli_command_count` | Click main group recursive traversal | 0.0 (exact) | Number of CLI commands |
| `rule_type_count` | graph DB `rules` table | 0.0 (exact) | Number of architecture rules |

### False-Positive Filtering

The DocScanner masks the following patterns before number extraction to prevent false matches:

| Pattern | Example | Regex |
|---------|---------|-------|
| ISO dates | `2026-02-19` | `\b\d{4}-\d{2}-\d{2}\b` |
| Month-year dates | `Feb 2026` | Month name + 4-digit year |
| Issue IDs | `#123`, `BDL-021` | `#\d+`, `[A-Z]+-\d+` |
| Hex colors | `#FF0000` | `#[0-9a-fA-F]{3,8}` |
| Hex literals | `0xFF` | `0x[0-9a-fA-F]+` |
| Version pins | `>=0.80`, `^1.2.3` | Operator + version |
| Line references | `:15`, `line 42`, `L42` | Various patterns |

Numbers 0 and 1 are always skipped as too common and ambiguous.

### Keyword-Proximity Matching

The DocScanner uses a sliding window of `PROXIMITY_WINDOW = 5` word positions around each detected number. If any keyword associated with a fact type appears within this window, the number is classified as a mention of that fact type.

Each fact type has a list of associated keywords:

| Fact Type | Keywords |
|-----------|----------|
| `language_count` | language, lang, programming language |
| `mcp_tool_count` | MCP, tool, server tool |
| `cli_command_count` | command, CLI, subcommand |
| `rule_type_count` | rule type, rule kind, rule |
| `node_count` | node, module, domain, component |
| `edge_count` | edge, dependency, connection |
| `test_count` | test, spec, assertion |
| `framework_count` | framework, supported framework |

Keywords use prefix matching (e.g., "language" matches "languages").

### Tolerance System

Tolerances control how much a mentioned value may deviate from the ground truth before being flagged as stale:

- **Exact match** (tolerance = 0.0): The mentioned integer must equal the ground truth exactly.
- **Percentage tolerance** (tolerance > 0.0): The mentioned value must fall within `[actual * (1 - t), actual * (1 + t)]`.
- **Version strings**: Always exact string comparison (leading `v` prefix is stripped).
- **Special case**: When the ground truth is 0, only an exact match of 0 is accepted (regardless of tolerance).

Tolerances are merged in order: built-in defaults, then user overrides from `config.yml`.

### Data Structures

#### Fact (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Fact identifier (e.g., `"version"`, `"node_count"`) |
| `value` | `str \| int` | Ground-truth value |
| `source` | `str` | Human-readable origin (e.g., `"pyproject.toml"`, `"graph DB"`) |

#### Mention (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `fact_name` | `str` | Associated fact type |
| `value` | `str \| int` | Mentioned value |
| `file` | `Path` | Source markdown file |
| `line` | `int` | Line number |
| `context` | `str` | Stripped line content for display |

#### AuditFinding (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `mention` | `Mention` | The documentation mention |
| `fact` | `Fact` | The ground-truth fact it was compared against |
| `status` | `str` | `"stale"` or `"fresh"` |
| `tolerance` | `float` | Applied tolerance |

#### AuditResult (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `facts` | `dict[str, Fact]` | All collected ground-truth facts |
| `findings` | `list[AuditFinding]` | Findings for matched mentions |
| `unmatched` | `list[Mention]` | Mentions with no corresponding fact |

### CLI Interface

```
beadloom docs audit [--json] [--fail-if EXPR] [--stale-only] [--verbose] [--path GLOB] [--project DIR]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json` | flag | `False` | Output results as structured JSON |
| `--fail-if` | `str` | `None` | CI gate expression (e.g., `stale>0`, `stale>=5`) |
| `--stale-only` | flag | `False` | Show only stale findings |
| `--verbose` | flag | `False` | Include extra detail (unmatched mentions, fact sources) |
| `--path` | `str` (multiple) | `None` | Override default scan paths with custom glob patterns |
| `--project` | `Path` | current directory | Project root |

The `--fail-if` expression supports the `stale` metric with `>` and `>=` operators. When the condition is met, the command exits with code 1.

### Configuration

Tolerance overrides and extra facts are configured in `.beadloom/config.yml`:

```yaml
docs_audit:
  tolerances:
    test_count: 0.10
    node_count: 0.05
  extra_facts:
    custom_metric:
      value: 42
      source: "manual config"
```

- `tolerances`: Per-fact tolerance overrides merged on top of built-in defaults.
- `extra_facts`: User-defined facts with a `value` (str or int) and optional `source` label.

### Debt Report Integration

The docs audit contributes to the debt report under the `meta_doc_staleness` category. Stale findings from the audit increase the architecture debt score.

### Default Scan Paths

The DocScanner resolves markdown files using these default glob patterns:

- `*.md` -- Root-level markdown files
- `docs/**/*.md` -- All markdown files under `docs/`
- `.beadloom/*.md` -- Beadloom configuration markdown files

`CHANGELOG.md` is always excluded. Directories `.git`, `__pycache__`, `.venv`, `venv`, and `node_modules` are also excluded.

## API

### Public Functions

```python
def run_audit(
    project_root: Path,
    db: sqlite3.Connection,
    *,
    scan_paths: list[str] | None = None,
) -> AuditResult
```
Full audit facade: collect facts, scan docs, compare. Loads tolerance overrides from config if present.

```python
def compare_facts(
    facts: dict[str, Fact],
    mentions: list[Mention],
    tolerances: dict[str, float] | None = None,
) -> AuditResult
```
Compare mentions against ground-truth facts with configurable tolerances.

```python
def parse_fail_condition(expr: str) -> tuple[str, str, int]
```
Parse a `--fail-if` expression. Returns `(metric, operator, threshold)`. Raises `click.BadParameter` on invalid input.

### Public Classes

```python
class FactRegistry:
    def collect(self, project_root: Path, db: sqlite3.Connection) -> dict[str, Fact]: ...

class DocScanner:
    def scan(self, paths: list[Path]) -> list[Mention]: ...
    def scan_file(self, file_path: Path) -> list[Mention]: ...
    def resolve_paths(self, project_root: Path, scan_globs: list[str] | None = None) -> list[Path]: ...

@dataclass(frozen=True)
class Fact: ...

@dataclass(frozen=True)
class Mention: ...

@dataclass(frozen=True)
class AuditFinding: ...

@dataclass(frozen=True)
class AuditResult: ...
```

## Invariants

- `FactRegistry.collect` never raises; each data source is wrapped in try/except and silently omitted on failure.
- Version extraction uses a priority fallback: `pyproject.toml` > `package.json` > `Cargo.toml` (first match wins).
- The DocScanner skips code blocks (lines between triple-backtick fences).
- False-positive masking replaces matched patterns with spaces of equal length to preserve character positions.
- Each number in a line is matched to at most one fact type (first keyword match wins).
- Tolerance merging order: built-in `DEFAULT_TOLERANCES` < user overrides from config.
- When ground truth is 0 and tolerance > 0, only an exact mention of 0 is accepted.

## Constraints

- Requires a populated SQLite database. Running the audit before `beadloom reindex` will produce no findings (no facts to collect from DB).
- Keyword-proximity matching is heuristic; it may produce false positives for numbers near unrelated keywords.
- The scanner only processes `.md` files; other documentation formats are not supported.
- Version detection relies on regex, not full TOML/JSON parsing, which may miss edge cases.
- The `--fail-if` expression only supports the `stale` metric with `>` and `>=` operators.

## Testing

Test files: `tests/test_docs_audit.py`, `tests/test_doc_scanner.py`

Key scenarios:

- **Fact collection**: Verify facts are collected from pyproject.toml, graph DB, MCP tools, CLI commands.
- **Version extraction**: Verify semantic versions are detected and version pins are ignored.
- **Number extraction**: Verify keyword-proximity matching for each fact type.
- **False-positive masking**: Verify dates, issue IDs, hex colors, line refs are masked.
- **Tolerance comparison**: Verify exact match, percentage tolerance, and zero-value special case.
- **Code block skipping**: Verify numbers inside code fences are ignored.
- **Config loading**: Verify tolerance overrides and extra facts from config.yml.
- **Full audit pipeline**: Verify `run_audit` end-to-end with stale and fresh findings.
- **Fail condition parsing**: Verify valid and invalid `--fail-if` expressions.
