# Parallel Waves

<!-- beadloom:watches=cli,graph,flow.yml -->

What a wave of concurrent agents guarantees, what it only reports, and what nothing here can
check.

This guide is for whoever decides that two pieces of work may run at the same time — a
coordinator launching subagents, or a person opening a second terminal. It covers the sentence
`beadloom waves` is built to keep, the split inside that sentence, the two mechanisms whose
failure direction was chosen deliberately, and the limits that are stated rather than hidden.

---

## The sentence

> For any two beads placed in the same wave, no medium they share can carry one bead's
> in-progress state into the other's result — and where a medium cannot give that guarantee,
> the wave says so and names the one bead that measures the combined outcome.

Everything below is either a way of keeping that sentence or a statement of where it stops.
The sentence is also in `src/beadloom/application/waves/__init__.py` and in the
[Wave Plan SPEC](../domains/application/features/wave-plan/SPEC.md), because half of it is not
decidable from the graph and a reader meeting only the code would not know which half.

## Which half is which

**Code independence is decided from the graph.** A tracker knows which beads block which. Only
the architecture graph knows which code they occupy, so `beadloom waves` resolves each bead's
declared `refs:` to nodes and files and serialises a pair for one named reason:
`blocked_by_bead`, `unresolved_scope`, `shared_node`, `shared_file`, `dependency_edge` or
`override_serial`. This half is a decision, not advice. An advisory shape is prose that a model
may act on or ignore, which is the failure the enforced-flow work exists to remove.

**The four shared media are measured as a precondition, before the wave runs.** One working
tree, one pre-commit hook, one doc-freshness baseline and one tracker id space are shared no
matter which shape is chosen. Each carries a verdict that can come back `failed`, and a medium
nobody observed comes back `unmeasured`, which is a finding rather than a silent pass. What the
run establishes is that the wave may start, not that it went well.

**The wave's conduct afterwards is checked by nothing here, and cannot be.** No command holding
a plan can know whether the gate owner ran the combined tree, whether an agent committed
outside its own scope, or whether the doc pass that followed read what it re-attested. That is
why every wave of more than one bead names a `gate_owner`: the step that no check can perform
belongs to a named bead instead of to a coordinator's habit.

```bash
beadloom waves BEAD [BEAD ...] [--json] [--project DIR]
```

