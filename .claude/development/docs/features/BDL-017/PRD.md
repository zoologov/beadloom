# BDL-017: Beadloom v1.6 — Deep Code Analysis + Agent Infrastructure

## Metadata
- **Created:** 2026-02-16
- **Status:** Approved (2026-02-16)
- **Reference:** `.claude/development/STRATEGY-2.md` §4 (Phases 10, 11)
- **Predecessor:** BDL-015 (v1.5.0 — Smart Bootstrap + Doc Sync v2 + Languages)

## 1. Problem

### 1.1 Current situation
Beadloom v1.5 bootstraps rich graphs with 18+ frameworks, 9 languages, and honest doc drift detection. However:

1. **Graph nodes lack runtime context** — no API routes, no activity metrics, no test coverage. An agent gets "FastAPI service: auth — 5 classes, 12 fns" but not "POST /api/login, PUT /api/users/{id}" or "hot: 45 commits/month" or "3 test files, ~80% coverage".

2. **Agents can't validate via MCP** — `lint`, `why`, `diff` exist as CLI commands but not as MCP tools. Agents must shell out to CLI instead of calling structured MCP tools that return JSON.

3. **Rules are binary** — all violations are equal. No `warn` vs `error` distinction. Teams adopting gradually can't distinguish "must fix" from "should fix", making `--strict` an all-or-nothing gate.

### 1.2 Why this matters
- **Without routes:** Agent must read source files to discover API endpoints — 500K tokens instead of 2K
- **Without activity:** Agent can't prioritize: touching a dormant module is low-risk, touching a hot one needs review
- **Without test mapping:** Agent writes code without knowing if tests exist or what's covered
- **Without MCP lint/why/diff:** Multi-step agent workflows (plan→code→validate) break — agents can't validate their own work via MCP
- **Without severity:** CI gates reject good PRs for cosmetic violations

### 1.3 Who is affected
- AI agents using beadloom as context infrastructure (primary user)
- Developers using `beadloom ctx` for onboarding
- Teams adopting architecture rules gradually

## 2. Goals

### 2.1 Business goals
- [ ] Context bundles include API routes, git activity, and test mapping
- [ ] Agents can lint, analyze impact, and diff via MCP (not just CLI)
- [ ] Architecture rules support `warn` vs `error` severity

### 2.2 User goals
- [ ] As an agent, I want `beadloom ctx AUTH` to show API routes so I don't read source files
- [ ] As an agent, I want activity levels (hot/warm/cold/dormant) to prioritize changes
- [ ] As an agent, I want to know test coverage per module before writing code
- [ ] As an agent, I want MCP `lint` tool returning JSON violations
- [ ] As an agent, I want MCP `why` tool for impact analysis without CLI
- [ ] As an agent, I want MCP `diff` tool for graph changes since a git ref
- [ ] As a team, I want `beadloom lint` to distinguish warnings from errors

### 2.3 Non-goals (Out of Scope)
- Multi-repo references (Phase 12)
- Semantic search / embeddings (Phase 13)
- Plugin system (Phase 13)
- beadloom export (Phase 12)

## 3. Success Metrics

| Metric | v1.5 (current) | v1.6 (target) |
|--------|----------------|---------------|
| Context bundle content | Framework + entry points | + routes, activity, tests |
| MCP tools | 9 | **12** (+lint, why, diff) |
| Rule severity | binary (pass/fail) | `error` / `warn` |
| Test mapping | none | framework detection + file mapping |
| Activity tracking | none | hot/warm/cold/dormant per node |
| Docs polish data | symbols + deps | + routes, activity, tests, enriched diff |
