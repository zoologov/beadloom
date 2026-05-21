# BRIEF: BDL-045 — README rewrite (EN + RU)

> **Status:** Approved
> **Created:** 2026-06-02
> **Type:** task

---

## Problem

`README.md` / `README.ru.md` have drifted and read poorly:

- **Stale / inaccurate coverage.** Beadloom grew a lot across F1–F4.4 (cross-repo federation, the cross-service contract graph, the enforcement gate `beadloom ci` + `federate --fail-on`, AgentConfigAsCode, the VitePress site), but the READMEs were only patched piecemeal (F2 positioning + F3/F4 factual lines). The capability set, tool descriptions, goals, and positioning need a real re-audit against what Beadloom actually does now.
- **"AI-ish", low readability** — awkward logical turns, `;` used instead of `.`/`,`, and (in RU especially) calques that read like machine translation. Owner-flagged examples:
  - slogan «Федеративная инфраструктура архитектуры с контролем „намерение vs реальность"» — reads like an AI wrote it;
  - `;` as a clause separator throughout (bad grammar → bad readability);
  - «кросс-репозиторная идентичность» — hard to parse for a Russian reader;
  - «намерение vs реальность» → simpler «план/факт»;
  - «лимиты кардинальности» → plain wording (limits on node size — how much code/files);
  - «это и есть тот ров, который не воспроизвести» — drop the "moat" metaphor, say it plainly.

## Solution

Two parts, **medium form** (full *coverage* of key capabilities, *concise* delivery — details live in the VitePress portal, not duplicated here):

**(a) Accuracy audit + content refresh.** Re-audit the actual current capability set, tool set, command list, and counts (against the CLI + the graph + the gates), and rewrite the description / goals / intent / positioning to match reality after F1–F4.4. Verify every factual number with `beadloom docs audit` / `beadloom status` (no invented metrics).

**(b) Readability rewrite — human, not AI.** Rewrite `README.md` in clean, plain English and author `README.ru.md` as **natural Russian (not a calque of the English)**. Fix every owner-flagged issue: a human slogan, `;` → `.`/`,`, plain terms instead of calques (`план/факт`; "ссылки/связи между сервисами"; "ограничения на размер узла"; drop "ров"). EN and RU stay structurally in sync (same sections/claims), each idiomatic in its own language.

**Authoring note:** done **inline by the coordinator (not a background subagent)** — readability/RU quality is judgment-heavy and an AI subagent would risk reproducing the same "AI-ish" prose. Draft → owner readability review → 1–2 iterations.

This README also becomes the **About page** of the VitePress portal (EN + RU) in the follow-up portal epic — so the bilingual, human-quality rewrite here is the foundation for that.

## Beads

- **BEAD-01 (task):** README.md + README.ru.md full rewrite — capability/positioning audit + medium-form, human-readable EN + natural RU; owner-flagged issues fixed; `docs audit` clean; EN/RU structurally in sync. (Authored inline + owner review/iterate.)

## Acceptance Criteria

- [ ] README description/goals/positioning match the actual current capabilities (F1–F4.4): federation + contract graph + enforcement gate + portal, plus the per-repo context-oracle/doc-sync/lint foundation.
- [ ] EN reads cleanly and plainly; RU reads like natural Russian written by a human (owner-confirmed).
- [ ] Every owner-flagged issue fixed: human slogan; no `;`-as-separator; «план/факт»; no «кросс-репозиторная идентичность»/«лимиты кардинальности»/«ров» calques.
- [ ] No invented metrics — counts verified via `beadloom docs audit` / `beadloom status`; `docs audit` clean on both READMEs.
- [ ] EN and RU are structurally in sync (same sections + claims).
- [ ] `beadloom ci` / sync-check stay green; anonymization clean.

## Notes

- **Medium form:** cover all key capabilities, briefly; deep detail → the VitePress portal.
- The portal restructure + curated bilingual About + nav changes are the **follow-up epic** (after this).
- Owner review is part of "done" — readability is subjective; expect 1–2 iterations.
