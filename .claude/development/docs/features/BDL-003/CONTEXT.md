# CONTEXT: BDL-003 — Phase 2: Lower the Barrier (v0.4)

> **Last updated:** 2026-02-10
> **Phase:** Strategy Phase 2
> **Status:** COMPLETE
> **Depends on:** BDL-002 (v0.3.0 complete)

---

## Goal

From `pip install` to useful context in under 5 minutes, on any project.

## Design Principle

**Presets define rules. Bootstrap applies rules. Review confirms results.**

## Deliverables

| # | Item | Status | Bead |
|---|------|--------|------|
| 2.3 | Zero-doc mode | DONE | beadloom-26s |
| 2.1 | Architecture presets (`--preset`) | DONE | beadloom-hwu |
| 2.2 | Smarter bootstrap (patterns + edges) | DONE | beadloom-d70 |
| 2.4 | Interactive bootstrap review | DONE | beadloom-etl |

## Key Decisions

| Decision | Reason |
|----------|--------|
| **3 presets: monolith, microservices, monorepo** | Covers most real-world architectures |
| **Auto-detect when no preset given** | Friction-free for users who don't know their arch type |
| **Pattern-based, not import-based** | Import analysis is complex (Phase 5); dir names are 80% accurate |
| **Review in interactive mode only** | `--bootstrap` stays non-interactive for scripts/CI |
| **package.json only for manifest deps** | tomllib requires Python 3.11+; project targets 3.10+ |

## What Changed

| File | Change |
|------|--------|
| `src/beadloom/presets.py` | NEW — PresetRule, Preset, 3 presets, detect_preset() |
| `src/beadloom/onboarding.py` | preset-aware bootstrap, 2-level scan, edges, zero-doc, review |
| `src/beadloom/cli.py` | `--preset` flag on init command |
| `src/beadloom/__init__.py` | Version 0.3.0 → 0.4.0 |
| `docs/cli-reference.md` | Updated init section with preset docs |
| `tests/test_presets.py` | NEW — 19 tests for preset logic |
| `tests/test_onboarding.py` | Extended — 48 tests (was 30) |
