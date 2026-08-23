
---

## Project layer — Beadloom's own rules (`.beadloom/flow/claude/CLAUDE.md`)

Everything above is the shipped CORE plus the overlays `.beadloom/flow.yml`
selects. Everything below is true of **this repository only** and is never
distributed. Before BDL-061 S3 there was nowhere to put it, so it went into the
core and shipped verbatim — including a bead id and a claim about this repo's
branch protection that is false for an adopter (BDL-UX #177).

### `setup-branch-protection` — not safe to re-run right now

`DEFAULT_STATUS_CHECK_CONTEXTS` ships **nine** contexts since BDL-061 S2 (it
gained the two `tests-locale` legs); `main`'s live protection has **seven**.
Running the command today would require two checks that are knowingly red until
`beadloom-mr2l.42` closes, making `main` unmergeable. Re-run it once those legs
are green.

### Concurrent waves share one working tree

Commit only your own files, by explicit path — never `git add -A`. Take
`bd merge-slot acquire --wait` before committing and `release` after. Verify in
a clean room (`git archive HEAD` + only your files) and say so in those words:
"green in a clean room over N files" is a different claim from "green on the
tree" (BDL-UX #181).
