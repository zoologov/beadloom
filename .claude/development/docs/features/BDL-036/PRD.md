# PRD: BDL-036 — Phase 0: Foundation / Honesty Gate

> **Status:** Approved
> **Created:** 2026-05-30

---

## Problem

Beadloom's core promise is **trust**: "we tell you the truth about your code, architecture, and docs." The 2026-05 review (`.claude/development/REVIEW.md`) and `BDL-UX-Issues.md` found that Beadloom **does not currently tell itself the truth** — verified live again on 2026-05-30:

- **`beadloom lint --strict` exits 0 on a graph with 12 real violations** (cycles + `infrastructure → domains`), because `no-dependency-cycles` and `architecture-layers` were downgraded to `severity: warn` in `.beadloom/_graph/rules.yml:39,45`. The product that sells architecture enforcement does not enforce on itself (#91).
- **`beadloom doctor` reports false drift:** "Version drift: claims 1.9.0, actual is 1.7.0" (reads stale `importlib.metadata` instead of source `__version__`, #92) and "MCP tool drift: AGENTS.md documents 13 tools, actual is 14" (#93).
- **Silent / empty-result failure modes:** incremental reindex prints "Nodes: 0" though the index is intact (#88, display bug); flow-style YAML edges silently produce 0 nodes (#86); broad `except Exception` can swallow real errors (#94).
- **`sync-check` cannot reach honest green** even when files are correctly annotated/documented (#89), and `<!-- beadloom:track -->` markers are inert (#90).
- **Bootstrap is not clean out-of-the-box** — once rules are restored to `error`, a freshly bootstrapped repo would fail its own gate on day one (#71).

This is **STRATEGY-3 Phase 0** — the prerequisite "honesty gate" before any federation work, because federation multiplies any dishonesty across N repos.

## Impact

Until Beadloom passes its own `doctor` / `lint --strict` / `sync-check` honestly, every downstream goal is built on sand: the tool-agnostic CI gate would enforce nothing, the VitePress/AI-techwriter pipeline would publish a sync-check that lies, and any skeptic (or the maintainer's own team) can discredit the product in two commands. This gate also unblocks the entire STRATEGY-3 roadmap (F1 federation onward).

## Goals

- [ ] `beadloom lint --strict` **fails** (non-zero) on real cycle/layer violations; `no-dependency-cycles` + `architecture-layers` restored to `severity: error`, and Beadloom's own graph is genuinely clean (no cycles, no `infrastructure → domains`).
- [ ] `beadloom doctor` is honestly green on Beadloom itself: correct version source (#92), correct MCP tool count (#93).
- [ ] No silent/empty/misleading outputs: incremental reindex reports true totals (#88); flow-style YAML either works or errors clearly (#86); narrow exception handling (#94).
- [ ] `beadloom sync-check` can reach genuine 100% on a fully-annotated/documented repo; `beadloom:track` markers either work or are documented as unsupported (#89/#90).
- [ ] A freshly bootstrapped repo passes `lint --strict` out-of-the-box (#71).
- [ ] Test suite de-brittled enough to support the #91 refactor (#96, scoped to touched areas).
- [ ] **Exit criterion:** `beadloom doctor && beadloom lint --strict && beadloom sync-check` are *honestly* green on Beadloom itself.

## Non-goals

- Bootstrap-accuracy program (#74/75/77/78/80/81/82/83/84/85) — deferred, iterated live during federation.
- Performance #95 (symbol full-scan) — only when dogfooding hits scale.
- Federation (F1+), VitePress, AI tech-writer — later STRATEGY-3 phases.
- A full test-suite rewrite — #96 is scoped to what the #91 refactor touches, not all 193 sites.

## User Stories

### US-1: The linter enforces
**As** a developer (or AI agent) relying on Beadloom for guardrails, **I want** `lint --strict` to fail on real cycles/layer violations, **so that** "green" actually means "boundaries hold".

**Acceptance criteria:**
- [ ] Cycle/layer rules are `error`; `lint --strict` exits non-zero when violations exist.
- [ ] Beadloom's own graph passes with zero violations (god-package decoupled).

### US-2: Diagnostics tell the truth
**As** anyone running `beadloom doctor`, **I want** version and tool-count checks to be correct, **so that** I trust the rest of doctor's output.

**Acceptance criteria:**
- [ ] No false version drift; no false MCP-tool drift on a consistent tree.

### US-3: No silent lies
**As** a user editing the graph or running reindex, **I want** failures to be loud and outputs accurate, **so that** I never mistake a working index for an empty one (or vice versa).

**Acceptance criteria:**
- [ ] Incremental reindex prints true node/edge totals.
- [ ] Flow-style YAML edges either parse or raise a clear error (no silent 0 nodes).

### US-4: Sync-check reaches honest green
**As** a maintainer who annotated and documented everything, **I want** `sync-check` to reach 100%, **so that** the doc-sync signal is trustworthy.

**Acceptance criteria:**
- [ ] On a fully-annotated/documented sample, sync-check reports no false `untracked_files`.
- [ ] `beadloom:track` markers work, or are clearly documented as unsupported.

## Acceptance Criteria (overall)

- [ ] Exit criterion met: `beadloom doctor && beadloom lint --strict && beadloom sync-check` honestly green on Beadloom.
- [ ] A fresh `beadloom init --bootstrap` repo passes `lint --strict`.
- [ ] All targeted UX issues (#91, #88, #92, #93, #94, #86, #89, #90, #71) resolved or honestly re-scoped with evidence.
- [ ] Tests pass; ruff + mypy --strict clean; changes committed.
- [ ] `honest ≠ complete`: any issue that proves deeper than expected is re-scoped transparently in the docs, never silently dropped or faked.
