# BDL-011 — UX Feedback Log

> Collected during implementation of Plug & Play Onboarding.
> Format: `[DATE] [SEVERITY] Description — Context`

---

## Issues

1. [2026-02-13] [MEDIUM] `doctor` warns about auto-generated skeleton docs as "unlinked from graph" — Generated files like `features/why/SPEC.md` and `services/beadloom.md` don't get matched to graph nodes by the doctor check. The doc-node linking convention doesn't support nested paths like `features/{name}/SPEC.md`. Future fix: update doctor to match by path convention.

2. [2026-02-13] [LOW] `lint` produces no output on success — 0 violations prints nothing. Consider adding `"0 violations, N rules evaluated"` for confirmation. (Already handled in enhanced init output but not in standalone `beadloom lint`.)

3. [2026-02-13] [LOW] `docs generate` creates skeleton files for services including the root — `services/beadloom.md` is generated for the root project node (filtered by non-empty source, but root is "service" kind). The file is useful but "beadloom.md" as a service doc is slightly confusing. Already handled: root is skipped (source is empty).

4. [2026-02-13] [INFO] MCP server description says "8 tools" but now has 9 (generate_docs). CLI says "18 commands" but now has 20 (docs generate, docs polish). To be updated in BEAD-11.
