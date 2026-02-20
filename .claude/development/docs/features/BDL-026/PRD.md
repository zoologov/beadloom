# PRD: BDL-026 — Documentation Audit (Phase 12.11)

> **Status:** Approved
> **Created:** 2026-02-20

---

## Problem

Project-level documentation (README, CONTRIBUTING, guides, AGENTS.md) contains hardcoded numeric facts — version numbers, tool counts, command counts, language counts, test counts — that silently go stale after every release. These facts fall outside `sync-check` scope because they are not tied to specific graph nodes.

Evidence from the current project:
- BDL-022 (v1.7.0 doc refresh) required 6 parallel agents and 10 file updates to fix stale facts.
- Manual audit after Phase 12.10 found 2 drift issues even in a well-maintained project.
- Every release risks shipping documentation with wrong version numbers, outdated counts, and misleading feature lists.

This problem exists in every project with documentation and scales with development velocity — the faster you ship, the faster docs drift.

## Impact

- **AI agents** receive stale instructions (wrong version, outdated command lists) leading to errors.
- **New contributors** get misleading project overviews from README.
- **CI pipelines** have no way to catch documentation drift before release.
- **Maintainers** spend manual effort auditing docs after every release.

## Goals

- [ ] `beadloom docs audit` detects stale version numbers, outdated counts, and changed feature lists — zero configuration required
- [ ] False positive rate < 20% across diverse project types
- [ ] CI gate support: `--fail-if=stale>0` exits non-zero to block releases with outdated docs
- [ ] Configurable tolerance system to avoid false positives on naturally fluctuating metrics (test counts, growing metrics)
- [ ] Debt report integration: stale doc count feeds into existing debt score

## Non-goals

- List/enumeration matching (e.g., verifying "supports Python, Go, Rust" list completeness) — future
- Cross-language doc scanning (only markdown in v1.8) — future
- Automatic doc fixing / generating patches — future
- Semantic matching via embeddings — deferred to v2.0

## User Stories

### US-1: Zero-Config Audit
**As** a project maintainer, **I want** to run `beadloom docs audit` after a release, **so that** I immediately see which documentation files contain stale facts without any configuration.

**Acceptance criteria:**
- [ ] Command scans `*.md` and `docs/**/*.md` by default
- [ ] Detects stale version numbers, tool counts, command counts, language counts
- [ ] Human-readable Rich output with color-coded stale/fresh/unmatched sections
- [ ] `--json` flag for scripting

### US-2: CI Integration
**As** a DevOps engineer, **I want** `beadloom docs audit --fail-if=stale>0` to exit non-zero, **so that** CI blocks releases with outdated documentation.

**Acceptance criteria:**
- [ ] Non-zero exit code when stale count exceeds threshold
- [ ] Parseable output for CI log processing

### US-3: Tolerance for Fluctuating Metrics
**As** a maintainer of an active project, **I want** configurable tolerance per fact type (exact for versions, +/-5% for test counts), **so that** natural metric fluctuation doesn't trigger false positives.

**Acceptance criteria:**
- [ ] Per-fact tolerance configuration in `config.yml`
- [ ] Built-in defaults: exact for versions, +/-5% for test counts, +/-10% for growing metrics
- [ ] Tolerance applied during comparison, clearly shown in output

### US-4: Unified Debt View
**As** a project lead, **I want** stale doc mentions to appear in the debt report, **so that** I have a single view of all documentation health issues.

**Acceptance criteria:**
- [ ] `beadloom status --debt-report` includes "meta-doc staleness" category
- [ ] Stale count contributes to overall debt score

## Acceptance Criteria (overall)

- [ ] `beadloom docs audit` works zero-config on any Beadloom project
- [ ] Fact registry auto-computes ground truth from manifest, graph DB, and code symbols
- [ ] Doc scanner extracts numeric mentions via keyword-proximity matching
- [ ] Stale/fresh/unmatched results are clearly presented
- [ ] CI gate with `--fail-if` flag
- [ ] Tolerance system with sensible defaults
- [ ] Debt report integration
- [ ] Feature ships as experimental (marked in output and docs)
- [ ] All tests pass, coverage >= 80%
