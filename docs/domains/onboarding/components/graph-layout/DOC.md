# Graph Layout (component)

Internal building block of the onboarding domain.

**Source:** `src/beadloom/onboarding/graph_layout.py`

---

## Overview

`.beadloom/_graph/` has two questions about it and they are not the same question.
[graph-files](../graph-files/DOC.md) answers the reader's — which files may I open, and
what happens when one will not parse. This component answers the writer's: can two
agents adding two nodes collide.

The property, stated once:

> every node is declared in a graph file of its own, named after the node, and every
> edge is declared in a file named after one of its two endpoints.

The first clause is what removes the shared write. Two beads that add nodes create two
files, so the collision cannot be attempted rather than being detected afterwards. The
second is the weaker clause an edge can carry, because an edge is a fact about two
nodes and one file per node can give it only one home.

## Public surface

- `node_file_name(ref_id)` — the file a node is declared in: the ref id verbatim plus
  `.yml`. The ref id is already the graph's unique identifier, so transforming it would
  put a second spelling of one name into the tree.
- `layout_of(graph_dir)` — the directory's layout, read through `each_graph_file`. The
  skip policy is not restated here; a second policy over one directory is the defect
  that component exists to have removed.
- `shared_files(files)` — the files of a name-to-ref-ids mapping that declare more than
  one node. Takes a mapping rather than a directory so this repository's own graph and
  a wave plan's `GraphInput` are answered by one body.
- `GraphLayout` — `shared`, `shared_nodes`, `holds`, `declared`, `misnamed`,
  `misplaced_edges`.
- `SharedFile`, `EdgeHome` — the two records those answers are made of.

`holds` and `misnamed` are separate answers because a project can have the property
without the name: one node per file removes the shared write whatever the files are
called, and the name is what makes `vi .beadloom/_graph/<ref-id>.yml` a lookup instead
of a search through a file holding a hundred nodes.

## Why it exists

`beadloom-kqsv` shipped `graph-files` as the seventh medium every wave states: the graph
is an input to the plan AND an artifact a bead of the wave may be writing. Stating it is
as far as a plan can go, because the node a bead is about to add is in no graph the plan
could read. It also measured and declined the serialisation BDL-UX #261 sketched — on a
graph held in one file, "two beads whose declared nodes are defined in one graph file"
fires on every pair and collapses every wave to a wave of one.

BDL-UX #265 is the layout that removes the sharing instead of reporting it, and it is the
same primitive `beadloom-0mdo.66` took for the issue log's numbers at a different
boundary. On this repository 7 of the 8 commits that touched `.beadloom/_graph/` on
`features/BDL-068` ADDED a node, so the shared write was the common case and not a corner.

## What the split cost, measured

Over this repository's whole graph — a hundred node declarations and a hundred and
sixty-nine edge declarations at the time of the split — on macOS, Apple silicon, under
CPython 3.13.7, warm APFS; medians of 20 in-process runs and 5 subprocess runs over two
copies of the tree differing only in the graph's layout. The population is stated in
words rather than digits because a digit beside the word "nodes" in a sentence about a
measurement is read by `docs audit` as a claim about this project's current node count,
which it is not (BDL-062 `.7`'s precedent, and this project's node count has already
moved by one since the measurement was taken).

| Reader | One file | 100 files |
|--------|----------|-----------|
| `graph.loader.load_graph` | 61.34 ms | 66.40 ms |
| `each_graph_file` | 50.24 ms | 55.44 ms |
| `beadloom reindex --full` | 1895 ms | 1950 ms |
| `beadloom lint --strict` | 368 ms | 369 ms |
| `beadloom doctor` | 427 ms | 429 ms |
| `beadloom ctx graph` | 162 ms | 168 ms |
| `beadloom why graph` | 128 ms | 131 ms |
| `beadloom status` | 787 ms | 788 ms |

Nothing that is one pass became N. Every reader of the directory already globbed `*.yml`
and iterated — `load_graph`, `each_graph_file`, `graph/diff.py`,
`reindex/change_detection.py`, `reindex/indexing.py`, `services/commands/setup.py`,
`services/commands/index_ops.py` — so 100 files is the same single loop with more
iterations, and the readers that go through the index pay nothing at all.

The migration was text-level rather than a `yaml.safe_dump` round trip, because a round
trip destroys every comment and this graph's comments carry the rationale for the node
they precede. All 161 comment lines and all 1146 content lines survive as written, and
every node row and every edge row the loader produces is identical before and after.
What is not preserved is `git blame`: a 1-to-100 split gives every node's declaration a
new file, and `git log --follow` will not attribute it back through the split.

## What this does NOT change

`beadloom init` still writes one `services.yml`, and a single-file graph stays valid for
every reader. One file is the easier thing for an adopter to review once, and the shared
write only matters when concurrent agents write the graph — which is a mature-project
condition, not a bootstrap one. No migration command ships: what an adopter gets is the
number, through the `graph-files` medium of `beadloom waves`, which names the file every
node-adding bead writes and how many nodes it holds.

## What the layout does NOT make possible

`beadloom-kqsv` recorded that a graph split across files is the condition under which the
declined serialisation becomes worth building. Measured on the split tree, the conclusion
does not follow. One node per file makes the node-to-file map injective, so "two beads
whose declared nodes are defined in one graph file" holds exactly when the two beads
declare the same node — which `conflict_between` already serialises as `shared_node`. A
serialisation that produces no pair `shared_node` does not already produce is a check
that cannot fail, which is the ground on which `shared_document` was declined. The
mechanism is only ever non-trivial while some file holds several nodes, which is the
state the layout removes.

## Tests

`tests/test_the_graph_is_one_file_per_node.py`. The unit half runs over synthetic
directories; four pins run over this repository's own graph and go red the day a node is
appended to another node's file, a node is declared in a file not named after it, an edge
is declared under neither endpoint, or the injectivity above stops holding.
