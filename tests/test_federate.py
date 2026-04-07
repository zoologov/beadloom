"""Tests for `beadloom federate` — hub aggregation (BDL-037 BEAD-04).

Covers the federation hub that ingests >=2 satellite export artifacts and
composes ONE federated graph with:
- namespaced node union (``@repo:ref_id``) + edge union,
- foreign-ref (``@repo:node``) resolution across the union (unresolved reported),
- three-valued intent-vs-reality per edge (OK / DRIFT / expected / cleanup /
  UNDECLARED),
- both-sides AMQP contract confirmation (produces<->consumes),
- per-satellite staleness (commit_sha + exported_at age), reported never faked.

Fixtures are SYNTHETIC 2-repo export dicts built inline (per bead constraint);
real-repo dogfood is BEAD-05.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.graph.federation import (
    EdgeVerdict,
    aggregate_exports,
    render_federation_report,
    serialize_federation,
)
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_T0 = "2026-06-01T00:00:00+00:00"  # reference "now" for deterministic ages


def _export(
    repo: str,
    *,
    nodes: list[dict[str, object]] | None = None,
    edges: list[dict[str, object]] | None = None,
    commit_sha: str | None = "abc1234",
    exported_at: str = _T0,
) -> dict[str, object]:
    """Build a minimal synthetic satellite export artifact."""
    return {
        "schema_version": 1,
        "repo": repo,
        "commit_sha": commit_sha,
        "exported_at": exported_at,
        "generator": "beadloom test",
        "nodes": nodes or [],
        "edges": edges or [],
    }


def _node(ref_id: str, *, kind: str = "service", lifecycle: str = "active") -> dict[str, object]:
    return {
        "ref_id": ref_id,
        "kind": kind,
        "summary": ref_id,
        "lifecycle": lifecycle,
        "source": None,
    }


def _edge(
    src: str,
    dst: str,
    *,
    kind: str = "depends_on",
    lifecycle: str = "active",
    contract: dict[str, object] | None = None,
) -> dict[str, object]:
    edge: dict[str, object] = {
        "src": src,
        "dst": dst,
        "kind": kind,
        "lifecycle": lifecycle,
    }
    if contract is not None:
        edge["contract"] = contract
    return edge


class TestNodeUnionNamespacing:
    def test_nodes_namespaced_per_repo(self) -> None:
        exports = [
            _export("core", nodes=[_node("orders")]),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        ids = {n["ref_id"] for n in fed.nodes}
        assert ids == {"@core:orders", "@integration:plans"}

    def test_repos_listed(self) -> None:
        exports = [_export("core"), _export("integration")]
        fed = aggregate_exports(exports)
        assert sorted(r["repo"] for r in fed.repos) == ["core", "integration"]

    def test_same_ref_id_different_repos_distinct(self) -> None:
        exports = [
            _export("core", nodes=[_node("shared")]),
            _export("integration", nodes=[_node("shared")]),
        ]
        fed = aggregate_exports(exports)
        ids = {n["ref_id"] for n in fed.nodes}
        assert ids == {"@core:shared", "@integration:shared"}


class TestLocalEdgeNamespacing:
    def test_local_edge_endpoints_namespaced(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders"), _node("payments")],
                edges=[_edge("orders", "payments")],
            ),
            _export("integration"),
        ]
        fed = aggregate_exports(exports)
        edge = fed.edges[0]
        assert edge["src"] == "@core:orders"
        assert edge["dst"] == "@core:payments"


class TestForeignRefResolution:
    def test_foreign_ref_resolves_across_union(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:plans")],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        edge = fed.edges[0]
        assert edge["src"] == "@core:orders"
        assert edge["dst"] == "@integration:plans"
        assert fed.unresolved_refs == []

    def test_unresolved_foreign_ref_reported_not_dropped(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:ghost")],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        # Edge is still present (not dropped).
        assert len(fed.edges) == 1
        assert "@integration:ghost" in fed.unresolved_refs


class TestThreeValuedDrift:
    def test_active_target_present_is_ok(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:plans", lifecycle="active")],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        assert fed.edges[0]["verdict"] == EdgeVerdict.OK.value

    def test_active_target_absent_is_drift(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:ghost", lifecycle="active")],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        assert fed.edges[0]["verdict"] == EdgeVerdict.DRIFT.value

    def test_planned_target_absent_is_expected(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:future", lifecycle="planned")],
            ),
            _export("integration"),
        ]
        fed = aggregate_exports(exports)
        assert fed.edges[0]["verdict"] == EdgeVerdict.EXPECTED.value

    def test_deprecated_target_present_is_cleanup(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:plans", lifecycle="deprecated")],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        assert fed.edges[0]["verdict"] == EdgeVerdict.CLEANUP_CANDIDATE.value


class TestUndeclared:
    def test_produces_without_consumer_is_undeclared(self) -> None:
        # core produces a message; integration declares no matching consume.
        produces = {
            "protocol": "amqp",
            "source_file": "src/broker.py",
            "direction": "produces",
            "message_type": "PlanCreated",
        }
        exports = [
            _export(
                "core",
                nodes=[_node("orders"), _node("plans-queue", kind="queue")],
                edges=[
                    _edge("orders", "plans-queue", kind="produces", contract=produces)
                ],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        edge = fed.edges[0]
        assert edge["verdict"] == EdgeVerdict.UNDECLARED.value


class TestBothSidesContract:
    def _bidirectional_exports(self) -> list[dict[str, object]]:
        produces = {
            "protocol": "amqp",
            "source_file": "src/core_broker.py",
            "direction": "produces",
            "message_type": "PlanCreated",
        }
        consumes = {
            "protocol": "amqp",
            "source_file": "src/int_broker.py",
            "direction": "consumes",
            "message_type": "PlanCreated",
        }
        return [
            _export(
                "core",
                nodes=[_node("orders"), _node("plans-queue", kind="queue")],
                edges=[
                    _edge("orders", "plans-queue", kind="produces", contract=produces)
                ],
            ),
            _export(
                "integration",
                nodes=[_node("plans"), _node("plans-queue", kind="queue")],
                edges=[
                    _edge("plans", "plans-queue", kind="consumes", contract=consumes)
                ],
            ),
        ]

    def test_confirmed_both_sides(self) -> None:
        fed = aggregate_exports(self._bidirectional_exports())
        confirmed = [c for c in fed.contracts if c["confirmed"]]
        assert len(confirmed) == 1
        assert confirmed[0]["message_type"] == "PlanCreated"
        assert sorted(confirmed[0]["directions"]) == ["consumes", "produces"]

    def test_one_sided_contract_flagged(self) -> None:
        produces = {
            "protocol": "amqp",
            "source_file": "src/core_broker.py",
            "direction": "produces",
            "message_type": "LonelyEvent",
        }
        exports = [
            _export(
                "core",
                nodes=[_node("orders"), _node("q", kind="queue")],
                edges=[_edge("orders", "q", kind="produces", contract=produces)],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports)
        lonely = [c for c in fed.contracts if c["message_type"] == "LonelyEvent"]
        assert len(lonely) == 1
        assert lonely[0]["confirmed"] is False

    def test_same_message_type_different_exchange_not_confirmed(self) -> None:
        """G4: producer and consumer agree on message_type but use different
        exchanges -> distinct contract_key -> NOT a confirmed both-sides match.

        This is the false-confirm bug F2/BEAD-02 closes: before exchange folded
        into the key, these collapsed into one confirmed contract.
        """
        produces = {
            "protocol": "amqp",
            "direction": "produces",
            "message_type": "PlanCreated",
            "exchange": "plans-v1",
        }
        consumes = {
            "protocol": "amqp",
            "direction": "consumes",
            "message_type": "PlanCreated",
            "exchange": "plans-v2",
        }
        exports = [
            _export(
                "core",
                nodes=[_node("orders"), _node("q", kind="queue")],
                edges=[_edge("orders", "q", kind="produces", contract=produces)],
            ),
            _export(
                "integration",
                nodes=[_node("plans"), _node("q", kind="queue")],
                edges=[_edge("plans", "q", kind="consumes", contract=consumes)],
            ),
        ]
        fed = aggregate_exports(exports)
        plan = [c for c in fed.contracts if c["message_type"] == "PlanCreated"]
        # Two separate contracts (one per exchange), neither confirmed both-sides.
        assert len(plan) == 2
        assert all(c["confirmed"] is False for c in plan)

    def test_same_exchange_still_confirmed(self) -> None:
        """No regression: identical exchange/routing on both sides still confirms."""
        produces = {
            "protocol": "amqp",
            "direction": "produces",
            "message_type": "PlanCreated",
            "exchange": "plans",
            "routing_key": "upload",
        }
        consumes = {
            "protocol": "amqp",
            "direction": "consumes",
            "message_type": "PlanCreated",
            "exchange": "plans",
            "routing_key": "upload",
        }
        exports = [
            _export(
                "core",
                nodes=[_node("orders"), _node("q", kind="queue")],
                edges=[_edge("orders", "q", kind="produces", contract=produces)],
            ),
            _export(
                "integration",
                nodes=[_node("plans"), _node("q", kind="queue")],
                edges=[_edge("plans", "q", kind="consumes", contract=consumes)],
            ),
        ]
        fed = aggregate_exports(exports)
        confirmed = [c for c in fed.contracts if c["confirmed"]]
        assert len(confirmed) == 1
        assert confirmed[0]["message_type"] == "PlanCreated"


class TestStaleness:
    def test_age_reported_per_satellite(self) -> None:
        exports = [
            _export("core", exported_at="2026-05-30T00:00:00+00:00"),
            _export("integration", exported_at="2026-06-01T00:00:00+00:00"),
        ]
        fed = aggregate_exports(exports, now="2026-06-01T00:00:00+00:00")
        ages = {r["repo"]: r["age_seconds"] for r in fed.repos}
        assert ages["core"] == 2 * 86400
        assert ages["integration"] == 0

    def test_unknown_commit_sha_reported_honestly(self) -> None:
        exports = [
            _export("core", commit_sha=None),
            _export("integration"),
        ]
        fed = aggregate_exports(exports)
        core = next(r for r in fed.repos if r["repo"] == "core")
        assert core["commit_sha"] is None

    def test_unparseable_exported_at_age_is_none(self) -> None:
        exports = [
            _export("core", exported_at="not-a-date"),
            _export("integration"),
        ]
        fed = aggregate_exports(exports, now=_T0)
        core = next(r for r in fed.repos if r["repo"] == "core")
        assert core["age_seconds"] is None


class TestSerializeAndReport:
    def test_serialize_deterministic(self) -> None:
        exports = [
            _export("core", nodes=[_node("orders")]),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        a = serialize_federation(fed)
        b = serialize_federation(fed)
        assert a == b
        parsed = json.loads(a)
        assert parsed["schema_version"] == 1
        assert "nodes" in parsed and "edges" in parsed and "repos" in parsed

    def test_report_mentions_drift_and_repos(self) -> None:
        exports = [
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:ghost", lifecycle="active")],
            ),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        report = render_federation_report(fed)
        assert "core" in report
        assert "integration" in report
        assert "DRIFT" in report


class TestFederateCli:
    def _write_export(self, path: Path, export: dict[str, object]) -> None:
        path.write_text(json.dumps(export), encoding="utf-8")

    def test_federate_writes_outputs(self, tmp_path: Path) -> None:
        e1 = tmp_path / "core.json"
        e2 = tmp_path / "integration.json"
        self._write_export(
            e1,
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:plans", lifecycle="active")],
            ),
        )
        self._write_export(e2, _export("integration", nodes=[_node("plans")]))

        hub = tmp_path / "hub"
        hub.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["federate", str(e1), str(e2), "--project", str(hub)],
        )
        assert result.exit_code == 0, result.output
        out_json = hub / ".beadloom" / "federated.json"
        assert out_json.exists()
        parsed = json.loads(out_json.read_text(encoding="utf-8"))
        assert {n["ref_id"] for n in parsed["nodes"]} == {
            "@core:orders",
            "@integration:plans",
        }
        report = hub / ".beadloom" / "federated.txt"
        assert report.exists()

    def test_federate_requires_two_exports(self, tmp_path: Path) -> None:
        e1 = tmp_path / "core.json"
        self._write_export(e1, _export("core"))
        runner = CliRunner()
        result = runner.invoke(main, ["federate", str(e1)])
        assert result.exit_code == 1
        assert "at least two" in result.output.lower()

    def test_federate_reports_unresolved_in_stdout(self, tmp_path: Path) -> None:
        e1 = tmp_path / "core.json"
        e2 = tmp_path / "integration.json"
        self._write_export(
            e1,
            _export(
                "core",
                nodes=[_node("orders")],
                edges=[_edge("orders", "@integration:ghost", lifecycle="active")],
            ),
        )
        self._write_export(e2, _export("integration", nodes=[_node("plans")]))
        hub = tmp_path / "hub"
        hub.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            main, ["federate", str(e1), str(e2), "--project", str(hub)]
        )
        assert result.exit_code == 0, result.output
        assert "DRIFT" in result.output
