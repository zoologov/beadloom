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
| Withheld | a count, a reason, a release condition, a defeat notice | the account itself is not printed |
| Reachability | four channels, each inspected or named as uninspectable | what the reviewer can reach, which is a different question from what this command holds |

The `refs:` token is read from the title, the description, the design field and
the `notes` field, because this epic's own beads declare their scope in `notes`
as often as in the description. The **assignment** is composed from the title and
the description alone, because `notes` is also where a dev appends progress. One
string is scanned for a token; the other is handed to a reader.

The scope is resolved by `waves.scope.resolve_scope`, the one parser of that
grammar. A second reader of the same declaration is the two-sources-of-truth
defect this epic met three times (BDL-UX #171, #177, #179).

### Absence is never silence

A withheld input is reported with its count, and the count names the bead it was
taken over. `6 withheld` says there is an account on THIS bead and that it is
deliberately later; `0 withheld` says this bead carries none, and says nothing
about the beads that made the change. It used to say that a reviewer seeing `0
withheld` learns the author wrote nothing, which was measured false by 31,544
characters on this feature's own S2 review — the brief was for a review bead, and
the account sat on the two beads that made the change (BDL-068 S2 review, Major
1(a)). The same rule makes a suppressed lint crossing and an excused document
printable rather than implicit.

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

### What is reachable, per channel

`0 withheld` is true of bead comments and is read as a statement about the
reviewer's knowledge. It is not one. Three defeats of the withholding were
measured, and every one of them was known only because a reviewer declared it
unprompted:

| Finding | The channel that defeated it |
|---|---|
| BDL-UX #212 | `ACTIVE.md`, which the launch prompt named because the playbook says a role subagent gets `CONTEXT.md` and `ACTIVE.md` |
| BDL-UX #219 | the commit bodies of the reviewed range, which the review protocol itself sends the reviewer to |
| BDL-UX #204 | the launch prompt, which this command cannot see at all |

So the report states what is REACHABLE rather than what was withheld, over four
channels:

| Channel | Inspected from | When it cannot be inspected |
|---|---|---|
| bead comments | the tracker's answer for THIS bead, named in the statement — the beads that made the change are neither read nor counted (widening it is BDL-UX #229) | never; a tracker that will not answer is exit `2` |
| the work item's documents | the folder the branch's work item names | no project root, no branch, a branch naming no work item in the planning corpus, or a `flow.yml` that will not parse |
| the commit bodies of the reviewed range | `git log <base>..HEAD` | git gave no answer |
| the launch prompt | nothing | always — nothing in this process can observe one |

**A channel is DERIVED, never listed.** The document names come from the composed
prompts themselves: every role in `ROLE_NAMES` (itself derived from the shipped
CORE fragments) and every command fragment the package ships, composed for this
project's `flow.yml` and **including its project layer**, then matched by shape —
an upper-case name ending in `.md`. A team that names `DECISIONS.md` in
`.beadloom/flow/roles/review.md` moves this report by that act and by no other. A
hand-written list would satisfy every report test and go stale the first time a
role file gained a document.

The folder those documents live in comes from `work_item_of_branch`, whose
population is the project's own planning corpus rather than this repository's
convention, and the commit range comes from the review's own base ref.

**A channel that was inspected and found empty never reads like one nobody could
inspect.** `NOT INSPECTED — <reason>` and `0 item(s)` are different sentences, the
same rule `beadloom impact` follows for a `Population` it could not resolve.

**The report raises detectability and closes nothing.** The review protocol sends
the reviewer to the diff and the commit bodies come with it — the better the
commit message, the more completely the withholding is defeated. What the report
buys is that a reviewer knows what to declare.

**A commit body is counted, never quoted.** The channel carries each commit's
subject and the number of non-empty body lines, so a report about a leak is not
itself one.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | the brief rests on nothing unstated, or `--release` released the account |
| `1` | the brief carries findings: undeclared scope, an ambiguous one, unknown ref, unmeasured change, a change outside the scope, no bound scenario. Under `--release`: the account was released on a verdict whose independence the tracker could not confirm |
| `2` | no brief could be assembled: no index, no answer from the tracker, no such bead |
| `3` | `--release` was refused because no verdict is recorded |

`3` is distinct from `2` on purpose. Nothing failed — the account is simply still
withheld, and a caller that could not tell those apart would retry the wrong one.

### How a verdict is recognised

A comment whose **first non-blank line opens with** `REVIEW PASSED:`, `REVIEW
ISSUES:` or `REVIEW FINDINGS:` — **the colon included**. These are the exact
openings the review role is instructed to write, so recognising them here and
emitting them there are one convention rather than two. A verdict written in
other words is not recognised and the release says so by name, because a marker
list that quietly accepted anything would make the gate unfalsifiable.

Both conditions were bought with a defect. The match used to be anchored to a
line start and nothing more, and the docstring that described it named the case
it did not catch: `REVIEW ISSUES are still open, will fix` released the account,
measured. Requiring the colon closes that. Requiring the marker to open the
comment closes the second: a checkpoint reading `COMPLETED: shipped it` with a
verdict line beneath it opened the gate from the middle of the author's own
progress note.

### Who recorded the verdict

The author of the verdict comment is compared with the tracker's assignee for the
bead — the party whose account is being withheld. The answer is **reported, not
enforced**: a verdict recorded under the bead author's own identity still
releases, and the release prints the reason it cannot be called independent,
before the account, and exits `1`.

Refusing was rejected on a measurement. In this repository every comment on every
bead carries the one tracker identity `v.zoologov`, which is also every bead's
assignee: the dev agent, the review agent and the human all write under it. A
gate that refused a self-recorded verdict would refuse every release here, and a
gate nobody can pass is bypassed rather than obeyed — the reviewer would run `bd
comments` directly, which this command has never been able to prevent. So the
comparison is made and its answer costs the run its exit code, on the same rule
that makes an unmeasured medium a finding rather than a silent pass. On a tracker
where the roles hold separate accounts the same code reports an independent
verdict with nothing to say.

### Honest limits

**The reachability report is a statement, not a check.** No channel makes a
finding and no exit code moved: the launch prompt can never be inspected, so
treating an uninspected channel as a finding would put every brief on exit `1`
and the code would stop meaning anything.

**The report cannot see whether a reachable channel was read.** It says
`ACTIVE.md` is in the folder and that the composed role prompts send a reviewer
there. Whether that reviewer opened it is observable only by the reviewer, which
is why the duty to declare stays where the observation is.

**A branch whose name is not exactly the work item's key inspects no documents.**
`work_item_of_branch` matches a `/`-separated segment against the planning
corpus, so `features/BDL-068` names the work item and `features/BDL-068-S2S3`
names none — measured on this feature's own development branch, where the
documents channel reads `NOT INSPECTED` for that reason. The channel states it
rather than reporting an empty folder, and the rule is not restated here: a
second reader of the branch-to-work-item convention is the two-sources-of-truth
defect this epic exists to remove, so the convention is fixed in one place or
not at all.

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
not the content. `N bound scenario(s)` is therefore a count the reviewer must
still open.

**The change is measured over the branch, not over the bead.**
`git diff <base>...HEAD` plus the working tree plus the untracked files is
everything the whole branch did, and no per-bead attribution exists in the
commits. On a branch carrying five beads all five briefs report the same files,
so the `changed-outside-scope` finding names its window
(`measured over the branch since <ref>`) instead of claiming an attribution it
cannot make.
`--since <the sibling's landing point>` narrows the window when a caller knows
one.

**The withholding models the author's comments and the coordinator's paste of
them; it does not model the coordinator's own observations.** A launch prompt
carrying a directed hint is not a pasted summary and nothing counts it, yet it
converges a reviewer the same way — two findings of this feature's own first
review came from one. The duty the brief places on the reviewer therefore covers
anything in the prompt the reviewer did not derive itself.

**"Description-against-comment is structural" holds for a bead written before the
work.** It does not hold for a fix bead, whose description *is* the previous
review handed over as the assignment. That is correct — it is the assignment —
and it also means a fix bead's reviewer is converged on the previous reviewer's
framing by design. The mechanism cannot separate those two and does not claim to.

**The findings go to stderr while the brief goes to stdout.** A reviewer piping
the brief to a file keeps the body and loses the findings. Every other command
here does the same, and on this one the findings are the part a reviewer is least
able to re-derive.

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | the vocabulary: `ReviewBrief`, `AuthorNote`, `WithheldNotes`, `ChangedFile`, `SpecDocument`, `BoundScenario`, `ReleaseOutcome`, `Channel`, `Reachability`, `Commit`, and the finding names |
| `assembly.py` | build the brief from the graph, the change inventory and the scenario suite |
| `release.py` | recognise a recorded verdict and decide whether the account may be read |
| `reachability.py` | derive what can reach the reviewer per channel, and name a channel it could not inspect |

`models.py` holds no logic and `assembly.py` holds no policy about the release,
because the two decisions fail independently: a brief can be assembled correctly
and released too early, or withheld correctly and assembled from the wrong scope.

## Public API

```python
from beadloom.application.review_brief import (
    assemble_brief,           # -> ReviewBrief: the change, the specification, the reachability
    release_notes,            # -> ReleaseOutcome: the account, or the reason it is withheld
    verdict_recorded,         # -> str | None: the marker of the first recorded verdict
    reachability_of,          # -> Reachability: the four channels; `bead_id` names the count's population
    prompts_naming_documents, # -> {document: (prompt, ...)}, or None when the project's flow.yml will not parse
)
```

`assemble_brief` takes the author's notes, the change inventory, the scenario
suite and the commit range as **data**, so the decision runs without `bd`,
without git and without a repository, and so the application layer never reaches
up into `services`. `commits` follows the change inventory's convention: `None`
is *git gave no answer* and an empty sequence is *the range holds no commits*.

`reachability.py` reaches sideways into `onboarding` to compose the prompts and
into `declared_scope` to find the work item, the same join
`work_item_routing.py` makes for `/task-init`: the composed prompts live in
`onboarding`, the planning corpus is read in `application`, and neither domain
may import the other.

## Related

- `wave-plan` — the same slice's other decision: which beads may run at once.
- `cli-commands` — `beadloom review-brief`, the presentation and the seams.
