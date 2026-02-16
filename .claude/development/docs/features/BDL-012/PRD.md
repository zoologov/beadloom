# BDL-012 — Onboarding Quality: Bug-fixes from Dogfooding

> **Status:** Complete (delivered in v1.3.1)
> **Epic:** BDL-012

## Problem

Beadloom v1.3.0 Plug & Play Onboarding (`beadloom init --bootstrap`) works end-to-end but produces low-quality results on real projects. Dogfooding on two projects revealed 10 open issues:

- **core-monolith** — Django + Vue monolith, 44 nodes, backend/frontend split
- **secondary-system** — React Native (Expo) + TypeScript, 6 nodes, mobile app

## User Stories

**US-1**: As a developer running `beadloom init --bootstrap`, I want `beadloom doctor` to show 100% doc coverage (not 0%) so I trust the tool works.

**US-2**: As a developer running `beadloom lint`, I want 0 false positive violations so I can use lint in CI without noise.

**US-3**: As a developer reading generated doc skeletons, I want to see real dependency info (not "Depends on: (none)") so the docs are immediately useful.

**US-4**: As a developer running `beadloom docs polish`, I want readable text output (not 1 line) so I can review what needs enrichment without `--format json`.

**US-5**: As a developer installing beadloom on a TypeScript project, I want symbols to be indexed without knowing about `[languages]` extras.

## Scope

### In scope (UX issues #5-#13 from BDL-UX-Issues.md)

| # | Severity | Issue | Project |
|---|----------|-------|---------|
| 5 | HIGH | `doctor` 0% coverage — graph nodes missing `docs:` field | both |
| 6 | HIGH | `lint` false positives — rules don't handle nested domains + root | both |
| 7 | MEDIUM | Skeletons empty deps — `depends_on` edges not yet available | both |
| 8 | MEDIUM | `docs polish` text = 1 line — no useful output | both |
| 11 | MEDIUM | `uv tool install` gives 0 symbols — language parsers are optional | secondary-system |
| 9 | LOW | Generic summaries | both |
| 10 | LOW | Parenthesized ref_ids from Expo router | secondary-system |
| 12 | LOW | `reindex` ignores new parser availability | secondary-system |
| 13 | INFO | Bootstrap skeleton count includes pre-existing files | secondary-system |
| 14 | MEDIUM | Preset auto-detect picks `microservices` for mobile apps | secondary-system |

### Out of scope

- New features or commands
- Frontend/multi-language skeleton templates
- Semantic search / vector embeddings

## Success Criteria

- `beadloom init --bootstrap` on core-monolith → `doctor` 0 warnings, `lint` 0 violations
- `beadloom init --bootstrap` on secondary-system → `doctor` 0 warnings, `lint` 0 violations, symbols > 0, preset = monolith
- Skeleton docs contain real dependencies from import resolver
- `beadloom docs polish` text output includes node list with symbols
- All existing tests pass (756+), new tests for each fix
