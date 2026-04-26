# CONTEXT: BDL-040 — F4: Living Knowledge Base + Visual Landscape (VitePress)

> **Status:** Approved
> **Created:** 2026-06-02
> **Last updated:** 2026-06-02

---

## Goal

A `beadloom docs site` generator that makes VitePress the **showcase of three Beadloom products**: (A) the AaC+DocAsCode **metrics dashboard**, (B) the **interactive architecture** (intra-repo graph/C4 + the 🌟 cross-repo contract landscape map), and (C) the **published validated documentation** (the real root `docs/` rendered as the source of truth, with per-doc `doc_sync` validation badges). Beadloom produces the tree; VitePress renders it. Dogfooded by generating Beadloom's own site. (Immutable after approval.)

## Key Constraints

- **Beadloom produces, VitePress renders.** The generator emits Markdown/JSON/config; rendering polish must not become a scope sink. No LLM call (that is the deferred F4.1), no SaaS, no live/hosted server (static site only).
- **Honest by construction.** Every dashboard number AND every doc validation badge comes from the SAME code path as `lint`/`doctor`/`debt-report`/`sync-check`/`doc_sync` — the site can never show a metric/status the gate would contradict (the Phase-0 hard dependency; F1–F3 satisfy it).
- **Never mutate the source of truth.** Showcase C publishes the REAL `docs/` but injects badges only into the COPY under `site/docs/…`; the authored `docs/` prose is never rewritten (and no AI authoring — that is F4.1).
- **Separate output dir.** Generate into `--out` (default `site/`), NEVER into the source `docs/`. Build output (`site/.vitepress/dist`, `node_modules`) is gitignored; generated Markdown/config are reproducible (regenerated, not hand-edited).
- **Deterministic.** Identical graph → byte-identical generated tree (sorted nodes/edges/pages/badges; no wall-clock in diffed output). A determinism test re-generates and diffs.
- **No schema bump.** `docs site` is a read-only generator over the existing DB + `docs/` + `federate` output.
- **Node toolchain pinned, Python testable without it.** `site/package.json` pins exact VitePress + Mermaid-plugin versions; the Python generator is fully pytest-testable without node; `npm run build` is dogfood/CI-validated, not unit-tested.
- **Thin-slice the map.** Mermaid-rendered + clickable (native VitePress); rich Cytoscape/D3 interactivity is an explicit follow-up.
- **Anonymization (binding).** The landscape-map dogfood uses the committed anonymized F2/F3 fixtures (no real private-project names); never the gitignored scratch. Verify `git grep` before commit.
- Fifth real-code epic through the BDL-035 multi-agent process (agents/* subagents, swarm/gate/merge-slot).

## Code Standards

(from CLAUDE.md §0.1)

| Standard | Application |
|----------|-------------|
| Language/env | Python 3.10+ (`str \| None`), uv |
| TDD | Red → Green → Refactor |
| Linter/format | ruff |
| Typing | mypy --strict |
| Tests | pytest + pytest-cov, coverage ≥ 80% |

**Restrictions:** no `Any`/`# type: ignore` without reason; `pathlib`; parameterized SQL; `yaml.safe_load`; no bare `except:`; frozen/`@dataclass` models; deterministic serialization (sorted, stable). Generated Markdown/JSON are byte-stable.

**Commit format:** `[BDL-040] <type>: <description>`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-02 | VitePress = showcase of 3 Beadloom products (metrics / architecture / validated docs), not a new doc generator | the site renders what Beadloom already produces; framing prevents scope-sink + a "fourth doc system" |
| 2026-06-02 | New `application/site.py` (`docs site` use-case) | matches the use-case layer (gate.py/debt_report.py); reuses graph/c4/debt/doctor/doc_sync/federation renderers, no new graph logic |
| 2026-06-02 | Generate into a separate `--out` dir (default `site/`), build output gitignored | never clobber the source `docs/`; generated MD/config reproducible |
| 2026-06-02 | Showcase C publishes the REAL `docs/`; badges injected into the COPY only | the docs are the source of truth (rendered as-is); the source is never mutated; no AI prose-rewriting (F4.1) |
| 2026-06-02 | Doc validation badge derived from `doc_sync` `sync_state` (status/reason/synced_at + coverage) | same source as `sync-check` → DocAsCode honesty made visible |
| 2026-06-02 | Dashboard metrics reuse the exact `lint`/`doctor`/`debt-report`/`sync-check` code paths | honest by construction — no parallel metric computation |
| 2026-06-02 | Landscape map = Mermaid (native VitePress, `click`→link), from `federated.json`/graph | thin slice; no JS graph lib; rich Cytoscape/D3 is a follow-up |
| 2026-06-02 | VitePress scaffold committed + pinned; Python generator testable without node | reproducible build; the `npm run build` is dogfood/CI-validated, not pytest |
| 2026-06-02 | F4.1 (AI tech-writer in CI) deferred to a follow-up epic | external-model orchestration; most complex + independent; comes after the site exists |

## Related Files

(discover via `beadloom ctx`/`why` — never hardcode)
- NEW `src/beadloom/application/site.py` (`docs site` generator; maybe `site_pages.py` split if near size-limit)
- `src/beadloom/services/cli.py` (`docs site` subcommand under the `docs` group)
- `src/beadloom/graph/c4.py` + graph Mermaid/`--json` (reused: diagrams + node/edge data)
- `src/beadloom/application/debt_report.py`, `application/doctor.py`, `graph/linter.py` (reused: dashboard metrics)
- `src/beadloom/doc_sync/` engine + `sync_state` (reused: doc validation badges + coverage)
- `src/beadloom/graph/federation.py` + a `federated.json` (reused: landscape map data)
- NEW `site/.vitepress/config.mjs` + `site/package.json` (committed VitePress scaffold; pinned)
- `docs/` (the source of truth — published, NOT mutated) ; `tests/fixtures/` (anonymized landscape for the map dogfood)
- `docs/guides/` (new VitePress workflow guide), `CHANGELOG.md`, `.claude/development/STRATEGY-3.md` (§F4.2/§F4.3), `BDL-UX-Issues.md`
- `.gitignore` (add `site/.vitepress/dist`, `site/node_modules`)

## Current Phase

- **Phase:** Planning
- **Current bead:** (none yet — created after PLAN approval)
- **Blockers:** none
