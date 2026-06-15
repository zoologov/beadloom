# BRIEF: BDL-056 — Positioning refresh + writing-quality standard + docs hygiene

> **Status:** Approved
> **Created:** 2026-06-15
> **Type:** chore

---

## Problem

After the 2.0.0 release the public-facing texts and the docs tree have drifted from how the product is now positioned and from the quality bar we want to hold:

- **Product positioning is stale.** README.md + README.ru.md still describe Beadloom feature-first, not as the **source of truth about your code** (its architecture, contracts, and documentation), with tools built on top and a single Gate enforcing it. There is an owner-approved positioning thesis (locked, see below) that nothing public yet states — and the READMEs need a full content rewrite (not just a thesis line) so the whole document conveys the vision through what Beadloom does and what it offers.
- **Documentation-writing quality is not encoded anywhere.** The 2.0.0 rewrite of `BDL-AI-AGENTS-ARCHITECTURE.md` took several editorial passes to remove translationese/calques, apologetic section framing, and clipped abbreviations. That bar currently lives only in the owner's head — the **tech-writer role has no written standard**, so the quality is not reproducible by the agent.
- **A draft team deck is committed by accident.** `docs/presentations/` (~700 KB: `.html`/`.pdf`/`.md`/notes) was committed and — because the site generator does `rglob("*.md")` over `docs/` — **is being published to the live VitePress portal**. It is an internal draft, not public documentation.
- **The agent-architecture document is not on the portal.** `.claude/development/docs/BDL-AI-AGENTS-ARCHITECTURE.md` (the multi-agent development process; its 2.0.0 rewrite is already done) lives outside `docs/`, so it never reaches VitePress. Its polished 2.0.0 content currently sits **uncommitted in the `main` working tree** (edited on the protected branch).

## Solution

A single documentation/positioning chore. Encode the writing-quality bar into the tech-writer role so it is reproducible, fully rewrite the public READMEs (en+ru) so the whole document conveys the vision through content and capabilities, remove the accidentally-published deck, and bring the agent-architecture document onto the portal (carrying its already-done 2.0.0 rewrite from the working tree — do NOT redo it).

**README authoring is two-stage and interactive (main loop, NOT a fire-and-forget subagent):** write `README.ru.md` first → owner validates → iterate → only after the RU version is approved, translate it into `README.md` (EN). The thesis below is the positioning anchor, but the rewrite is full: structure, capabilities, usage — the whole document must carry the vision.

**No product/code behavior changes.** The only source change is the tech-writer role template (a writing standard) + recomposed role adapters. Everything else is docs and repo hygiene.

### LOCKED positioning thesis (owner-approved, verbatim — RU canonical)

> Beadloom — это источник правды о вашем коде: его архитектуре, контрактах и документации. Он следит, чтобы всё это не расходилось с кодом, и подсвечивает то, что устарело. В основе лежит запрашиваемый граф, выведенный из самого кода, а поверх него строятся инструменты — межсервисная федерация, проверки целостности, агентный процесс разработки и многое другое. А единый Gate не пропускает в `main` ни нарушения архитектурных границ и правил, ни код с устаревшей или отсутствующей документацией, ни сломанные контракты — одинаково для людей и для агентов.

