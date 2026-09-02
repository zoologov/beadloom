# Source Derivation (component)

Internal building block of the application domain.

**Source:** `src/beadloom/application/source_derivation/`

---

## Overview

Answers three questions about code from the source rather than from a list somebody keeps up
to date: *who else writes this*, *who else calls this*, and *how many branches does this have
and how many ways does it end*. It is the derivation half of `beadloom impact`; the command
that renders it is a separate node.

Each of the three was written inside BDL-067 as a test, because each was needed to answer a
question about a defect that a hand-maintained list had already got wrong. BDL-068 S1.1 lifted
them here so that production code can ask the same questions, and so that "is this list still
true?" is computed rather than remembered.

## The rule the package is built to

**A shape, never a spelling.** A check that asks for one way of writing something is a check
that other spellings walk past, and the size of that gap is measured on this repository rather
than supposed: a reader detector asking for `glob("*.yml")` and `yaml.safe_load` by name
walked past five bodies that read the same directory with `iterdir`, `rglob`, a pattern held
in a variable, `os.listdir`, or `yaml.load` with an explicit loader. Each of the five would
have carried a sixth skip policy into the product unseen.

So each shape is a pair of questions about what a body *does* — it lists a directory **and**
parses YAML; it builds a payload **and** commits it — and each half is matched over every name
the standard library offers for that act.

Widening is not free, and the trade-off is recorded where the shape is. A narrow shape
under-reports, which ships the defect. A wide shape may over-report: a body that lists a
directory of documents and parses YAML front matter for another purpose is named too. Measured
on this repository, the wide form names exactly the same one body the narrow form does, so
there is nothing to exempt today — and an over-report fails in front of the person adding the
body rather than at an adopter.

## What it is not

It is not a graph walk. Not one of the axes BDL-067 needed is a fact of the architecture
graph: the writers of a directory, the branches of a command, its exit forms, the readers and
their policies all live *inside* one node. A graph walk would answer confidently and miss all
of them. The graph supplies the boundary a found site falls in; the source supplies the sites.

## The modules

| Module | Responsibility |
|--------|----------------|
| `calls.py` | The callee of a call, spelled two ways — bare for reachability, dotted for identity |
| `source_tree.py` | A directory of Python files read as functions, imports and definitions |
| `call_graph.py` | Function-to-calls map, the reachability fixed point, direct callers |
| `termination.py` | Whether a statement ends the branch it sits in |
| `branches.py` | The branch a call sits in, what still runs after it, and the call sites of one command |
| `body_shapes.py` | Which bodies write a payload, read a directory of YAML, or serialise past a commit point |

Nothing here is bound to a particular question. The names that make a derivation a question
about *graph nodes* or about `init`'s *verdict* — the commit point, the payload key, the
marker call, the module terminator names resolve through — are parameters, supplied by the
caller and read off the product's own function objects so that a rename fails at import.

## Ceilings, stated rather than discovered later

- **A name is a name, not a resolved import.** Two same-named functions in one tree are one
  name here. The reachability answer errs toward reporting.
- **The branch reading is syntactic.** It reads that a call follows a branch; it cannot read
  what that call sees. Measured: `init --yes --mode both` carried the verdict call and passed
  this reading while judging an index written before the run's last graph file.
- **A terminator that cannot be resolved is read as continuing**, so whatever follows it counts
  as reachable. A derivation over syntax cannot close that; running the branches can.
- **A writer must hold both halves in one body.** One that builds the payload and hands the
  commit to a helper is invisible to `writers_that_build` — the helper is visible instead as a
  new direct caller of the commit point.

## Where it is called

`tests/test_init_branches_that_reach_the_bootstrap.py`, `tests/test_one_parent_post_condition_over_every_writer.py`,
`tests/test_graph_files_are_read_under_one_policy.py` and
`tests/test_every_caller_of_the_skeleton_writer.py` hold the derivations to their shape: each
supplies the synthetic bodies the code has to report or refuse, and those bodies are the tree
each derivation goes red on.

## Layering

Pure `ast` and `pathlib` over a path. It imports no other beadloom package, so it sits under
every consumer in `services → application → domains → infrastructure` without adding an edge.