Exit `0` = a shape was decided and rests on nothing unstated. Exit `1` = a shape was decided and
carries findings, which are visible and never blocking. Exit `2` = no shape could be decided.
Read the exit code or `--json`, never the number of lines printed (BDL-UX #148).

A real run on this epic's own S6 beads, all three of which turned out to be dependent:

```
$ beadloom waves beadloom-mr2l.21 beadloom-mr2l.78 beadloom-mr2l.79
3 wave(s) for 3 bead(s), 3 serialisation(s), 0 finding(s).

Wave 1: beadloom-mr2l.21
Wave 2: beadloom-mr2l.78
Wave 3: beadloom-mr2l.79

Serialised because:
  beadloom-mr2l.21 | beadloom-mr2l.78 — shared_node: sync-check
  beadloom-mr2l.21 | beadloom-mr2l.79 — shared_node: cli-commands
  beadloom-mr2l.78 | beadloom-mr2l.79 — dependency_edge: cli-commands -> doc-quality

0 declared override(s).

No wave runs more than one bead, so nothing is shared concurrently.

Plan-time precondition of each shared medium:
  working-tree: not_applicable — no wave runs more than one bead, so nothing is carried between beads through this medium
  commit-gate: not_applicable — no wave runs more than one bead, so nothing is carried between beads through this medium
  doc-baseline: not_applicable — no wave runs more than one bead, so nothing is carried between beads through this medium
  tracker-ids: passed — every bead's title agrees with the number the tracker allocated
```

The third serialisation is the one no tracker could have produced. `beadloom-mr2l.79` edited the
CLI, which depends on the doc-sync domain that `beadloom-mr2l.78` rewrote, and no bead blocked
the other.

---

## The direction a mechanism fails in

Two mechanisms in this slice were wrong in the same way: each had a failure mode, and the
failure mode pointed at the outcome that costs more. Both were repaired by choosing the
direction rather than by patching the individual cases.

### The declaration parser fails toward serialisation

A bead says what it occupies in the tracker, in its own words:

```bash
bd update <bead-id> --append-notes "refs: wave-plan, sync-check"
```

The declaration **opens a line**, and its list runs to the end of that line, separated by commas
or semicolons. Four things count as a declaration that cannot be read, each printed with its own
remedy, and **every one of them serialises the bead against every other bead**:

| Reason | What it means |
|---|---|
| `no_declared_refs` | the bead declared nothing |
| `ref_not_in_graph` | a name the graph does not have |
| `declaration_not_at_a_line_start` | a `refs:` written inside a sentence, which is prose |
| `declaration_dropped_a_node` | a second ref written without a separator that the graph confirms is a node |

An unknown scope is not an empty scope. An empty scope compares independent of everything, so a
parser that read silence as independence would rest the command's whole claim on it.

The two later reasons were bought with measured defects, both of which widened a wave. The
sentence *"It is serialised until it declares `refs: <ref_id>`, billing being the example."*
resolved to `refs=('billing',)` with nothing unresolved, so a bead acquired a genuine scope it
never declared and every pairwise verdict then rested on it. And `refs: wave-plan; sync-check`
beside `refs: sync-check` produced one wave, zero findings and exit 0, because the list stopped
at the semicolon: two beads that both declared `sync-check` were placed side by side and nothing
said so.

A wave shape is acted on. A parser whose errors widen a wave is therefore worse than no parser
at all, which is why the repair was the direction and not the three parses.

### The release gate fails toward withholding

`beadloom review-brief --release` prints the author's account only once a verdict is recorded on
the bead. Two defeats were measured, and both are now closed by requiring more of the verdict:

- The marker must carry its **colon**. `REVIEW ISSUES are still open, will fix` released the
  account, and the docstring of the function that matched it named that exact string as the case
  it prevented.
- The marker must open the comment's **first non-blank line**. A checkpoint reading
  `COMPLETED: shipped it` with a verdict line beneath it opened the gate from the middle of the
  author's own progress note.

The author of the verdict comment is now compared with the bead's assignee. The answer is
**reported, not enforced**: a self-recorded verdict still releases the account, the run prints
why its independence cannot be established *before* the account rather than after it, and it
exits `1`.

**Refusing was rejected, and the reason is a measurement about this repository.** Every comment
on every bead here carries the one tracker identity `v.zoologov`, which is also every bead's
assignee — the dev agent, the review agent and the human all write under it. A gate that refused
a self-recorded verdict would refuse every release in this repository, including the one that
corrected a Major on this slice. A gate nobody can pass is bypassed rather than obeyed, and the
bypass is one shell command away, because `bd comments` was never something this tool could
prevent. A rule that gets worked around is worse than one that reports. On a tracker where the
roles hold separate accounts the same code reports an independent verdict with nothing to say.

---

## What a wave shares no matter what shape it takes

Printed by every plan whose widest wave holds more than one bead, each with the evidence it came
from, and each with a plan-time precondition that is actually checked:

| Medium | Precondition checked | Observed from | Evidence |
|---|---|---|---|
| `working-tree` | no path differs from `HEAD` that no bead in the plan owns | `git status` | BDL-UX #181 |
| `commit-gate` | the installed pre-commit hook judges the paths a commit stages | `.git/hooks/pre-commit` | BDL-UX #118 |
| `doc-baseline` | no doc pair is stale before the wave starts | the doc index | BDL-UX #182, #133 |
| `tracker-ids` | every bead's title numbers it the way the tracker did | the bead records | BDL-UX #171 |

`failed` and `unmeasured` are findings and reach exit 1. `passed` and `not_applicable` are not.
The three machine-observed media read `not_applicable` when no wave holds more than one bead,
because a wave of one shares nothing concurrently — its clean room *is* the tree.

`tracker-ids` is checked even for a fully serial plan. The mis-numbering it looks for happens at
bead creation, upstream of any wave, so a plan that serialises the beads it mis-wired is exactly
the plan whose ids most need checking. Dogfooding found a live one on this repository:
`beadloom-mr2l.72` carried the title `BDL-061.17b`.

**Two obligations the shape hands to a named bead rather than to habit.**

- The wave's `gate_owner` runs the combined-tree Gate once the wave has landed. Every agent
  verifying in its own clean room is correct and blind by construction to any interaction
  between beads: four agents once each reported green on a tree that was red, and none of them
  was wrong.
- An agent reports its result in the words that say which measurement it made. "Green in a clean
  room over 16 files" is a different claim from "green on the tree", and "green on `tests-locale`"
  is a third; reporting them with one word is what makes a discrepancy read as a contradiction
  later. [`beadloom rooms`](../services/cli.md#beadloom-rooms) prints the room a run is in and
  the declared rooms it did not enter, and `beadloom ci` prints the same census beside its own
  verdict — so the address is derived from the project's CI declaration rather than typed by
  the agent. Naming the room does not make the verdict stronger. It makes it answerable.

## Overriding the shape

A human outranks the computation by declaring it, with a reason and an exit condition, the way
every other stand-down in this tool is recorded:

```yaml
waves:
  overrides:
  - beads: [proj-1, proj-2]
    decision: parallel        # or: serial
    reason: "the two touch one vocabulary module and nothing else"
    until: "2026-09-01"
```

Every key is required, and required by its **content** — a key present but blank is a
configuration error, because an override with no reason and no deadline outranks the graph
permanently by accident. Each override is reported with the number of decisions it changed, and
one that changed none is a finding: an override nobody can see doing anything is how a check
gets switched off without anybody saying so.

The tracker still outranks the override. A `parallel` entry cannot place a bead ahead of a bead
that blocks it.

---

## Handing a reviewer the change: `beadloom review-brief`

A review that reads what the author said it did is not an independent check. The measurement
behind that: in hidden-profile tasks, where the facts needed for the right answer are split
across a group, groups scored **17–36% accuracy against ~100%** for a single agent holding all
the facts, because hearing one member's conclusion first silences the dissenting evidence
(BDL-UX #155 C).

```bash
beadloom review-brief BEAD [--since REF] [--release] [--json] [--project DIR]
```

The brief hands the reviewer the **assignment** (the bead's title and description), the
**declared scope**, the **specification** (the graph's documents for those nodes and every
scenario whose `@bead:` tag names the bead) and the **change** (three git questions, each path
carrying the node that owns it). It does not hand over the bead's comments. Those are counted,
never printed: `N author comment(s) withheld`, with the reason, the release condition and a
notice about the defeats the command cannot see.

**Its boundary is as sharp as its purpose, and both belong in the same paragraph.**

**Enforced**, in code, with a test that bites: the command will not print the comments before a
verdict comment exists. It exits `3` — distinct from `2`, so a caller cannot confuse *refused*
with *failed* — and says the account stays withheld.

**Documented, not enforced**, for three defeats it cannot observe:

1. **A reviewer with a shell can run `bd comments` directly.** Nothing here can prevent that, and
   a mechanism that claimed to would be the overstatement this feature exists to remove.
2. **A coordinator can paste the author's summary into the launch prompt.** `coordinator.md` now
   forbids it: the review launch prompt carries the bead id and nothing else about the change.
   That is a rule, not a lock, and the duty to report a defeat is placed where the only
   observation is — the brief tells the reviewer to say in its verdict if the prompt carried
   anything it did not derive itself, including the coordinator's own observation of the change
   rather than only a pasted summary.
3. **The commit bodies on the reviewed range carry the account as well.** `review-brief`
   withholds bead comments and does not touch `git log`, while step 3 of the review protocol
   sends the reviewer to `git diff <base>...HEAD`. Measured on BDL-067: the `.21` and `.22`
   commit messages were longer and more specific than any bead comment, one of them opening
   with an explicit *FINDING for `.23`*, while the brief reported 0 comments withheld. It is
   not reachable by prompt discipline, because the protocol itself sends the reviewer to the
   diff and this project deliberately writes long commit bodies — the better the message, the
   more completely the mechanism is defeated. Filed as BDL-UX #219 and undecided: either the
   brief withholds or summarises the commit bodies on the range and says how many, or it stops
   claiming to withhold and instead reports what is reachable so the reviewer can declare it.
   Both reviewers who met it declared it unprompted, which is the only reason it is known.

What changed is the **default**. The cheap path is now the independent one, and the withholding
is counted and visible.

The account is **released, not destroyed**. After the verdict is recorded, `--release` prints
the comments, so the deferrals, sabotage tables and measured numbers stay available to a
reviewer who would otherwise re-derive them or file a finding against something deferred on
purpose. A bead that already carries a verdict releases at once, because a second pass reviews
the author's response to a judgement already independently recorded. The hidden-profile risk is
in the first pass.

### The first use, recorded as evidence rather than as anecdote

This epic's S6 review (`beadloom-mr2l.23`) was the first review run under the brief. It covered
five beads, reported withheld counts of **5/4/4/4/3**, and every finding was formed before
`--release` was run.

Its sharpest finding was about a sentence rather than about code. `beadloom-mr2l.79`'s own
honesty note listed a protection under **ENFORCED** — "the marker is matched at a LINE START, so
a checkpoint that MENTIONS a review does not open the gate" — in the paragraph written
specifically to avoid overstating what the code did. The code did not provide it, measured:
`REVIEW ISSUES are still open, will fix` released the account. The reviewer said it would have
accepted that sentence as the specification had it read it first, and probed the function only
because the note was withheld.

A sincere, careful, wrong sentence is the most expensive kind of documentation defect, because
it is the kind a reader has no reason to check. That is what the withholding caught on its first
outing, and it is the argument for the mechanism that no feature list makes.

The release also corrected a finding in the other direction. A Major filed against a missing CLI
reference section was withdrawn once the account showed the omission was a deliberate, stated
hand-off to the documentation wave. The ordering cost nothing, because the first judgement was
already recorded and could not be un-said.

---

## The doc baseline: a pair nobody can revise

A wave shares one doc-freshness index, and until this slice it shared a defect that made
integrating a wave expensive. The freshness fact was stored per pair and computed per **node**,
so one changed file marked every pair its node owned `stale/symbols_changed`, and the only way
to clear the followers was the blanket re-attestation that BDL-UX #163 was filed to prevent.

`sync_state` now also carries `file_symbols_hash`, the symbol surface of a pair's **own** code
file. Only that fact can make a pair `stale`. A pair whose own file did not move while a sibling
file of the same node did is reported:

```
[not verified] <doc> ↔ <code> (not checked: this file's symbols did not move;
architecture_view.py did — revise the document against that file, not against this pair)
```

Three decisions are worth reading off that line.

- **The verdict is `unverified`, and the reason token is `sibling_symbols_changed`.** No fifth
  status was invented. The epic had already answered this question four times, and `unverified`
  already means "reported by name, never counted as fresh, never blocking", which is exactly the
  treatment a pair nobody can revise needs. The verdict sum
  `ok + stale + missing + unverified + exempt + incomplete = total` is untouched.
- **The moved file is named.** The remedy is to revise the document against *that* file, and a
  line that reported the condition without naming the file would leave the reader to find it.
- **`sync-update` is not offered.** There is nothing for this pair's author to revise, and
  offering re-attestation would be offering the bulk re-baseline the change exists to remove.

Measured in two clean rooms differing only in this change, each run against its own code:
appending one function to `application/architecture_view.py` produced **69 stale pairs, 67 of
them naming a file nobody touched**, and afterwards **2 stale plus 67
`unverified`/`sibling_symbols_changed`**, every one carrying `details: architecture_view.py`.
Both rooms exit 2. The gate still bites, on the two pairs somebody can act on.

**This closed BDL-UX #182, #133 and #105 — three filings of one root over eleven weeks**
(2026-06-01, 2026-06-15 and 2026-08-23), each from a fresh measurement, none of them finding the
earlier one. That is the clearest evidence this epic produced that a written issue log earns its
keep, and also the clearest statement of how it fails: the entries are searched by **symptom**,
and the three symptoms — `symbols_changed`, `worktree`, `re-baseline` — share no word.

When a sibling wave has moved a file, read the reason before revising or attesting. A follower
pair is `unverified`, not `stale`, and re-attesting it would record a claim about a comparison
nobody made.

---

## Stated limits

Each of these is a limit somebody measured and chose to state, rather than a gap nobody noticed.

**The `git add` half of BDL-UX #118 is not fixable at the hook layer.** The pre-commit hook now
judges the commit rather than the tree — ruff and mypy run over the staged files, `sync-check`
runs with `--staged`, and the hook prints how many modified files outside the commit it did not
judge. What it cannot catch is a neighbour's hunk swept in through `git add`: that hunk is
*inside* the commit, which is the region the gate judges, and the index does not record who wrote
a line.

**Part of that gap now has an instrument, and it reports rather than prevents.** BDL-068 S1.6
shipped `beadloom scope-check`, which compares the paths a commit stages against the `## Axes`
section the work item declared. It is not the mechanism `beadloom-mr2l.81` filed and the
difference is deliberate: the unit is the WORK ITEM's axes, not the committing bead's scope. A
bead may narrow freely inside an approved scope, so judging against the bead would fire on
every legitimate cross-bead commit, while a path that leaves the *work item's* axes means the
approval no longer covers the change. Nothing about it stops a determined agent — a shell can
commit anything the file system allows. What it raises is detectability, at the moment the
commit is made rather than at review.

Where it runs, and what it does there:

| Where | Scope | On a finding |
|---|---|---|
| the pre-commit hook | the staged paths | warns, in both hook modes, and never blocks |
| `beadloom ci` (`scope-check` step) | `<trunk>...HEAD`, what the pull request contains | reports; the step passes |

Both are `warn` for one measured reason: one work item in 64 on this repository carries an
`## Axes` section today, so a check that blocked would meet a repository that cannot satisfy
it and be answered with `--no-verify`. A run that found no branch, no work item, no index or
no section is reported as SKIPPED with its reason, never as a pass — and neither surface
catches a neighbour's hunk that lands inside the same approved axes, which is the half of
BDL-UX #118 that stays open.

`beadloom ci`'s step is branch-scoped rather than tree-scoped for the reason the whole guide
turns on: the tree is shared, so judging it would fail one agent's push on a neighbour's edit.
See [`beadloom scope-check`](../services/cli.md#beadloom-scope-check) for the flags and
[Scope Check SPEC](../domains/doc-sync/features/scope-check/SPEC.md) for the rule.

Adopters must re-run `beadloom install-hooks` to pick the commit-scoped hook up, and again to
pick up the `scope-check` warning. An installed hook keeps its old behaviour until they do, and
`beadloom waves` now says so by name (`commit-gate: failed`) instead of leaving it to be
noticed.

**A "field read and never compared" lint is not feasible, and the reason is that the three
occurrences are alike only in prose.** The shape appeared three times in this epic: a validator
computed an answer the linter discarded, `waves` held both the allocated id and the title id
without comparing them, and the release gate held the verdict comment's author without comparing
it. Mechanically they are three different things — a discarded return value, two live values in
one scope that are never compared, and a dataclass field populated at one seam and read at none.
The middle one is not a static property at all, because "never compared" is only a defect
relative to an intent no analyser holds. The third is decidable per field inside a closed
package and would fire on every legitimately carried-through field. What generalises is not a
lint: a field that a mechanism's own purpose depends on should be named in that mechanism's
tests, and the durable form of that is a findings ledger with a meta-test asserting every closed
finding is still owned by a passing test.

**`waves` judges only direct `depends_on` edges between the declared scopes.** Transitive reach
through an unchanged intermediate node is not judged. On a real graph everything reaches
infrastructure eventually, and the honest answer would degrade to "serialise everything".

**The `working-tree` check will report `failed` on this repository for tracker and session
files** — `.beads/*.jsonl` and `ACTIVE.md` are owned by no node's code. It errs toward safety,
which is right, and a check that is always red is a check people learn to scroll past. Naming
those paths as a stated exclusion is unfiled work.

**Attestation is still per ref while the freshness fact is now per file.** `sync-update <ref>`
re-baselines every pair of that node, so a document pass that revised one pair still attests its
siblings. That is the residue of BDL-UX #133 rather than its return, it is correctly diagnosed,
and a per-pair attestation has no CLI today.

## See also

- [Wave Plan SPEC](../domains/application/features/wave-plan/SPEC.md) — the decision, its
  invariants and its API.
- [Review Brief SPEC](../domains/application/features/review-brief/SPEC.md) — what the brief
  carries, how a verdict is recognised, and the honest limits in full.
- [Agentic Dev Flow](agentic-flow.md) — the packaged roles, the guards and the Gate the wave
  runs inside.
- [CLI Reference](../services/cli.md) — `beadloom waves` and `beadloom review-brief`.
