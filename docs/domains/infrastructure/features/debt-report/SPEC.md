# Debt Report

Architecture debt aggregation, scoring, and trend tracking.

Source: `src/beadloom/infrastructure/debt_report.py`

## Specification

### Purpose

The debt report module aggregates all architecture health signals (lint violations, documentation gaps, complexity smells, test coverage gaps) into a single quantified debt score (0-100) with category breakdown, per-node top offenders, and trend tracking against graph snapshots. It provides a unified answer to "how healthy is our architecture?" and supports CI gating via the `--fail-if` flag on the CLI.

### Debt Score Formula

```
debt_score = min(100, sum(category_scores))

category_scores:
  rule_violations = (error_count * rule_error) + (warning_count * rule_warning)
  doc_gaps        = (undocumented * undocumented_node) + (stale * stale_doc)
                  + (untracked * untracked_file)
  complexity      = (oversized * oversized_domain) + (high_fan_out * high_fan_out)
                  + (dormant * dormant_domain)
  test_gaps       = (untested * untested_domain)
```

Default weights (configurable via `config.yml` `debt_report` section):

| Weight | Default | Description |
|--------|---------|-------------|
| `rule_error` | 3.0 | Per lint error |
| `rule_warning` | 1.0 | Per lint warning |
| `undocumented_node` | 2.0 | Per node without docs |
| `stale_doc` | 1.0 | Per stale doc-code pair |
| `untracked_file` | 0.5 | Per untracked source file |
| `oversized_domain` | 2.0 | Per oversized domain |
| `high_fan_out` | 1.0 | Per high fan-out node |
| `dormant_domain` | 0.5 | Per dormant domain |
| `untested_domain` | 1.0 | Per untested domain |

Default thresholds:

| Threshold | Default | Description |
|-----------|---------|-------------|
| `oversized_symbols` | 200 | Symbol count above which a domain is oversized |
| `high_fan_out` | 10 | Edge count above which a node has high fan-out |
| `dormant_months` | 3 | Months without git activity for dormant classification |

### Severity Classification

| Score Range | Severity | Indicator |
|-------------|----------|-----------|
| 0 | clean | check mark (green) |
| 1-10 | low | filled circle (yellow) |
| 11-25 | medium | triangle (yellow) |
| 26-50 | high | diamond (red) |
| 51-100 | critical | X mark (red bold) |

### Data Structures

#### DebtWeights (frozen dataclass)

