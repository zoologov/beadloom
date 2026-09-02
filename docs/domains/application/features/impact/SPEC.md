# Impact

Answer what a change touches from the source, over a seed the command derived
rather than one a human happened to know.

**Source:** `src/beadloom/application/impact/`

---

## Specification

### Purpose

BDL-067 spent nine review cycles on one file. Its instrument was seeded from the
function the first dev bead was changing, and under that seed it reported three
branches of `init` and no other writer of graph nodes — cleanly, with nothing to
suggest a fourth branch and a second writer existed. Both were true. The second
writer was first answered in the epic's fourth fix cycle and the fourth branch by
its ninth review, and the number three was repeated in every plan in between.

BDL-068 `.3` re-ran the lifted derivations against that tree, `af26750d`, and
measured the cause. Seeded with the commit point they report **2 writers and 4
branches**; seeded with `bootstrap_project`, the function under change, they
report **0 and 3**. One tree, one derivation, two seeds, opposite answers. So the
thing that decides the answer is the seed, and a command that took the seed as an
argument would move the defect one level up: an agent given a list trusts it and
stops, where an agent reading widely because it does not know the boundary
occasionally stumbles onto the neighbouring shape — which is how several of
BDL-067's findings surfaced at all.

`beadloom impact <path|symbol>` therefore derives its seed, names it, names the
rule that found it, and reports a target it can find no seed for as **unresolved**
rather than answering over an empty set.

### The seed rule

Named `reaches-an-effect-sink`, and carried in every answer so a reader can argue
with it:

> A seed is a name the target reaches through the call graph — transitively, not
> only the names its own bodies call — whose own body performs a declared effect
> directly.

Both halves are measurements taken at `af26750d`, not preferences.

| half | what a rule without it does |
|---|---|
| **transitively** | From `services/commands/setup.py` the first hop holds 71 names and not one body that serialises YAML. The forward closure holds 1277 and reaches the commit point two hops down. |
| **its own body** | 58 names *reach* a body that serialises YAML; exactly 3 *are* one. Seeding on "reaches one" returns the first hop and not the sink. |

The declared effects are two, each a shape this repository has measured:

| effect | a body qualifies when it |
|---|---|
| `serialises-yaml` | turns data into YAML text itself |
| `reads-a-yaml-directory` | lists a directory **and** parses YAML, both in one body |

**`PUTS_BYTES_ON_DISK` is deliberately not one of them**, and the exclusion is a
check rather than a comment. Two reasons, the second the stronger. It does not
contain this product's own commit point: measured at `af26750d`, 268 names reach
a body in that set and `write_yaml_atomic` is not among them, because it puts its
bytes down through `os.fdopen(...).write` and `Path.replace` while the set spells
`write_text`, `write_bytes` and `open`. And it is not a sound predicate alone,
because `open` also reads — seeded on it, `setup.py` yields 19 sinks and 65
co-writers, most of them readers. BDL-068 `.1` handed its narrowing to a later
bead; nothing here is built on top of it.

### What the answer contains

Four axes from the source, one boundary from the graph, and the population the
derivation could not resolve.

| field | what it answers |
|---|---|
| `seeds` + `seed_rule` | what the answer was computed over, and the rule that chose it |
| `co_writers` | who else commits through the same sink |
| `callers` | who else calls what the target defines |
| `commands` | each function's branches, by the guard the source spells, and every way it ends |
| `boundary` | the node and bounded context each site sits in, and whether the change leaves the target's own |
| `unresolved` | what this derivation could not read |

`co_writers` carries `resolved` as well as `sites`, because *no population* and
*an empty population* are different statements and conflating them is how a
derivation that knows nothing reads as one that found nothing.

Every path in the answer — the seeds, the sites and the commands — is written
relative to the project root, so two runs from different working directories
produce the same text and a diff between them is a difference in the code.

### This is not a graph walk

Not one axis BDL-067 needed is a fact of the architecture graph. The writers of a
directory, the branches of a command, its exit forms, the readers and their
policies all live **inside** one node. A graph walk would answer confidently and
miss every one of them — a green describing the checker's ignorance, shipped as a
feature. The graph supplies the boundary and nothing else, and a module whose
axes live entirely inside it still produces an answer.

### The unresolved population

Every entry names a `kind`, so a consumer can act on the class rather than parse a
sentence, and a place, so a human can go and look.

| kind | what it means |
|---|---|
| `no-seed` | no declared effect rule found a sink this target reaches |
| `no-graph-index` | there was no index to read ownership from |
| `unparsed-module` | a file under the root no sweep could read |
| `call-through-a-variable` | a call whose callee is not a name or an attribute |
| `dynamic-dispatch` | a `getattr` call, whose target is a value at runtime |
| `unresolved-terminator-name` | a name imported from outside the standard library, which could be a `NoReturn` helper this answer does not list |
| `name-defined-more-than-once` | a name in this answer with two definitions under the root, which the bare-name call graph merges |
| `no-node-for-path` | a found site the graph does not own |

Terminator names are bound from the module's **own** imports and only from the
standard library. Asking a project-local object would mean importing the tree
under examination, and a derivation that runs the tree it is reading is a
derivation that can change it.

### Known ceilings

- **A name is a name, not a resolved import.** Two same-named functions under one
  root share a call-graph entry; the collisions that touch an answer are reported
  as `name-defined-more-than-once` rather than left to be discovered.
- **The branch reading is syntactic.** It reads that a call follows a branch, not
  what that call sees at runtime.
- **A sweep is re-read on each run.** A cache would be a second thing that can
  disagree with the tree. Measured on this repository's own `src/beadloom` — 250
  modules, 1688 names — one answer takes 1.1 s, macOS, foreground.

## Modules

| Module | Responsibility |
|---|---|
| `seeds.py` | the seed rule, the declared effect table, and the sinks a target reaches |
| `axes.py` | the four questions, computed over a seed set |
| `boundary.py` | which node owns a path, and the bounded context above it |
| `unresolved.py` | what the derivation could not read, as a population |
| `answer.py` | the vocabulary and the one orchestration every rendering reads |
| `render.py` | that one answer as a dictionary and as text |
| `section.py` | that one answer as the `## Axes` section a work item's document carries |

## Public API

```python
from beadloom.application.impact import (
    impact_of,        # -> ImpactAnswer: the four axes, the boundary and the gaps
    answer_to_dict,   # -> dict: the whole answer as plain data
    render_impact,    # -> str: the same answer as text, seed first
    THE_SEED_RULE,    # the rule's name, carried in every answer
    THE_EFFECT_RULES, # the declared effects, each with its statement
)
from beadloom.application.impact.section import render_axes_section  # -> str
```

`render_axes_section` is a THIRD rendering of the same computation, not a third
answer (BDL-068 S1.4). It writes the derivation's half — the seed, the rule, the
axes and the population the derivation could not read — and leaves the person's
scope decision undecided, because a renderer that filled that column in would be
deciding the thing the section exists to record. An absent seed renders as the
word `none` with every axis below it unresolved, never as an empty population.
The grammar is `doc_sync.axes_section`'s, imported rather than restated, and a
round-trip case holds the writer and the reader to one shape.

`impact_of` takes the target and the project root. It never takes a commit point,
and no module under `src/beadloom/application/impact/` spells one — checked over
the AST, so a docstring may cite the measurement while no identifier, argument or
string constant may decide anything by it.

## Related

- `source-derivation` — the AST derivations this feature is written in.
- `cli-commands` — `beadloom impact`, the presentation and the seams.
