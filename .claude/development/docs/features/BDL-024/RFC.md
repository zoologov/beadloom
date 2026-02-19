# RFC: BDL-024 — Architecture Debt Report

> **Status:** Approved
> **Created:** 2026-02-20

---

## Overview

Add a single command (`beadloom status --debt-report`) that aggregates all architecture health signals into a quantified debt report with a numeric score 0-100, category breakdown, trend tracking, and CI gate support. Expose via MCP tool for AI agent consumption.

## Motivation

### Problem
Architecture debt signals are scattered across 4 commands (`lint`, `sync-check`, `doctor`, `status`). Each gives a partial view — lint violations here, stale docs there, complexity smells elsewhere. No aggregated metric exists to answer "how healthy is our architecture?" or track debt over time.

### Solution
A new `debt_report` module in the `infrastructure` domain that:
1. Collects data from all existing sources (lint, sync, doctor, git activity, test mapping)
2. Computes a weighted debt score with configurable formula
3. Renders human-readable Rich output or machine-readable JSON
4. Provides CI gate via `--fail-if` flag
5. Shows trend vs last snapshot
6. Exposes via MCP tool `get_debt_report`

## Technical Context

### Constraints
- Python 3.10+
- SQLite (WAL mode)
- All data sources already exist in v1.7 — no new storage tables needed
- Must not break existing `beadloom status` output (additive flag)
- Configurable weights in `config.yml` (with sensible defaults)

### Affected Areas
- `infrastructure` domain — new `debt_report.py` module
- `services/cli.py` — extend `status` command with `--debt-report`, `--fail-if`, `--trend`, `--category` flags
- `services/mcp_server.py` — new `get_debt_report` tool
- `onboarding/config_reader.py` — may need extension for `debt_report` config section (or use separate loader)

## Proposed Solution

### Approach

**New module:** `src/beadloom/infrastructure/debt_report.py`

Core function chain:
```
collect_debt_data(conn, project_root) → DebtData
compute_debt_score(data, weights) → DebtReport
format_debt_report(report) → str (Rich)
format_debt_json(report) → dict
```

**Data structures (frozen dataclasses):**

```python
@dataclass(frozen=True)
class CategoryScore:
    name: str           # "rule_violations", "doc_gaps", "complexity", "test_gaps"
    score: float        # weighted points
    details: dict       # category-specific breakdown

@dataclass(frozen=True)
class NodeDebt:
    ref_id: str
    score: float
    reasons: list[str]  # ["2 violations", "stale doc", "oversized"]

@dataclass(frozen=True)
class DebtTrend:
    previous_snapshot: str    # ISO date
    previous_score: float
    delta: float
    category_deltas: dict[str, float]

@dataclass(frozen=True)
class DebtReport:
    debt_score: float         # 0-100
    severity: str             # clean/low/medium/high/critical
    categories: list[CategoryScore]
    top_offenders: list[NodeDebt]
    trend: DebtTrend | None   # None if no previous snapshot
```

**Debt score formula (from Strategy 5.10):**

```
debt_score = min(100, Σ category_scores)

category_scores:
  rule_violations = (error_count × 3) + (warning_count × 1)
  doc_gaps        = (undocumented × 2) + (stale × 1) + (untracked × 0.5)
  complexity      = (oversized × 2) + (high_fan_out × 1) + (dormant × 0.5)
  test_gaps       = (untested × 1)

severity:
  0       = clean    ✓
  1-10    = low      ●
  11-25   = medium   ▲
  26-50   = high     ◆
  51-100  = critical ✖
```

**Weight configuration (config.yml):**

```yaml
debt_report:
  weights:
    rule_error: 3
    rule_warning: 1
    undocumented_node: 2
    stale_doc: 1
    untracked_file: 0.5
    oversized_domain: 2
    high_fan_out: 1
    dormant_domain: 0.5
    untested_domain: 1
  thresholds:
    oversized_symbols: 200
    high_fan_out: 10
    dormant_months: 3
```

### Data Collection Sources

| Category | Source function | Module |
|----------|---------------|--------|
| Rule violations | `evaluate_all(conn, rules)` → `list[Violation]` | `graph/rule_engine.py` |
| Doc gaps — undocumented | Nodes without `docs` in services.yml | `doc_sync/engine.py` |
| Doc gaps — stale | `check_sync(conn, project_root)` → status=stale | `doc_sync/engine.py` |
| Complexity — oversized | Symbol count per node from `code_symbols` table | `infrastructure/db.py` |
| Complexity — fan-out | Edge count per node from `edges` table | `graph/loader.py` |
| Complexity — dormant | `analyze_git_activity()` → activity_level=dormant | `infrastructure/git_activity.py` |
| Test gaps | `map_tests()` → coverage_estimate=none | `context_oracle/test_mapper.py` |

### Changes

| File / Module | Change |
|---------------|--------|
| `src/beadloom/infrastructure/debt_report.py` | NEW — core debt calculation engine |
| `src/beadloom/services/cli.py` | Add `--debt-report`, `--fail-if`, `--trend`, `--category` to `status` |
| `src/beadloom/services/mcp_server.py` | Add `get_debt_report` tool |
| `tests/test_debt_report.py` | NEW — unit + integration tests |

### API Changes

**CLI:**
```bash
beadloom status --debt-report              # human-readable Rich output
beadloom status --debt-report --json       # machine JSON
beadloom status --debt-report --fail-if=score>30
beadloom status --debt-report --fail-if=errors>0
beadloom status --debt-report --trend      # vs last snapshot
beadloom status --debt-report --category=docs,rules
```

**MCP:**
```python
# New tool: get_debt_report
# Arguments: { "trend": bool, "category": str | None }
# Returns: DebtReport as JSON dict
```

**Public API:**
```python
def collect_debt_data(conn: sqlite3.Connection, project_root: Path) -> DebtData: ...
def compute_debt_score(data: DebtData, weights: DebtWeights | None = None) -> DebtReport: ...
def format_debt_report(report: DebtReport) -> str: ...
def format_debt_json(report: DebtReport) -> dict[str, Any]: ...
def load_debt_weights(project_root: Path) -> DebtWeights: ...
```

## Alternatives Considered

### Option A: New top-level command `beadloom debt`
Pros: clean namespace. Cons: adds another command to learn; `status` already shows project overview and debt is logically an extension. **Rejected** — per Strategy decision: extend `status`.

### Option B: Separate config file `debt.yml`
Pros: isolation. Cons: yet another config file; beadloom already has `config.yml` precedent. **Rejected** — use `config.yml` section.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Weight formula produces unintuitive scores | Medium | Medium | Sensible defaults + config override + test with beadloom itself |
| Data collection slow on large repos | Low | Low | All sources already cached in SQLite; no new I/O |
| `--fail-if` parsing edge cases | Low | Medium | Strict regex, clear error messages, tested |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Config loading: extend `config_reader.py` or new loader? | Decided: new `load_debt_weights()` in debt_report.py reads `config.yml` `debt_report` section via yaml.safe_load. Simple, isolated |
| Q2 | Where to place module? | Decided: `infrastructure/debt_report.py` — aggregates infrastructure-level data |
| Q3 | Trend: recompute from snapshot or store score? | Decided: recompute score from snapshot data (no new storage). Snapshots already have full graph state |
