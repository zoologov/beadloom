"""The one policy every reader of `.beadloom/_graph/` holds."""

# beadloom:domain=onboarding
# beadloom:component=graph-files

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The file in `.beadloom/_graph/` that is not a graph file. `rules.yml` holds
#: rules and no nodes, so a reader that walked it would either find nothing or
#: mistake a rule for a node. Every reader skipped it before this module existed
#: and none of them had a reason of its own for doing so, which is why it is the
#: policy rather than a parameter of it.
NOT_A_GRAPH_FILE = frozenset({"rules.yml"})


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
