"""Two small indexed projects every surface that states a layer rule's population reads.

Moved out of ``test_every_surface_past_lint_states_the_population.py`` when BDL-074 E1
split it by node: the rule engine's phrase, the Gate line, the MCP tool, the TUI
panel, the debt report and ``prime`` each read the same two projects, and a helper
two test modules share lives here rather than in either of them.

``partly_layered`` is the smallest graph whose layer rule reaches half the edges it
is handed — ``svc -> dom`` carries a declared tag at both ends, ``widget -> helper``
carries none — so every surface has the same ``1 of 2`` to state. ``unlayered``
declares no layer rule, so every surface has nothing to state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.reindex import incremental_reindex

if TYPE_CHECKING:
    from pathlib import Path

#: The layer rule both projects are judged by, as ``rules.yml`` spells it.
LAYER_RULE = (
    "  - name: architecture-layers\n"
    '    description: "Services -> domains, not the reverse"\n'
    "    severity: error\n"
    "    layers:\n"
    "      - name: services\n"
    "        tag: layer-service\n"
    "      - name: domains\n"
    "        tag: layer-domain\n"
    "    enforce: top-down\n"
    "    allow_skip: true\n"
    "    edge_kind: depends_on\n"
)

#: What the rule judged on the partly layered project, spelled once. `svc -> dom`
#: carries a declared tag at both ends; `widget -> helper` carries none, so the rule
#: passes over it. 1 of 2 is the whole point of BDL-070 at a size a reader can hold.
THE_PHRASE = "architecture-layers judged 1 of 2 live depends_on edge(s)"

#: The graph of the partly layered project.
PARTLY_LAYERED_GRAPH = (
    "nodes:\n"
    "  - ref_id: svc\n    kind: service\n    summary: A service\n"
    "    tags: [layer-service]\n"
    "  - ref_id: dom\n    kind: domain\n    summary: A domain\n"
    "    tags: [layer-domain]\n"
    "  - ref_id: widget\n    kind: feature\n    summary: An untagged feature\n"
    "  - ref_id: helper\n    kind: feature\n    summary: Another untagged feature\n"
    "edges:\n"
    "  - src: svc\n    dst: dom\n    kind: depends_on\n"
    "  - src: widget\n    dst: helper\n    kind: depends_on\n"
)


def write_partly_layered_project(root: Path) -> Path:
    """A project whose layer rule reaches half the edges it is handed, indexed.

    ``rules.yml`` is written TWICE, and the duplicate is a defect BDL-070 A4 found
    rather than a convenience. Every reader in the product resolves
    ``.beadloom/_graph/rules.yml``; ``debt_report/collect.py`` resolves
    ``<root>/rules.yml`` and then ``<root>/.beadloom/rules.yml``, neither of which
    exists in a standard layout, so its rule-violation counts are zero on every
    project. The second copy is what makes the debt surface reachable at all;
    ``TestTheDebtReportReadsRulesFromAPlaceNobodyWritesThem`` holds the defect so it
    fails loudly when it is fixed.
    """
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(PARTLY_LAYERED_GRAPH)
    rules = f"version: 1\nrules:\n{LAYER_RULE}"
    (graph_dir / "rules.yml").write_text(rules)
    (root / "rules.yml").write_text(rules)
    (root / "docs").mkdir()
    incremental_reindex(root)
    return root


def write_unlayered_project(root: Path) -> Path:
    """A project that declares no layer rule, indexed — every surface stays silent."""
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: billing\n    kind: domain\n    summary: Billing\n"
        "  - ref_id: auth\n    kind: domain\n    summary: Auth\n"
        "edges: []\n"
    )
    rules = (
        "version: 1\n"
        "rules:\n"
        "  - name: billing-no-auth\n"
        '    description: "Billing must not import auth"\n'
        "    deny:\n"
        "      from: { ref_id: billing }\n"
        "      to: { ref_id: auth }\n"
    )
    (graph_dir / "rules.yml").write_text(rules)
    (root / "rules.yml").write_text(rules)
    (root / "docs").mkdir()
    incremental_reindex(root)
    return root
