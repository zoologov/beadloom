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
> give that guarantee, the wave says so and names the one bead that measures the
> combined outcome.

The sentence has two halves because measurement says one half is not enough. The
first half is code independence, which the graph decides. The second is the set
of media a wave shares whatever shape it takes — one working tree, one
pre-commit hook, one doc-freshness baseline, one tracker id space — and no
choice of shape makes any of them independent.

### How a bead says what it occupies

A bead declares its node scope in its own words, in the tracker:

```
refs: wave-plan, sync-check
```

`ref:`, `refs:` and `area:` are all accepted, every occurrence is read, and the
list ends at the first newline or sentence stop. The declaration is parsed in
one place (`waves.scope.declared_refs`), which is also what the MCP
`bead_context` tool reads, so the two cannot come to disagree about what a bead
said.

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
| `unresolved_scope` | one of the two did not say what it occupies, or named a ref the graph does not have |
| `shared_node` | the expanded scopes intersect |
| `shared_file` | distinct nodes, but the index says a source file belongs to both |
| `dependency_edge` | a `depends_on` edge runs between the scopes, in either direction |
| `override_serial` | a declared override put the pair apart on purpose |

`unresolved_scope` is the reason an advisory tool gets wrong. **An unknown scope
is not an empty scope**: an empty one compares independent of everything, so a
bead that says nothing would be placed in every wave and the command's whole
claim would rest on silence. It is serialised against every bead, and the
remedy — declare `refs:` — is printed.

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
| `doc-baseline` | hashed per node, so one bead's changed file marks every pair its node owns |
| `tracker-ids` | allocated at creation, while a title written beforehand carries the id the author predicted |

A wave of one shares nothing concurrently — its clean room *is* the tree — and
the plan says that rather than printing the list as a banner.

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

Each override is reported with the number of decisions it actually changed. One
that changed **none** is a finding: an override nobody can see doing anything is
how a check gets switched off without anybody saying so.

## Invariants

- An unresolved scope never reads as an independent one.
- One reason per serialised pair, taken from a closed named vocabulary.
- The same inputs produce the same shape, including the order within a wave.
- A wave of more than one bead always names its shared media and its gate owner.
- The plan is read-only with respect to the index and the tracker.

## API

| Entry point | Answers |
|---|---|
| `plan_waves(records, *, conn, overrides, today)` | the whole shape, as a `WavePlan` |
| `resolve_scope(conn, record)` | what one bead occupies, or why that is unknown |
| `conflict_between(conn, left, right, *, blockers)` | why one pair may not run together |
| `load_overrides(project_root)` | the declared overrides in `flow.yml` |
| `media_for(wave_size)` | what a wave of that size shares |

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
| `planner.py` | assign beads to waves, apply overrides, report findings |
| `config.py` | read and validate the declared `waves:` overrides |

## Testing

`tests/acceptance/features/wave_plan.feature` states the behaviour as executable
scenarios; `tests/test_wave_plan.py` covers the reasons, the ordering and the
override arithmetic; `tests/test_cli_waves.py` covers the command's two output
shapes and its three exit codes.

## Related

- `beadloom waves` — the command (`src/beadloom/services/commands/waves.py`)
- `flow-guards` — the sibling primitive that answers a process question per edit
- `sync-check` — where the `commit-gate` medium's repair lives (`--staged`)
