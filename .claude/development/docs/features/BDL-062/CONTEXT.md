# CONTEXT: BDL-062 — Graph metadata is an unchecked surface

> **Status:** Approved
> **Created:** 2026-08-26

---

## State

Baseline `main` = `cdc16de` (release 3.0.0). Tree clean, `beadloom ci` green, tag `v3.0.0`
published, PyPI verified in a fresh venv.

Branch: `features/BDL-062`. One PR to `main`, then the release commit.

## Standing verification rules

BDL-061's rules carry over verbatim and are cited **by name, never by number** — renumbering
silently rewrote a commit message during that epic:

- **FAKES PROVE FAKES** — a fixture that cannot exhibit the defect proves nothing.
- **TESTS MUST BITE** — every check ships with a test proving it FAILS on its condition.
  Reverting one correction must turn `beadloom ci` red.
- **REPORTS ARE NOT EVIDENCE** — including the coordinator's own reports. Verify the claim,
  not the summary of the claim.
- **CLEAN-ROOM REVERT** — verify over `git archive HEAD` plus only your files; say "green in
  a clean room over N files" when that is what was done. **Amended 2026-08-26, and the
  amendment is the point: `git archive HEAD | tar -x` produces a tree that is not a git work
  tree, so `git_baseline` can answer nothing and every doc pair returns `unverified`.**
  Measured on the same tree: 363 `unverified` without `git init`, 363 `ok` with it. `beadloom
  ci` exits 0 in both and says `0 pair(s) fresh, 363 NOT VERIFIED` in the one — so a check
  reading the exit code accepted a room that verified nothing. **Run `git init` plus one commit
  inside the clean room before measuring, and quote the sync-check line, not the rc.** Every
  clean-room claim in BDL-061 and earlier in this feature was, on the doc-freshness axis, a
  measurement of the absence of git. The tool said so on every run; nobody read the line.
  (See #198.)
- **NO CALLER NO CAPABILITY** — a function nothing calls is not a feature.
- **A GREEN COUNT IS NOT A CHECKED COUNT** — state the denominator and name what was skipped.
- **CAPTURE, DON'T RE-RUN** — capture failing output on first sight; an intermittent failure
  re-run is an identity lost.
- **TRUE HERE IS NOT TRUE** — one platform, one locale, one project is not verification.

Added by this feature:

- **UNCHECKED IS NOT CLEAN, AND THE CHECKER MUST SAY WHICH.** The whole feature is one
  instance of the epic's class: a green result describing the checker's ignorance rather
  than the code's health. Every rule here reports `unverifiable` as its own state.
- **A TOTAL STAND-DOWN IS NOT A PARTIAL GAP.** A check that verified *none* of its
  population states a different fact from one with a hole in it, and must not reach the reader
  through the same channel or the same severity. Established by `.9`: `liveness_finding`
  hardcoded `severity = "warn"`, so a rule this project escalated to `error` could stop
  checking all 86 of its pairs while `lint --strict` exited 0. The same shape survives one
  layer up in `sync-check` (#198), recorded rather than fixed.

- **A FILTER THAT CANNOT SEE THE FAILURE IS NOT A MEASUREMENT.** The coordinator failed to
  reproduce #195 because it filtered on `rule_type == doc_area_coherence`, and the stand-down
  publishes under the liveness type. The probe returned 0 while the defect was live. Before
  concluding *absent*, prove the instrument could have shown *present*.

- **A SELF-FACT IS NOT A PROJECT FACT.** A value read from the running package describes the
  tool. If it appears in a report about someone else's project, it is a defect, and being
  correct about Beadloom does not excuse it.

## Decisions

**Rules go in the lint engine, not the audit.** The graph is already indexed as
`nodes(ref_id, kind, summary, source, extra, lifecycle)` + `docs(…, ref_id, …)`. Rules query
that schema, so they are generic across any project's `_graph/*.yml` for free. The audit
keeps computing facts; the rules consume them.

**R2 derives its convention from the graph, never from a hardcoded layout.** Measured here:
69 agree / 4 differ. A graph with no dominant convention gets "checked nothing", not a pass.

**R2 ships `warn`, escalated to `error` by this repository's config.** A convention check
that blocks an adopter's first run on their own house style is a rule they disable.

**The release is not gated on the rules.** If R1–R3 need another pass, the corrections and
docs ship as 3.0.1 and the rules follow. Stated so the deadline never becomes an argument
for a weaker rule.

## Out of scope — recorded so it is not re-litigated

- **Positioning.** The README lead, the audience it addresses first, whether one name covers
  three products. Owner decision, tracked separately, not this feature.
- **The model.** `application` as a join layer with `kind: domain`, `services.yml` at 84
  nodes, `onboarding` no longer matching its contents. An epic.

## Standards

Python ≥3.10 · ruff (lint + format) · mypy --strict · pytest.
Gate: `uv run pytest`, `uv run ruff check src/ tests/`, `uv run mypy src/`, `beadloom ci` rc 0.

Concurrent waves share one working tree: commit only your own files by explicit path, never
`git add -A`; take `bd merge-slot acquire --wait` before committing, `release` after.

## Open questions

None blocking. The two deferred items above need owner input before they become work, and
neither blocks a line of this feature.
