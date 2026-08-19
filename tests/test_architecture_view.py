"""Tests for beadloom.application.architecture_view — the interactive arch graph.

The architecture top-level diagram (formerly a Mermaid mess) is now rendered with
the SAME Cytoscape+ELK viz the landscape uses, fed a deterministic,
renderer-agnostic ``architecture.data.json``. These tests assert the artifact
carries the LOCAL graph honestly: nodes (kind/summary/layer/symbol-count/
doc-status/lint-clean + page url + doc links) and edges (``depends_on`` solid +
``part_of`` containment for the ELK compound layout). Honest degradation: a node
with no doc gets no fabricated link; absent lint/coverage is omitted, not faked.
Determinism: every section is sorted and the payload is byte-stable.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from beadloom.application.architecture_view import (
    build_architecture_view_data,
    render_architecture_view_md,
    serialize_architecture_view,
)
from beadloom.application.site import generate_site
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _add_node(
    conn: sqlite3.Connection,
    ref_id: str,
    kind: str,
    source: str | None,
    *,
    layer_tag: str | None = None,
) -> None:
    extra = json.dumps({"tags": [layer_tag]}) if layer_tag else "{}"
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, kind, f"{ref_id} summary.", source, extra),
    )


def _add_edge(conn: sqlite3.Connection, src: str, dst: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src, dst, kind),
    )


def _add_symbol(conn: sqlite3.Connection, file_path: str, name: str, line: int) -> None:
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, file_hash) "
        "VALUES (?, ?, 'function', ?, ?, 'h')",
        (file_path, name, line, line + 1),
    )


def _add_doc(conn: sqlite3.Connection, path: str, kind: str, ref_id: str) -> None:
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, 'h')",
        (path, kind, ref_id),
    )


def _mark_stale(conn: sqlite3.Connection, ref_id: str, doc: str, code: str) -> None:
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        "synced_at, status) VALUES (?, ?, ?, 'c', 'd', 't', 'stale')",
        (doc, code, ref_id),
    )


def _seed_arch(conn: sqlite3.Connection) -> None:
    """A small but representative local-architecture corpus across all layers.

    - ``beadloom`` (service, root) — part_of parent of the domains.
    - ``application`` (domain, layer-application) depends_on ``graph`` (domain).
    - ``graph`` (domain, layer-domain) depends_on ``infrastructure`` (layer-infra).
    - ``site-generation`` (feature) part_of ``application`` (compound containment).
    - ``application`` has a fresh doc; ``graph`` has a STALE doc (doc-status honest).
    - ``infrastructure`` has NO doc (honest: no fabricated link).
    """
    _add_node(conn, "beadloom", "service", None, layer_tag="layer-service")
    _add_node(
        conn, "application", "domain", "src/beadloom/application/",
        layer_tag="layer-application",
    )
    _add_node(conn, "graph", "domain", "src/beadloom/graph/", layer_tag="layer-domain")
    _add_node(
        conn, "infrastructure", "domain", "src/beadloom/infrastructure/",
        layer_tag="layer-infra",
    )
    _add_node(conn, "site-generation", "feature", "src/beadloom/application/site.py")

    # Containment (part_of) + dependency (depends_on).
    _add_edge(conn, "application", "beadloom", "part_of")
    _add_edge(conn, "graph", "beadloom", "part_of")
    _add_edge(conn, "infrastructure", "beadloom", "part_of")
    _add_edge(conn, "site-generation", "application", "part_of")
    _add_edge(conn, "application", "graph", "depends_on")
    _add_edge(conn, "graph", "infrastructure", "depends_on")

    # Symbols (drive the symbol count); two public + one private under application.
    _add_symbol(conn, "src/beadloom/application/site.py", "generate_site", 1)
    _add_symbol(conn, "src/beadloom/application/site.py", "_helper", 50)
    _add_symbol(conn, "src/beadloom/graph/loader.py", "load_graph", 1)

    # Docs: application fresh, graph stale, infrastructure none.
    _add_doc(conn, "domains/application/README.md", "domain", "application")
    _add_doc(conn, "domains/graph/SPEC.md", "domain", "graph")
    _mark_stale(conn, "graph", "domains/graph/SPEC.md", "src/beadloom/graph/loader.py")


def _pages() -> dict[str, str]:
    return {
        "beadloom": "/services/beadloom",
        "application": "/domains/application",
        "graph": "/domains/graph",
        "infrastructure": "/domains/infrastructure",
        "site-generation": "/features/site-generation",
    }


def _build(conn: sqlite3.Connection) -> dict[str, object]:
    return build_architecture_view_data(conn, pages=_pages())


# ---------------------------------------------------------------------------
# Shape + content
# ---------------------------------------------------------------------------


def test_has_schema_version_and_sections() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    assert isinstance(data["schema_version"], int)
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_nodes_carry_kind_layer_summary_symbols() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    app = by_id["application"]
    assert app["kind"] == "domain"
    assert app["layer"] == "application"
    assert app["summary"] == "application summary."
    # Symbol count follows OWNERSHIP, not the raw path prefix: the two symbols
    # in `application/site.py` belong to the `site-generation` node whose source
    # IS that file, so the domain that merely contains it owns none of them
    # (BDL-UX #144). A compound view drawing the child inside the parent must
    # not also count the child against the parent.
    assert app["symbols"] == 0
    assert by_id["site-generation"]["symbols"] == 2
    graph = by_id["graph"]
    assert graph["layer"] == "domain"
    assert graph["symbols"] == 1


def test_node_layer_honest_when_no_tag() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    # The feature has no layer tag → honest empty layer (not fabricated).
    assert by_id["site-generation"]["layer"] == ""


def test_node_doc_status_fresh_stale_none() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    assert by_id["application"]["doc_status"] == "fresh"
    assert by_id["graph"]["doc_status"] == "stale"
    # No doc → honest "none" (not "fresh").
    assert by_id["infrastructure"]["doc_status"] == "none"


def test_node_doc_links_only_when_doc_exists() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        # published_doc_slugs gates the link to a doc that is actually published.
        data = build_architecture_view_data(
            conn,
            pages=_pages(),
            published_doc_slugs={"domains/application/README"},
        )
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    # application has a real, PUBLISHED doc → the served `.html` link (NOT `.md`,
    # which 404s — VitePress has no cleanUrls here), no fabrication.
    app_docs = by_id["application"]["doc_links"]
    assert app_docs == ["/docs/domains/application/README.html"]
    # infrastructure has NO doc → empty doc_links (honest, no dead link).
    assert by_id["infrastructure"]["doc_links"] == []


def test_node_doc_links_omitted_when_doc_not_published() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        # graph has a doc row but it is NOT in the published-slug set → the link
        # would 404, so it is honestly omitted (never a dead link).
        data = build_architecture_view_data(
            conn,
            pages=_pages(),
            published_doc_slugs={"domains/application/README"},
        )
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    assert by_id["graph"]["doc_links"] == []


def test_node_doc_links_default_when_slugs_unknown() -> None:
    """When the published-slug set is not supplied, emit the served link for any
    doc row (honest degradation — the slug gate is opt-in, not a silent drop)."""
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    assert by_id["application"]["doc_links"] == ["/docs/domains/application/README.html"]


# ---------------------------------------------------------------------------
# Layer rank / partition (the canonical layered-lanes layout)
# ---------------------------------------------------------------------------


def test_nodes_carry_layer_rank_by_layer() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    # service=0, application=1, domain=2, infra=3 (top→bottom dependency order).
    assert by_id["beadloom"]["layer_rank"] == 0
    assert by_id["application"]["layer_rank"] == 1
    assert by_id["graph"]["layer_rank"] == 2
    assert by_id["infrastructure"]["layer_rank"] == 3


def test_unlayered_node_inherits_parent_layer_rank() -> None:
    """A feature/component carries no layer tag → it inherits its container's
    rank so it sits in the domain's lane (stable lanes regardless of topology)."""
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    # site-generation is part_of application (rank 1) → inherits rank 1.
    assert by_id["site-generation"]["layer_rank"] == 1


