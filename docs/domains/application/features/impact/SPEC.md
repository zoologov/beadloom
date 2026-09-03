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
| `target-outside-the-sweep` | a file this answer is about that does not lie under the swept root, so nothing it defines was read |
| `sweep-narrower-than-the-project` | the swept root is not the project's source root, so every axis is an answer about a subtree |
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

### How wide the sweep is, and how it says so

The swept root is derived from the target and printed as `root swept:` in every
rendering. BDL-068 `.15` is why it is also a claim the answer can withdraw.

The walk up from the target does **not** require `__init__.py`. Requiring one was
correct for this repository, where every package carries it, and wrong for a
PEP 420 namespace package, where the walk stopped at the first subpackage: on a
tree with `src/mypkg/` carrying no `__init__.py`, `impact src/mypkg/sub/writer.py`
swept `src/mypkg/sub` and reported the caller in `src/mypkg/cli/main.py` as
`none found.` — resolved, empty and wrong — while the same function spelled as a
symbol swept `.` and found it. One tree, one derivation, two spellings, opposite
answers, and the wrong one was the clean one. The walk now stops where a source
tree stops: below a directory named `src`, below one carrying `pyproject.toml`,
and never above the project root. `source_root_of` counts a child of `src/` that
**holds** Python at any depth for the same reason.

Two consequences are stated in the answer rather than left to be noticed:

- `callers.resolved` is a **predicate** — false when a file this answer is about
  does not lie under the swept root. It was the literal `True` before, which made
  it the one axis that could never be unresolved while being the axis whose
  completeness depends entirely on the swept root.
- `sweep-narrower-than-the-project` is emitted whenever the swept root is not the
  project's source root, carrying both paths, so a narrowed answer cannot read as
  a complete one.

**An unresolved axis still prints the sites it did find**, under the caveat rather
than instead of it. A caveat that emptied a partial answer would trade one silence
for another.

### Known ceilings

- **A name is a name, not a resolved import.** Two same-named functions under one
  root share a call-graph entry; the collisions that touch an answer are reported
  as `name-defined-more-than-once` rather than left to be discovered.
- **The branch reading is syntactic.** It reads that a call follows a branch, not
  what that call sees at runtime.
- **The branch axis is computed for the target AND for the callers this answer
  named, and each count carries its seat.** BDL-068 `.15` chose this over the
  alternative — emitting an `unresolved` entry per caller whose branches were not
  read — because an entry saying a number exists without printing it is what a
  reader stops at, which is the failure this command was built against. Measured
  on this repository: `impact src/beadloom/onboarding/scanner/bootstrap.py
  --section` wrote `bootstrap_project: 3 branch(es)` and nothing else, while
  `init` — named one row above as a caller — has four branches, and three was the
  number this project carried for nine review passes. The same invocation now
  writes `init: 4 branch(es), 1 exit form(s), from a caller's seat` beside it.
  The ceiling that remains: only the caller FUNCTIONS the answer already found are
  read, not every function in their files, and a caller of a caller is not read at
  all. The axis is one hop out, exactly as `co_writers` is.
- **The narrowing gap is measured against the source root, not against the
  project, so Python OUTSIDE `src/` is swept by nothing and declared by nothing.**
  `_sweep_gaps` emits `sweep-narrower-than-the-project` when the swept root
  differs from `source_root_of(project_root)`, and `source_root_of` returns
  `src/<the one package>` when exactly one child of `src/` holds Python. On that
  layout the two are equal, so the gap cannot fire however narrow the sweep
  actually is. Reproduced 2026-09-03, macOS, foreground, on a tree of
  `pyproject.toml`, `src/myapp/core/target.py` and `scripts/migrate.py`:
  `impact src/myapp/core/target.py` printed `root swept: src/myapp` and
  `who else calls this: none found.`, while `run_migration` calls the target from
  `scripts/migrate.py:10` — and the `unresolved` population carried `no-seed`,
  `no-graph-index` and `unresolved-terminator-name` and nothing about the sweep.
  `callers.resolved` and `co_writers.resolved` are both `True` over that answer,
  and the `## Axes` section `--section` writes carries the same silence in its
  `Unresolved` field, which is what `scope-check` and `axes --refs` then read.
  This is the commonest Python layout there is — `src/pkg` beside `tests/`,
  `scripts/`, `tools/`, `noxfile.py`, `manage.py` — and it bites adopters rather
  than this repository, which holds no production Python outside `src/beadloom`.
  Filed as `beadloom-l4rn` / BDL-UX #225 with its red proof, by the re-review
  that closed the PEP 420 critical above. The two are the same class one layout
  apart. Until it is closed, an empty `callers` or `co_writers` axis is evidence
  only about the swept root, and the swept root is the line to read first.
- **A sweep is re-read on each run.** A cache would be a second thing that can
  disagree with the tree. Measured on this repository's own `src/beadloom` — 250
  modules, 1688 names — one answer takes 1.1 s, macOS, foreground. Reading the
  callers' branches costs one parse per caller file: for `bootstrap.py`, three
  caller sites in two files, `impact_of` went from **1.48 s to 1.65 s**, mean of
  three runs each, macOS Darwin 25.6.0, CPython 3.13.7, in the foreground with no
  pipe. Measured on the tree, not in a clean room and not on a CI leg.

## Modules

| Module | Responsibility |
|---|---|
| `seeds.py` | the seed rule, the declared effect table, and the sinks a target reaches |
| `axes.py` | the four questions, computed over a seed set, each branch count carrying the seat it was taken from |
| `boundary.py` | which node owns a path, and the bounded context above it — `owner_of(path)` and, since BDL-068 S1.6, `context_of(node)` for a caller that starts from a DECLARED node and has no path to look it up by |
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
    THE_TARGET_SEAT,  # the seat a branch count was taken from: the target itself
    THE_CALLER_SEAT,  # ... or a caller of it this answer already named
    package_root_of,  # -> Path: how wide to sweep, derived from the target
    source_root_of,   # -> Path: the project's own source root, to compare against
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
