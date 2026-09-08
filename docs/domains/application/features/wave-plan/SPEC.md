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
of media a wave shares whatever shape it takes — one working tree, one
pre-commit hook, one landing order, one doc-freshness baseline, one tracker id
space — and no choice of shape makes any of them independent.

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

Each declared ref gets one of four verdicts, and only one of them is a finding:

| Verdict | What it means | Finding |
|---|---|---|
| `agrees` | a kept row, or a `Derived by` target, names it | no |
| `ruled_out_of_scope` | a row names it and rules it **out** — the approval does not cover it | yes |
| `no_scope_decision` | a row names it and decides nothing; `axis-without-a-scope-decision` owns that fault | no |
| `not_derived` | no row names it at all | no |

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
work item approves that **no bead of a wave declares**. It is reported per wave
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
| `working-tree` | an agent's clean-room green is a claim about N files, not about the tree, and the room is built at `room-<bead-id>` so it can say whose it is |
| `commit-gate` | one pre-commit hook; a commit is judged over the paths it stages, and states the rest |
| `landing-order` | one branch. What keeps two agents out of one FILE is the disjoint scopes the plan derived; what orders their COMMITS is the merge slot, and only in the form that grants it (BDL-UX #194, #237) |
| `doc-baseline` | one git-ignored index. The freshness fact is recorded per FILE (`beadloom-mr2l.78`), so a bead's change no longer marks the pairs its node's other files own — but an attestation still re-baselines every pair of the ref it names |
| `tracker-ids` | allocated at creation, while a title written beforehand carries the id the author predicted; a creation of more than one bead goes through one plan whose edges name plan-local keys, and a hand-wired `dep add` is where the echoed titles are the only check (BDL-UX #171, #165) |

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
deliberately **not** one of the five: a medium here is one with a plan-time
precondition a command can observe, and a scratchpad path exists only inside a
running agent session. An entry for it would be permanently `unmeasured` — a
finding on every plan — or permanently true. What is observable is the remedy,
so the remedy is what ships, in `room_for`, in the `working-tree` statement and
in the role cores that carry the `clean-room` duty.

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
| `doc-baseline` | no doc pair is stale before the wave starts | the doc index |
| `tracker-ids` | every bead's title numbers it the way the tracker did | the bead records |

The work item's axes are gathered the same way and for the same reason:
`work_item_axes(project_root)` in `declared-scope` renders the read the commit
gate already makes into the planner's vocabulary, so the gate and the plan cannot
come to disagree about what one work item approved, and a work item nothing can
be read from arrives as a `WorkItemAxes` carrying its reason rather than as an
absence dropped at the edge.

The four file-observed media are gathered by the command and handed to
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
| `media_checks.py` | whether each medium's plan-time precondition holds |
| `planner.py` | assign beads to waves, apply overrides, report findings |
| `config.py` | read and validate the declared `waves:` overrides |

## Testing

`tests/acceptance/features/wave_plan.feature` states the behaviour as executable
scenarios; `tests/test_wave_plan.py` covers the reasons, the ordering and the
override arithmetic; `tests/test_wave_media_checks.py` covers the five medium
verdicts and the title-against-id comparison;
`tests/acceptance/features/landing_lock.feature` and
`tests/test_landing_lock_sites.py` cover the landing-lock derivation and hold
this repository's own instructions to it; `tests/test_cli_waves.py` covers
the command's two output shapes and its three exit codes;
`tests/test_bead22_wave_guarantee.py` holds the guarantee to both of its clauses
and owns the five findings BDL-061.22 measured;
`tests/test_bead83_failure_direction.py` pins the DIRECTION each of the two S6
decisions fails in; `tests/test_wave_derivation.py` covers the four agreement
verdicts, the per-wave gap and the remedies that read the work item's document.

## Related

- `beadloom waves` — the command (`src/beadloom/services/commands/waves.py`)
- `flow-guards` — the sibling primitive that answers a process question per edit
- `sync-check` — where the `commit-gate` medium's repair lives (`--staged`)