Per-item weights and thresholds for debt score computation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rule_error` | `float` | 3.0 | Weight for lint errors |
| `rule_warning` | `float` | 1.0 | Weight for lint warnings |
| `undocumented_node` | `float` | 2.0 | Weight for undocumented nodes |
| `stale_doc` | `float` | 1.0 | Weight for stale docs |
| `untracked_file` | `float` | 0.5 | Weight for untracked files |
| `oversized_domain` | `float` | 2.0 | Weight for oversized domains |
| `high_fan_out` | `float` | 1.0 | Weight for high fan-out nodes |
| `dormant_domain` | `float` | 0.5 | Weight for dormant domains |
| `untested_domain` | `float` | 1.0 | Weight for untested domains |
| `oversized_symbols` | `int` | 200 | Oversized threshold |
| `high_fan_out_threshold` | `int` | 10 | Fan-out threshold |
| `dormant_months` | `int` | 3 | Dormant threshold (months) |

#### DebtData (frozen dataclass)

Raw counts aggregated from all data sources.

| Field | Type | Description |
|-------|------|-------------|
| `error_count` | `int` | Lint rule errors |
| `warning_count` | `int` | Lint rule warnings |
| `undocumented_count` | `int` | Nodes without docs |
| `stale_count` | `int` | Stale sync pairs |
| `untracked_count` | `int` | Untracked source files |
| `oversized_count` | `int` | Oversized domains |
| `high_fan_out_count` | `int` | High fan-out nodes |
| `dormant_count` | `int` | Dormant domains |
| `untested_count` | `int` | Untested domains |
| `node_issues` | `dict[str, list[str]]` | Per-node issue tracking for top offenders |

#### CategoryScore (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Category: `rule_violations`, `doc_gaps`, `complexity`, `test_gaps` |
| `score` | `float` | Weighted score for this category |
| `details` | `dict[str, int \| float]` | Per-item breakdown (e.g. `{"errors": 2, "warnings": 1}`) |

#### NodeDebt (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `ref_id` | `str` | Graph node reference ID |
| `score` | `float` | Debt contribution for this node |
| `reasons` | `list[str]` | Issue reasons (e.g. `["undocumented", "stale_doc"]`) |

#### DebtTrend (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `previous_snapshot` | `str` | Display string for the previous snapshot (ISO date + optional label) |
| `previous_score` | `float` | Debt score from previous snapshot |
| `delta` | `float` | Change in overall debt score |
| `category_deltas` | `dict[str, float]` | Per-category score changes |

#### DebtReport (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `debt_score` | `float` | Overall debt score, 0-100 |
| `severity` | `str` | Severity label: clean/low/medium/high/critical |
| `categories` | `list[CategoryScore]` | Four category scores |
| `top_offenders` | `list[NodeDebt]` | Top 10 nodes ranked by debt contribution |
| `trend` | `DebtTrend \| None` | Trend vs last snapshot, or `None` |

### Data Collection Sources

| Category | Source | Module |
|----------|--------|--------|
| Rule violations | `evaluate_all(conn, rules)` | `graph/rule_engine.py` |
| Doc gaps -- undocumented | Nodes without docs (LEFT JOIN) | `infrastructure/debt_report.py` |
| Doc gaps -- stale | `sync_state` entries with `status='stale'` | `infrastructure/debt_report.py` |
| Doc gaps -- untracked | Nodes with source but no sync_state | `infrastructure/debt_report.py` |
| Complexity -- oversized | Symbol count per node vs threshold | `infrastructure/debt_report.py` |
| Complexity -- fan-out | Edge count per node vs threshold | `infrastructure/debt_report.py` |
| Complexity -- dormant | `analyze_git_activity()` with dormant level | `infrastructure/git_activity.py` |
| Test gaps | `map_tests()` with coverage_estimate=none | `context_oracle/test_mapper.py` |

### Top Offenders

`compute_top_offenders()` ranks individual graph nodes by their weighted debt contribution. Each node's score is computed from its issue list in `DebtData.node_issues`:

- `"violation:error:<rule>"` -- weighted by `rule_error`
- `"violation:warning:<rule>"` -- weighted by `rule_warning`
- Issue keywords (`undocumented`, `stale_doc`, `oversized`, `high_fan_out`, `dormant`, `untested`) -- weighted via `_ISSUE_WEIGHT_MAP`

Nodes are sorted by descending score (ties broken alphabetically by ref_id). Default limit: 10 nodes.

### Trend Tracking

`compute_debt_trend()` compares the current debt report against the most recent graph snapshot. Snapshot data contains structural information (nodes, edges, symbol count) but does not include dynamic data (rules, docs, tests). Therefore:

- The **complexity** category is recomputed from snapshot edges (high fan-out).
- The **rule_violations**, **doc_gaps**, and **test_gaps** categories are set to 0 for the snapshot (not computable from snapshot data).

Trend output shows per-category directional arrows: improved (down arrow), regressed (up arrow), or unchanged (equals sign).

### Config Loading

`load_debt_weights()` reads the `debt_report` section from `config.yml` at the project root. The section has two subsections: `weights` (per-item multipliers) and `thresholds`. Missing keys fall back to defaults. Missing file or invalid YAML also falls back to defaults.

Example `config.yml`:

```yaml
debt_report:
  weights:
    rule_error: 3
    rule_warning: 1
    undocumented_node: 2
    stale_doc: 1
  thresholds:
    oversized_symbols: 200
    high_fan_out: 10
    dormant_months: 3
