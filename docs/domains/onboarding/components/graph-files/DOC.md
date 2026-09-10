# Graph Files (component)

Internal building block of the onboarding domain.

**Source:** `src/beadloom/onboarding/graph_files.py`

---

## Overview

One body holding the skip policy a reader of `.beadloom/_graph/` applies before it
looks at a graph file, for every reader that reads the directory FOR NODES and is
outside the `graph` domain. `init` held four of them with four different policies, and
two of the four carried no guard at all.

The population is narrower than "every reader", and BDL-069 narrowed it by
measurement rather than by preference. See *The population, and what is outside it*
below.

The policy, stated once because there is one of it:

> a file whose name is not a graph file's is skipped; a file that will not read or
> will not parse is skipped; a file that parses to anything other than a mapping is
> skipped. Everything else is yielded as `(path, data)`, so a caller may read
> `data["nodes"]` without asking again whether it can.

`rules.yml` belongs to the policy rather than to any caller: a rules file holds rules
and no nodes, so it is not a graph file for any reader, and no reader had a reason of
its own for skipping it.

## Public surface

- `each_graph_file(graph_dir, *, also_skip=frozenset())` — yields `(path, data)` for
  every graph file under *graph_dir* that survives the policy. A missing directory is
  no graph files rather than an error, which is the virgin case and the common one.
- `NOT_A_GRAPH_FILE` — the names the policy skips for every caller: `rules.yml`.

`also_skip` is the one genuine difference between the callers, and it is a parameter
so that the difference has to be stated at the call site rather than written into a
second body. Exactly one caller passes anything: `doc_classify._existing_graph` names
`imported.yml`, because the run that asks is about to replace that file and the graph
it must read is the one it will be added to.

## Callers

| Caller | What it reads the directory for |
|--------|--------------------------------|
| `onboarding/doc_generator.py::_load_graph_from_yaml` | every node and edge, to render the document set |
| `onboarding/doc_generator.py::_patch_docs_field` | each file it must write a `docs:` field back into |
| `onboarding/scanner/doc_classify.py::_existing_graph` | the graph's root, and which ref_ids already have a parent |
| `services/commands/setup.py::_graph_file_of_each_node` | which file each node came from, for the failure report |
| `services/commands/setup.py::_graph_nodes_now` | each node as written, for the report's attribution |
| `application/reindex/indexing.py::read_declared_docs` | every `docs:` entry a node declares, for the doc index |
| `services/commands/index_ops.py::link` | the file holding one ref_id, to patch its `links:` |

## Why it exists

BDL-067 `.21` removed `generate_skeletons`' node-list parameter, so `init --bootstrap`
stopped passing its own nodes and started reading the tree — through
`_load_graph_from_yaml`, which called `yaml.safe_load` with no `try`. Measured by the
review of `.23` (major 3) on a project carrying one hand-edited
`.beadloom/_graph/legacy.yml` that does not parse: `beadloom init --bootstrap` printed
a raw `yaml.parser.ParserError` traceback at the adopter. The same commit added exactly
that guard to two of the sibling readers and listed it in its own message as delivered.

The traceback is the instance. The shape is one invariant in N bodies, which is what
`.21` had just consolidated for the WRITERS (`scanner/parent_edges.py`), standing on the
readers. Both callers' stated reasons for skipping an unreadable file were already the
same reason — `init` can meet a hand-edited graph file, and failing over it replaces a
missing edge with a traceback; the failure report is being handed to an adopter, and a
traceback from the reporter is worse than one unattributed node — which is why they are
now one body.

The mapping guard is not the same guard as the parse guard and is needed separately: a
graph file holding a top-level list parses without complaint and then raises
`AttributeError` on `data.get`.

## The population, and what is outside it

BDL-069 `beadloom-4ad3` asked each of the seven readers of `.beadloom/_graph/` the same
question over two directories holding THE SAME NODES and DIFFERENT BYTES — a YAML
comment — and then over two holding different nodes. A reader whose answer moves on the
comment reads bytes; one whose answer moves only on the nodes reads nodes.