# ---------------------------------------------------------------------------
# Edge layering-violation flag (dogfood our own layering rule visually)
# ---------------------------------------------------------------------------


def test_depends_on_edges_carry_violation_flag() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    deps = {
        (e["src"], e["dst"]): e
        for e in data["edges"]
        if e["kind"] == "depends_on"
    }
    # application(1) → graph(2): DOWN the layers → healthy, not a violation.
    assert deps[("application", "graph")]["violation"] is False
    # graph(2) → infrastructure(3): DOWN the layers → healthy.
    assert deps[("graph", "infrastructure")]["violation"] is False


def test_upward_depends_on_edge_is_a_violation() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        # graph(2) depends_on application(1): UP the layers → a layering concern.
        _add_edge(conn, "graph", "application", "depends_on")
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    deps = {
        (e["src"], e["dst"]): e
        for e in data["edges"]
        if e["kind"] == "depends_on"
    }
    assert deps[("graph", "application")]["violation"] is True


def test_part_of_edge_has_no_violation_flag() -> None:
    """Containment is not a flow arrow → it carries no violation verdict."""
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    part_of = [e for e in data["edges"] if e["kind"] == "part_of"]
    assert part_of
    for e in part_of:
        assert "violation" not in e


def test_node_page_url_only_when_page_exists() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = build_architecture_view_data(conn, pages={"application": "/domains/application"})
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    assert by_id["application"]["url"] == "/domains/application"
    # graph has no page in the map → honest empty url (no dead link).
    assert by_id["graph"]["url"] == ""


