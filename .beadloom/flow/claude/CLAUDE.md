
---

## Project layer — Beadloom's own rules (`.beadloom/flow/claude/CLAUDE.md`)

Everything above is the shipped CORE plus the overlays `.beadloom/flow.yml`
selects. Everything below is true of **this repository only** and is never
distributed. Before BDL-061 S3 there was nowhere to put it, so it went into the
core and shipped verbatim — including a bead id and a claim about this repo's
branch protection that is false for an adopter (BDL-UX #177).

### `setup-branch-protection` — not safe to re-run right now

`DEFAULT_STATUS_CHECK_CONTEXTS` ships **ten** contexts; `main`'s live protection
has **seven**. Running the command today would require checks that do not yet
report green, making `main` unmergeable.

The count has moved twice, which is the thing to notice rather than the number:
S2 added the two `tests-locale` legs (red until `beadloom-mr2l.42` closed them —
they are green now), and S4 added `tests-windows`, which is expected red until
`beadloom-mr2l.60` adjudicates the backslash refusal on a real Windows runner.

So the rule is not "wait for a named bead" — that reading was wrong within an
hour of being written. It is: **before running this command, compare the declared
contexts against what actually reports green.**

    gh api repos/:owner/:repo/branches/main/protection \
      --jq '.required_status_checks.contexts'
    gh pr checks <any open PR>

A dimension is added whenever this project learns it was only ever verified along
one axis, so the declared set will keep growing ahead of the green set. That gap
is the normal state, not an incident.

### Concurrent waves share one working tree

Commit only your own files, by explicit path — never `git add -A`. Take
`bd merge-slot acquire --wait` before committing and `release` after. Verify in
a clean room (`git archive HEAD` + only your files) and say so in those words:
"green in a clean room over N files" is a different claim from "green on the
tree" (BDL-UX #181).
