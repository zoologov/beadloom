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
pre-commit hook, one doc-freshness baseline, one tracker id space — and no
choice of shape makes any of them independent.

**The split the sentence names.** The second half was a constant tuple until
BDL-061.80: the four media were printed with the evidence they came from, and
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
| `declaration_not_at_a_line_start` | `refs:` inside a sentence | move the declaration to the start of its own line |
| `declaration_dropped_a_node` | a second ref without a comma | separate the names with a comma |

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

Printed by every plan whose widest wave holds more than one bead, each with the
evidence it comes from:

| Medium | Evidence |
|---|---|
| `working-tree` | an agent's clean-room green is a claim about N files, not about the tree |
| `commit-gate` | one pre-commit hook; a commit is judged over the paths it stages, and states the rest |
| `doc-baseline` | one git-ignored index. The freshness fact is recorded per FILE (`beadloom-mr2l.78`), so a bead's change no longer marks the pairs its node's other files own — but an attestation still re-baselines every pair of the ref it names |
| `tracker-ids` | allocated at creation, while a title written beforehand carries the id the author predicted |

A wave of one shares nothing concurrently — its clean room *is* the tree — and
the plan says that rather than printing the list as a banner.

### What each medium is checked against

One verdict per medium, in `plan.media_checks` and under `media_checks` in
`--json`. `failed` and `unmeasured` are findings and reach exit 1; `passed` and
`not_applicable` are not.

| Medium | Precondition checked | Observed from |
|---|---|---|
| `working-tree` | no path differs from `HEAD` that no bead in the plan owns | `git status` |
| `commit-gate` | the installed pre-commit hook judges the paths a commit stages | `.git/hooks/pre-commit` |
| `doc-baseline` | no doc pair is stale before the wave starts | the doc index |
| `tracker-ids` | every bead's title numbers it the way the tracker did | the bead records |

The three machine-observed media are gathered by the command and handed to
`plan_waves` as a `WaveEnvironment`, so the decision stays runnable without git,
without a repository and without a hook — each absence arrives as a `None` the
check reports, never as a silent zero. They are reported `not_applicable` when no
wave holds more than one bead, on the same rule that governs the statements.

The `tracker-ids` check runs whether or not the plan is concurrent. The
mis-numbering it looks for happens at bead *creation*, before any wave runs, so a
plan that serialises the beads it mis-wired is exactly the plan whose ids most
need checking. Only the trailing number is compared: the title convention writes
`BDL-061.<n>` while the tracker allocates `<project>.<n>`, so comparing whole ids
would report every bead and comparing prefixes would report none.

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
- One composition of a bead's declaration, shared by every caller of the parser.
- One reason per serialised pair, taken from a closed named vocabulary.
- The same inputs produce the same shape, including the order within a wave.
- A wave of more than one bead always names its shared media and its gate owner.
- Every medium the plan names carries a verdict, and an unobserved one is
  `unmeasured` rather than `passed`.
- A required override field is required by its content: a key present but blank
  is a configuration error, because an override with no reason and no deadline
  outranks the graph permanently by accident.
- The plan is read-only with respect to the index and the tracker.

## API

| Entry point | Answers |
|---|---|
| `plan_waves(records, *, conn, overrides, today, environment)` | the whole shape, as a `WavePlan` |
| `resolve_scope(conn, record)` | what one bead occupies, or why that is unknown |
| `parse_declaration(text)` | the refs a declaration names, the words it dropped, and whether it was anchored |
| `compose_declaration(record)` | the tracker's four fields as the one string the parser reads |
| `conflict_between(conn, left, right, *, blockers)` | why one pair may not run together |
| `load_overrides(project_root)` | the declared overrides in `flow.yml` |
| `media_for(wave_size)` | what a wave of that size shares |
| `check_media(records, *, concurrent, owned_paths, environment)` | one verdict per medium |
| `title_id_mismatches(records)` | every bead whose title numbers it differently |

`plan_waves` takes bead records as **data**, never a tracker handle: the
application layer does not import the `bd` seam (which lives in `services`), and
every scenario runs without a `bd` binary on the machine.

## Structure

| Module | Responsibility |
|---|---|
| `models.py` | the vocabulary — records, scopes, conflicts, overrides, waves |
| `scope.py` | resolve a bead to the nodes and files it occupies |
| `independence.py` | decide whether one pair may run together, and say why not |
| `media.py` | what a wave shares no matter how independent its code is |
| `media_checks.py` | whether each medium's plan-time precondition holds |
| `planner.py` | assign beads to waves, apply overrides, report findings |
| `config.py` | read and validate the declared `waves:` overrides |

## Testing

`tests/acceptance/features/wave_plan.feature` states the behaviour as executable
scenarios; `tests/test_wave_plan.py` covers the reasons, the ordering and the
override arithmetic; `tests/test_wave_media_checks.py` covers the four medium
verdicts and the title-against-id comparison; `tests/test_cli_waves.py` covers
the command's two output shapes and its three exit codes;
`tests/test_bead22_wave_guarantee.py` holds the guarantee to both of its clauses
and owns the five findings BDL-061.22 measured;
`tests/test_bead83_failure_direction.py` pins the DIRECTION each of the two S6
decisions fails in.

## Related

- `beadloom waves` — the command (`src/beadloom/services/commands/waves.py`)
- `flow-guards` — the sibling primitive that answers a process question per edit
- `sync-check` — where the `commit-gate` medium's repair lives (`--staged`)