```

### Category Short Names

The `--category` CLI flag and MCP `category` argument accept short names mapped to internal names:

| Short Name | Internal Name |
|------------|---------------|
| `rules` | `rule_violations` |
| `docs` | `doc_gaps` |
| `complexity` | `complexity` |
| `tests` | `test_gaps` |

### CLI Interface

```
beadloom status --debt-report [--json] [--fail-if=EXPR] [--category=NAME] [--project DIR]
```

- `--debt-report`: Show debt report instead of standard status.
- `--json`: Output as structured JSON.
- `--fail-if=EXPR`: CI gate. Expressions: `score>N`, `errors>N`. Exits with code 1 if condition is met.
- `--category=NAME`: Filter to one category.

### MCP Interface

Tool: `get_debt_report`

Arguments:
- `trend` (bool, default false): Include trend vs last snapshot.
- `category` (string, optional): Filter to a specific category.

Returns JSON with: `debt_score`, `severity`, `categories`, `top_offenders`, `trend`.

### Output Formats

**Rich (human-readable)**:
- Header panel: "Architecture Debt Report"
- Score line with severity indicator and label
- Category breakdown with per-item detail lines (tree-style prefixes)
- Top offenders table (rank, node, score, reasons)

**JSON (machine-readable)**:
- `debt_score`: float
- `severity`: string
- `categories`: list of `{name, score, details}`
- `top_offenders`: list of `{ref_id, score, reasons}`
- `trend`: null or `{previous_snapshot, previous_score, delta, category_deltas}`

## API

### Public Functions

```python
def load_debt_weights(project_root: Path) -> DebtWeights
```
Load debt weights from `config.yml` `debt_report` section, falling back to defaults.

```python
def collect_debt_data(
    conn: sqlite3.Connection,
    project_root: Path,
    weights: DebtWeights | None = None,
) -> DebtData
```
Aggregate raw counts from all data sources (lint, sync, doctor, git activity, test mapper).

```python
def compute_debt_score(
    data: DebtData,
    weights: DebtWeights | None = None,
) -> DebtReport
```
Apply the weighted formula to produce a complete debt report. Caps score at 100.

```python
def compute_top_offenders(
    data: DebtData,
    weights: DebtWeights,
    limit: int = 10,
) -> list[NodeDebt]
```
Rank nodes by their debt contribution and return the top N.

```python
def compute_debt_trend(
    conn: sqlite3.Connection,
    current_report: DebtReport,
    project_root: Path,
    weights: DebtWeights | None = None,
) -> DebtTrend | None
```
Compare current debt against the last snapshot. Returns `None` if no snapshot exists.

```python
def format_debt_report(report: DebtReport) -> str
```
Render a debt report as Rich-formatted terminal output.

```python
def format_trend_section(trend: DebtTrend | None) -> str
```
Render trend data as plain text with directional arrows.

```python
def format_debt_json(
    report: DebtReport,
    category: str | None = None,
) -> dict[str, Any]
```
Serialize a debt report to a JSON-safe dict with optional category filter.

```python
def format_top_offenders_json(
    offenders: list[NodeDebt],
) -> list[dict[str, object]]
```
Serialize a list of `NodeDebt` to JSON-safe dicts.

### Public Classes

```python
@dataclass(frozen=True)
class DebtWeights: ...

@dataclass(frozen=True)
class DebtData: ...

@dataclass(frozen=True)
class CategoryScore: ...

@dataclass(frozen=True)
class NodeDebt: ...

@dataclass(frozen=True)
class DebtTrend: ...

@dataclass(frozen=True)
class DebtReport: ...
```

## Invariants

- The debt score is always clamped to the range [0, 100].
- All four categories (rule_violations, doc_gaps, complexity, test_gaps) are always present in `DebtReport.categories`, even when their score is 0.
- `compute_debt_score` never modifies the database. All data collection is read-only.
- `load_debt_weights` always returns a valid `DebtWeights` instance, even with missing or malformed config files.
- Top offenders are sorted by descending score with alphabetical ref_id tiebreaking for deterministic output.
- Trend computation is based on structural snapshot data only; categories not stored in snapshots (rules, docs, tests) have 0 as the previous value.
- Each private data collection helper (`_count_undocumented`, `_count_stale`, etc.) gracefully handles import failures or missing tables, returning zero counts.

## Constraints

- Requires a populated SQLite database. Running the debt report before `beadloom reindex` will produce a zero score (no data to aggregate).
- Trend tracking depends on at least one graph snapshot existing (created by `beadloom snapshot save` or automatically during reindex).
- Trend comparisons for non-structural categories (rules, docs, tests) always show zero for the previous snapshot since these are not captured in snapshot data.
- The `--fail-if` CI gate only supports two expressions: `score>N` and `errors>N`. Other expressions produce an error.
- Weight configuration lives in `config.yml` under the `debt_report` key. The module reads `config.yml` from the project root, not from `.beadloom/`.

## Testing

Test file: `tests/test_debt_report.py`

Tests should cover the following scenarios:

- **Zero debt**: Verify that an empty/healthy graph produces a debt score of 0 with severity `clean`.
- **Severity boundaries**: Verify correct severity labels at boundaries (0, 1, 10, 11, 25, 26, 50, 51).
- **Category scoring**: Verify each category independently contributes the correct weighted score.
- **Score capping**: Verify that extreme values are capped at 100.
- **Config loading**: Verify loading weights from `config.yml`, including missing file, missing section, and partial overrides.
- **Top offenders**: Verify ranking by score, tiebreaking by ref_id, and limit enforcement.
- **Per-node issue tracking**: Verify that `violation:error:*`, `violation:warning:*`, and issue keywords are correctly weighted.
- **Trend computation**: Verify delta calculation when a snapshot exists, and `None` return when no snapshot exists.
- **Format JSON**: Verify JSON serialization with and without category filter.
- **Format Rich**: Verify that Rich output contains expected sections (header, score, categories, offenders).
- **Category short names**: Verify that short names (`rules`, `docs`, `tests`) map correctly to internal names.
