# ACTIVE: BDL-042 — GitHub Pages deploy (VitePress project-page)

> **Last updated:** 2026-06-02

---

## Current Focus

- **Phase:** Starting (BEAD-01)
- **Parent bead:** `beadloom-xh40` (chore)
- **Next bead:** `beadloom-xh40.1` — base + base-aware Mermaid clicks
- **Blockers:** none

## Bead Map (`beadloom-xh40`)

| Bead | Role | Status | Depends |
|------|------|--------|---------|
| .1 base=/beadloom/ + base-aware Mermaid clicks + local build verify | dev | open (READY) | — |
| .2 `.github/workflows/deploy-site.yml` (Pages deploy) | chore | open | .1 |

## Notes / Reminders

- **Mode B (project page `/beadloom/`).** Markdown/nav links auto-rewrite with `base`; the gap is Mermaid `click` raw paths → make base-aware (DiagramViewer prepends `import.meta.env.BASE_URL`), keep generated MD base-agnostic + deterministic.
- Owner enabled **Settings → Pages → Source = GitHub Actions** ✓ (the one repo-setting I can't do).
- Coordinator verifies the base-build locally (`beadloom docs site` + `npm run docs:build` with base) — node v18 available.
- Outward-facing: the deploy workflow runs on every push to main; ships with the next push → site live at `https://zoologov.github.io/beadloom/` (owner browser-verifies).
- Content stays deterministic (`beadloom docs site`); CI regenerates so the published site never drifts from the graph.
