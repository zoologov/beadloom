# ACTIVE: BDL-056 — Positioning refresh + writing-quality standard + docs hygiene

> **Type:** chore
> **Branch:** features/BDL-056
> **Parent bead:** beadloom-7gxi
> **Updated:** 2026-06-15

---

## Current focus

`.2 [tech-writer]` — README.ru.md full rewrite (RU-first, owner-validated, interactive in main loop) → EN README.md after RU approval; adapt the moved guide for VitePress; regenerate the site (this is where the committed `site/docs/presentations/` pages get dropped). Fold in the P0 `beadloom-mft7` `{{ }}` fix so the build is green.

## Bead status

| Bead | Role | Status | Depends |
|------|------|--------|---------|
| beadloom-7gxi.1 | dev | ✓ done | — |
| beadloom-7gxi.2 | tech-writer | ready | .1 |
| beadloom-7gxi.3 | review | blocked | .2 |

## Plan notes

- README (en/ru) is authored **interactively in the main loop**, RU-first: draft `README.ru.md` → owner validates → iterate → after RU approval translate to `README.md` (en ≡ ru). Not a fire-and-forget subagent.
- `docs/vision.md` was dropped (owner's call 2026-06-15): the thesis becomes the README lead; one less prose doc to keep fresh, no duplication/drift.
- Agent-architecture doc lands at `docs/guides/multi-agent-development.md`; its 2.0.0 rewrite is already done and sits uncommitted in the working tree — the `git mv` must preserve that content.

## Watch-out

- Pre-existing **P0 bug beadloom-mft7**: VitePress build broken by `{{ }}` Vue-interpolation in `docs/guides/ai-techwriter.md`. This blocks the "site build green" acceptance criterion for `.2`/`.3`. Decide with owner whether to fold its fix into this branch or land it first.

## Progress log

- 2026-06-15 — BRIEF approved; parent + 3 sub-beads created (beadloom-7gxi.1/.2/.3) with deps; branch `features/BDL-056` created (carried the uncommitted agent-arch doc). Starting `.1`.
- 2026-06-15 — `.1 [dev]` DONE: standard in CORE role + recomposed/re-vendored tech-writer adapter (drift-guard green); deck source + `.gitignore` entry removed; doc moved to `docs/guides/multi-agent-development.md` (2.0.0 content preserved). 4227 tests pass, ruff clean, `beadloom ci` green. **Correction:** the deck was NOT committed in source (gitignored) but its GENERATED pages live in `site/docs/presentations/` (committed → on the live site); `.2`'s site regeneration drops them. **Lesson:** `setup-agentic-flow --force` inside the Beadloom repo corrupts the vendored `CLAUDE.md.txt` placeholder — reverted; recompose touched only the tech-writer role.
