# RFC: BDL-046 — VitePress portal: navigation + bilingual About

> **Status:** Done
> **Created:** 2026-06-02
> **PRD:** ./PRD.md

---

## Summary

Reshape the generated VitePress portal's information architecture and add a curated bilingual entry page. Everything is produced by the existing Python generator (`beadloom docs site --out site`) — no hand-maintained content. Four moving parts:

1. **About = README as the home page** (`/`), replacing the architecture overview as the landing. The architecture overview moves to its own page under the Architecture group.
2. **Left-menu restructure** in `site_nav.py`: exact order, flattened single-item groups, Documentation led by a real overview.
3. **Top nav removed** (empty `nav`), theme toggle + built-in search + locale switch retained automatically by the default theme.
4. **Bilingual About** via VitePress `locales`: EN root (`/`, from `README.md`) + RU locale (`/ru/`, from `README.ru.md`); the default theme's locale switcher is the visible language toggle. Only About is translated.

All generator output stays pure + deterministic (sorted, byte-stable) and link-safe (only emits links to pages that exist), consistent with F4/F4.4.

## Current state (what exists)

- `application/site.py` — `generate_site()` orchestrator: emits `index.md` (currently the **architecture overview** / C4 landing), per-node pages (`/services`, `/domains`, `/features`), `/dashboard`, `/landscape`, the `/docs/` tree, and `.vitepress/config.generated.mjs`.
- `application/site_nav.py` — pure nav/sidebar builders: `render_architecture_group()` (collapsed `part_of` tree, top entry `{ text: "Architecture overview", link: "/index" }`), the Documentation group (mirrors `docs/`), `human_label()`. Emits JS fragments into `config.generated.mjs` (`export const nav`, `export const sidebar`).
- `site/.vitepress/config.mjs` — stable committed shell: `withMermaid`, `base: "/beadloom/"`, imports `nav`/`sidebar` from `config.generated.mjs` into `themeConfig`.
- README.md (EN) + README.ru.md (RU) — rewritten in BDL-045; the bilingual source for About.
- `.github/workflows/deploy-site.yml` — generates + builds + deploys to Pages (unchanged by this epic).

Current generated nav (to be replaced): `Dashboard · Architecture(→/index) · Landscape · Documentation`. Current sidebar nests `Dashboard → Metrics` and (per F4.4) `Landscape → Map`.

## Proposed design

### 1. About home from README (G2)

New transform turns `README.md` into the VitePress home page at `/` ("About"). Because README links are repo-relative, the transform **rebases links** so they resolve on the published site:

| README link target | Rebased to |
|--------------------|------------|
| `docs/<x>.md` that has a published page | site doc link `/docs/<x>` (extension-less) |
| `README.ru.md` / `README.md` cross-links | dropped from body (handled by the locale switcher) |
| `LICENSE`, source paths, anything without a published page | absolute GitHub repo URL (`https://github.com/<owner>/beadloom/blob/main/<path>`) |
| external URLs + shields.io badges | unchanged |

Mechanics: a new helper `application/site_about.py` (`render_about(readme_text, *, published_doc_slugs, repo_url) -> str`) — pure, deterministic, unit-testable. It rewrites Markdown link/image targets per the table, leaving prose untouched. `site.py` calls it for EN (`/index.md`) and RU (`/ru/index.md`).