def test_edges_carry_depends_on_and_part_of() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    rels = {(e["src"], e["dst"], e["kind"]) for e in data["edges"]}
    assert ("application", "graph", "depends_on") in rels
    assert ("graph", "infrastructure", "depends_on") in rels
    # part_of containment is carried so the view can build ELK compound parents.
    assert ("site-generation", "application", "part_of") in rels


def test_node_parent_is_part_of_container() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    # site-generation is part_of application → application is its compound parent.
    assert by_id["site-generation"]["parent"] == "application"
    # application is part_of beadloom (the service root).
    assert by_id["application"]["parent"] == "beadloom"
    # beadloom (root) has no parent.
    assert by_id["beadloom"]["parent"] == ""


def test_node_dependency_lists_like_why() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    graph = by_id["graph"]
    # graph depends_on infrastructure (downstream it relies on).
    assert graph["depends_on"] == ["infrastructure"]
    # application depends_on graph → graph is depended_on_by application.
    assert graph["depended_on_by"] == ["application"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_nodes_and_edges_sorted() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    node_ids = [n["id"] for n in data["nodes"]]
    assert node_ids == sorted(node_ids)
    edge_keys = [(e["src"], e["dst"], e["kind"]) for e in data["edges"]]
    assert edge_keys == sorted(edge_keys)


def test_serialize_is_byte_stable() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        first = serialize_architecture_view(_build(conn))
        second = serialize_architecture_view(_build(conn))
    finally:
        conn.close()
    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["schema_version"] == json.loads(second)["schema_version"]


def test_render_md_mounts_component_and_links_diagram_fallback() -> None:
    conn = _open()
    try:
        _seed_arch(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    first = render_architecture_view_md(data)
    second = render_architecture_view_md(data)
    assert first == second
    assert "<ClientOnly>" in first
    assert "<ArchitectureMap" in first
    # The Mermaid diagram is demoted to a fallback page (no dead link).
    assert "/architecture-diagram" in first


# ---------------------------------------------------------------------------
# Generator wiring
# ---------------------------------------------------------------------------


def test_generator_emits_architecture_data_under_public(tmp_path: Path) -> None:
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_arch(conn)
        conn.commit()
        result = generate_site(conn, out, project_root=tmp_path)
    finally:
        conn.close()
    data_path = out / "public" / "architecture.data.json"
    assert data_path.exists()
    assert data_path in result.written
    # The interactive architecture page + the Mermaid fallback both exist.
    assert (out / "architecture.md").exists()
    assert (out / "architecture-diagram.md").exists()


def test_generator_architecture_data_byte_identical_on_regenerate(tmp_path: Path) -> None:
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_arch(conn)
        conn.commit()
        generate_site(conn, out, project_root=tmp_path, now_ts="2026-06-05T00:00:00+00:00")
        first = (out / "public" / "architecture.data.json").read_bytes()
        generate_site(conn, out, project_root=tmp_path, now_ts="2026-06-05T00:00:00+00:00")
        second = (out / "public" / "architecture.data.json").read_bytes()
    finally:
        conn.close()
    assert first == second
