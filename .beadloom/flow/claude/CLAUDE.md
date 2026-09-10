
---

## Project layer — Beadloom's own rules (`.beadloom/flow/claude/CLAUDE.md`)

Everything above is the shipped CORE plus the overlays `.beadloom/flow.yml`
selects. Everything below is true of **this repository only** and is never
distributed. Before BDL-061 S3 there was nowhere to put it, so it went into the
core and shipped verbatim — including a bead id and a claim about this repo's
branch protection that is false for an adopter (BDL-UX #177).

### `setup-branch-protection` — the gap is closed as of 4.0.0, and will reopen

**As of 2026-09-10 the declared set and the live set are the same nine.** The two
`tests-locale` legs were the whole difference; they reported `SUCCESS` on PR #64
and #65, `ci.yml` carries no `if:` and no `paths:` filter on that job so it runs
on every PR, and its matrix produces the two context names verbatim. The command
was re-run against `zoologov/beadloom` and the payload differed from the live
protection in those two entries and nothing else — `strict`, `enforce_admins`,
0 required reviews, `restrictions: null`, force-push and deletion all unchanged,
compared before and after.

**This paragraph is the thing most likely to be false when you read it.** It was
false for the four months before this line was written, and the sentence it
replaced described a seven-vs-nine gap as the standing state. Re-measure; do not
believe this.

The count has moved three times, which is the thing to notice rather than the
number: S2 added the two `tests-locale` legs (red until `beadloom-mr2l.42` closed
them — they are green now), S4 added `tests-windows`, and `beadloom-mr2l.64`
withdrew it again by owner decision — ~16-28 runner-minutes per PR and the
pipeline's critical path, for a platform outside this project's audience. So the
declared set can shrink as well as grow, and a withdrawal moves the ci.yml job
and the context together or it leaves a lockout behind.

So the rule is not "wait for a named bead" — that reading was wrong within an
hour of being written. It is: **before running this command, compare the declared
contexts against what actually reports green.**

    gh api repos/:owner/:repo/branches/main/protection \
      --jq '.required_status_checks.contexts'
    gh pr checks <any open PR>

A dimension is added whenever this project learns it was only ever verified along
one axis, so the declared set will keep growing ahead of the green set. That gap
is the normal state, not an incident — and closing it, as 4.0.0 did, is a moment
rather than a property.

One risk this repository carries and an adopter may not: `ai-techwriter` runs on
a **self-hosted** runner. It is a required check, so `main` is unmergeable while
that VPS is down. That predates the nine and is not part of it.

### Concurrent waves share one working tree

Commit only your own files, by explicit path — never `git add -A`. Take the
landing lock as `bd merge-slot acquire --holder <bead-id>` before committing and
`bd merge-slot release --holder <bead-id>` after, and treat a non-zero exit as
*you do not hold it*. The lock orders the COMMITS; what keeps two agents out of
one file is the disjoint scopes `beadloom waves` derived, and every wave this
project ran before 2026-09-04 relied on the second while believing it held the
first (BDL-UX #194, #237). Verify in a clean room built by
`beadloom clean-room <bead-id> --carry <path>...`, which derives the room's path
from the bead and refuses a directory it did not create, and say so in those
words: "green in a clean room over N files" is a different claim from "green on
the tree" (BDL-UX #181).
