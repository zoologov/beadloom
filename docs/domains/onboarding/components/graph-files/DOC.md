# Graph Files (component)

Internal building block of the onboarding domain.

**Source:** `src/beadloom/onboarding/graph_files.py`

---

## Overview

One body holding the policy every reader of `.beadloom/_graph/` applies before it
looks at a graph file. `init` held four of them with four different policies, and two
of the four carried no guard at all.

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

## Scope, and what is outside it

This policy covers the readers `init`'s own modules hold. It is not a claim about the
command. MEASURED at `.24` on the review's own tree, after all four were converted:
`application/reindex/indexing.py::read_declared_docs` walks the same directory with no
guard, so `init --bootstrap` still ends in a `ParserError` one step later, reached
through `do_reindex`. That reader is in another domain and `--bootstrap` reached it
before `.21` as well, so it is outside what BDL-067 broke and was left alone
deliberately. `graph/loader.py`, `graph/diff.py`, `reindex/change_detection.py` and
`services/commands/index_ops.py` walk the directory too. Closing the class is a
planning decision rather than a fix.

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
