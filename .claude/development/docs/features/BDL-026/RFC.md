# RFC: BDL-026 — Documentation Audit (Phase 12.11)

> **Status:** Approved
> **Created:** 2026-02-20

---

## Overview

Add a `beadloom docs audit` command that automatically detects stale facts in project-level documentation (README, guides, AGENTS.md). The feature computes ground truth from existing Beadloom infrastructure (manifest, graph DB, code symbols) and compares it against numeric mentions found in markdown files via keyword-proximity matching. Ships as experimental in v1.8.

## Motivation

### Problem
After every release, meta-documentation contains wrong version numbers, outdated tool/command counts, and stale feature metrics. `sync-check` covers node-level docs but not project-level files. Manual audit is error-prone and doesn't scale — BDL-022 required 6 parallel agents to fix stale facts across 10 files.

### Solution
Two-pass architecture: (1) Fact Registry computes ground truth from project state, (2) Doc Scanner extracts numeric mentions from markdown and matches them to facts via keyword proximity. Comparison produces stale/fresh/unmatched results with configurable tolerance.

## Technical Context

### Constraints
- Python 3.10+, SQLite (WAL mode)
- Zero-config: works without any user configuration
- Must integrate with existing `docs` CLI group and debt report
- Experimental: API may change in v1.9

### Affected Areas
- `doc_sync/` — new `audit.py` module (fact registry + doc scanner + comparator)
- `services/cli.py` — new `docs audit` subcommand (in existing `@docs` group, line ~1617)
- `infrastructure/debt_report.py` — new `meta_doc_staleness` category in debt score
- `.beadloom/config.yml` — optional `docs_audit` section for tolerance + extra facts
- Graph node: new `docs-audit` feature under `doc-sync` domain in `services.yml`

## Proposed Solution

### Approach

**Two-pass architecture within a single module:**

**Pass 1 — Fact Registry** (`FactRegistry` class):
Computes ground truth from existing data sources. Zero-config — all facts derived automatically.

| Fact | Source | Method |
|------|--------|--------|
| `version` | `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod` | Manifest regex parsing |
| `node_count` | SQLite `nodes` table | `SELECT COUNT(*) FROM nodes` |
| `edge_count` | SQLite `edges` table | `SELECT COUNT(*) FROM edges` |
| `language_count` | SQLite `code_symbols` | `SELECT COUNT(DISTINCT language) FROM code_symbols` |
| `test_count` | SQLite `code_symbols` | Count `kind='test'` symbols |
| `framework_count` | SQLite `nodes.extra` | Count nodes with framework detection data |
| `mcp_tool_count` | MCP server introspection | Count tools from server definition |
| `cli_command_count` | Click group introspection | Traverse `main.commands` |

Extensible via `config.yml` `docs_audit.extra_facts` for project-specific facts (e.g., API endpoint count).

**Pass 2 — Doc Scanner** (`DocScanner` class):
Scans markdown files, extracts numeric mentions, matches to facts via keyword proximity.

- Built-in keyword associations per fact type (e.g., `"language_count" → ["language", "lang"]`)
- Proximity window: 5 words before/after the number
- Special regex for version strings (`v?\d+\.\d+\.\d+`)
- False positive filters: dates, issue IDs, code blocks, hex colors, version pinning, line numbers

**Pass 3 — Comparator** (`compare_facts()` function):
Compares mentions against ground truth with tolerance. Produces `AuditResult` with stale/fresh/unmatched lists.

### Changes

| File / Module | Change |
|---------------|--------|
| `src/beadloom/doc_sync/audit.py` | **NEW** — `FactRegistry`, `DocScanner`, `compare_facts()`, data classes (`Fact`, `Mention`, `AuditFinding`, `AuditResult`) |
| `src/beadloom/doc_sync/__init__.py` | Export `run_audit`, `AuditResult` |
| `src/beadloom/services/cli.py` | Add `@docs.command("audit")` with `--json`, `--fail-if`, `--stale-only`, `--verbose`, `--path` options |
| `src/beadloom/infrastructure/debt_report.py` | Add `meta_doc_stale_count` to `DebtData`, new `meta_doc_staleness` category in `compute_debt_score()` |
| `.beadloom/_graph/services.yml` | Add `docs-audit` feature node under `doc-sync` domain |
| `tests/test_docs_audit.py` | **NEW** — unit tests for fact registry, doc scanner, comparator, CLI |

### API Changes

**Public API (doc_sync module):**
```python
@dataclass(frozen=True)
class Fact:
    name: str           # e.g. "version", "node_count"
    value: str | int    # ground truth value
    source: str         # e.g. "pyproject.toml", "graph DB"

@dataclass(frozen=True)
class Mention:
    fact_name: str      # matched fact type
    value: str | int    # mentioned value
    file: Path          # file containing mention
    line: int           # line number
    context: str        # surrounding text snippet

@dataclass(frozen=True)
class AuditFinding:
    mention: Mention
    fact: Fact
    status: str         # "stale" | "fresh"
    tolerance: float    # applied tolerance (0.0 = exact)

@dataclass(frozen=True)
class AuditResult:
    facts: dict[str, Fact]
    findings: list[AuditFinding]
    unmatched: list[Mention]    # mentions with no fact match

def run_audit(
    project_root: Path,
    db: Connection,
    *,
    scan_paths: list[str] | None = None,
    config: dict | None = None,
) -> AuditResult: ...
```

**CLI interface:**
```bash
beadloom docs audit                    # zero-config scan
beadloom docs audit --json             # JSON output
beadloom docs audit --fail-if=stale>0  # CI gate
beadloom docs audit --stale-only       # show only stale
beadloom docs audit --verbose          # include fresh + unmatched
beadloom docs audit --path="*.md"      # custom scan paths
```

## Alternatives Considered

### Option A: Regex-only matching (no keyword proximity)
Match all numbers in docs against all facts. Too many false positives — "3 sections" would match `language_count=3`. Rejected.

### Option B: Structured doc annotations
Require `<!-- beadloom:fact=version -->1.7.0<!-- /beadloom -->` markers. Zero-config goal violated. Rejected.

### Option C: AST-based markdown parsing
Use markdown AST to understand document structure. More precise but significantly more complex, slower, and harder to maintain. Keyword proximity is simpler and sufficient for v1.8. Could revisit in v1.9 if false positive rate is too high.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| High false positive rate | Medium | Medium | Proximity window tuning, skip rules for dates/codes/hex, configurable tolerance |
| Manifest parsing fails on unusual project layouts | Low | Low | Graceful fallback: skip facts that can't be computed, report in output |
| Performance on large doc sets | Low | Low | Only scans *.md files, skip code blocks early |
| Keyword collisions across fact types | Medium | Low | Priority ordering: version regex first, then most specific keywords |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Should audit scan CHANGELOG.md by default? | Decided: No — changelog contains many version/number mentions that are intentionally historical, not current facts. Exclude by default, configurable. |
| Q2 | Where to place the module — `doc_sync/` or new `audit/` domain? | Decided: `doc_sync/audit.py` — the feature is about doc-code freshness, fits doc_sync domain semantically. Single module is sufficient for v1.8. |
| Q3 | Should tolerance defaults be hardcoded or in config? | Decided: Both — sensible hardcoded defaults (exact for versions, +/-5% for counts), overridable in `config.yml`. |
