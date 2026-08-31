# CONTEXT: BDL-066 — Agent behaviour observability

> **Status:** Draft
> **Created:** 2026-08-31

---

## State

Baseline `main` = `92a86c4`. Beadloom 3.0.2 on PyPI, `beadloom ci` green.

Two guards exist today and both are the seed of this feature: `bead-claimed`
(373 firings) and `working-branch` (334), both at `warn`, neither ever blocking.
They are the only machinery in the product that looks at process rather than at
code.

Branch: `features/BDL-066`. One PR per slice to `main`.

## Standing verification rules

Carried from BDL-061 and BDL-062, cited **by name, never by number** —
renumbering silently rewrote a commit message during BDL-061:

- **FAKES PROVE FAKES** — a fixture that cannot exhibit the defect proves nothing.
- **TESTS MUST BITE** — every check ships with a test proving it FAILS on its
  condition.
- **REPORTS ARE NOT EVIDENCE** — including the coordinator's own, and now
  including the retrospective role's.
- **CLEAN-ROOM REVERT** — `git archive HEAD | tar -x` is not a git work tree, so
  every doc pair returns `unverified`. Run `git init` plus one commit inside the
  room and quote the sync-check line, not the exit code.
- **NO CALLER NO CAPABILITY** — a function nothing calls is not a feature.
- **A GREEN COUNT IS NOT A CHECKED COUNT** — state the denominator.
- **CAPTURE, DON'T RE-RUN** — an intermittent failure re-run is an identity lost.
- **TRUE HERE IS NOT TRUE** — one platform, one locale, one project is not
  verification.
- **A TOTAL STAND-DOWN IS NOT A PARTIAL GAP** — a check that verified none of its
  population must not reach the reader through the same channel as one with a hole.
- **A FILTER THAT CANNOT SEE THE FAILURE IS NOT A MEASUREMENT** — before
  concluding *absent*, prove the instrument could have shown *present*.

Added by this feature:

- **DETECTABILITY, NOT PREVENTION.** Every mechanism here raises the chance a
  deviation is seen. None stops it. Any shipped text claiming otherwise is a
  defect, because a false sense of oversight is worse than none.
- **THE AUDITOR IS NOT EXEMPT.** The retrospective role is held to the rules
  above, starting with the denominator. An agent summarising agents is the
  easiest place in this product to hide an unverifiable green.
- **AN AMBIGUOUS CONSTRAINT IS RESOLVED BY ASKING, NOT BY CHOOSING** — and when
  it is resolved by choosing, the choice is named out loud. Two measured failures
  share this root and differ only in direction. A session on another project read
  a conditional instruction — *"unless the user requested it"* — as a wall, and
  silently dropped to single-agent mode where the reviewer was the author. The
  coordinator on 2026-08-27 read a free brief as needing five hard constraints,
  silently locked what the owner had spent a day arranging to change, and then
  reported the lock as an achievement. One resolved ambiguity toward less work,
  the other toward less risk. Both resolved it alone.

- **A LINK NEEDS A SHARED NAME.** Trace and result may be joined only when both
  sides name the same object. Otherwise they are reported side by side, unlinked.

## Decisions

**Collection is optional and third-party.** Beadloom reads a store through a
narrow adapter and never collects. An absent store yields *not verified*, with
the reason, everywhere it is consumed.

**Hook events first, proxy later.** Hooks carry the subagent launch and its
`tool_input` — the brief — which is what the failure classes need. The proxy adds
the system prompt and every secret in it.

**Numbers before narrative.** The deterministic layer computes; the role
interprets and may not exceed what was computed.

**The retrospective role is read-only.** The thing auditing the process must not
be able to change the process.

**Secrets handling is mechanism, not advice.** Store git-ignored by default,
redaction on read, retention window, a `doctor` check that the store is untracked.
This is not deferrable: a live API key already passed through tool arguments in
this repository on 2026-08-31.

## Out of scope — recorded so it is not re-litigated

- **The proxy adapter and the system prompt.** A later slice behind the same
  interface.
- **Per-agent scoring.** The output is measurements and process changes.
- **Blocking on behaviour.** Guards here ship `warn`. Raising any of them to
  `error` is a separate, measured decision, and the same reasoning applies as in
  BDL-062: a rule that blocks an adopter's first run is a rule they disable.

## Standards

Python >=3.10 · ruff · mypy --strict · pytest.
Gate: `uv run pytest`, `uv run ruff check src/ tests/`, `uv run mypy src/`,
`beadloom ci` rc 0.

Concurrent waves share one working tree: commit only your own files by explicit
path, never `git add -A`. Note that the pre-commit hook re-stages
`.beads/issues.jsonl` regardless (BDL-UX #207, confirmed five times) — report it,
do not fight it. `bd merge-slot` enqueues a holder behind itself (#194); if
`acquire` does not grant, say so rather than polling.

## Open questions

**Does the retrospective role consume the owner's verdict?** The owner's
judgement of the result — "this text is good", "this was wrong" — is the highest
quality signal available and the trace cannot produce it. Taking it as an
optional input makes the retrospective sharper. Requiring it makes the feature
depend on a human writing something after every epic, which is the kind of
discipline this project has repeatedly measured decaying. Proposed: optional
input, and its absence stated in the report.
