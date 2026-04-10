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


class TestGraphQLContractFederation:
    """BEAD-03 / G3: GraphQL contracts reconcile cross-language at the hub."""

    def _v2_export(self, repo: str, **kw: object) -> dict[str, object]:
        """A schema_version=2 export (the GraphQL wire). aggregate ignores version."""
        export = _export(repo, **kw)  # type: ignore[arg-type]
        export["schema_version"] = 2
        return export

    def test_graphql_producer_consumer_confirmed_by_schema_name(self) -> None:
        produces = {
            "protocol": "graphql",
            "schema": "PublicAPI",
            "direction": "produces",
            "exposed": ["Plan", "plan", "plans"],
        }
        consumes = {
            "protocol": "graphql",
            "schema": "PublicAPI",
            "direction": "consumes",
            "references": ["plan", "plans"],
        }
        exports = [
            self._v2_export(
                "backend",
                nodes=[_node("api", kind="schema")],
                edges=[_edge("api", "api", kind="produces", contract=produces)],
            ),
            self._v2_export(
                "ui",
                nodes=[_node("client", kind="page")],
                edges=[_edge("client", "client", kind="consumes", contract=consumes)],
            ),
        ]
        fed = aggregate_exports(exports)
        gql = [c for c in fed.contracts if c["message_type"] == "PublicAPI"]
        assert len(gql) == 1
        # Cross-language resolve by NAME: producer (backend) + consumer (ui).
        assert gql[0]["confirmed"] is True
        assert sorted(gql[0]["directions"]) == ["consumes", "produces"]

    def test_v1_export_still_federates(self) -> None:
        """Back-compat: a v1 (AMQP-only, no GraphQL fields) export reconciles."""
        produces = {
            "protocol": "amqp",
            "direction": "produces",
            "message_type": "PlanCreated",
        }
        consumes = {
            "protocol": "amqp",
            "direction": "consumes",
            "message_type": "PlanCreated",
        }
        # _export defaults schema_version=1 — explicitly the old wire.
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
        assert all(e["schema_version"] == 1 for e in exports)
        fed = aggregate_exports(exports)
        confirmed = [c for c in fed.contracts if c["confirmed"]]
        assert len(confirmed) == 1
        assert confirmed[0]["message_type"] == "PlanCreated"

    def test_mixed_v1_amqp_and_v2_graphql_coexist(self) -> None:
        """A v1 AMQP satellite and a v2 GraphQL satellite federate together."""
        amqp = {"protocol": "amqp", "direction": "produces", "message_type": "Evt"}
        gql = {"protocol": "graphql", "schema": "Api", "direction": "produces"}
        exports = [
            _export(
                "core",
                nodes=[_node("svc"), _node("q", kind="queue")],
                edges=[_edge("svc", "q", kind="produces", contract=amqp)],
            ),
            self._v2_export(
                "backend",
                nodes=[_node("api", kind="schema")],
                edges=[_edge("api", "api", kind="produces", contract=gql)],
            ),
        ]
        fed = aggregate_exports(exports)
        names = {c["message_type"] for c in fed.contracts}
        assert {"Evt", "Api"} <= names


class TestContractVerdicts:
    """BEAD-04 / G5: contract-level intent-vs-reality verdicts at the hub."""

    def test_confirmed_carries_verdict(self) -> None:
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "M"}
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "M"}
        exports = [
            _export("a", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces", contract=produces)]),
            _export("b", nodes=[_node("w"), _node("q", kind="queue")],
                    edges=[_edge("w", "q", kind="consumes", contract=consumes)]),
        ]
        fed = aggregate_exports(exports)
        m = next(c for c in fed.contracts if c["message_type"] == "M")
        assert m["verdict"] == "confirmed"

    def test_producer_only_is_undeclared_producer(self) -> None:
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "Lonely"}
        exports = [
            _export("a", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces", contract=produces)]),
            _export("b", nodes=[_node("w")]),
        ]
        fed = aggregate_exports(exports)
        m = next(c for c in fed.contracts if c["message_type"] == "Lonely")
        assert m["verdict"] == "undeclared_producer"

    def test_consumer_only_is_orphaned_consumer(self) -> None:
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "Ghost"}
        exports = [
            _export("a", nodes=[_node("w"), _node("q", kind="queue")],
                    edges=[_edge("w", "q", kind="consumes", contract=consumes)]),
            _export("b", nodes=[_node("svc")]),
        ]
        fed = aggregate_exports(exports)
        m = next(c for c in fed.contracts if c["message_type"] == "Ghost")
        assert m["verdict"] == "orphaned_consumer"

    def test_graphql_breaking_references_not_subset(self) -> None:
        produces = {
            "protocol": "graphql", "schema": "PublicAPI", "direction": "produces",
            "exposed": ["plan"],
        }
        consumes = {
            "protocol": "graphql", "schema": "PublicAPI", "direction": "consumes",
            "references": ["plan", "removedField"],
        }
        exports = [
            _export("backend", nodes=[_node("api", kind="schema")],
                    edges=[_edge("api", "api", kind="produces", contract=produces)]),
            _export("ui", nodes=[_node("client", kind="page")],
                    edges=[_edge("client", "client", kind="consumes", contract=consumes)]),
        ]
        fed = aggregate_exports(exports)
        m = next(c for c in fed.contracts if c["message_type"] == "PublicAPI")
        assert m["verdict"] == "breaking"
        assert m["missing"] == ["removedField"]

    def test_planned_lifecycle_is_expected(self) -> None:
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "Future"}
        exports = [
            _export("a", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces", lifecycle="planned",
                                 contract=produces)]),
            _export("b", nodes=[_node("w")]),
        ]
        fed = aggregate_exports(exports)
        m = next(c for c in fed.contracts if c["message_type"] == "Future")
        assert m["verdict"] == "expected"

    def test_contracts_sorted_by_contract_key(self) -> None:
        z = {"protocol": "amqp", "direction": "produces", "message_type": "zeta"}
        a = {"protocol": "amqp", "direction": "produces", "message_type": "alpha"}
        exports = [
            _export("a", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces", contract=z),
                           _edge("svc", "q", kind="produces", contract=a)]),
            _export("b", nodes=[_node("w")]),
        ]
        fed = aggregate_exports(exports)
        keys = [c["contract_key"] for c in fed.contracts]
        assert keys == sorted(keys)

    def test_report_lists_breaking_and_actionable_verdicts(self) -> None:
        produces = {
            "protocol": "graphql", "schema": "PublicAPI", "direction": "produces",
            "exposed": ["plan"],
        }
        consumes = {
            "protocol": "graphql", "schema": "PublicAPI", "direction": "consumes",
            "references": ["plan", "removedField"],
        }
        exports = [
            _export("backend", nodes=[_node("api", kind="schema")],
                    edges=[_edge("api", "api", kind="produces", contract=produces)]),
            _export("ui", nodes=[_node("client", kind="page")],
                    edges=[_edge("client", "client", kind="consumes", contract=consumes)]),
        ]
        fed = aggregate_exports(exports)
        report = render_federation_report(fed)
        assert "BREAKING" in report
        assert "removedField" in report

    def test_federation_schema_version_is_2(self) -> None:
        fed = aggregate_exports([_export("a"), _export("b")], now=_T0)
        parsed = json.loads(serialize_federation(fed))
        assert parsed["schema_version"] == 2


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
        assert parsed["schema_version"] == 2
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
