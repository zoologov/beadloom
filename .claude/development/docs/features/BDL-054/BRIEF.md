# BRIEF: BDL-054 — Release 2.0.0 prep

> **Status:** Approved
> **Created:** 2026-06-14
> **Type:** chore

---

## Problem

A lot shipped since the last version (1.10.0): BDL-049 (strict trunk-based), BDL-050 (consolidated CI), BDL-051 ("Beadloom governs itself" — component kind + `module-coverage`=error + `ai_agents` domain), BDL-053 (tracker/ACTIVE coherence), BDL-052 (the configurable, tool-agnostic, Gate-enforced agentic doc-flow). The public-facing artifacts haven't caught up:

- **Badges are stale/broken:** the `Tests` badge points at `tests.yml`, **retired in BDL-050** (consolidated into `ci.yml`) → broken. PyPI / Python-version badges depend on a PyPI release that may not exist yet.
- **README (en+ru), `docs/architecture.md`, `docs/getting-started.md` are behind** the shipped reality — and they feed the **VitePress site** (generated from `docs/` + README via `beadloom docs site`), so the public portal is stale too.
- **No release cut:** `__version__` is still `1.10.0`; CHANGELOG has an open `[Unreleased]`; no `v2.0.0` tag / GitHub Release / PyPI publish.

## Solution

Ship a full **2.0.0** release (semver MAJOR — justified: breaking changes for adopters [ai_techwriter module path moved `tools.ai_techwriter`→`beadloom.ai_agents.ai_techwriter`; `module-coverage` promoted to error → can fail previously-green repos; vendoring retired] + a product-level capability leap). Refresh all public docs so the VitePress portal reflects 2.0.0.

**ty migration is OUT OF SCOPE / DEFERRED** — `ty` is still beta with lower accuracy than mypy; keep `mypy --strict`. Do NOT touch the type-checker in this release.

Mechanism notes: version lives in `src/beadloom/__init__.py` (`__version__`, read by `[tool.hatch.version]`). `pypi-publish.yml` triggers `on: release` (a GitHub Release → build + testpypi + pypi). VitePress refresh: `beadloom docs site` + the `deploy-site.yml` on push:main.

## Beads

- **BDL-054.1 [dev] — release mechanics:** bump `__version__` → `2.0.0` (+ CLAUDE.md §0.1 "Current version"); fix the **`Tests` badge** `tests.yml`→`ci.yml` in BOTH README.md + README.ru.md; verify/repair the other badges (PyPI: confirm published or adjust); finalize CHANGELOG `[Unreleased]` → a dated **2.0.0** entry (consolidating BDL-049/050/051/053/052); update ROADMAP (2.0.0 shipped). `beadloom ci` green.
- **BDL-054.2 [tech-writer] — public docs refresh (feeds VitePress):** README.md + README.ru.md positioning + accuracy (lead with federation / intent-vs-reality + the free/MIT integrated-loop moat; reflect what shipped; **en ≡ ru in sync**); `docs/architecture.md` (current DDD package set incl. `ai_agents/`, the `component` node kind, graph/lint/sync-check, the agentic flow + configurator, no-shadow-code); `docs/getting-started.md` (END-USER clarity: what Beadloom does, configuration — `.beadloom/config.yml` + `flow.yml` tools/architecture(ddd|fsd)/stack, `setup-agentic-flow --tool/--stack/--architecture`, `install-hooks` pre-commit + pre-push Gate, `setup-mcp`/`setup-rules` — and GREAT usage examples: init → task-init→coordinator→roles→Gate→PR, the ai-techwriter, federation hub/satellites; concrete commands + expected output). Depends .1.
- **BDL-054.3 [review] — release readiness:** badges render; README en ≡ ru; docs match the shipped reality (no overclaim); `__version__`/CHANGELOG/CLAUDE.md version consistent at 2.0.0; **VitePress site builds clean** (`beadloom docs site` + `npm run docs:build`); `beadloom ci` rc 0. Depends .2.
- **Release step (coordinator, post-merge):** merge the single PR → create GitHub Release `v2.0.0` (triggers `pypi-publish.yml`) → confirm `deploy-site.yml` refreshes the portal.

One branch `features/BDL-054`, dev → tech-writer → review, ONE PR → merge → release.

## Acceptance criteria

- `__version__ == "2.0.0"`; CHANGELOG has a dated 2.0.0 entry (no dangling `[Unreleased]` content for shipped work); CLAUDE.md §0.1 says 2.0.0.
- The `Tests` badge points at `ci.yml` and renders; all README badges (en+ru) render correctly; PyPI status confirmed/handled.
- README.md ≡ README.ru.md (content parity); both lead with the current positioning + reflect shipped capabilities.
- `docs/architecture.md` + `docs/getting-started.md` are accurate, end-user-clear, with working examples — and the **regenerated VitePress site shows them**.
- `beadloom ci` + the consolidated `ci.yml` green; VitePress build green; the v2.0.0 tag/Release cut + PyPI publish confirmed (or documented).
- `mypy --strict` unchanged (ty deferred).
