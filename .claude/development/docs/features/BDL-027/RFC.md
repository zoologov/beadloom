# RFC: BDL-027 — UX Issues Batch Fix (Phase 12.12)

> **Status:** Approved
> **Created:** 2026-02-20

---

## Overview

Fix 15 open UX issues discovered during dogfooding, grouped into 5 independent domain areas. Each area has isolated changes with no cross-dependencies between domains, enabling parallel development.

## Motivation

### Problem
Dogfooding on beadloom itself and a React Native project exposed issues ranging from completely broken C4 diagrams to 86% false positive rate in docs audit. These undermine user trust and block feature adoption.

### Solution
Targeted fixes in 5 independent modules, each with clear root causes identified during exploration. No architectural changes needed — all fixes are localized to specific functions.

## Technical Context

### Constraints
- Python 3.10+
- SQLite (WAL mode)
- No breaking API changes
- All existing tests must pass

### Affected Areas
- `graph/c4.py` — C4 diagram rendering (issues #41-45)
- `doc_sync/scanner.py` + `doc_sync/audit.py` + `services/cli.py` — docs audit (issues #52-57)
- `infrastructure/doctor.py` + `infrastructure/debt_report.py` — doctor/debt (issues #38-40)
- `onboarding/scanner.py` + `services/cli.py` — init/bootstrap (issues #32-34)
- `context_oracle/route_extractor.py` + `context_oracle/test_mapper.py` — context output (issues #26, 29-30)

## Proposed Solution

### Area 1: C4 Diagrams (5 fixes)

| Issue | Fix | Location |
|-------|-----|----------|
| #41 Self-ref breaks depths | Filter `if child != par` in `_compute_depths()` before building roots set | `c4.py:60-96` |
| #42 Label = description | Generate label from ref_id via title-case + hyphen-to-space; keep summary as description | `c4.py:173-202` `_build_c4_node()` |
| #43 Root inside boundary | Skip self-referencing entries in `_load_edges()` part_of handling | `c4.py:144-170` |
| #44 Boundary ordering | Sort orphan boundaries: root-first, then alphabetical | `c4.py:502-538` |
| #45 Wrong !include | Select include URL based on `--level` flag: Context/Container/Component | `c4.py:463-465` |

### Area 2: Docs Audit (6 fixes)

| Issue | Fix | Location |
|-------|-----|----------|
| #52 86% FP rate | Skip numbers < 10 for count facts (not version); combined with #53, #54 fixes | `scanner.py` `_match_number()` |
| #53 Year "2026" matched | Add standalone year regex `\b20[0-9]{2}\b` to false positive filters | `scanner.py:32-71` |
| #54 SPEC.md dominates FP | Add `_graph/features/*/SPEC.md` to default exclude list + `docs_audit.exclude_paths` config | `scanner.py:294-338` `resolve_paths()` |
| #55 test_count inflated | Document as "symbol count" in output; add `(symbols)` suffix to fact label | `audit.py` + `cli.py` output |
| #56 No full path in output | Show relative path from project root instead of `.name` (basename) | `cli.py:1850-1933` |
| #57 Dynamic versioning | Detect `dynamic = ["version"]` + Hatch `[tool.hatch.version] path=...`; fallback to `importlib.metadata.version()` | `audit.py:418-448` |

### Area 3: Doctor/Debt Report (3 fixes)

| Issue | Fix | Location |
|-------|-----|----------|
| #38 Info not warn | Change `Severity.INFO` to `Severity.WARNING` in `_check_nodes_without_docs()` | `doctor.py:75` |
| #39 Untracked not listed | Return `(count, ref_ids)` from `_count_untracked()` instead of count only; add ref_id list to output | `debt_report.py:236-247` |
| #40 Oversized false positive | In `_count_oversized()`, exclude paths claimed by child nodes — query child source prefixes, filter LIKE matches | `debt_report.py:250-274` |

### Area 4: Init/Onboarding (3 fixes)

| Issue | Fix | Location |
|-------|-----|----------|
| #32 Incomplete scan_paths | In `scan_project()`, lower threshold for Pass 2 code-file detection; add React Native dirs (`components/`, `hooks/`, `contexts/`, `modules/`) to `_SOURCE_DIRS` | `scanner.py:147-206` |
| #33 Interactive-only | Add `--mode`, `--yes`/`--non-interactive`, `--force` flags to `init` CLI command | `cli.py` init command |
| #34 Root rule fails | Exclude root node (source="") from `service-needs-parent` rule generation, or don't generate it if already removed | `scanner.py:706-763` |

### Area 5: Route/Test Context (3 fixes)

| Issue | Fix | Location |
|-------|-----|----------|
| #26 0 tests at domain level | Aggregate test mappings by domain source path prefix in `map_tests()` | `test_mapper.py:493-528` |
| #29 Route self-matching | Add self-exclusion: skip files inside `route_extractor.py` own package; scope route propagation to source file's domain | `route_extractor.py` |
| #30 Poor route formatting | Improve `{method:<5} {path:<20}` format; separate GraphQL section with QUERY/MUTATION labels | `route_extractor.py` or display code |

## Alternatives Considered

### Option A: Fix issues incrementally across multiple releases
Rejected — issues are small, well-understood, and independent. Batch fix is more efficient.

### Option B: Rewrite C4 module
Rejected — root cause is self-referencing edges, not architectural. Simple filters fix all 5 issues.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Test regressions from scanner changes | Low | Medium | Comprehensive test coverage per area |
| Init flag changes break scripts | Low | Low | Flags are additive, no behavior change without flags |
| Doctor severity change breaks CI | Medium | Low | Documented as intentional behavior change |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Should #55 use pytest --collect-only or keep symbol count? | Decided: keep symbol count, label as "(symbols)" — pytest invocation too slow for CI |
| Q2 | Should #34 rule already be removed? | Decided: verify during implementation — explore agent found it may already be gone |
