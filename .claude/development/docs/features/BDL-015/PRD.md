# BDL-015: Beadloom v1.5 — Product Requirements Document

## Metadata
- **Created:** 2026-02-15
- **Status:** Draft
- **Reference:** `.claude/development/STRATEGY-2.md` §4 (Phases 8, 8.5, 9)

## 1. Problem

### 1.1 Current situation
Beadloom v1.4 is a working Architecture-as-Code platform but has three critical gaps:

1. **Bootstrap is shallow** — `Domain: auth (15 files)` tells an agent nothing about frameworks, entry points, dependencies, or routes.
2. **Doc Sync is broken** — `sync-check` reports "31/31 OK" despite 12 real discrepancies (UX Issues #15, #18). Hash-based detection doesn't catch semantic drift.
3. **4 languages aren't enough** — no Java/Kotlin (Android), Swift (iOS), C/C++ (native modules). Mobile and cross-platform projects get empty nodes.

### 1.2 Why this matters
- Agents relying on `doctor` and `status` will work with stale specs thinking they're current
- Bootstrap graph has no real dependencies until after `reindex`, defeating the "instant context" promise
- Dogfood project (dreamteam: React Native + Expo + Valhalla C++ + Meshtastic) can't be fully indexed

### 1.3 Who is affected
- AI agents using beadloom as context infrastructure
- Developers onboarding onto new codebases
- Cross-platform/mobile development teams

## 2. Goals

### 2.1 Business goals
- [ ] Bootstrap produces a graph with real architectural meaning, not just file counts
- [ ] Doc Sync honestly catches discrepancies between code and documentation
- [ ] 9 programming languages supported (from 4)

### 2.2 User goals
- [ ] As a developer, I want `beadloom init` to show framework types, entry points, and dependencies in the first graph
- [ ] As an agent, I want `sync-check` to truthfully report stale docs when code changes
- [ ] As a mobile developer, I want Kotlin/Java/Swift/C++ files indexed with symbols and imports

### 2.3 Non-goals (Out of Scope)
- API route extraction (Phase 10)
- Git history analysis (Phase 10)
- Multi-repo support (Phase 12)
- Semantic search (Phase 13)

## 3. Success Metrics

| Metric | v1.4 (current) | v1.5 (target) |
|--------|----------------|---------------|
| Node summaries | "15 files" | Framework + entry points |
| First graph edges | `part_of` only | `part_of` + `depends_on` |
| Doc drift detection | file-hash only | symbol-level |
| Frameworks detected | 4 patterns | 15+ |
| Languages | 4 | 9 (+Kt, Java, Swift, C/C++, ObjC) |
