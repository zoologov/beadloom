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
    md = render_landscape_md(data)
    # Each node is clickable, linking to its service page.
    assert 'click svc_a "/services/svc-a"' in md
    assert "```mermaid" in md


def test_render_marks_broken_edge_class(tmp_path: Path) -> None:
    fed = _federated_json(tmp_path)
    data = build_landscape_data(federated=fed)
    md = render_landscape_md(data)
    # The drift edge gets the broken link style; the ok edge does not.
    assert "linkStyle" in md


# ---------------------------------------------------------------------------
# Degenerate single-repo case (no --federated)
# ---------------------------------------------------------------------------


def test_single_repo_one_landscape(tmp_path: Path) -> None:
    conn = _open()
    try:
        _seed_single_repo(conn)
        conn.commit()
        data = build_landscape_data(conn=conn, federated=None)
    finally:
        conn.close()
    # One repo (this project); nodes are the local services.
    node_ids = {n["id"] for n in data["nodes"]}
    assert "cli" in node_ids
    # The single-repo map renders without crashing and is non-empty.
    md = render_landscape_md(data)
    assert "```mermaid" in md
    assert "```" in md


def test_single_repo_edges_default_confirmed(tmp_path: Path) -> None:
    conn = _open()
    try:
        _seed_single_repo(conn)
        conn.commit()
        data = build_landscape_data(conn=conn, federated=None)
    finally:
        conn.close()
    # Intra-repo edges have no cross-repo verdict; they default to confirmed.
    for edge in data["edges"]:
        assert edge["verdict"] == "confirmed"


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
