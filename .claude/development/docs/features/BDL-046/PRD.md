# PRD: BDL-046 — VitePress portal: navigation + bilingual About

> **Status:** Approved
> **Created:** 2026-06-02

---

## Problem

The published VitePress portal (F4/F4.4) works, but its information architecture doesn't match how a visitor actually arrives and reads:

- **No "front door".** The landing page is the architecture overview (a C4 diagram), not an explanation of *what Beadloom is and why*. A first-time visitor lands in the middle of the system instead of at an introduction.
- **The left menu is awkward.** "Dashboard → Metrics" and "Landscape → Map" are single pages buried under a one-child group (needless nesting); "Architecture" is large; "Documentation" is a flat wall of links with no shape.
- **The top nav is redundant.** It duplicates the sidebar and adds clutter; the only thing worth keeping up there is the light/dark toggle.
- **English only.** The owner wants the entry page available in Russian too — but not the cost of translating (and forever syncing) the entire docs tree.

## Impact

This turns the portal into a real product front door: a visitor lands on a clear "About", moves to "Getting Started", and navigates a clean, tree-shaped menu that mirrors the architecture and the docs. The About page is offered in English and Russian (the two languages the maintainer cares about) without taking on the maintenance burden of a fully bilingual site. Small, high-visibility polish on top of the F4 foundation.

**Scope decision (Q2 = curated bilingual, agreed with owner):** only the **About** page is bilingual (EN + RU, sourced from `README.md` / `README.ru.md`). The rest of the portal — generated architecture, dashboard, landscape, docs — stays English. This avoids translating and syncing the whole docs tree (a large, ongoing cost); full content i18n remains a possible future follow-up (e.g. via the deferred AI tech-writer).

Success criterion: **the live portal opens on a clear About page, has the exact restructured left menu, no top nav (theme toggle only), a Documentation overview that reads as a guided tree, and an About available in EN and RU — verified in the browser.**

## Goals

- [ ] **G1 — Left-menu restructure**, in this exact order:
  - **About** — first item and the **landing page** (the README — what Beadloom is and why).
  - **Getting Started** — a single item (`docs/getting-started.md`).
  - **Dashboard** — a single flat item (no "Metrics" child).
  - **Architecture** — collapsed by default (the `part_of` tree from F4.4, unchanged), with the current top-level architecture overview / C4 diagram living **inside** it (e.g. "Architecture overview").
  - **Landscape map** — a single flat item (no "Landscape → Map" nesting).
  - **Documentation** — expanded by default, a parent-child tree (the F4.4 docs tree), led by a real Overview page (G3).
- [ ] **G2 — About = the README as the home/landing page.** The site root renders the README content as "About"; the architecture overview that used to be the landing moves under Architecture. Generated from `README.md` (no hand-maintained duplicate).
- [ ] **G3 — Documentation Overview page.** Replace the flat link wall at `/docs/` with a short intro + a section tree (domains → their docs; services; guides) — a guided map, not a dump.
- [ ] **G4 — Remove the top nav, keep the theme switcher.** No top navigation bar entries; the light/dark appearance toggle (and built-in search, if present) stays.
- [ ] **G5 — Curated bilingual About (EN + RU).** The About page is available in both languages (sourced from `README.md` and `README.ru.md`) with a visible language switch. The rest of the portal stays English; a reader who switches to RU and navigates into the (English) docs sees English — that's expected and acceptable for this slice.
- [ ] **G6 — Dogfood (the success criterion).** Generate + build Beadloom's own portal and verify in the browser: About is the landing, the menu matches G1 exactly, the Documentation overview is a tree, there's no top nav (theme toggle works), and the About page switches EN↔RU. Capture friction in `BDL-UX-Issues.md`.
- [ ] **G7 — Tech-writer (docs).** Update the VitePress guide for the new IA + the bilingual-About setup; CHANGELOG; STRATEGY note.

## Non-goals (deferred / out of scope)

- **Full portal/docs i18n** — only About is bilingual; translating + syncing the whole docs tree is out of scope (future follow-up, likely via the deferred AI tech-writer).
- **New content** — this is information-architecture + a bilingual entry page; it does not rewrite docs or add features. (The README itself was just rewritten in BDL-045.)
- **Landscape-map / dashboard / diagram behavior changes** — unchanged from F4/F4.4.
- **A hosted service** — the site stays static, built + deployed by the existing Pages workflow.

## User Stories

### US-1: Land on a clear front door
**As** a first-time visitor, **I want** the portal to open on an "About" page that explains what Beadloom is and why, **so that** I understand it before diving into diagrams.

**Acceptance criteria:**
- [ ] The site root is the About page (README content), first in the left menu.
- [ ] The architecture overview / C4 diagram is reachable under "Architecture", not as the landing.

### US-2: A clean, shaped left menu
**As** a reader, **I want** the left menu to read About · Getting Started · Dashboard · Architecture · Landscape map · Documentation, **so that** navigation is obvious.

**Acceptance criteria:**
- [ ] Dashboard and Landscape map are single flat items (no one-child groups).
- [ ] Architecture is collapsed by default; Documentation is expanded and tree-shaped.

### US-3: A guided Documentation overview
**As** a reader, **I want** the Documentation landing to be a short intro + a section tree, **so that** I can find the right doc instead of scanning a wall of links.

**Acceptance criteria:**
- [ ] `/docs/` shows an intro paragraph + a grouped tree (domains / services / guides), not a flat list.

### US-4: An About I can read in Russian
**As** a Russian-speaking visitor, **I want** to switch the About page to Russian, **so that** the entry page reads naturally in my language.

**Acceptance criteria:**
- [ ] The About page offers EN and RU (from `README.md` / `README.ru.md`) with a visible switch.
- [ ] No top navigation bar; the theme (light/dark) toggle remains.
