# Wave Plan

Decide, from the architecture graph, which beads may run at the same time.

**Source:** `src/beadloom/application/waves/`

---

## Specification

### Purpose

Every scaffolded multi-agent flow asks a human to guess the wave shape, and the
guess is made without the one fact that decides it. A tracker knows which beads
block which; only the architecture graph knows which *code* they occupy. So the
shape is computed here, and it is a **decision** rather than advice: an advisory
wave shape is prose a model may act on or ignore, which is the failure the
enforced-flow work exists to remove.

The guarantee the shape makes, in one sentence:

> For any two beads placed in the same wave, no medium they share can carry one
> bead's in-progress state into the other's result — and where a medium cannot
> give that guarantee, the wave says so, names the one bead that measures the
> combined outcome, and checks the medium's plan-time precondition.

The sentence has two halves because measurement says one half is not enough. The
first half is code independence, which the graph decides. The second is the set
of media a wave shares whatever shape it takes — one graph, one working tree,
one pre-commit hook, one landing order, one focus document, one doc-freshness
baseline, one tracker id space — and no choice of shape makes any of them
independent.

**The split the sentence names.** The second half was a constant tuple until
BDL-061.80: the media were printed with the evidence they came from, and
nothing checked any of them, so a wave asserted a property nothing verified. Each
medium now carries a verdict that can come back `failed`, and a medium nobody
measured comes back `unmeasured` rather than passing in silence. What is checked
is a **precondition**, measured before the wave runs. What is not checked, and
cannot be by anything holding a plan, is the wave's conduct afterwards: no check
here knows whether the gate owner ran the combined tree.

### How a bead says what it occupies

A bead declares its node scope in its own words, in the tracker:

```
refs: wave-plan, sync-check
```

`ref:`, `refs:` and `area:` are all accepted and every occurrence is read. The
declaration **opens a line** — optionally behind list or quote markup — and its
list runs to the end of that line, separated by commas or semicolons.

The declaration is parsed in one place (`waves.scope.parse_declaration`) and
composed in one place (`waves.scope.compose_declaration`), and both are shared by
`beadloom waves`, `beadloom review-brief` and the MCP `bead_context` tool, so the
three cannot come to disagree about what a bead said. The composer is not
decoration: the four tracker fields are joined with newlines, and a caller that
joined them with a space put the next field's first word directly behind a
dangling `refs:` header.

The separator between the colon and the list is spaces and tabs, not any
whitespace. A dangling `refs:` with nothing after it used to skip forward to the
next non-empty line and read that line as the declaration, handing the bead a
scope it never named.

### The parser fails toward serialisation

Every way the declaration cannot be read with confidence leaves the bead
unresolved, which serialises it. That is the direction, and it is the point: the
wave shape is acted on, so a parser whose errors *widen* a wave is worse than no
parser at all.

| Reason | What the bead wrote | Remedy |
|---|---|---|
| `no_declared_refs` | nothing about its scope | declare `refs: <ref_id>` on a line of its own |
| `ref_not_in_graph` | a name the graph does not have | name a real node, or add it |
| `declaration_not_at_a_line_start` | `refs:` inside a sentence | both cases stated, because nothing here can tell them apart — see below |
| `declaration_dropped_a_node` | a second ref without a comma | separate the names with a comma |

