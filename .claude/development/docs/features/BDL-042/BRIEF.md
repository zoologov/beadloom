# BRIEF: BDL-042 — GitHub Pages deploy (VitePress project-page)

> **Status:** Approved
> **Created:** 2026-06-02
> **Type:** chore

---

## Problem

F4/F4.4 produce a buildable VitePress site (`site/`), but it is only built locally — there is no published URL. The owner wants it served via **GitHub Pages as a project page**: `https://zoologov.github.io/beadloom/`. The repo is public (Pages available) and the owner has already set **Settings → Pages → Source = GitHub Actions**.

A project-page lives under the `/beadloom/` sub-path, which exposes one real gap: the generated internal links are **root-absolute** (`/services/…`, `/docs/…`). VitePress auto-prepends `base` to markdown/nav links during build, BUT the **Mermaid `click "/services/…"`** directives are raw strings the plugin does NOT rewrite — so landscape/diagram node clicks would 404 under `/beadloom/`.

## Solution

A small chore: set the VitePress `base`, make Mermaid click-targets base-aware, and add a Pages deploy workflow.

1. **`base: '/beadloom/'`** in `site/.vitepress/config.mjs`.
2. **Base-aware Mermaid clicks** — make the landscape (and any diagram) `click` hrefs respect the base: either the generator emits base-prefixed paths, or `DiagramViewer.vue` prepends `import.meta.env.BASE_URL` to click targets on mount. Prefer the runtime approach (DiagramViewer) so the generated Markdown stays base-agnostic and deterministic. Verify every diagram click resolves under `/beadloom/`.
3. **Deploy workflow** `.github/workflows/deploy-site.yml` (on push to `main`, + manual `workflow_dispatch`): checkout → setup uv+Python → `uv sync` → `beadloom docs site --out site` → setup Node 18 → `npm ci` (in `site/`) → `npm run docs:build` → `actions/upload-pages-artifact` (`site/.vitepress/dist`) → `actions/deploy-pages`. Correct `permissions:` (pages: write, id-token: write) + `concurrency` per the GitHub Pages action conventions.
4. **Verify** locally: `beadloom docs site --out site` then `npm run docs:build` with `base='/beadloom/'`, confirm the dist + that diagram clicks point at `/beadloom/services/…` (no bare `/services/…`).

## Beads

- **BEAD-01 (dev):** `base: '/beadloom/'` + base-aware Mermaid clicks (DiagramViewer prepends `BASE_URL`); local build with base verified; the existing dead-link/click guards still pass. TDD where applicable.
- **BEAD-02 (chore):** `.github/workflows/deploy-site.yml` (Pages deploy: beadloom docs site → npm build → upload-pages-artifact → deploy-pages; correct permissions/concurrency); valid YAML.
- (Verification + the published-URL note handled by the coordinator on landing; CHANGELOG/guide line for the deploy added with BEAD-02.)

## Acceptance Criteria

- [ ] `site/.vitepress/config.mjs` sets `base: '/beadloom/'`.
- [ ] Mermaid/diagram `click` targets resolve under `/beadloom/` (no bare-root 404); markdown/nav links work under base.
- [ ] `beadloom docs site` + `npm run docs:build` succeed locally with `base` set; `.vitepress/dist` produced.
- [ ] `.github/workflows/deploy-site.yml` is valid, has `pages: write` + `id-token: write`, builds the site (beadloom → npm) and deploys to Pages on push to main.
- [ ] `beadloom ci` / pytest / lint / doctor stay green; anonymization clean.
- [ ] On the next push, the Pages deploy runs and the site is live at `https://zoologov.github.io/beadloom/` (owner-verified in browser).

## Notes

- Owner has enabled Settings → Pages → Source = GitHub Actions (the one repo-setting I can't do).
- Outward-facing: this publishes a public site + adds a workflow that runs on every push to main. Ships as part of the next push.
- Honest: the site content is still generated deterministically by `beadloom docs site` (no hand-editing); the workflow regenerates it in CI so the published site never drifts from the graph.
