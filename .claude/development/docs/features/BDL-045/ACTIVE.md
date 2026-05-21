# ACTIVE: BDL-045 — README rewrite (EN + RU)

> **Last updated:** 2026-06-02

---

## Current Focus

- **Phase:** Capability audit → EN draft → RU draft → owner review
- **Bead:** `beadloom-o6hz` (in progress)
- **Authoring:** inline by coordinator (judgment/readability-heavy); owner reviews RU, trusts EN.
- **Blockers:** none

## Plan

1. Audit the actual current capability set (CLI commands, counts, gates, F1–F4.4 features) + read the current READMEs to see what is stale/AI-ish.
2. Draft `README.md` — medium form, plain human English.
3. Author `README.ru.md` — natural Russian (not a calque); fix all owner-flagged issues (план/факт, no `;`, plain terms, no "ров").
4. Verify counts (`docs audit` / `status`); `docs audit` clean; `beadloom ci` green; anonymization clean.
5. Owner readability review → 1–2 iterations → close.

## Notes

- Medium form: full coverage of key capabilities, concise; deep detail → the VitePress portal.
- EN + RU both human-readable; EN on me, RU owner-verified.
- This README becomes the bilingual About page in the follow-up portal epic.
