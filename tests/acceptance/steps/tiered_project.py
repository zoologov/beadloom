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
    from collections.abc import Mapping
    from pathlib import Path

#: The layering the fixture projects declare, top to bottom.
TIERS = ("tier-web", "tier-core", "tier-store")

#: A SECOND declared layering, whose layer names are the role words a reader of
#: this epic's documents meets — ``application`` / ``domain`` /
#: ``infrastructure`` — carried on tags that are still none of ours (BDL-070 B5,
#: `beadloom-bi78`). The PRD names a scenario about "an import from
#: infrastructure into a domain", and a scenario whose text says
#: *infrastructure* while its fixture declares ``tier-store`` asks a reader to
#: hold a translation in their head. The tags stay foreign, so what is proved is
#: still proved against a declaration and not against a hardcoded vocabulary.
ZONES = ("zone-app", "zone-domain", "zone-infra")

#: The names :data:`ZONES` declares, in the same order.
ZONE_NAMES = ("application", "domain", "infrastructure")

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
    layer_names: tuple[str, ...] | None = None,
    with_layer_rule: bool = True,
    severity: str = "error",
    exempt: str = "",
) -> str:
    """The project's `rules.yml`: one layer rule over *tiers*, or no rule at all.

    *severity* is a parameter because an adopter may declare its layering at
    `warn` — and because a warning the RULE decided is the only way to tell
    that flag's exclusion of Release A's advisories from an exclusion of
    warnings in general (A8 review, Major 1).

    *layer_names* names the layers positionally when the tag is not the name
    with a prefix taken off it. The default keeps `tier-web` reading as `web`,
    and :data:`ZONES` needs the two to differ: a layer whose declared NAME is
    `infrastructure` and whose TAG is `zone-infra` is the pair that shows a
    finding's wording comes from the declaration rather than from the tag.
    """
    if not with_layer_rule:
        return "version: 3\n\nrules: []\n"
    names = layer_names or tuple(tag.removeprefix("tier-") for tag in tiers)
    declared = "\n".join(
        f"      - name: {name}\n        tag: {tag}"
        for name, tag in zip(names, tiers, strict=True)
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


def nodes_yaml(
    nodes: list[Node],
    edges: list[Edge],
    sources: Mapping[str, str] | None = None,
) -> str:
    """The project's `_graph/nodes.yml`.

    *sources* overrides a node's `source` for the nodes it names. A node whose
    source is a FILE rather than a directory is the shape an adopter has the
    moment one module of a package belongs to a component of its own, and the
    import resolver attributes a file to the most specific node that covers it
    — so a fixture that can only build directory-owned nodes cannot exercise
    the attribution an adopter's graph depends on.
    """
    lines = ["nodes:"]
    for ref_id, kind, tags in nodes:
        lines += [
            f"  - ref_id: {ref_id}",
            f"    kind: {kind}",
            f'    summary: "the {ref_id} of a project that is not beadloom"',
            f"    source: {(sources or {}).get(ref_id, f'src/{ref_id}/')}",
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
    layer_names: tuple[str, ...] | None = None,
    with_layer_rule: bool = True,
    severity: str = "error",
    exempt: str = "",
    sources: Mapping[str, str] | None = None,
    modules: Mapping[str, str] | None = None,
) -> Path:
    """Write the project at *root* and index it ONCE, returning *root*.

    The index is built here and nowhere else. Callers read it with `lint(root)`,
    whose default performs no reindex, so the two sides of a before/after
    differential cannot end up looking at two different graphs — a carried
    forward and a fresh index disagree on a population's denominator
    (BDL-UX #290), and a differential in which each side counted a different
    graph measures the index rather than the change.

    *modules* writes real source files, path relative to *root*, AFTER the
    empty package per node — so a module it names replaces that package's
    `__init__.py`. A file written here goes through the indexer's import
    extraction and its `depends_on` edges are DERIVED, which is the path an
    adopter's graph is built on and the one a hand-written `depends_on` edge in
    `nodes.yml` never touches.
    """
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(_CONFIG, encoding="utf-8")
    (graph_dir / "rules.yml").write_text(
        rules_yaml(
            tiers=tiers,
            layer_names=layer_names,
            with_layer_rule=with_layer_rule,
            severity=severity,
            exempt=exempt,
        ),
        encoding="utf-8",
    )
    (graph_dir / "nodes.yml").write_text(nodes_yaml(nodes, edges, sources), encoding="utf-8")
    for ref_id, _kind, _tags in nodes:
        source = (sources or {}).get(ref_id, f"src/{ref_id}/")
        if not source.endswith("/"):
            continue
        package = root / source
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text(f'"""{ref_id}."""\n', encoding="utf-8")
    for relative_path, body in (modules or {}).items():
        module_path = root / relative_path
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_text(body, encoding="utf-8")
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


def graph_with_nested_parts() -> tuple[list[Node], list[Edge]]:
    """Two containers in DIFFERENT tiers, each holding an untagged part.

    The shape this repository's own graph has and an own-tag rule cannot see:
    ``web-api`` and ``store-db`` carry no tag of their own, so every edge
    between them is invisible to a rule that reads own tags only. Through
    ``part_of`` they are in ``tier-web`` and ``tier-store``, which makes
    ``store-db -> web-api`` an edge from the bottom tier into the top one and
    ``web-api -> store-db`` the same dependency the right way round.

    ``root`` carries no tier, so the two containers are not made peers of one
    tagged parent by accident.
    """
    nodes: list[Node] = [
        ("root", "service", []),
        ("web", "domain", [TIERS[0]]),
        ("store", "domain", [TIERS[2]]),
        ("web-api", "component", []),
        ("store-db", "component", []),
    ]
    edges: list[Edge] = [
        ("web", "root", "part_of"),
        ("store", "root", "part_of"),
        ("web-api", "web", "part_of"),
        ("store-db", "store", "part_of"),
        ("web-api", "store-db", "depends_on"),
        ("store-db", "web-api", "depends_on"),
    ]
    return nodes, edges


def graph_with_a_deeper_nest(*, middle_tag: str | None = None) -> tuple[list[Node], list[Edge]]:
    """Parts two `part_of` generations below the container that carries the tier.

    BDL-070 B5 (`beadloom-bi78`). :func:`graph_with_nested_parts` puts each part
    one generation under its tagged container, where the NEAREST tagged
    ancestor and the ONLY tagged ancestor are the same node — so it cannot tell
    a rule that climbs to the nearest from one that climbs to the last. Here
    ``web-api-handlers`` is inside ``web-api`` is inside ``web``, and
    ``store-db-pool`` is inside ``store-db`` is inside ``store``.

    With *middle_tag* the intermediate ``web-api`` carries a tier of its own, so
    the two readings give DIFFERENT answers rather than the same answer by
    different routes: passing ``TIERS[2]`` puts ``web-api-handlers`` in the
    bottom tier beside ``store-db-pool``, which turns the upward edge between
    them into a same-layer crossing — a different finding, not a different
    message.
    """
    nodes: list[Node] = [
        ("root", "service", []),
        ("web", "domain", [TIERS[0]]),
        ("store", "domain", [TIERS[2]]),
        ("web-api", "component", [middle_tag] if middle_tag else []),
        ("web-api-handlers", "component", []),
        ("store-db", "component", []),
        ("store-db-pool", "component", []),
    ]
    edges: list[Edge] = [
        ("web", "root", "part_of"),
        ("store", "root", "part_of"),
        ("web-api", "web", "part_of"),
        ("web-api-handlers", "web-api", "part_of"),
        ("store-db", "store", "part_of"),
        ("store-db-pool", "store-db", "part_of"),
        ("store-db-pool", "web-api-handlers", "depends_on"),
        ("web-api-handlers", "store-db-pool", "depends_on"),
    ]
    return nodes, edges


def graph_with_a_part_that_declares_its_own_tier() -> tuple[list[Node], list[Edge]]:
    """A part carrying a tier its container does not, and two edges that tell which won.

    ``web-cache`` is ``part_of`` ``web`` — the top tier — and carries the bottom
    tier itself. The rule keeps a node's own tag and does not climb, so both
    edges below are findings; under inheritance both would be legal, which is
    what makes them a discriminator rather than a demonstration:

    - ``web-cache -> web-api`` runs from the bottom tier to the top and is a
      direction violation. Inherited, both ends would be in the top tier inside
      one container, and legal.
    - ``web-cache -> store-db`` runs between two nodes in the bottom tier with
      no shared tagged container, and is a same-layer crossing. Inherited,
      ``web-cache`` would be in the top tier and the edge would run downward,
      and legal.

    ``web-api -> web-cache`` is the control: legal under either reading, so a
    test can show that keeping the own tag does not report everything.
    """
    nodes: list[Node] = [
        ("root", "service", []),
        ("web", "domain", [TIERS[0]]),
        ("store", "domain", [TIERS[2]]),
        ("web-api", "component", []),
        ("web-cache", "component", [TIERS[2]]),
        ("store-db", "component", []),
    ]
    edges: list[Edge] = [
        ("web", "root", "part_of"),
        ("store", "root", "part_of"),
        ("web-api", "web", "part_of"),
        ("web-cache", "web", "part_of"),
        ("store-db", "store", "part_of"),
        ("web-cache", "web-api", "depends_on"),
        ("web-api", "web-cache", "depends_on"),
        ("web-cache", "store-db", "depends_on"),
    ]
    return nodes, edges


#: The modules of :func:`write_zoned_import_project`, keyed by path under the
#: project root. ``catalog`` declares the value; the other two import it, so
#: every ``depends_on`` edge in that project is derived from a real import
#: statement by the real indexer.
_ZONED_MODULES = {
    "src/catalog/__init__.py": '"""The catalogue this project sells from."""\n\nPRICE_LIST = ()\n',
    "src/checkout/__init__.py": (
        '"""Checkout, in the application layer, reading the catalogue below it."""\n\n'
        "from catalog import PRICE_LIST\n\n"
        '__all__ = ["PRICE_LIST"]\n'
    ),
    "src/storage/__init__.py": '"""Storage, in the infrastructure layer."""\n',
    "src/storage/pool.py": (
        '"""The connection pool, which has no business knowing what is for sale."""\n\n'
        "from catalog import PRICE_LIST\n\n"
        '__all__ = ["PRICE_LIST"]\n'
    ),
}


def write_zoned_import_project(root: Path) -> Path:
    """A project whose every `depends_on` edge is DERIVED from a Python import.

    BDL-070 B5 (`beadloom-bi78`), for the PRD's scenario *an import from
    infrastructure into a domain is reported*. `nodes.yml` declares `part_of`
    and nothing else: the two dependencies come from `import` statements the
    indexer reads, which is the path an adopter's graph is actually built on.

    The layering is declared as :data:`ZONE_NAMES` over :data:`ZONES`, so the
    finding says *layer 'infrastructure'* while the tag on the node says
    ``zone-infra`` — a message that repeated the tag would read the same under
    an implementation that never opened the declaration.

    ``storage-pool`` owns the single FILE `src/storage/pool.py` and carries no
    tag, so the reported edge leaves a node whose layer is inherited from the
    container two facts away: the file's owning node, and that node's tagged
    parent.
    """
    nodes: list[Node] = [
        ("platform", "service", []),
        ("checkout", "feature", [ZONES[0]]),
        ("catalog", "domain", [ZONES[1]]),
        ("storage", "domain", [ZONES[2]]),
        ("storage-pool", "component", []),
    ]
    edges: list[Edge] = [
        ("checkout", "platform", "part_of"),
        ("catalog", "platform", "part_of"),
        ("storage", "platform", "part_of"),
        ("storage-pool", "storage", "part_of"),
    ]
    return write_tiered_project(
        root,
        nodes=nodes,
        edges=edges,
        tiers=ZONES,
        layer_names=ZONE_NAMES,
        sources={"storage-pool": "src/storage/pool.py"},
        modules=_ZONED_MODULES,
    )
