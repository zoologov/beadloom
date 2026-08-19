# ACTIVE: BDL-060 — Integration Map with Data

> **Type:** epic
> **Parent bead:** beadloom-8qqp
> **Branch:** features/BDL-060-s4
> **Updated:** 2026-08-19

---

## Current focus

**S1–S3 merged to main** (PRs #27/#28/#29). **S4 dev DONE** on `features/BDL-060-s4` (`.13` + follow-ups `.26`/`.27`): landscape + architecture graphs via Cytoscape+ELK, compound domains, doc-links, impact, filters, canonical layered lanes. **Next: `.14` [test]** — byte-stable regeneration + pop-up data + dead-link guard, then `.15` [review] and `.16` [tech-writer], then ONE PR for S4.

**Target after S4: release 2.2.0** (owner decision 2026-08-19). It is overdue and now load-bearing: `main` carries S1–S3 unreleased, which is the mechanism behind BDL-UX #151 (a fresh install reports `config-check` drift against projects scaffolded from `main`, and `--fix` would rewrite them back to older templates). The release is also breaking-by-dependency — Beadloom now requires `mcp >= 2.0` — so it is a MINOR bump, not a patch.

Scope refocused (owner): GraphQL (incl. subscriptions) + AMQP done maximally; external cross-protocol verdict federation (protobuf/Pact/REST) deferred. Viz = Cytoscape + ELK. Standards: TDD + DDD + cohesion-driven + data-strictness, Gate-green + dogfood per slice.

## Slice status

| Slice | Beads | State |
|-------|-------|-------|
| S1 atomic YAML | .1–.4 | **DONE** — merged to main (PR #27) |
| S2 GraphQL Tier-A | .5–.8 | **DONE** — merged to main (PR #28) |
| S3 AMQP body | .9–.12 | **DONE** — merged to main (PR #29) |
| S4 viz (Cytoscape+ELK) | .13–.16 | .13 (+ .26/.27) dev DONE; **.14 test NEXT**, then .15 review, .16 tech-writer |
| S5 cross-repo ctx | .17–.20 | blocked → S4 |
| S6 sweep + unverified | .21–.24 | blocked → S5 |

## Plan notes

- One PR per slice on `features/BDL-060` (sequential; principle 1). Each slice: dev → test → review → tech-writer, TDD, behavior-preserving, `beadloom ci` rc0, dogfooded on the anonymized landscape fixture.
- Key decisions: Cytoscape+ELK (build-time preset, byte-stable); native deep GraphQL (incl. subscriptions, Hive-aware, no external tool); AMQP JSON-Schema body + optional AsyncAPI ingestion; `unverified` = new lifecycle value; G5 deferred.
- Seams confirmed against HEAD per slice (coordinator does NOT read raw source). Carry BDL-059 lessons: worktree integration via file-checkout + 3-way + #133 re-baseline; recompose without `--force`; verify under multiple seeds; `site/` gitignored.

## Progress log

- 2026-08-19 — **Session resumed after a break.** Committed the accumulated BDL-UX dogfood/design input (#150–156) and the uncommitted TUI/test-mapping work (which had NO tests; 13 added). Full dependency-currency pass: **BDL-UX #150 reproduced and fixed** (`tree-sitter` pinned `>=0.25,<0.26` + two pin guards — the crash needs a repo-wide reindex, small parses survive), **migrated to mcp 2.0** (constructor handlers, result models, `input_schema`, self-classified in-band tool errors; verified over real stdio, +3 handler tests where coverage had been `assert server is not None`), mypy 2.3 / textual 8 / rich 15 / ruff 0.16, and the site's npm stack (echarts 6, elkjs 0.12, cytoscape 3.34, mermaid 11.17). Repo hygiene: 4 orphaned swarm molecules closed, 2 superseded worktree branches deleted, empty `[Unreleased]` CHANGELOG filled. Gate green (4793 tests, both orders; `beadloom ci` 6/6). **Open risk carried into `.15`:** the S4 graphs have NOT been looked at since elkjs 0.9→0.12 — layout may have shifted, and a green build is not a rendered page (cf. #117/#120).
- 2026-06-17 — PRD → RFC v2 (refocused GraphQL+AMQP, G5 deferred) → CONTEXT + PLAN all Approved. Epic beadloom-8qqp + 24 beads created, linear slice DAG. Branch features/BDL-060 off main (ecfd6a5, post-BDL-059 + currency #26). Ready to start S1.
