"""The parent post-condition every writer of graph nodes holds."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import Any


def parented_by(edges: list[dict[str, Any]]) -> set[str]:
    """The ref_ids *edges* already give a parent.

    Only a `part_of` edge is a parent. That is not a stylistic choice: it is what
    `domain-needs-parent` requires, so an edge of any other kind leaves the node
    it leaves in violation of the rule the same command wrote.

    Both callers of `missing_parent_edges` answer its `parented` question by
    reading edges — `bootstrap_project` the ones it is about to write,
    `doc_classify._existing_graph` the ones already on disk — so the source
    differs and the question does not. Left as a comprehension at each call site
    the kind filter was untestable: the bootstrap writes no edge of another kind
    before it holds the post-condition, so deleting the filter there would keep
    every end-to-end case green.

    An edge with no `src` names nobody: a hand-edited graph file can hold a
    half-written edge, and the importer must skip it rather than raise on it.
    Sources are named as strings for the reason `missing_parent_edges` names
    ref_ids as strings — YAML loads a document called `2024.md` as an int.
    """
    return {
        str(edge["src"])
        for edge in edges
        if edge.get("kind") == "part_of" and edge.get("src")
    }


def missing_parent_edges(
    nodes: list[dict[str, Any]],
    root_ref_id: str,
    parented: set[str],
) -> list[dict[str, str]]:
    """Name the `part_of` edges *nodes* are still short of, given *parented*.

    THE POST-CONDITION, stated once because there is one of it:

        every node a writer commits to `.beadloom/_graph/` carries at least one
        outgoing `part_of` edge — to the parent its classifier chose where there
        is one, and to the root otherwise.

    It exists because `generate_rules` writes `domain-needs-parent` at error
    severity into the same `rules.yml`, in the same command, so a node written
    without the edge fails a rule its own author wrote one step earlier: `init`
    exited 0 and `beadloom ci` exited 1 (BDL-UX #192).

    *parented* is the caller's answer to "which ref_ids already have a parent",
    and it is the only thing the two writers do differently. `bootstrap_project`
    reads it off the edges it is about to write, because it is producing the
    whole graph; `import_docs` reads it off the graph already on disk, because it
    is adding to one. Passing it in is what let those two facts stay each
    caller's own while the rule over them stayed one function. The set is copied
    rather than added to: it describes the graph as the caller found it, and a
    caller that got it back describing nodes only about to be written would be
    told a different thing than it asked.

    Two nodes are deliberately left alone. One that is already parented keeps the
    parent its classifier chose — the root is the fallback, never an override.
    One whose ref_id is the root's own gets nothing, because an edge from a node
    to itself is not a parent; that collision is reachable, since the classic
    `src/<project>/` layout hands the root service and the single domain the same
    ref_id (tracked on its own as `beadloom-7c6k`, since its fix is a unique
    ref_id and not an edge).

    The pass ranges over every KIND, not over the kinds today's generated rules
    require a parent for. A post-condition that tracked the current rule set
    would go stale the next time a rule is added, which is how this epic's first
    fix came to need a second one — and the two copies of this function disagreed
    about exactly that for three waves (the review of BDL-067 `.16`, minor 2).

    *root_ref_id* must be the value written into the root node, not a name
    recomputed from the project: cluster refs pass through `_sanitize_ref_id` and
    the root ref does not, so a recomputed destination silently resolves to
    nothing for a project whose name contains parentheses (BDL-067 `.1`).

    Ref_ids are named as strings because a graph file on disk need not hold
    them as strings: YAML loads a document called `2024.md` as an int, and an
    edge whose `src` is an int does not match the node whose ref_id is one.
    """
    edges: list[dict[str, str]] = []
    seen = set(parented)
    for node in nodes:
        ref_id = str(node["ref_id"])
        if ref_id == root_ref_id or ref_id in seen:
            continue
        edges.append({"src": ref_id, "dst": root_ref_id, "kind": "part_of"})
        seen.add(ref_id)
    return edges
