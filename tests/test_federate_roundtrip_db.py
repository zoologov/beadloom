"""End-to-end round-trip through the REAL DB path (BDL-037 BEAD-09, #100-#102).

These tests deliberately avoid hand-built export dicts: they drive YAML
`.beadloom/_graph` files through `load_graph` (the real reindex loader),
`build_export` (the real artifact builder reading the SQLite index), and
`aggregate_exports` (the hub). This closes the gap flagged in BDL-UX-Issues
#100/#101/#102 where the federation model was only ever tested on dicts that
bypassed the DB CHECK / UNIQUE constraints.

Covers:
- #100: a declared ``depends_on: @other:x`` edge survives YAML -> export.
- #101: ``produces``/``consumes`` contract edges persist through the DB CHECK.
- #102: two AMQP contracts on one node pair both survive (per-message identity).
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


def _export_from_yaml(tmp_path: Path, repo: str, yaml_text: str) -> dict[str, object]:
    """YAML -> load_graph (real DB) -> build_export. Returns the artifact dict."""
    graph_dir = tmp_path / repo / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(yaml_text, encoding="utf-8")
    conn = open_db(tmp_path / repo / "beadloom.db")
    create_schema(conn)
    load_graph(graph_dir, conn)
    export = build_export(
        conn,
        repo=repo,
        commit_sha=_FIXED_SHA,
        exported_at=_FIXED_TIME,
        generator="beadloom test",
    )
    conn.close()
    return export


class TestForeignEdgeRoundTrip:
    """#100: declared @repo: edges survive YAML -> export -> hub."""

    def test_foreign_edge_in_export(self, tmp_path: Path) -> None:
        export = _export_from_yaml(
            tmp_path,
            "core",
            "nodes:\n"
            "  - ref_id: orders\n"
            "    kind: service\n"
            '    summary: "Orders"\n'
            "edges:\n"
            "  - src: orders\n"
            "    dst: '@integration-service:plans'\n"
            "    kind: depends_on\n",
        )
        foreign = [e for e in export["edges"] if e["dst"] == "@integration-service:plans"]
        assert len(foreign) == 1
        assert foreign[0]["src"] == "orders"
        assert foreign[0]["kind"] == "depends_on"

    def test_foreign_edge_resolves_at_hub(self, tmp_path: Path) -> None:
        core = _export_from_yaml(
            tmp_path,
            "core",
            "nodes:\n"
            "  - ref_id: orders\n"
            "    kind: service\n"
            '    summary: "Orders"\n'
            "edges:\n"
            "  - src: orders\n"
            "    dst: '@integration-service:plans'\n"
            "    kind: depends_on\n",
        )
        integ = _export_from_yaml(
            tmp_path,
            "integration-service",
            "nodes:\n"
            "  - ref_id: plans\n"
            "    kind: feature\n"
            '    summary: "Plans"\n',
        )
        fed = aggregate_exports([core, integ], now=_FIXED_TIME)
        edge = next(
            e for e in fed.edges if e["dst"] == "@integration-service:plans"
        )
        # Target IS present in the union -> resolved, not drift.
        assert edge["verdict"] == "ok"
        assert fed.unresolved_refs == []


class TestContractKindsRoundTrip:
    """#101/#102: produces/consumes + per-message contracts persist via DB."""

    def test_produces_consumes_confirmed_both_sides(self, tmp_path: Path) -> None:
        core = _export_from_yaml(
            tmp_path,
            "core",
            "nodes:\n"
            "  - ref_id: core\n"
            "    kind: service\n"
            '    summary: "Core"\n'
            "  - ref_id: q\n"
            "    kind: feature\n"
            '    summary: "Q"\n'
            "edges:\n"
            "  - src: core\n"
            "    dst: q\n"
            "    kind: produces\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: m1\n"
            "      direction: produces\n",
        )
        integ = _export_from_yaml(
            tmp_path,
            "integration-service",
            "nodes:\n"
            "  - ref_id: integ\n"
            "    kind: service\n"
            '    summary: "Integ"\n'
            "  - ref_id: q\n"
            "    kind: feature\n"
            '    summary: "Q"\n'
            "edges:\n"
            "  - src: integ\n"
            "    dst: q\n"
            "    kind: consumes\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: m1\n"
            "      direction: consumes\n",
        )
        fed = aggregate_exports([core, integ], now=_FIXED_TIME)
        confirmed = [c for c in fed.contracts if c["confirmed"]]
        assert [c["message_type"] for c in confirmed] == ["m1"]

    def test_two_contracts_same_pair_both_in_export(self, tmp_path: Path) -> None:
        export = _export_from_yaml(
            tmp_path,
            "core",
            "nodes:\n"
            "  - ref_id: core\n"
            "    kind: service\n"
            '    summary: "Core"\n'
            "  - ref_id: q\n"
            "    kind: feature\n"
            '    summary: "Q"\n'
            "edges:\n"
            "  - src: core\n"
            "    dst: q\n"
            "    kind: produces\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: msg_a\n"
            "  - src: core\n"
            "    dst: q\n"
            "    kind: produces\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: msg_b\n",
        )
        contract_edges = [
            e
            for e in export["edges"]
            if isinstance(e.get("contract"), dict)
        ]
        message_types = {e["contract"]["message_type"] for e in contract_edges}
        assert message_types == {"msg_a", "msg_b"}
