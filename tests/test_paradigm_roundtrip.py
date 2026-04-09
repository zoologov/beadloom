"""Paradigm-agnostic round-trip hardening (BDL-038 BEAD-07, U1 / G6).

Beadloom must be paradigm-agnostic, not DDD-only: an arbitrary node ``kind`` or
edge ``kind`` (Feature-Sliced Design ``page`` / ``feature`` / ``entity`` /
``repository`` alongside DDD ``domain`` / ``service``) MUST survive
``export -> federate`` with **zero loss and zero rejection** — no drop, no
coercion to a DDD kind.

These tests deliberately drive YAML through the REAL DB path
(``load_graph`` -> ``build_export`` -> ``aggregate_exports``), not hand-built
export dicts: the proof has to cover the loader's DB CHECK, which is where a
DDD-only assumption would otherwise reject an unknown kind before it ever
reaches the kind-agnostic federation/contract path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.federation import aggregate_exports, build_export
from beadloom.graph.loader import load_graph
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

_FIXED_TIME = "2026-06-01T00:00:00+00:00"
_FIXED_SHA = "0123456789abcdef0123456789abcdef01234567"

# Feature-Sliced Design node kinds — none of these are DDD preset kinds.
_FSD_NODE_KINDS = ("page", "feature", "entity", "repository", "widget", "shared")


def _export_from_yaml(tmp_path: Path, repo: str, yaml_text: str) -> dict[str, object]:
    """YAML -> load_graph (real DB) -> build_export. Returns the artifact dict."""
    graph_dir = tmp_path / repo / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(yaml_text, encoding="utf-8")
    conn = open_db(tmp_path / repo / "beadloom.db")
    create_schema(conn)
    result = load_graph(graph_dir, conn)
    export = build_export(
        conn,
        repo=repo,
        commit_sha=_FIXED_SHA,
        exported_at=_FIXED_TIME,
        generator="beadloom test",
    )
    conn.close()
    # No FSD kind may be rejected at load time (the DB-CHECK regression guard).
    assert result.errors == [], f"loader rejected FSD input: {result.errors}"
    return export


class TestFsdNodeKindsRoundTrip:
    """Arbitrary FSD node kinds survive the real DB load + export byte-faithfully."""

    def test_all_fsd_node_kinds_persist_through_db(self, tmp_path: Path) -> None:
        nodes = "\n".join(
            f"  - ref_id: n_{kind}\n    kind: {kind}\n    summary: {kind}"
            for kind in _FSD_NODE_KINDS
        )
        export = _export_from_yaml(tmp_path, "mobile", "nodes:\n" + nodes + "\n")
        by_ref = {n["ref_id"]: n for n in export["nodes"]}
        for kind in _FSD_NODE_KINDS:
            assert by_ref[f"n_{kind}"]["kind"] == kind  # no coercion to DDD

    def test_fsd_kinds_survive_export_to_federate(self, tmp_path: Path) -> None:
        mobile = _export_from_yaml(
            tmp_path,
            "mobile",
            "nodes:\n"
            "  - ref_id: home\n    kind: page\n    summary: Home\n"
            "  - ref_id: cart\n    kind: feature\n    summary: Cart\n"
            "edges:\n"
            "  - src: home\n    dst: cart\n    kind: depends_on\n",
        )
        # >=2 exports required to federate.
        other = _export_from_yaml(
            tmp_path,
            "web",
            "nodes:\n  - ref_id: shell\n    kind: page\n    summary: Shell\n",
        )
        fed = aggregate_exports([mobile, other], now=_FIXED_TIME)
        kinds = {str(n["ref_id"]): n["kind"] for n in fed.nodes}
        assert kinds["@mobile:home"] == "page"
        assert kinds["@mobile:cart"] == "feature"
        assert kinds["@web:shell"] == "page"
        # The intra-repo edge resolved (both endpoints present) — not drift.
        edge = next(e for e in fed.edges if e["dst"] == "@mobile:cart")
        assert edge["verdict"] == "ok"


class TestFsdEdgeKindsRoundTrip:
    """Arbitrary FSD-style edge kinds survive load + export without rejection."""

    def test_fsd_edge_kind_persists(self, tmp_path: Path) -> None:
        export = _export_from_yaml(
            tmp_path,
            "mobile",
            "nodes:\n"
            "  - ref_id: cart\n    kind: feature\n    summary: Cart\n"
            "  - ref_id: user\n    kind: entity\n    summary: User\n"
            "edges:\n"
            "  - src: cart\n    dst: user\n    kind: renders\n",
        )
        edge = next(e for e in export["edges"] if e["src"] == "cart")
        assert edge["kind"] == "renders"  # free-form edge kind, no coercion


class TestFsdContractRoundTrip:
    """An FSD-kind producer/consumer reconciles across repos (contract path)."""

    def test_fsd_nodes_carry_amqp_contract(self, tmp_path: Path) -> None:
        producer = _export_from_yaml(
            tmp_path,
            "backend",
            "nodes:\n"
            "  - ref_id: orders_repo\n    kind: repository\n    summary: Orders\n"
            "  - ref_id: bus\n    kind: shared\n    summary: Bus\n"
            "edges:\n"
            "  - src: orders_repo\n    dst: bus\n    kind: produces\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: order_placed\n"
            "      direction: produces\n",
        )
        consumer = _export_from_yaml(
            tmp_path,
            "mobile",
            "nodes:\n"
            "  - ref_id: cart\n    kind: feature\n    summary: Cart\n"
            "  - ref_id: bus\n    kind: shared\n    summary: Bus\n"
            "edges:\n"
            "  - src: cart\n    dst: bus\n    kind: consumes\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: order_placed\n"
            "      direction: consumes\n",
        )
        fed = aggregate_exports([producer, consumer], now=_FIXED_TIME)
        confirmed = [c for c in fed.contracts if c["confirmed"]]
        assert [c["message_type"] for c in confirmed] == ["order_placed"]
        # The repository/feature producer + consumer nodes survived intact.
        kinds = {str(n["ref_id"]): n["kind"] for n in fed.nodes}
        assert kinds["@backend:orders_repo"] == "repository"
        assert kinds["@mobile:cart"] == "feature"
