# Review Brief

Hand a reviewer the change and the specification, and not the author's account of
either.

**Source:** `src/beadloom/application/review_brief/`

---

## Specification

### Purpose

A review that reads what the author said it did is not an independent check. In
hidden-profile tasks — where the facts needed for the right answer are split
across a group — groups scored **17-36% accuracy against ~100%** for a single
agent holding all the facts, because consensus silences dissenting evidence
(BDL-UX #155 C). The scaffolded review role told the reviewer, in its first step,
to read the bead comments before looking at anything, so the reviewer met the
author's framing before the code.

The BDL-061 epic supplied six of its own instances. Each was an honesty note that
understated what the code did, and each was caught by a reader who opened the
code instead of the note: a defect closed "for one spelling only", structural
pins that were spelling-deep, a `config-check` verifying nothing about a file's
body, an anti-vacuity guard blind to a per-kind hole, a population's third exit
found by planting a directory, and one clause of a stated guarantee that was a
constant tuple. In several the comment was accurate about what its bead set out
to do and simply silent about what it had missed, which is why reading it first
is a handicap rather than a help.

`beadloom review-brief <bead>` assembles what a reviewer sees.

### The split: before and after, not summary against measurement

A bead's **description is the assignment** and is handed over. A bead's
**comments are the author's report** and are withheld until a verdict is
recorded.

The obvious alternative — hand over the measurements and withhold the claims —
was rejected because it cannot be built. The six understated notes were each
accurate about their stated aim while silent about the gap, so a measurement and
a claim arrive in the same sentence; separating them needs a judgement no
mechanism can make and an author could phrase around. Description-against-comment
is structural, and the same string is read the same way by everyone.

The account is **released, not destroyed**. The author's comments are where
deliberate deferrals, sabotage tables and measured numbers live, and a reviewer
denied them re-derives work and files findings against things the author deferred
on purpose with a stated reason. A rule that makes review slower without making
it more independent is not an improvement. Once the reviewer's own judgement is
on the record it cannot be un-said, so reading the account afterwards can only
add a finding or explain a deferral.

A bead that already carries a verdict releases at once, deliberately. A second
pass reviews the author's response to a judgement the reviewer already formed
independently and recorded; the hidden-profile risk is in the first pass.

### What the brief carries

| Part | Source | Why it is not the author's account |
|---|---|---|
| Assignment | the bead's title and description | what the bead was asked to do, written before the work |
| Declared scope | the `refs:` token, read from anywhere in the bead | a machine token, not prose |
| Specification | the graph's documents for those nodes | authored against the design, held to the code by `sync-check` |
| Scenarios | the acceptance suite's `@bead:` tags | executable; it either runs or it does not |
| Change | `git diff <base>...HEAD`, the working tree, and the untracked files | measured from the repository |
| Withheld | a count, a reason, a release condition | the account itself is not printed |

The `refs:` token is read from the title, the description, the design field and
the `notes` field, because this epic's own beads declare their scope in `notes`
as often as in the description. The **assignment** is composed from the title and
the description alone, because `notes` is also where a dev appends progress. One
string is scanned for a token; the other is handed to a reader.

The scope is resolved by `waves.scope.resolve_scope`, the one parser of that
grammar. A second reader of the same declaration is the two-sources-of-truth
defect this epic met three times (BDL-UX #171, #177, #179).

### Absence is never silence

A withheld input is reported with its count: `N author comment(s) withheld`. A
reviewer that sees `0 withheld` learns the author wrote nothing; a reviewer that
sees `6 withheld` learns there is an account and that it is deliberately later.
The same rule makes a suppressed lint crossing and an excused document printable
rather than implicit.

A change nobody could measure — no repository, no git, a base ref that does not
resolve — comes back as `change_measured: false` with a finding, never as an
empty change set. "Nothing changed" and "nobody looked" reaching a reviewer as
the same brief is the silent false-green the command exists to remove.

A changed file owned by a node the bead never declared is named as outside the
declared scope. A changed file no node owns — a test, a document, a workflow — is
reported as unowned and is **not** a finding: conflating the two would file a
finding against every changed test file and drown the one that matters.

Ownership is answered from the nodes' declared sources, not from the file index,
because a file added by the change under review is not in the index yet.

The change is three git questions, not one. `git diff` never lists an untracked
path, so a brief built from diffs alone showed a reviewer every file the change
touched and none of the files it added — the half of a change most worth reading.
Ignored files stay out: git does not track them, so git has no opinion about
them, and inventing one would put an index and a build directory in front of a
reviewer as work.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | the brief rests on nothing unstated, or `--release` released the account |
| `1` | the brief carries findings: undeclared scope, unknown ref, unmeasured change, a change outside the scope, no bound scenario. Visible, never blocking |
| `2` | no brief could be assembled: no index, no answer from the tracker, no such bead |
| `3` | `--release` was refused because no verdict is recorded |

`3` is distinct from `2` on purpose. Nothing failed — the account is simply still
withheld, and a caller that could not tell those apart would retry the wrong one.

### How a verdict is recognised

A comment whose line starts with `REVIEW PASSED`, `REVIEW ISSUES` or `REVIEW
FINDINGS`. These are the exact openings the review role is instructed to write,
so recognising them here and emitting them there are one convention rather than
two. The match is anchored to a line start, so a checkpoint that *mentions* a
review does not read as one being recorded. A verdict written in other words is
not recognised and the release says so by name, because a marker list that
quietly accepted anything would make the gate unfalsifiable.

### Honest limits

**This withholds an input; it does not lock a door.** A reviewer with a shell can
run `bd comments` directly, and a coordinator can paste the author's summary into
the launch prompt — which is what happened throughout this epic's own S5 wave,
deliberately, to save cycles. What the command changes is the **default**: the
cheap path is the independent one, the withholding is counted and visible, and
the brief carries a notice telling the reviewer to report the paste in its
verdict, because the reviewer is the only party that can observe it.

**A `git` that answers slowly enough to hit the 30-second timeout is reported as
unmeasured**, the same as an absent one. That is deliberate — the brief says
nobody looked rather than guessing — and it means a very large repository can
report unmeasured for a reason that is not a defect.

**The scenarios are matched by tag, not verified to assert anything.** A scenario
that binds to the bead and asserts nothing appears in the brief as specification.
Judging that is the reviewer's work, and `scenario-coverage` reports the binding,
not the content.

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | the vocabulary: `ReviewBrief`, `AuthorNote`, `WithheldNotes`, `ChangedFile`, `SpecDocument`, `BoundScenario`, `ReleaseOutcome`, and the finding names |
| `assembly.py` | build the brief from the graph, the change inventory and the scenario suite |
| `release.py` | recognise a recorded verdict and decide whether the account may be read |

`models.py` holds no logic and `assembly.py` holds no policy about the release,
because the two decisions fail independently: a brief can be assembled correctly
and released too early, or withheld correctly and assembled from the wrong scope.

## Public API

```python
from beadloom.application.review_brief import (
    assemble_brief,   # -> ReviewBrief: the change, the specification, a count
    release_notes,    # -> ReleaseOutcome: the account, or the reason it is withheld
    verdict_recorded, # -> str | None: the marker of the first recorded verdict
)
```

`assemble_brief` takes the author's notes, the change inventory and the scenario
suite as **data**, so the decision runs without `bd`, without git and without a
repository, and so the application layer never reaches up into `services`.

## Related

- `wave-plan` — the same slice's other decision: which beads may run at once.
- `cli-commands` — `beadloom review-brief`, the presentation and the seams.
