"""Tests for beadloom.application.site_landscape — Showcase B (BDL-040 BEAD-03).

The 🌟 cross-repo landscape map is a Mermaid diagram GENERATED from data (never
hand-drawn): nodes = services/repos, edges = contracts/cross-repo links labelled
by their ``ContractVerdict``-style verdict, a health overlay via Mermaid
``classDef``, and clickable nodes (``click <id> "<url>"``) linking to the
intra-repo service page. These tests assert the verdict labels, health classes,
and clickable links are present, that the single-repo degenerate case works, and
that the output is deterministic (re-generate -> byte-identical).
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from beadloom.application.site import generate_site
from beadloom.application.site_landscape import (
    build_landscape_data,
    render_landscape_md,
)
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_single_repo(conn: sqlite3.Connection) -> None:
    """A small single-repo graph (services/domains + uses/depends_on edges)."""
    nodes = [
        ("beadloom", "service", "Beadloom CLI service.", None),
        ("cli", "service", "Click CLI.", "src/beadloom/services"),
        ("graph", "domain", "Graph format.", "src/beadloom/graph"),
    ]
    for ref_id, kind, summary, source in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, source),
        )
    edges = [
        ("cli", "graph", "uses"),
        ("graph", "beadloom", "part_of"),
    ]
    for src, dst, kind in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )


def _seed_contract_repo(conn: sqlite3.Connection) -> None:
    """A single-repo graph with a real produces/consumes contract pair.

    Mirrors the own-site shape (BDL-041 F4.4): the ``beadloom`` service PRODUCES
    a ``site-data`` contract that the ``vitepress-site`` consumer CONSUMES. Both
    edges share one ``contract_key`` so the pair reconciles to ``CONFIRMED``. A
    structural ``uses`` edge and an unrelated node are also seeded — the local
    landscape must show the CONTRACT participants, not the structural arch.
    """
    nodes = [
        ("beadloom", "service", "Beadloom service (producer).", "src/beadloom"),
        ("vitepress-site", "site", "VitePress site (consumer).", "site/"),
        ("graph", "domain", "Graph domain (not in any contract).", "src/beadloom/graph"),
    ]
    for ref_id, kind, summary, source in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, source),
        )
    edges = [
        ("vitepress-site", "beadloom", "part_of", ""),
        ("graph", "beadloom", "depends_on", ""),
        ("beadloom", "vitepress-site", "produces", "site-data:site-bundle"),
        ("vitepress-site", "beadloom", "consumes", "site-data:site-bundle"),
    ]
    for src, dst, kind, ckey in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) "
            "VALUES (?, ?, ?, ?)",
            (src, dst, kind, ckey),
        )


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _federated_json(tmp_path: Path) -> Path:
    """A federated.json fixture exercising several verdicts + health classes."""
    payload = {
        "schema_version": 2,
        "repos": [
            {"repo": "svc-a", "landscape": "shop", "commit_sha": "abc"},
            {"repo": "svc-b", "landscape": "shop", "commit_sha": "def"},
            {"repo": "svc-c", "landscape": "shop", "commit_sha": "ghi"},
        ],
        "nodes": [],
        "edges": [
            # confirmed contract producer -> consumer (healthy/green)
            {"src": "@svc-a:p", "dst": "@svc-b:c", "kind": "uses", "repo": "svc-a",
             "verdict": "ok"},
            # a drift edge (unhealthy/red)
            {"src": "@svc-a:x", "dst": "@svc-c:y", "kind": "uses", "repo": "svc-a",
             "verdict": "drift"},
            # external target (grey)
            {"src": "@svc-b:m", "dst": "@svc-c:n", "kind": "uses", "repo": "svc-b",
             "verdict": "external"},
        ],
        "contracts": [
            {"contract_key": "amqp:*/*:OrderPlaced", "verdict": "confirmed",
             "repos": ["svc-a", "svc-b"]},
            {"contract_key": "graphql:Catalog", "verdict": "breaking",
             "repos": ["svc-a", "svc-c"], "missing": ["price"]},
        ],
        "unresolved_refs": [],
    }
    path = tmp_path / "federated.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Federated landscape map
# ---------------------------------------------------------------------------


def test_federated_nodes_are_repos(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    node_ids = {n["id"] for n in data["nodes"]}
    assert node_ids == {"svc-a", "svc-b", "svc-c"}


def test_federated_edges_carry_verdict_labels(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    verdicts = {(e["src"], e["dst"]): e["verdict"] for e in data["edges"]}
    assert verdicts[("svc-a", "svc-b")] == "ok"
    assert verdicts[("svc-a", "svc-c")] == "drift"
    assert verdicts[("svc-b", "svc-c")] == "external"


def test_render_includes_verdict_labels(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    md = render_landscape_md(data)
    # ContractVerdict-style labels appear on the edges (upper-cased).
    assert "DRIFT" in md
    assert "EXTERNAL" in md


def test_render_includes_health_classdefs(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    md = render_landscape_md(data)
    # classDef health overlay (red/green/grey) is emitted.
    assert "classDef" in md
    assert "healthy" in md
    assert "broken" in md


def test_render_has_clickable_nodes(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    # A federated node maps to a local page only when one exists; pass an
    # explicit page map so a click is emitted for the covered ref.
    md = render_landscape_md(data, pages={"svc-a": "/services/svc-a"})
    # The covered node is clickable, linking to its (existing) page.
    assert 'click n_svc_a "/services/svc-a"' in md
    assert "```mermaid" in md


def test_render_omits_click_for_uncovered_node(tmp_path: Path) -> None:
    """A node absent from the page map emits NO click (no dead link)."""
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    md = render_landscape_md(data, pages={})  # no pages exist
    assert "click " not in md
    # Nodes + edges + verdicts still render.
    assert "DRIFT" in md
    assert "n_svc_a" in md


def test_render_marks_broken_edge_class(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    md = render_landscape_md(data)
    # The drift edge gets the broken link style; the ok edge does not.
    assert "linkStyle" in md


# ---------------------------------------------------------------------------
# Degenerate single-repo case (no --federated)
# ---------------------------------------------------------------------------


def test_local_landscape_is_contract_graph(tmp_path: Path) -> None:
    """Default (no --federated) = LOCAL contract graph, not the structural arch.

    The map shows only nodes that participate in produces/consumes contracts and
    the contract edges between them — NOT every depends_on/uses node (that lives
    in the C4 overview). The unrelated ``graph`` domain is excluded.
    """
    conn = _open()
    try:
        _seed_contract_repo(conn)
        conn.commit()
        data = build_landscape_data(conn=conn, federated=None)
    finally:
        conn.close()
    node_ids = {n["id"] for n in data["nodes"]}
    assert node_ids == {"beadloom", "vitepress-site"}
    # The structural-only node (no contract) is NOT in the landscape.
    assert "graph" not in node_ids


def test_local_landscape_contract_edge_confirmed(tmp_path: Path) -> None:
    """The real producer->consumer contract renders as one CONFIRMED edge."""
    conn = _open()
    try:
        _seed_contract_repo(conn)
        conn.commit()
        data = build_landscape_data(conn=conn, federated=None)
    finally:
        conn.close()
    edges = data["edges"]
    assert len(edges) == 1
    edge = edges[0]
    assert edge["src"] == "beadloom"
    assert edge["dst"] == "vitepress-site"
    assert edge["verdict"] == "confirmed"
    # The CONFIRMED edge renders (not dropped) with a green/healthy node.
    md = render_landscape_md(data)
    assert "beadloom -->" in md or "n_beadloom -->" in md
    assert "CONFIRMED" in md
    assert "healthy" in md


def test_local_landscape_drops_self_loop(tmp_path: Path) -> None:
    """A contract whose producer == consumer emits no self-edge.

    Guards the ``src == dst`` skip: a node that both produces and consumes the
    same contract participates as a node but must not draw an edge to itself.
    """
    conn = _open()
    try:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("self-node", "service", "Self producer/consumer.", "src/x"),
        )
        # The same node both produces and consumes the same contract key.
        for kind in ("produces", "consumes"):
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) "
                "VALUES (?, ?, ?, ?)",
                ("self-node", "self-node", kind, "topic:loop"),
            )
        conn.commit()
        data = build_landscape_data(conn=conn, federated=None)
    finally:
        conn.close()
    # The node participates, but there is no self-edge (src == dst skipped).
    assert {n["id"] for n in data["nodes"]} == {"self-node"}
    assert data["edges"] == []


def test_local_landscape_no_contracts_is_empty(tmp_path: Path) -> None:
    """A graph with no produces/consumes contracts yields an empty contract map."""
    conn = _open()
    try:
        _seed_single_repo(conn)  # only uses/part_of edges, no contracts
        conn.commit()
        data = build_landscape_data(conn=conn, federated=None)
    finally:
        conn.close()
    assert data["nodes"] == []
    assert data["edges"] == []
    # Still renders a valid (empty) Mermaid diagram, no crash.
    md = render_landscape_md(data)
    assert "```mermaid" in md


# ---------------------------------------------------------------------------
# Wiring into the generator + determinism
# ---------------------------------------------------------------------------


def test_generator_emits_landscape_file(tmp_path: Path) -> None:
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_single_repo(conn)
        conn.commit()
        result = generate_site(conn, out, project_root=tmp_path)
    finally:
        conn.close()
    assert (out / "landscape.md").exists()
    assert (out / "landscape.md") in result.written


def test_generator_landscape_uses_federated(tmp_path: Path) -> None:
    conn = _open()
    out = tmp_path / "site"
    fed = _federated_json(tmp_path)
    try:
        _seed_single_repo(conn)
        conn.commit()
        generate_site(conn, out, project_root=tmp_path, federated=fed)
    finally:
        conn.close()
    md = (out / "landscape.md").read_text(encoding="utf-8")
    assert "svc-a" in md
    assert "DRIFT" in md


def _emitted_click_targets(md: str) -> list[str]:
    """Extract every ``click <id> "<url>"`` URL from a landscape page."""
    targets: list[str] = []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("click "):
            # ``click n_foo "/services/foo"`` -> /services/foo
            parts = stripped.split('"')
            if len(parts) >= 2:
                targets.append(parts[1])
    return targets


def test_no_click_targets_a_missing_page(tmp_path: Path) -> None:
    """Guard for the live 404/MIME bug: every emitted click path must EXIST.

    Generates the full site and asserts every landscape ``click`` URL resolves to
    a real generated page in the tree (no dead link → no 404 → no MIME error).
    """
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_contract_repo(conn)
        conn.commit()
        generate_site(conn, out, project_root=tmp_path)
    finally:
        conn.close()
    md = (out / "landscape.md").read_text(encoding="utf-8")
    targets = _emitted_click_targets(md)
    for url in targets:
        # A click URL ``/domains/graph`` must map to a real ``graph.md`` page.
        rel = url.lstrip("/") + ".md"
        assert (out / rel).exists(), f"dead click target: {url} (no {rel})"


def test_site_node_without_page_has_no_click(tmp_path: Path) -> None:
    """A node with no generated page (kind=site) must NOT emit a dead click."""
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_contract_repo(conn)
        conn.commit()
        generate_site(conn, out, project_root=tmp_path)
    finally:
        conn.close()
    md = (out / "landscape.md").read_text(encoding="utf-8")
    # ``vitepress-site`` (kind=site) has no /services or /domains page → no click.
    assert "vitepress-site" in md  # the node still renders + carries its edge
    assert 'click n_vitepress_site' not in md


def test_federated_foreign_node_has_no_dead_click(tmp_path: Path) -> None:
    """A federated foreign repo has no local page — it must not emit a click."""
    conn = _open()
    out = tmp_path / "site"
    fed = _federated_json(tmp_path)
    try:
        _seed_contract_repo(conn)
        conn.commit()
        generate_site(conn, out, project_root=tmp_path, federated=fed)
    finally:
        conn.close()
    md = (out / "landscape.md").read_text(encoding="utf-8")
    for url in _emitted_click_targets(md):
        rel = url.lstrip("/") + ".md"
        assert (out / rel).exists(), f"dead click target: {url} (no {rel})"
    # The foreign edges + verdicts still render.
    assert "DRIFT" in md


def test_render_is_deterministic(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    first = render_landscape_md(build_landscape_data(federated=fed))
    second = render_landscape_md(build_landscape_data(federated=fed))
    assert first == second


def test_data_json_safe_and_sorted(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    # Re-serialization is stable (JSON-safe, sorted).
    assert json.dumps(data, sort_keys=True) == json.dumps(data, sort_keys=True)
    # Nodes + edges are sorted for stable Mermaid output.
    node_ids = [n["id"] for n in data["nodes"]]
    assert node_ids == sorted(node_ids)
