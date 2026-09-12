"""A whole beadloom project whose layering is NOT this repository's.

BDL-070 A7 (`beadloom-cfkk`). Every layer claim this epic makes is measured on
at least one graph that is not ours, because this repository hides the shapes an
adopter meets — it declares four `layer-*` tags and puts them on its domains,
and a check that only ever ran here could hardcode all four and still be green.
Both BDL-069 blockers survived exactly that way.

So the projects built here declare `tier-web` / `tier-core` / `tier-store`,
three tags that appear nowhere under `src/`. A test that passes against this
vocabulary passed because the code read the declaration.

The builder writes a real project directory — `config.yml`, `_graph/rules.yml`,
`_graph/nodes.yml` and one Python package per node — and indexes it with the
real reindex. Nothing here constructs a database by hand: a fixture assembled
out of `INSERT` statements proves what the test author believed the indexer
writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.reindex import reindex

if TYPE_CHECKING:
    from pathlib import Path

#: The layering the fixture projects declare, top to bottom.
TIERS = ("tier-web", "tier-core", "tier-store")

#: The tag prefix THIS repository's own layering uses. Asserted absent from the
#: fixtures, so a claim proved over them is a claim about a foreign declaration.
OUR_LAYER_PREFIX = "layer-"

#: ``(ref_id, kind, tags)``.
Node = tuple[str, str, list[str]]

#: ``(src, dst, kind)``.
Edge = tuple[str, str, str]

_CONFIG = "languages:\n- .py\nscan_paths:\n- src\n"


def rules_yaml(
    *,
    tiers: tuple[str, ...] = TIERS,
    with_layer_rule: bool = True,
    severity: str = "error",
    exempt: str = "",
) -> str:
    """The project's `rules.yml`: one layer rule over *tiers*, or no rule at all.

    *severity* is a parameter because an adopter may declare its layering at
    `warn` — and because a warning the RULE decided is the only way to tell
    that flag's exclusion of Release A's advisories from an exclusion of
    warnings in general (A8 review, Major 1).
    """
    if not with_layer_rule:
        return "version: 3\n\nrules: []\n"
    declared = "\n".join(
        f"      - name: {tag.removeprefix('tier-')}\n        tag: {tag}" for tag in tiers
    )
    return (
        "version: 3\n\n"
        "rules:\n"
        "  - name: tier-order\n"
        '    description: "web -> core -> store, and never the other way"\n'
        f"    severity: {severity}\n"
        "    layers:\n"
        f"{declared}\n"
        "    enforce: top-down\n"
        "    allow_skip: true\n"
        "    edge_kind: depends_on\n" + exempt
    )


def nodes_yaml(nodes: list[Node], edges: list[Edge]) -> str:
    """The project's `_graph/nodes.yml`."""
    lines = ["nodes:"]
    for ref_id, kind, tags in nodes:
        lines += [
            f"  - ref_id: {ref_id}",
            f"    kind: {kind}",
            f'    summary: "the {ref_id} of a project that is not beadloom"',
            f"    source: src/{ref_id}/",
        ]
        if tags:
            lines.append(f"    tags: [{', '.join(tags)}]")
    lines.append("edges:")
    for src, dst, kind in edges:
        lines += [f"  - src: {src}", f"    dst: {dst}", f"    kind: {kind}"]
    return "\n".join(lines) + "\n"


def write_tiered_project(
    root: Path,
    *,
    nodes: list[Node],
    edges: list[Edge],
    tiers: tuple[str, ...] = TIERS,
    with_layer_rule: bool = True,
    severity: str = "error",
    exempt: str = "",
) -> Path:
    """Write the project at *root* and index it ONCE, returning *root*.

    The index is built here and nowhere else. Callers read it with `lint(root)`,
    whose default performs no reindex, so the two sides of a before/after
    differential cannot end up looking at two different graphs — a carried
    forward and a fresh index disagree on a population's denominator
    (BDL-UX #290), and a differential in which each side counted a different
    graph measures the index rather than the change.
    """
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(_CONFIG, encoding="utf-8")
    (graph_dir / "rules.yml").write_text(
        rules_yaml(
            tiers=tiers,
            with_layer_rule=with_layer_rule,
            severity=severity,
            exempt=exempt,
        ),
        encoding="utf-8",
    )
    (graph_dir / "nodes.yml").write_text(nodes_yaml(nodes, edges), encoding="utf-8")
    for ref_id, _kind, _tags in nodes:
        package = root / "src" / ref_id
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text(f'"""{ref_id}."""\n', encoding="utf-8")
    reindex(root)
    return root


def graph_with(*, tiered_edges: int, untiered_edges: int) -> tuple[list[Node], list[Edge]]:
    """A graph with exactly the two edge counts a population statement reports.

    *tiered_edges* `depends_on` edges carry a declared tier at BOTH ends and are
    the population the rule judges; *untiered_edges* carry one at neither end and
    are what it passes over. Each tiered edge runs between ADJACENT tiers in
    declaration order, so the graph is legal under `enforce: top-down` — a
    scenario about counting must not also be a scenario about violating.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    steps = len(TIERS) - 1
    for index in range(tiered_edges):
        upper, lower = TIERS[index % steps], TIERS[index % steps + 1]
        nodes += [(f"a{index}", "domain", [upper]), (f"b{index}", "domain", [lower])]
        edges.append((f"a{index}", f"b{index}", "depends_on"))
    for index in range(untiered_edges):
        nodes += [(f"u{index}", "component", []), (f"v{index}", "component", [])]
        edges.append((f"u{index}", f"v{index}", "depends_on"))
    return nodes, edges


def graph_with_peer_containers() -> tuple[list[Node], list[Edge]]:
    """Two containers in ONE tier, each holding a part, and three edges between parts.

    ``ledger`` and ``postings`` both carry the middle tier and are ``part_of``
    ``root``, which carries none — the shape this repository has, where every
    domain sits under an untagged root service. So ``ledger-api -> ledger-store``
    is internal to one container and ``ledger-api -> postings-api`` crosses
    between peers, which is the pair BDL-070 RFC Q1's predicate exists to tell
    apart. ``postings-api -> ledger-api`` is the same crossing in the other
    direction, so a scenario can show that excusing one does not excuse both.
    """
    nodes: list[Node] = [
        ("root", "service", []),
        ("ledger", "domain", [TIERS[1]]),
        ("postings", "domain", [TIERS[1]]),
        ("ledger-api", "component", []),
        ("ledger-store", "component", []),
        ("postings-api", "component", []),
    ]
    edges: list[Edge] = [
        ("ledger", "root", "part_of"),
        ("postings", "root", "part_of"),
        ("ledger-api", "ledger", "part_of"),
        ("ledger-store", "ledger", "part_of"),
        ("postings-api", "postings", "part_of"),
        ("ledger-api", "ledger-store", "depends_on"),
        ("ledger-api", "postings-api", "depends_on"),
        ("postings-api", "ledger-api", "depends_on"),
    ]
    return nodes, edges