**Five read for nodes**, and belong to this policy's population:
`graph/loader.py::update_node_in_yaml`, `graph/loader.py::load_graph`,
`graph/diff.py::compute_diff`, `application/reindex/indexing.py::read_declared_docs`
and `services/commands/index_ops.py::link`.

**Two read for bytes**, and are outside it by nature rather than by oversight:
`application/reindex/change_detection.py::_scan_project_files` hashes each file to
decide whether a reindex is needed, and `services/commands/setup.py::_graph_files_now`
digests them to tell the files a run wrote from the ones it inherited. There is nothing
for either to skip, because a file that will not parse still has bytes.

**Three of the five do not reach this body**, and the structural half of the reason is
one boundary rather than three judgements: all three are in the `graph` domain, this
module is in `onboarding`, and `onboarding` already imports `graph`. A `graph` ->
`onboarding` import would be a dependency cycle, which `no-dependency-cycles` refuses at
error severity, so those three restate the guards where they read and each names this
module in its own docstring. Two of them would keep a behavioural exemption even if the
cycle were broken, and those are the reasons worth reading:

- `load_graph` must REPORT a file it cannot parse rather than pass over it, so a broken
  graph does not load as a silently smaller one (BDL-UX #86). Skipping is the right
  answer for `init` and the wrong one for the loader.
- `compute_diff` has two sides — the working tree and content at a git ref — and a
  directory walk covers only the first. Its guards are in `_parse_yaml_content`, which
  both sides pass through, because a guard applied to one side of a comparison and not
  the other invents changes.

Only `update_node_in_yaml` restates the guards for the boundary alone. Removing that
duplication means moving this body into a layer every reader may import, which is filed
as `beadloom-4axf`. The DATA half is already shared: `NOT_A_GRAPH_FILE` is declared in
`graph/loader.py` and re-exported here, because the direction that allows one constant
is `onboarding` -> `graph` and not the reverse.

BDL-UX #220 is closed except for one shape, and that shape is not an unreadable file.
MEASURED over `init`'s own eight (entry point x mode) cells crossed with three shapes of
a hand-edited `.beadloom/_graph/legacy.yml`: a file that does not parse and a file whose
top level is a list now leave `init --bootstrap` at exit 0, because `read_declared_docs`
was routed here. A file carrying `added: 2026-09-02` still ends in `TypeError` — the
date loads as a `datetime.date` and `graph/loader.py::load_graph` cannot `json.dumps` it
into the `extra` column. No skip policy reaches that one, because the file is perfectly
readable.

## Tests

`tests/test_graph_files_are_read_under_one_policy.py` asks every reader the same two
questions over the same tree — a file that does not parse, and a file that is not a
mapping — and derives the reader population from the source: a function that both LISTS
a directory and PARSES YAML, by any name the standard library or PyYAML offers for
either, is a graph-file reader, and this module is the only one under `onboarding/` or
in `setup.py`. Both halves were widened at BDL-067 `.25` after five bodies that read the
directory were measured passing the narrower detector `.24` shipped, which asked for
`glob` with the literal `"*.yml"` and for `yaml.safe_load` by name — the spelling
`each_graph_file` happens to use rather than what makes a body a reader. It also pins
the residue above, so the case fails as soon as somebody closes it.

`tests/test_what_each_reader_of_the_graph_directory_reads_for.py` holds the population
measurement: the comment-versus-node experiment for all seven readers, the skip-policy
cases for the five that read nodes, and the two-ended record of each exemption — the
body names this module in its docstring, and this module names the body. It also states
the derivation's ceiling: the one-body shape sees `each_graph_file` and
`update_node_in_yaml` and is blind to `load_graph` and `compute_diff`, which hand their
parse to a helper, which is why the epic's grep found seven readers where the derivation
finds two.