`README.ru.md` uses this verbatim. `README.md` uses a faithful English rendering (same meaning, equally clean prose). **Do NOT use «экосистема» / "ecosystem" in any public text** (owner's call — it is a direction, not yet a fact).

### Writing-quality standard (goes into the CORE tech-writer role)

> **Writing quality (non-negotiable).** Documentation must read as clean, natural prose in the document's own language. No translationese/calques (e.g. RU «держать» for "enforce", «громкое warning»); no bureaucratic filler; no apologetic or persuasive section framing. No clipped slang abbreviations (RU «доки/репо/конфиг») — write the full word. Do not switch languages mid-sentence — Latin script only for genuine tool/method/command terms (Beadloom, Goose, `sync-check`, ddd/fsd, pull request, push…). Consistent terminology throughout. Full sentences; never stitch two independent clauses with a semicolon. Every claim verified against the code; pronouns unambiguous; headings neutral and descriptive.

### Facts behind the thesis (verified, for accuracy)

`run_ci_gate` (`application/gate.py`) = reindex → lint --strict → sync-check → config-check → doctor → **federate --fail-on** (step 6, only when hub exports are present; fail-set `breaking,drift,orphaned_consumer,undeclared_producer`). Architecture is enforced by `lint --strict`; documentation freshness by `sync-check` + `module-coverage`=error; broken contracts by the federate step. The thesis must not overclaim beyond this.

## Beads

- **BDL-056.1 [dev] — writing-quality standard + docs-tree hygiene:**
  (a) Add the **Writing-quality standard** (text above) to the CORE tech-writer role at `src/beadloom/onboarding/templates/roles/core/tech-writer.md.txt`; recompose the role adapters (`setup-agentic-flow`) so `.claude/agents/tech-writer.md` (+ `.cursor/agents/*`) carry it; drift-guard green.
  (b) `git rm -r docs/presentations/` (remove the accidentally-published draft deck).
  (c) `git mv .claude/development/docs/BDL-AI-AGENTS-ARCHITECTURE.md docs/guides/multi-agent-development.md` — bring the document under `docs/guides/`, **carrying the already-polished 2.0.0 content from the working tree** (the move must preserve that uncommitted text, not the old committed version).
  `beadloom ci` green.

- **BDL-056.2 [tech-writer] — public positioning + portal page** (applies the new standard; depends .1):
  - **Full rewrite of `README.ru.md` first** (two-stage, interactive — see Solution): the whole document conveys the vision through content and capabilities, not just a thesis line. Data-core positioning, the Gate as the single enforcement point for people and agents, tools-on-top; the LOCKED thesis verbatim as the lead; a clear capabilities/usage narrative for an end user. No «экосистема». No overclaim beyond the verified Gate facts. **Owner validates and iterates on the RU version; only after RU is approved, translate it into `README.md` (EN)** — faithful in meaning and structure, en ≡ ru.
  - Adapt the **moved agent-architecture document** for VitePress: title/front-matter, relative links, Mermaid diagrams render. Confirm it appears in the generated site.
  - Regenerate the site (`beadloom docs site`) and confirm the build is clean.

- **BDL-056.3 [review] — fidelity + quality + portal** (depends .2):
  - README is a full content rewrite that conveys the vision through capabilities/usage; RU thesis verbatim as the lead; RU approved by the owner before EN; en ≡ ru (meaning + structure); no «экосистема»/"ecosystem"; no claim beyond the verified Gate behaviour.
  - The writing-quality standard is present in the CORE role template **and** in the composed adapters; drift-guard green.
  - `docs/presentations/` is gone from the tree **and** from the generated site.
  - The agent-architecture document is under `docs/guides/`, renders on VitePress (Mermaid + links OK), and carries the 2.0.0 content (not the stale version).
  - `beadloom ci` rc 0; `beadloom docs site` + `npm run docs:build` green.

- **Integration (coordinator, post-review):** one branch `features/BDL-056`, waves dev → tech-writer → review, **ONE PR → main** → merge → `deploy-site.yml` refreshes the portal.

## Acceptance criteria

- README.md + README.ru.md are a full content rewrite that conveys the vision through what Beadloom does and offers; both lead with the data-core positioning; `README.ru.md` contains the locked thesis verbatim; the RU version is owner-approved before the EN translation; `README.md` is a faithful EN rendering; the two are in lockstep (meaning + structure). No «экосистема»/"ecosystem" anywhere public.
- The Writing-quality standard is in `src/beadloom/onboarding/templates/roles/core/tech-writer.md.txt` and in the composed `.claude/agents/tech-writer.md` (+ Cursor adapter); `setup-agentic-flow` drift-guard is green.
- `docs/presentations/` removed from the repository and absent from the generated VitePress site.
- The agent-architecture document lives under `docs/`, carries its 2.0.0 rewrite, and renders on the portal.
- `beadloom ci` green; VitePress build green; no product/code behavior change (only the role template + docs).
