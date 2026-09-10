"""The skip policy for a reader of `.beadloom/_graph/` that reads it for NODES.

THE POPULATION, narrowed by measurement rather than by preference. This module
was declared "the one policy every reader of this directory holds", and BDL-069
measured what each of the seven readers reads FOR. Two of them do not read the
directory as a graph at all — `change_detection._scan_project_files` hashes each
file's bytes to decide whether a reindex is needed, and `setup._graph_files_now`
digests them to tell the files THIS run wrote from the ones it inherited. Their
answers move when a comment is added to a graph file and a node reader's do not,
which is the experiment `tests/test_what_each_reader_of_the_graph_directory_reads_for.py`
performs. For those two the policy is inapplicable by nature: there is nothing
to skip, because a file that will not parse still has bytes.

So the claim this module makes is over the readers that PARSE NODES, and three
of those five do not reach it either. `graph.loader.update_node_in_yaml`,
`graph.loader.load_graph` and `graph.diff.compute_diff` each state their
exemption where they read, and the structural half of the reason is the same for
all three: this module is in `onboarding`, which already imports `graph`, so a
`graph` -> `onboarding` import would be a dependency cycle. `no-dependency-cycles`
refuses that at error severity, so those three restate the guards instead. The
duplication is real and is filed as `beadloom-4axf`: closing it means moving this
body into a layer every reader may import, which is a bead of its own and not a
line in a docstring.

What is left is the claim this module can hold: `read_declared_docs`, `link`, and
`init`'s own readers under `onboarding/` and `services/commands/setup.py` — every
node reader outside the `graph` domain — go through one body, and the derivation
in `tests/test_graph_files_are_read_under_one_policy.py` fails on a second one.
"""

# beadloom:domain=onboarding
# beadloom:component=graph-files

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from beadloom.graph.loader import NOT_A_GRAPH_FILE

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

__all__ = ["NOT_A_GRAPH_FILE", "each_graph_file"]


def each_graph_file(
    graph_dir: Path, *, also_skip: frozenset[str] = frozenset()
) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Yield each graph file under *graph_dir* with the mapping it holds.

    THE SKIP POLICY, stated once because there is one of it:

        a file whose name is not a graph file's is skipped; a file that will not
        read or will not parse is skipped; a file that parses to anything other
        than a mapping is skipped. Everything else is yielded as `(path, data)`,
        so a caller may read `data["nodes"]` without asking again whether it can.

    It exists because `init` held FOUR readers of this directory with four skip
    policies — `_load_graph_from_yaml`, `_existing_graph`,
    `_graph_file_of_each_node` and `_patch_docs_field` — and two of them carried
    no guard at all. BDL-067 `.21` removed `generate_skeletons`' node-list
    parameter, so the `--bootstrap` branch stopped passing its own nodes and
    began reading the tree through the unguarded one: on a project carrying a
    hand-edited `.beadloom/_graph/legacy.yml` that does not parse, `init
    --bootstrap` printed a raw `yaml.parser.ParserError` traceback at the
    adopter, while the same commit added exactly that guard to two of the
    siblings and listed it as delivered (the review of `.23`, major 3).

    A file that cannot be read is skipped rather than raised on because of what
    each caller is doing when it meets one. `init` can meet a hand-edited graph
    file, and failing over it replaces a missing edge with a traceback; the
    failure report is being handed to an adopter, and a traceback from the
    reporter is a worse answer than one unattributed node. Both readings are the
    same reading, which is why they are now one body.

    The mapping guard is not the same guard as the parse guard, and it is needed
    separately: a graph file holding a top-level LIST parses without complaint
    and then raises `AttributeError` on `data.get`, which no
    `except yaml.YAMLError` catches.

    *also_skip* is the one difference between the callers, and it is a parameter
    so that it has to be stated at the call site rather than written into a
    second body. `doc_classify._existing_graph` passes `imported.yml`, because
    the run that asks is about to replace that file and the graph it must read is
    the one it will be added to. No other caller has a reason and none passes
    anything.

    A missing directory is no graph files rather than an error: that is the
    virgin case, and it is the common one.
    """
    if not graph_dir.is_dir():
        return
    skip = NOT_A_GRAPH_FILE | also_skip
    for yml in sorted(graph_dir.glob("*.yml")):
        if yml.name in skip:
            continue
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, UnicodeDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        yield yml, data
