# PRD: BDL-027 — UX Issues Batch Fix (Phase 12.12)

> **Status:** Approved
> **Created:** 2026-02-20

---

## Problem

Dogfooding beadloom on real-world projects (beadloom itself, React Native/Expo app) has exposed 15 UX issues across 5 domains. These range from HIGH severity bugs (C4 diagrams completely broken, docs audit 86% false positive rate) to MEDIUM quality-of-life improvements (poor formatting, missing aggregation). These issues erode user trust and block adoption.

## Impact

- **C4 diagrams** (#41-45): completely unusable — all nodes render as `System()`, no differentiation
- **Docs audit** (#52-57): 86% false positive rate makes the feature unreliable for CI gates
- **Doctor/debt report** (#38-40): misleading metrics — false positives on root nodes, missing details
- **Init/onboarding** (#32-35): poor first-run experience for non-trivial projects (React Native, mobile)
- **Route/test mapping** (#26, 29-30): incorrect context output undermines trust in `beadloom ctx`

## Goals

- [ ] Fix all 15 open UX issues from BDL-UX-Issues.md
- [ ] C4 diagrams render correct element types (System/Container/Component)
- [ ] Docs audit false positive rate < 20% on beadloom project
- [ ] Doctor/debt report provide actionable, accurate metrics
- [ ] Init works for React Native/Expo projects with proper scan_paths
- [ ] Route extraction has no self-matching false positives

## Non-goals

- Issue #20 (`.beadloom/README.md` stale) — not planned, low severity, manual
- Issue #31 (`bd dep remove` bug) — Beads CLI bug, not beadloom
- Issue #35 (init doesn't offer `docs generate`) — deferred, low severity
- Issue #36 (existing docs not auto-linked) — future, requires fuzzy matching
- Issue #37 (bootstrap quality metrics) — tracking only, no code change

## User Stories

### US-1: Accurate C4 Diagrams
**As** a developer, **I want** `beadloom graph --format=c4-plantuml` to render correct C4 element types, **so that** I can use the output in architecture documentation.

**Acceptance criteria:**
- [ ] Domains render as Container, features as Component
- [ ] Root node is the System_Boundary, not an element inside it
- [ ] Labels are human-readable (ref_id title-cased), descriptions are summaries
- [ ] Boundaries ordered semantically (root first)
- [ ] Correct `!include` based on `--level` flag

### US-2: Reliable Docs Audit
**As** a CI pipeline, **I want** `beadloom docs audit --fail-if='stale>0'` to have < 20% false positive rate, **so that** it doesn't produce noise.

**Acceptance criteria:**
- [ ] Small numbers (< 10) excluded from count fact matching
- [ ] Standalone years (2020-2030) filtered
- [ ] SPEC.md files excluded from default scan or configurable via `exclude_paths`
- [ ] Full relative paths shown in output
- [ ] Dynamic versioning (Hatch/setuptools-scm) detected
- [ ] Test count uses more accurate source (or documented as symbol count)

### US-3: Actionable Doctor/Debt Reports
**As** a developer, **I want** `beadloom doctor` and debt reports to show accurate, actionable data, **so that** I can prioritize improvements.

**Acceptance criteria:**
- [ ] Nodes without docs show `[warn]` not `[info]`
- [ ] Untracked nodes listed by name in debt report
- [ ] Oversized detection respects ownership boundaries (no false positives on root/parent)

### US-4: Better Init for Diverse Projects
**As** a developer bootstrapping a React Native project, **I want** `beadloom init` to detect all source directories, **so that** I don't miss 60% of my architecture.

**Acceptance criteria:**
- [ ] Scan all top-level dirs with code files, not just manifest-adjacent
- [ ] `--mode`, `--yes`, `--force` flags for non-interactive use
- [ ] Auto-generated rules don't fail on root nodes

### US-5: Correct Route/Test Context
**As** a developer, **I want** `beadloom ctx` to show accurate test and route data, **so that** I can trust the context output.

**Acceptance criteria:**
- [ ] Test counts aggregated at domain level
- [ ] Route extractor doesn't self-match its own patterns
- [ ] Route formatting improved (long paths, GraphQL sections)

## Acceptance Criteria (overall)

- [ ] All 15 open issues from BDL-UX-Issues.md resolved
- [ ] All issues marked as FIXED with commit references
- [ ] Full test suite passes (2389+ tests)
- [ ] ruff clean, mypy clean
- [ ] beadloom validation clean (sync-check, lint, doctor)
- [ ] Dogfooding verification on beadloom project