The **architecture overview** (today's `index.md` body) moves to a new page `architecture.md` (`/architecture`). `site_nav.py`'s Architecture-group top entry changes from `link: "/index"` to `link: "/architecture"`.

> VitePress home: the About page is plain Markdown (no `layout: home` hero) — the README *is* the front-door content, so we render it as a normal doc rooted at `/`. This keeps it identical to GitHub.

### 2. Left-menu restructure (G1)

`site_nav.py` emits the sidebar in this exact order; `nav` (top) becomes empty (G4):

```
About            → /            (link)
Getting Started  → /docs/getting-started   (link; emitted only if the page exists)
Dashboard        → /dashboard   (link, flat — no "Metrics" child)
Architecture     → group, collapsed: true
                     • Architecture overview → /architecture
                     • <part_of tree…>       (unchanged from F4.4)
Landscape map    → /landscape   (link, flat — no "Map" child)
Documentation    → group, collapsed: false (expanded)
                     • Overview → /docs/      (G3)
                     • <docs/ tree…>          (unchanged from F4.4)
```

- **Flatten** Dashboard + Landscape: emit a plain `{ text, link }` instead of a one-child group.
- **About / Getting Started** are link-safe: About always exists; Getting Started emitted only if `docs/getting-started.*` published (else omitted, no dead entry).
- **Documentation** group gets `collapsed: false` and an "Overview" leading item; Architecture stays `collapsed: true`.

New/changed `site_nav.py` API: `render_sidebar(conn, *, docs_root, has_getting_started) -> str` composes the full ordered list (About, Getting Started, Dashboard, Architecture group, Landscape map, Documentation group). `render_nav()` returns `[]`.

### 3. Top nav removed, theme + search + locale kept (G4)

`config.generated.mjs` exports `nav = []`. The VitePress default theme renders the **appearance (light/dark) toggle**, **local search** (if configured), and the **locale switcher** in the nav bar independently of `nav` entries — so removing nav items keeps all three. No `config.mjs` change needed for this beyond what locales require (below).

### 4. Bilingual About — in-page toggle (G5)

> **Design correction (dogfood, round 2):** the original plan below used VitePress `locales` for the language switch. Live dogfood proved it the WRONG tool for "only About is bilingual": the default-theme locale switcher does a global `/x ↔ /ru/x` path mapping for EVERY page, so (a) it translated the whole menu and (b) clicking it on any page other than `/ru/` 404'd (no mirrored RU tree exists). **Corrected design:** drop `locales` entirely; keep a single EN sidebar (menu never translated); make the bilingual About an **in-page cross-link** — `render_about` rewrites the README's `[Русский](README.ru.md)` / `[English](README.md)` line to the counterpart route (`/ru/` ↔ `/`) instead of dropping it. The toggle then appears ONLY on About and never 404s elsewhere. `navRu`/`sidebarRu`/`render_sidebar_ru` are removed. The struck-through `locales` plan below is kept for the record.

~~Use VitePress's native i18n. `config.mjs` gains a `locales` block; the generator drives per-locale nav/sidebar:~~

```js
// config.mjs (shell) — locales merged from generated per-locale trees
locales: {
  root: { label: "English", lang: "en", themeConfig: { nav, sidebar } },
  ru:   { label: "Русский", lang: "ru", link: "/ru/",
          themeConfig: { nav: navRu, sidebar: sidebarRu } },
},
```

- `config.generated.mjs` additionally exports `navRu` + `sidebarRu`. The **RU sidebar contains only the About entry** (`/ru/`) plus links back into the EN sections (Dashboard/Architecture/Landscape/Documentation point at the EN `/...` routes) — so a RU visitor has the full menu but only the About text is translated. This matches Q2 = curated-About-only.
- RU About page generated at `/ru/index.md` from `README.ru.md` via the same `render_about` transform (RU doc slugs reuse the EN published pages).
- The **locale switcher** (default-theme dropdown, top-right) is the visible language toggle required by G5.
- `base: "/beadloom/"` is unchanged; RU About resolves to `/beadloom/ru/`.

### 5. Documentation Overview page (G3)

`site.py` emits `/docs/index.md` as: a one-paragraph intro + a **grouped tree** (Domains → their docs; Services; Guides), built from the same node/doc data the Documentation sidebar uses — a guided map, not the current flat link list. Pure + link-safe (only published pages).

## Module / file impact

| File | Change | Tested by |
|------|--------|-----------|
| `application/site_about.py` (NEW) | `render_about()` — README→About Markdown transform + link rebasing | unit |
| `application/site_nav.py` | new ordered `render_sidebar()`, flatten Dashboard/Landscape, About/Getting-Started entries, `/architecture` link, Documentation overview + `collapsed: false`, empty `render_nav()`, RU sidebar variant | unit |
| `application/site.py` | About home (`/index.md` EN, `/ru/index.md` RU), move arch overview → `/architecture.md`, docs overview `/docs/index.md`, emit `navRu`/`sidebarRu` | unit |
| `site/.vitepress/config.mjs` | `locales` block (EN root + RU), import `navRu`/`sidebarRu` | dogfood build only |
| docs (VitePress guide), CHANGELOG, STRATEGY | tech-writer | — |

The Python generator stays fully unit-testable without Node; the `config.mjs` shell + locales are verified by the dogfood build (G6), consistent with F4/F4.4.

## Alternatives considered

- **Full site i18n (translate every page).** Rejected (PRD non-goal): large one-time cost + permanent sync burden on generated docs. Curated-About-only gives the high-value bilingual entry without it.
- **Hand-written About page (duplicate of README).** Rejected: two sources drift. Generating from README keeps a single source (the README we just rewrote in BDL-045).
- **Custom Vue language-toggle component instead of locales.** Rejected: VitePress `locales` already provides routing, the switcher UI, and `lang` attributes for free; a custom toggle reinvents it and fights the router.
- **`layout: home` hero for About.** Rejected: the README is the curated front-door copy; rendering it verbatim (same as GitHub) is the point. A hero would mean maintaining separate landing copy.

## Risks & mitigations

- **README link rebasing misses a case → dead/awkward link on About.** Mitigate: `render_about` rebases by an explicit table, defaults unknown internal links to absolute GitHub URLs (never a broken site link), and dogfood (G6) walks the built About in-browser. The existing build is run with link-checking from F4.
- **Locales interaction with `base`.** Mitigate: keep `base` in the shell; locale `link: "/ru/"` is base-relative by VitePress convention; verified by the dogfood build, not assumed.
- **RU sidebar linking into EN pages feels inconsistent.** Accepted + documented (PRD US-4): only About is bilingual this slice; the menu still works, links just land on EN docs. Tech-writer notes this in the guide.
- **"Build green ≠ renders right"** (the F4/F4.4/BDL-043 lesson). Mitigate: G6 is the success criterion — verify About-as-landing, exact menu, no top nav, theme toggle, docs-overview tree, and EN↔RU switch on the **deployed** site, not just `docs:dev`.

## Rollout

Single epic, waves: dev (generator: about-transform → nav restructure → docs-overview → locales/home wiring) → test → review → dogfood (G6) → tech-writer. Deployed by the existing `deploy-site.yml`. No data migration; regeneration is idempotent.