**A remedy follows its cause down as far as the reason does.** The four are not a
table lookup: `remedy_for(reason, axes=...)` reads what else is known, because
one cause has two sub-cases and another has an answer only the work item's
document can give. `declaration_not_at_a_line_start` covers both a declaration
written carelessly mid-sentence and prose *about* declarations, and nothing here
can tell the two apart, so both are stated and the ambiguity is stated with them.
A bead that declares no scope on purpose and explains why in prose met the older
one-sentence remedy and was told to promote its explanation to a real
declaration — which would have manufactured exactly the authored scope the
comparison below exists to remove (BDL-UX #234). And `no_declared_refs` sends the
author to the `## Axes` section of the work item's document when there is one,
rather than asking for a line to be invented, because that is where a `refs:`
line is generated from.

The last two were silent narrowings before `beadloom-mr2l.83`. A `refs:` written
inside a sentence handed the bead the next word as a genuine, fully *resolved*
scope — a bead discussing this parser acquired one that way — and a second ref
written after a space or a semicolon was dropped, so `refs: wave-plan;
sync-check` beside `refs: sync-check` shared one wave at exit 0 with no findings.

Only the first word of a list item is read as a ref, because a declaration is
written inside prose and reading every following word as an id found nothing at
all. The words that rule throws away are checked against the graph: one the graph
confirms is a node is a ref the bead declared and this parser did not read, so it
is named and the bead serialises. One the graph does not have is prose and costs
nothing, which is what keeps the rule usable on beads that explain themselves.

A scope expands **downward through `part_of`**. A node's own file set excludes a
nested node's files, so without the expansion a bead scoped to a domain and a
bead scoped to one of its components would compare independent while editing the
same package.

### Why two beads are serialised

One reason is returned per pair — the pair is already serialised, and a second
reason would not change the shape. They are tried in this order:

| Reason | What it means |
|---|---|
| `blocked_by_bead` | the tracker says one blocks the other; ordering the tracker owns, restated here so the shape cannot contradict it in silence |
| `unresolved_scope` | one of the two did not say what it occupies, named a ref the graph does not have, or wrote a declaration this parser will not read |
| `shared_node` | the expanded scopes intersect |
| `shared_file` | distinct nodes, but the index says a source file belongs to both |
| `dependency_edge` | a `depends_on` edge runs between the scopes, in either direction |
| `override_serial` | a declared override put the pair apart on purpose |

`unresolved_scope` is the reason an advisory tool gets wrong. **An unknown scope
is not an empty scope**: an empty one compares independent of everything, so a
bead that says nothing would be placed in every wave and the command's whole
claim would rest on silence. It is serialised against every bead, and the
remedy is printed — one remedy per reason, because the four differ.

The finding says what *happened* rather than where the bead ended up: "its scope
was compared with no bead's". A `parallel` override may legitimately place an
unresolved bead beside another, and a finding claiming it was "serialised against
every bead" was then contradicted by the wave list printed beside it.

### The declaration, held against the derivation

The scope every verdict above rests on is a line the bead's **author** wrote,
while everything else this flow derives is computed and names the population it
could not resolve. So two beads that edit one document read as independent
whenever neither declaration happens to name the node that owns it. That is
measured, not hypothetical: two beads declaring `review-brief` and
`mutation-scope, ci-gate` both edited `docs/services/cli.md`, owned by a node
neither named, and the plan reported 1 wave, 2 beads, 0 serialisations, 0
findings (BDL-UX #232).

The fix is not to stop reading the declaration. The declaration still decides the
shape; what is added is the comparison the epic's own decision already states —
the axes are **derived**, the work item's document records the derivation and the
human's scope decision, a bead's `refs:` is **generated** from that document, and
a disagreement between the three is a finding.

The unit compared against is the **work item's** axes, never the bead's. A bead
may narrow freely inside them: one bead of this epic edited a node its own `refs:`
does not name and that was correct, because the node is a kept row of the work
item's table. A check reading that as a finding would be noise on its first day.

Each declared ref gets one of five verdicts, and only one of them is a finding:

| Verdict | What it means | Finding |
|---|---|---|
| `agrees` | a kept row names it | no |
| `ruled_out_of_scope` | a row names it and rules it **out** — the approval does not cover it | yes |
| `no_scope_decision` | a row names it and decides nothing; `axis-without-a-scope-decision` owns that fault | no |
| `swept_no_scope_decision` | the `Derived by` field ran over it and no row rules on it | no |
| `not_derived` | no row names it at all, and the derivation never reached it | no |

**Approval follows the scope decision and nothing else (BDL-UX #250).**
`WorkItemAxes.approved` was `kept | targets`, so every node owning a file a
`Derived by` field names was inside the approval whatever its own row said. The
rule held while a slice CHANGED what it derived from — true of BDL-068's S1
through S4 — and became false at S5, whose subject is where this project calls
`bd` and whose derivation targets therefore include files it only reads.
Measured on this repository: 39 approved nodes, of which six were approved by
having been swept — `cli`, `doc-spaces`, `flow-composer`, `guard-hooks`,
`intent-reader` and `typed-surface` — and two of the six carry rows that say
`no`. Provenance is not consent, and the approval list is what a wave plan names
back to an author as nodes to declare.

The fifth verdict exists because the four could not say what those six are.
Calling a swept node `not_derived` would state something false: the derivation
reached it, which is precisely why its absence from the table is worth saying.
The commit gate keeps the wider reading — `scope_check.DeclaredScope.inside` is
still `kept | targets` — and that is a difference between two questions rather
than two answers to one. The gate asks whether a staged PATH is covered, and it
measured the narrower rule going red on three of this branch's own code commits;
the plan asks what a human DECIDED, because it prints those names back as work.

`not_derived` is not an accusation, and keeping it apart from the other three is
the point. This project has measured its own derivation under-reporting: seeded
under `tests/`, `beadloom impact` attributed a node to none of the 148 caller
sites it found (BDL-UX #225). "The derivation did not reach here" and "the
declaration is wrong" are two answers, and printing them with one word would send
an author to correct a line that is already right. The section's own `Unresolved`
field is carried verbatim beside the verdicts taken under it.

An axis row that attributes **no node** is reported as `not_attributed`: no
declaration can name it and no comparison can reach it. It is the table's version
of a changed path no node owns — measured at 41 of 52 over one branch's commits —
and it is stated, never counted as agreement.

The finding that would have caught the collision is `unguarded_axis`: a node the
work item approves that **no bead of a wave declares**. Its remedy names a
PER-BEAD derivation, and the level confusion that is guarding against is
BDL-UX #245: a work item's axes are the UNION of its slices' and a bead's scope
is a SUBSET chosen for that bead, while `beadloom axes --refs` renders one line
for the whole work item — 24 nodes when the entry was filed, 52 on BDL-068
today. The remedy used to say "generate each bead's `refs:` from the `## Axes`
section", which performed exactly would give every bead an identical scope,
fire `shared_node` on every pair and collapse every wave to a wave of one. The
tests hold that consequence as an executable fact rather than as prose. It is reported per wave
and only for a wave holding two beads or more, because that is the extent of what
it may claim — the sentence is *the pairwise verdict for these beads did not
compare these nodes*, and a wave of one bead makes no pair. Reported per plan
instead, it would have printed one finding per undeclared axis for every bead of
an epic whose table keeps ten, every time; an always-red check is an ignored
check.

A caller that gathers no axes at all gets `declarations_not_compared`, under the
same rule and for the same reason `unmeasured` is a medium verdict rather than a
lenient pass — but again only where a wave actually holds a pair, so a plan run
off a work-item branch does not exit 1 on every run.

### The shape

Beads are laid out greedily in tracker order (Kahn over the blocker relation,
ready set taken sorted), each into the first wave holding no bead it conflicts
with, and never earlier than the wave after its blockers. Greedy colouring is
not optimal, and optimal is not what is wanted: the shape has to be the **same**
shape every time it is computed, so that two agents reading one plan act on one
decision.

Each wave names a `gate_owner`: the bead that runs the combined-tree gate for
that wave. It is assigned deterministically (the last bead of the wave in sorted
order) rather than wisely. The point is that the step belongs to a named bead
instead of to a coordinator's habit — four agents once each verified in a clean
room, each honestly reported green, and the combined tree was red, because
nothing ran the combined tree until the very end and that step was in nobody's
bead.

### What a wave shares regardless of the shape

Printed by every plan, whatever the width of its widest wave, each with the
evidence it comes from:

| Medium | Evidence |
|---|---|
| `graph-files` | one graph, in files no bead's code owns and every node-adding bead writes — and it is what this plan derives every serialisation from. A derivation cannot describe its own input by asking it (BDL-UX #261) |
| `working-tree` | an agent's clean-room green is a claim about N files, not about the tree, and the room is built at `room-<bead-id>` so it can say whose it is |
| `commit-gate` | one pre-commit hook; a commit is judged over the paths it stages, and states the rest |
| `landing-order` | one branch. What keeps two agents out of one FILE is the disjoint scopes the plan derived; what orders their COMMITS is the merge slot, and only in the form that grants it (BDL-UX #194, #237) |
| `focus-document` | one document per work item that every one of its beads writes and no bead's code owns. `/task-init` routes every type through it, so a wave shares it whatever the plan says — and the plan says nothing, because it resolves a bead to the nodes and files its CODE occupies (BDL-UX #257) |
| `doc-baseline` | one git-ignored index. The freshness fact is recorded per FILE (`beadloom-mr2l.78`), so a bead's change no longer marks the pairs its node's other files own — but an attestation still re-baselines every pair of the ref it names |
| `tracker-ids` | allocated at creation, while a title written beforehand carries the id the author predicted; a creation of more than one bead goes through one plan whose edges name plan-local keys, and a hand-wired `dep add` is where the echoed titles are the only check (BDL-UX #171, #165) |

**Why `focus-document` is a medium and not a serialisation (BDL-UX #257).** The
bead that filed it asked for a bead's document scope to be derived, and derived
from OWNERSHIP that is worth exactly zero: `docs.ref_id` is a single column and
`docs.path` is `UNIQUE`, so a document belongs to at most one node, and
`conflict_between` fires `shared_node` on any ref intersection before a document
could be compared. Two beads that reach a document comparison therefore hold
disjoint refs and disjoint owned documents, so a `shared_document` reason adds no
serialisation `shared_node` does not already produce — a check that cannot fail.
It could not reach the measured case in any event: BDL-068's `ACTIVE.md` is in
the docs table nowhere, and the first observed collision was over
`docs/domains/application/README.md`, owned by `application` — an ancestor of one
of the two scopes and of neither. `TestDocumentOwnershipCannotSerialiseAnything`
in `tests/test_the_document_every_bead_writes.py` holds that claim as an
executable, so a schema that later gives a document two owners is found by a red
test.

**The shared population is wider than the documents, and the derivation cannot
reach all of it.** Measured in the same slice by `beadloom-0mdo.59`: three beads
whose code scopes are disjoint shared four artifacts —
`.claude/development/docs/features/BDL-068/ACTIVE.md`,
`docs/services/components/cli-commands/DOC.md`,
`tests/test_bead77_kind_and_root_disagree.py` and `.beadloom/_graph/services.yml`
(one file per node since `beadloom-0mdo.80`).
Two of those are not documents: one is a test carrying hand-maintained population
literals that any bead adding a node has to bump, and the other is the graph this
plan derives its scopes FROM.

**Why `graph-files` is a medium and not a serialisation either (BDL-UX #261,
then #265).** BDL-UX #261 sketched one — a bead's scope reaching the graph FILE
its declared nodes are defined in — and it was measured before it was built
rather than after. One file held every one of this project's 100 nodes, so the
reason fired on every pair of every wave and collapsed each of them to a wave of
one, which is BDL-UX #245's failure mode, against a real write rate of 8 of the
55 commits this epic's branch carries. It would also miss the case it was drawn
from: both colliding beads were ADDING nodes, and a node being added is in no
graph the plan can read. The condition named for reopening it was a graph split
across files, pinned as a test that goes red when it holds.

**The condition was met, and the answer did not change — for the opposite
reason.** `beadloom-0mdo.80` split this repository's graph into one file per node
(BDL-UX #265). Under that layout the node-to-file map is INJECTIVE, so "two beads
whose declared nodes are defined in one graph file" holds exactly when the two
beads declare the same node — which `conflict_between` already reports as
`shared_node`. The reason was noise on a single-file graph and is redundant on a
split one, and there is no layout between the two where it is neither.
`TestTheSplitMakesTheSerialisationRedundantRatherThanMeaningful` in
`tests/test_the_graph_is_one_file_per_node.py` is that measurement, and it goes
red the day some file of this graph declares two nodes again.

**What the medium says now depends on the layout, because the answer does.**
While some file declares several nodes, the pass names it with the count it holds
— that is the file every node-adding bead writes. Once every node has a file of
its own, the pass says two node-adding beads write two files and the collision
cannot be attempted. The half no plan can reach is stated either way, because it
moved rather than disappearing: under a shared file the plan cannot see the NODE
a bead is about to add, and under one file per node it cannot see the FILE that
node will be created in. The medium remains, since the layout is a property of a
project and not of the command: `beadloom init` still writes one `services.yml`,
which is the easier thing for an adopter to review once, and what an adopter gets
here is the number rather than a verdict.

**The primitive is one writer per file, and `beadloom-0mdo.66` took it first.**
`O_CREAT|O_EXCL`, one claim file per issue number, so a shared write cannot be
attempted rather than being detected afterwards. Applied to the graph it is one
file per node — `each_graph_file` already globs `*.yml`, so no reader changed —
and the cost was measured rather than assumed before it was taken: `load_graph`
61.34 ms to 66.40 ms and `beadloom reindex --full` 1895 ms to 1950 ms over 100
nodes and 169 edges, with `lint`, `doctor` and `status` unmoved because they read
the index. Nothing that was one pass became N. `graph-layout`
(`onboarding/graph_layout.py`) states the layout and reports the surface where a
shared write is still possible.

**The two artifacts neither medium covers, and why each needs a different
answer.** `tests/test_bead77_kind_and_root_disagree.py` carries hand-maintained
population counts (`populations[SPACE_TO_BE] == 203`,
`populations[SPACE_AS_IS] == 116`, `len(working_documents(REPO_ROOT)) == 58`)
that any bead adding a node or a document has to bump — one derivable fact with
two homes, whose answer is to remove the copy, not to serialise around it. One
writer per file does not apply: the file has one writer per bead already.
`docs/services/components/cli-commands/DOC.md` is not the ancestor-document case
#261 guessed at, and the measurement says so: node `cli-commands` owns
`src/beadloom/services/commands/` — both `setup.py`, which `beadloom-0mdo.59`
changed, and `waves.py`, which `beadloom-0mdo.75` changed — and neither bead
declared it, so `conflict_between` had no ref to intersect and `shared_node`
would have fired if either had. The plan already reports that gap, as
`unguarded_axis` naming `cli-commands`. An ancestor-reaching rule would be noise
in any case: every one of this project's 100 nodes reaches the root service
`beadloom` through `part_of`, so it is shared by every pair of every wave.
`TestTheCliCommandsDocumentIsAnUndeclaredNode` and
`TestAnAncestorReachingRuleIsSharedByEveryPair` hold both measurements as
executables.

**Taking the landing lock does not prevent the collision, and that was measured
rather than reasoned about.** The fourth instance in the slice was an agent that
did everything the flow asks: it acquired the merge slot with `--holder`, waited,
and 43 lines of its `ACTIVE.md` entry still landed inside a neighbour's commit.
The lock orders the COMMITS; the edit had already happened. That is the same
sentence the `landing-order` medium states, met from the other side.

**Which document, and whose.** The kind is derived, never spelled:
`Routing.shared_kinds` is the intersection of the document kinds every route of
the composed `/task-init` writes, beside the two difference properties that
decide a work item's route. On this project it answers `ACTIVE`. The FOLDER is
the work item's own, taken from `work_item_axes(project_root).document`. Scoping
it to one work item is a measurement rather than a preference: reading every
focus document in this repository reported `passed` for all three beads of
BDL-068's S6 wave over 58 documents, none of which carries a row for any of them,
because a table abbreviates `beadloom-0mdo.75` to `.75` and BDL-061's table has a
`.75` row of its own.

The first version printed the list only for a wave of more than one bead, on the
reasoning that a wave of one shares nothing concurrently. BDL-UX #228 measured
what that cost: `wave_size` is the width of ONE plan, and a plan is one slice of
one epic, so it says nothing about solitude — the `working-tree` check exists
precisely to report paths owned by no bead in the plan, which is work from
outside it in the same tree. Roughly twenty single-bead waves ran across two
epics, and in every one of them the discipline travelled by the coordinator's
launch prompt because the instrument was silent there.

`room_for(bead_id)` names the clean room a bead owes — `room-<bead-id>`, printed
per bead by `beadloom waves` and under `rooms` in `--json`. Two agents once each
built a room at one shared session-scratchpad path, and one took a measurement
over its neighbour's untracked files that looked exactly like a correct clean
room (BDL-UX #235). The session scratchpad is a genuinely shared medium and is
deliberately **not** one of the seven: a medium here is one with a plan-time
precondition a command can observe, and a scratchpad path exists only inside a
running agent session. An entry for it would be permanently `unmeasured` — a
finding on every plan — or permanently true. What is observable is the remedy,
so the remedy is what ships, in `room_for`, in the `working-tree` statement and
in the role cores that carry the `clean-room` duty.

### Building the room, rather than describing it

`room_for` names the room; `build_room` creates it, and refuses a directory it
did not create empty. Naming was not enough, twice. Under the convention the
name replaced, two agents of one wave reached one directory (BDL-UX #235), and a
room entered a second time manufactured a failure of its own: files copied into
an already-indexed room postdate its doc-freshness baseline, measured as
`sync-check` exit 2 with `stale: 2` against a change that is clean at `HEAD`
(BDL-UX #243). A convention that is only correct when performed exactly once,
and does not say so, will be performed twice.

So the build has three properties, and each answers one of those:

- the path is DERIVED from the bead, so two beads cannot be handed one room;
- the directory is CREATED, never entered — an existing one is refused, and a
  refused build writes nothing into it;
- `rebuild=True` REPLACES the room rather than refreshing it, and deletes only a
  directory whose `.beadloom-room.json` names that same bead. A directory that
  merely carries the right name is refused, because removing a path chosen by a
  caller's typing is a worse failure than the one this exists to prevent.

What the room carries is `git archive HEAD` plus the files the caller NAMES.
There is no "everything that differs from `HEAD`" mode: on a shared working tree
that set holds the neighbour's work, which is #235 by a second route. A room
under the project root is refused too — it would be untracked work in the tree
it copies.

#### A rebuild reproduces the request, not the room

Naming every file is the correct path and it was retyped on every rebuild:
measured by `beadloom-0mdo.37` while using the command on the bead that built it,
16 `--carry` flags entered twice, once after each fix the room itself caught. The
room is right and the retyping costs seconds. What earns the fix a place is that
the alternative an agent reaches for under that friction is to copy files into
the LIVE room, which is #243 again — a fix that makes the correct path more
tedious than the wrong one has a countdown on it. `beadloom-0mdo.74` shortened
it, because a room now builds its own interpreter and a rebuild pays that again.

So a room's record carries a `request` block — the carry list, the extras the
caller pinned or `null`, and whether an environment was asked for — and
`rebuild=True` reads it out of the marker it is about to delete. Two properties
keep that from reopening what it was built on:

- **What is reused is the LIST, never the content.** The files are copied from
  the working tree at build time, exactly as a typed list would be, so a rebuild
  is still a room nothing inside postdates. Reusing the previous room's files
  would BE #243.
- **An option named beside `--rebuild` REPLACES its remembered counterpart** and
  never adds to it, so the remembered list cannot grow into the mode that
  deliberately does not exist. A remembered path the working tree no longer holds
  refuses the rebuild by the same `file_missing` route a typed one would, and
  refuses it while the room and its record are still there.

The request is recorded beside the outcome rather than read back out of it,
because the two come apart: a room given no environment records no extras choice
at all, so a request reconstructed from the outcome would lose the set the caller
pinned. A room recorded before the `request` block existed falls back to its
`carried` list, which IS the carry request faithfully — the alternative is a
rebuild that silently carries nothing, which is the failure this reuse exists to
prevent arriving by another door.

**One rule decides what may be remembered: a rebuild must never silently produce
a room whose verdict is greener or less isolated than the one it replaces.** It
settles both open cases and they point opposite ways. Extras the caller PINNED
are reused, because forgetting `--extras dev` widens the room to the legs' union
and on this code base at one commit that is 0 mypy errors where the pinned leg
reports 82 (BDL-UX #236) — a greener room than the one asked for. A set the LEGS
derived is re-derived instead, for the reason the "everything that differs" mode
does not exist: pinning it carries a set nobody named. And `--no-environment` is
recorded and NOT reused, because remembering a decline hands back a room whose
verdict the machine decides (BDL-UX #256) with no way to ask for anything else
short of deleting the room, while forgetting it costs a measured 3.6 s and 160 MB
and gives the room its own interpreter. To leave a pinned set, name another one:
`beadloom rooms --dimension extras` prints the sets the legs declare.

`room_invocation` hands back how to measure in the room and how to check that you
did. With an editable install, running the suite from inside the room under the
project's environment imports the TREE's source; the first run that did it was
caught from a warning path rather than from a failure, which is a green that is
a measurement of the tree wearing a room's name. `PYTHONPATH` pointing at the
room's own `src` is the fix, and the `import beadloom` line is the check.

The interpreter the invocation names is the ROOM's own when it has one, the
project's `.venv` when it keeps one, and `sys.executable` otherwise. The room's
comes first because isolating the files and leaving the interpreter to the
machine is BDL-UX #256, below. The second distinction was found by running the
command on this bead: `sys.executable` is the CLI PROCESS's interpreter, and
Beadloom installed as a `uv` tool runs under one with neither `pytest` nor the
project's development dependencies, so the first invocation handed back could not
be run at all.

The room records its owner, the commit, the carried files, both interpreters —
the one the invocation names and the one that built the room — and the optional
extras the invocation's interpreter has, in `.beadloom-room.json`.

The extras are recorded because they, and not the files, decide the verdict
(BDL-UX #236). Measured on this repository at `6c4d0a9`, over one code base at
one commit: `mypy src/` reported 0 errors under `.[all,dev]` and 82 under
`.[dev]`, and under the second the whole `tui` suite leaves the run — three of its
four modules skip and the fourth stops the collection with an error. A room's name isolates its FILES; which
extras its interpreter has is a second question, and a report that cannot be
reproduced from what it prints is a claim rather than a measurement. The
derivation is `application.rooms.installed_extras` — the same one `beadloom
rooms` reports, because two answers to one question are two things that can
disagree — and `resolved: false` records that nothing could look, which is never
the same answer as no extras.

### The interpreter the room holds

BDL-UX #256, and it is the second half of the same failure. A room isolates the
FILES a verdict is taken over, and until this bead nothing isolated the
interpreter they run under, so the verdict was decided by whatever the machine
happened to hold — the same measurement as above, 0 mypy errors against 82 over
one code base at one commit. So `build_room` creates a virtual environment inside
the room and installs the room's own sources into it, and `room_invocation` names
that interpreter.

**Which extras: the union of every extra any leg of this project's workflows
installs**, read from the typed install step by
`application.rooms.leg_installs`. Two readings were measured before choosing.
The COMMONEST set is wrong on this repository: of the 8 installing jobs
`leg_installs` reports, four install `dev, languages` to build a site or run a
release gate and two run the suite, so the modal set is the one no suite verdict
is taken under. The UNION is taken because the two errors are not symmetric — a
missing extra removes tests from a run without failing it, while a surplus one
removes nothing. Measured over this tree on a warm `uv` cache: the union
(`dev, graphql, languages, mutation, tui, watch`) installs in 1.07 s for 169 MB,
against 1.78 s and 160 MB for `.[all,dev]`. The surplus is 9 MB and no time.

A leg spelling `--all-extras` names every extra and enumerates none, so it is
expanded from the packaging by `application.rooms.declared_extra_names`, read
without a TOML parser for the reason `application/rooms.py` states — `tomllib` is
3.11+ and this project supports 3.10. That read finds no key spelled across lines
or inside an inline table, so it is a lower bound on what a project declares.

**Three answers, never two.** `--extras` names them and wins, because
reproducing one particular leg is the reason to override a union and a union
cannot express it. No leg installing the project at all leaves the choice
UNDERIVED, and an underived choice builds nothing: installing a guess is how
`.[dev]` lost four test modules silently. `--extras ""` is a fourth request and
not the third one — an environment with no extras is a declared environment,
where an underived choice is no answer at all.

**A room without one is a finding and never a refusal.** The files are still
isolated, so a room whose environment could not be built is still a room; what it
must not do is let the reader assume it has one. It reports which interpreter its
verdict will be taken under instead, `beadloom clean-room` exits 1, and the
record carries `environment.built: false` with the failure in the installer's own
words. A half-built environment is removed, for the reason a half-built room is:
an interpreter that exists, answers imports and holds an unknown subset of what a
verdict needs is worse than none.

**`interpreter.extras` is read off the ROOM's interpreter**, through
`installed_extras(project_root, search_path=...)` — the same derivation, pointed
at another environment's installed metadata, which is files on disk and is read
without importing anything that environment holds. What `environment.asked`
records is a request and what `interpreter.extras` records is the answer; they can
differ, and that difference is what BDL-UX #236 is about.

**The cost is paid per room and never cached.** Measured on this machine, warm
`uv` cache, macOS/APFS: `uv venv` 0.082 s, `uv pip install -e` 1.07 s, room 184 MB
apparent. Against a seven-minute suite that is under half a percent, and every
`--rebuild` pays it again on purpose: a virtual environment kept outside the room
and reused is a directory two rooms share, which is the property BDL-UX #235 was
filed about. The reuse that matters is `uv`'s own package cache, which is
content-addressed and so cannot carry one room's source into another.

**Without `uv`, the stdlib path is used and it is not the same measurement**:
`python -m venv` 1.84 s plus `pip install -e` 39.6 s over this tree, against
`uv`'s 0.082 s plus 1.07 s. The room records which installer built it, because a
forty-second step and a one-second step reported as one fact is how a cost that
decides whether rooms get built at all becomes invisible. A failure is reported
rather than retried under the other installer: falling back would hide which
resolver produced the verdict.

### What each medium is checked against

One verdict per medium, in `plan.media_checks` and under `media_checks` in
`--json`. `failed` and `unmeasured` are findings and reach exit 1; `passed` is
not. `STATUS_NOT_APPLICABLE` is still defined in `models.py` and is emitted by no
check — see below.

| Medium | Precondition checked | Observed from |
|---|---|---|
| `working-tree` | no path differs from `HEAD` that no bead in the plan owns | `git status` |
| `commit-gate` | the installed pre-commit hook judges the paths a commit stages | `.git/hooks/pre-commit` |
| `landing-order` | every instruction of the landing lock names its holder and asks for no queue | the composed flow artifacts |
| `focus-document` | the document every route writes carries a row for each bead of the plan | the composed `/task-init` routing table and the work item's folder |
| `graph-files` | the node population the graph files declare is the one the index resolved these scopes from | `.beadloom/_graph/*.yml` through `each_graph_file`, and `get_all_nodes` on the index |
| `doc-baseline` | no doc pair is stale before the wave starts | the doc index |
| `tracker-ids` | every bead's title numbers it the way the tracker did | the bead records |

The work item's axes are gathered the same way and for the same reason:
`work_item_axes(project_root)` in `declared-scope` renders the read the commit
gate already makes into the planner's vocabulary, so the gate and the plan cannot
come to disagree about what one work item approved, and a work item nothing can
be read from arrives as a `WorkItemAxes` carrying its reason rather than as an
absence dropped at the edge.

The six file-observed media are gathered by the command and handed to
`plan_waves` as a `WaveEnvironment`, so the decision stays runnable without git,
without a repository, without a hook and without a scaffolded flow — each absence
arrives as a `None` the check reports, never as a silent zero. Every medium is checked at every wave
size: `not_applicable` was withdrawn as a verdict a plan's shape could produce
(BDL-UX #228), because a check that switches itself off is silent exactly where
nobody is already thinking about the risk. The constant survives in `models.py`
and in the package's `__all__`, emitted by nothing — a name kept for a caller that
may still read it, not a state any plan reaches.

The `tracker-ids` check has run whether or not the plan is concurrent since
`beadloom-mr2l.80`, and is no longer the exception it was written as. The
mis-numbering it looks for happens at bead *creation*, before any wave runs, so a
plan that serialises the beads it mis-wired is exactly the plan whose ids most
need checking. Only the trailing number is compared: the title convention writes
`BDL-061.<n>` while the tracker allocates `<project>.<n>`, so comparing whole ids
would report every bead and comparing prefixes would report none.

This check is the DETECTING half, and `beadloom-0mdo.53` added the preventing
half at the other end of the same fact. `title_references(text)` is the reader
both use: it is public here, and `services/bd_seam/creation.py` calls it to refuse
a creation plan whose title states a number the tracker has not allocated yet. One
grammar read twice — where a number is written and where it is compared — rather
than two readers that can come to disagree, which is the duplication
`beadloom-0mdo.51` deleted from the landing lock. The two halves answer different
moments: at creation there is no id to compare against, so any number in a title
is a promise nothing can check, and refusing costs nothing; by the time a wave is
planned the beads exist and only the comparison is left.


### The landing lock, and the two guarantees it is asked to give

The `landing-order` medium exists because one primitive was asked for two
guarantees and gave neither in the form this flow requested it. BDL-UX #194 and
#237 are the same defect, filed nine days apart by two agents that had never met.

**What was measured, on bd 1.0.4, in an isolated rig with every exit code read
without a pipe.** The primitive is sound: `acquire` on a held slot exits 1 and
names the holder, and across four rounds of eight simultaneous acquires exactly
one won each round. `release --holder <name>` is owner-checked and refuses a
caller that is not the holder. `--holder` accepts any string, so a bead id can
hold the slot today, and `check --json` reports it back.

**What granted nothing was the call form.** Three defects, all in the
instructions rather than in the tracker:

| Defect | What the form costs |
|---|---|
| `anonymous-holder` | an `acquire` with no `--holder` takes the tracker actor (`$BEADS_ACTOR` → `git user.name` → `$USER`), one identity for every role on one machine, so the holder cannot be told from the claimant |
| `unguarded-release` | a `release` with no `--holder` frees whoever holds the slot, including a live neighbour, and reports success |
| `queue-only-wait` | `--wait` appends the caller to a queue nothing drains and returns at once with exit 1; prose that calls it blocking is what stops an agent reading the exit code |
| `unknown-form` | a subcommand this derivation has not measured — reported rather than passed, because an unjudged site that reads as clean is the class this instrument exists to remove |

`landing.lock_sites(invocations)` judges each invocation by its **flags**, never
by the prose around it: a check that read English for the promise "blocks until
free" would repeat the keyword-proximity class already filed three times against
the docs audit.

**It no longer parses.** This module derived its own population until BDL-068 S5,
when `beadloom-0mdo.51` generalised that grammar to every `bd` subcommand and
homed it at the seam. There is now ONE grammar for "this text invokes `bd`"
(`services.bd_seam.invocations.text_invocations`) and ONE judgement of the lock,
here; `services.bd_seam.assumptions.lock_invocations` is the only bridge between
them, and the application layer imports no `re` at all. Two derivations of one
kind is the defect BDL-068 removes, so there is one. The population it is handed
is still the composed flow artifacts — the agent directories from
`TOOL_AGENT_DIRS`, the slash commands from `COMMAND_FILES`, the project layer
from `.beadloom/flow` — so a tool added to the flow is covered by the same act.

The verdict states the size of the population it judged. A project that has never
scaffolded a flow instructs the lock nowhere, and a pass over nothing says so
rather than reading as a pass over something.

**What this medium cannot check**, stated here rather than discovered later: it
reads what an agent is TOLD, and cannot know what an agent DID. Nothing in a plan
can observe whether the slot was taken before a commit, for the same reason
nothing in a plan can observe whether the gate owner ran the combined tree.

### Overrides

A human may outrank the computation, and records it the way every stand-down in
this codebase is recorded — with a reason and an exit condition:

```yaml
waves:
  overrides:
  - beads: [proj-1, proj-2]
    decision: parallel        # or: serial
    reason: "the two touch one vocabulary module and nothing else"
    until: "2026-09-01"
```

Every key is required; a missing one is a configuration error, not a lenient
default. `until` may name a date or an event, and which it is, is decided by the
same `exit_condition_deadline` the guard exclusions and the `forbid_import`
exemptions use.

Each override is reported with the number of decisions it actually changed —
measured as the number of its pairs the **shape** decides differently when the
override is removed and every other one still applies. Counting edits to the
conflict set instead reported work an override had not done: deleting a
`blocked_by_bead` conflict counted as a change while the blocked bead was placed
behind its blocker anyway. One that changed **none** is a finding: an override
nobody can see doing anything is how a check gets switched off without anybody
saying so.

An override speaks only about pairs the plan actually contains. A `serial` entry
naming beads that have since closed used to create a conflict for the absent
pair, which was then printed beside the real serialisations where a reader could
not tell them apart.

## Invariants

- An unresolved scope never reads as an independent one, and every way the
  declaration cannot be read lands there.
- A declaration compared against nothing never reads as one that agreed.
- A ref the derivation did not reach is never reported as a wrong declaration,
  and an axis row naming no node is never counted as agreement.
- One composition of a bead's declaration, shared by every caller of the parser.
- One reason per serialised pair, taken from a closed named vocabulary.
- The same inputs produce the same shape, including the order within a wave.
- Every wave names its shared media, its gate owner and one room per bead,
  whatever its width.
- A room is created, never entered: a build that finds a directory at the derived
  path refuses and leaves it byte-for-byte as it was.
- A rebuild deletes only a directory whose recorded owner is the bead it was
  asked for.
- A rebuild reuses the request the room it replaces recorded and re-reads the
  files from the working tree, so the reused list can never carry stale content.
- An option named beside a rebuild replaces its remembered counterpart, and a
  remembered path the tree no longer holds refuses the rebuild rather than
  dropping out of it.
- A room STATES the optional extras its invocation's interpreter has, and never
  reports "no extras" for "nothing looked".
- A room HOLDS the interpreter its verdict is taken under, or says which one it
  borrows instead. Failing to build one is a finding and never a refusal: the
  files are isolated either way, and what a reader must not do is assume.
- Every medium the plan names carries a verdict, and an unobserved one is
  `unmeasured` rather than `passed`.
- A required override field is required by its content: a key present but blank
  is a configuration error, because an override with no reason and no deadline
  outranks the graph permanently by accident.
- The plan is read-only with respect to the index and the tracker.

## API

| Entry point | Answers |
|---|---|
| `plan_waves(records, *, conn, overrides, today, environment, axes)` | the whole shape, as a `WavePlan` |
| `compare_declarations(scopes, axes)` | one verdict per declared ref, plus one per axis row naming no node |
| `unguarded_axes(waves, scopes, axes)` | per concurrent wave, the approved nodes none of its beads declares |
| `remedy_for(reason, *, axes)` | what to do about an unresolved scope, given what else is known |
| `resolve_scope(conn, record)` | what one bead occupies, or why that is unknown |
| `parse_declaration(text)` | the refs a declaration names, the words it dropped, and whether it was anchored |
| `compose_declaration(record)` | the tracker's four fields as the one string the parser reads |
| `conflict_between(conn, left, right, *, blockers)` | why one pair may not run together |
| `load_overrides(project_root)` | the declared overrides in `flow.yml` |
| `room_for(bead_id)` | the clean room that bead owes, `room-<bead-id>` |
| `room_path(parent, bead_id)` | that room's directory under a parent |
| `build_room(*, bead_id, project_root, parent, carry, rebuild, extras, environment)` | build it from `HEAD` plus the named files, give it an interpreter, or refuse and say why |
| `room_owner(path)` | the bead a room records, or `None` when the directory is not a room |
| `room_request(path)` | what that room was asked for, or `None` when the directory is not a room |
| `RoomBuild.reused` | the request parts this build took from the record of the room it replaced |
| `room_invocation(path)` | how to run a suite in the room, and how to check that you did |
| `RoomBuild.extras` | the optional extras the room's interpreter has, or `None` when nothing could look |
| `RoomBuild.environment` | the interpreter the room holds, or the reason it holds none |
| `extras_a_room_installs(project_root, asked)` | what the caller named, or the union of every extra the legs install |
| `build_environment(*, room, choice, otherwise)` | create the room's interpreter and install its sources, or say why there is none |
| `room_python(room)` | the interpreter inside a room, or `None` |
| `site_packages(room)` | where that interpreter keeps its installed metadata |
| `check_media(records, *, owned_paths, environment)` | one verdict per medium |
| `lock_sites(invocations)` | what each landing-lock invocation's call form grants |
| `LockInvocation` | one parsed lock invocation, handed in by the seam's grammar |
| `defect_detail(defect)` | what one defective call form costs and the flag that fixes it |
| `title_id_mismatches(records)` | every bead whose title numbers it differently |
| `title_references(text)` | every bead reference a title states — the reader both halves of #171 share |

`plan_waves` takes bead records as **data**, never a tracker handle: the
application layer does not import the `bd` seam (which lives in `services`), and
every scenario runs without a `bd` binary on the machine.

## Structure

| Module | Responsibility |
|---|---|
| `models.py` | the vocabulary — records, scopes, conflicts, overrides, waves, and the words each named reason prints in |
| `scope.py` | resolve a bead to the nodes and files it occupies |
| `derivation.py` | hold each declaration against the derivation its work item recorded |
| `independence.py` | decide whether one pair may run together, and say why not |
| `landing.py` | what the landing lock grants, and which call form grants it |
| `media.py` | what a wave shares no matter how independent its code is |
| `clean_room.py` | build the room a bead owns, and refuse a directory this run did not create |
| `room_env.py` | the interpreter a room's verdict is taken under, and which extras it holds |
| `media_checks.py` | whether each medium's plan-time precondition holds |
| `planner.py` | assign beads to waves, apply overrides, report findings |
| `config.py` | read and validate the declared `waves:` overrides |

## Testing

`tests/acceptance/features/wave_plan.feature` states the behaviour as executable
scenarios; `tests/test_wave_plan.py` covers the reasons, the ordering and the
override arithmetic; `tests/test_wave_media_checks.py` covers the medium
verdicts and the title-against-id comparison;
`tests/test_the_graph_a_plan_is_derived_from.py` covers the `graph-files`
medium and holds the two mechanisms BDL-UX #261 sketched and this feature
declined, each with the condition that reopens it;
`tests/acceptance/features/landing_lock.feature` and
`tests/test_landing_lock_sites.py` cover the landing-lock derivation and hold
this repository's own instructions to it; `tests/test_cli_waves.py` covers
the command's two output shapes and its three exit codes;
`tests/test_bead22_wave_guarantee.py` holds the guarantee to both of its clauses
and owns the five findings BDL-061.22 measured;
`tests/test_bead83_failure_direction.py` pins the DIRECTION each of the two S6
decisions fails in; `tests/test_wave_derivation.py` covers the four agreement
verdicts, the per-wave gap and the remedies that read the work item's document;
`tests/acceptance/features/clean_room.feature` states the room's ownership and
its once-only build as executable scenarios;
`tests/acceptance/features/room_environment.feature` states the interpreter it
holds, over real environments, and `tests/test_room_environment.py` covers what
those cannot reach — the second installer, a create step that fails, and the
install spellings this repository's own workflows do not use.
`tests/test_cli_clean_room.py`
covers `beadloom clean-room`'s two output shapes and its three exit codes;
`tests/acceptance/features/room_extras.feature` states that a room records the
extras its interpreter has, and `tests/test_room_extras.py` covers the
derivation those records come from.

## Related

- `beadloom waves` — the command (`src/beadloom/services/commands/waves.py`)
- `beadloom clean-room` — the command that builds a room the plan names
  (`src/beadloom/services/commands/clean_room.py`)
- `flow-guards` — the sibling primitive that answers a process question per edit
- `sync-check` — where the `commit-gate` medium's repair lives (`--staged`)
