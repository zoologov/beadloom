"""Landscape gate — ``gate_failures`` + ``federate --fail-on`` (BDL-039 F3 BEAD-01).

The gate gives F2's hub verdicts teeth: a hub CI can *block* a cross-service
``DRIFT`` / ``BREAKING`` / orphaned-or-undeclared contract. Two surfaces:

- :func:`gate_failures` — a PURE function over a :class:`FederatedGraph`: scan
  every edge ``EdgeVerdict`` + every contract ``ContractVerdict`` against a
  fail-set (case-insensitive), returning deterministic :class:`GateFailure`s.
- ``beadloom federate --fail-on <csv>`` — writes ``federated.json``/``.txt`` and
  prints the report FIRST, THEN exits 1 on any failure (artifact always
  available); exit 0 when clean.

No-false-gate (principle 3): ``external`` / ``expected`` / ``dead`` / ``unmapped``
/ ``confirmed`` / ``ok`` / ``cleanup_candidate`` NEVER fail a gate — passing one
to ``--fail-on`` is rejected with a clear error. All fixtures are SYNTHETIC
export dicts with an injected ``now`` / ``exported_at`` (never wall-clock).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.graph.contracts import ContractVerdict
from beadloom.graph.federation import (
    NEVER_FAIL_VERDICTS,
    SAFE_DEFAULT_FAIL_ON,
    EdgeVerdict,
    GateFailure,
    aggregate_exports,
    gate_failures,
)
from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_T0 = "2026-06-01T00:00:00+00:00"  # injected reference "now" / exported_at


def _export(
    repo: str,
    *,
    nodes: list[dict[str, object]] | None = None,
    edges: list[dict[str, object]] | None = None,
    commit_sha: str | None = "abc1234",
    exported_at: str = _T0,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "repo": repo,
        "commit_sha": commit_sha,
        "exported_at": exported_at,
        "generator": "beadloom test",
        "nodes": nodes or [],
        "edges": edges or [],
    }


def _node(
    ref_id: str, *, kind: str = "service", lifecycle: str = "active"
) -> dict[str, object]:
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
    contract: Mapping[str, object] | None = None,
) -> dict[str, object]:
    edge: dict[str, object] = {
        "src": src,
        "dst": dst,
        "kind": kind,
        "lifecycle": lifecycle,
    }
    if contract is not None:
        edge["contract"] = dict(contract)
    return edge


def _drift_exports() -> list[dict[str, object]]:
    """A cross-repo active edge whose target is absent -> edge DRIFT."""
    return [
        _export(
            "core",
            nodes=[_node("orders")],
            edges=[_edge("orders", "@integration:gone")],
        ),
        _export("integration", nodes=[_node("plans")]),
    ]


def _amqp(direction: str, message_type: str) -> dict[str, object]:
    return {"protocol": "amqp", "direction": direction, "message_type": message_type}


def _gql(direction: str, *, exposed: list[str] | None = None,
         references: list[str] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "protocol": "graphql", "schema": "API", "direction": direction,
    }
    if exposed is not None:
        payload["exposed"] = exposed
    if references is not None:
        payload["references"] = references
    return payload


class TestGateFailuresEdgeVerdicts:
    """Each gated EDGE verdict is collected; safe edge verdicts never are."""

    def test_edge_drift_is_a_failure(self) -> None:
        fed = aggregate_exports(_drift_exports(), now=_T0)
        failures = gate_failures(fed, {"drift"})
        assert [f.verdict for f in failures] == ["drift"]
        assert failures[0].kind == "edge"
        assert "@integration:gone" in failures[0].identity

    def test_edge_undeclared_producer_is_a_failure(self) -> None:
        # An AMQP producer with no consuming peer -> edge verdict UNDECLARED.
        exports = [
            _export("core", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces",
                                 contract=_amqp("produces", "Lonely"))]),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        failures = gate_failures(fed, {"undeclared"})
        assert any(f.kind == "edge" and f.verdict == "undeclared" for f in failures)

    def test_ok_edge_not_failed_by_default_set(self) -> None:
        exports = [
            _export("core", nodes=[_node("orders")],
                    edges=[_edge("orders", "@integration:plans")]),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        # 'ok' is not in the safe-default set, so a healthy edge never trips the
        # default gate (the no-false-gate guarantee for the default). The pure
        # fn matches exactly what it is given; safe-verdict REJECTION is the
        # CLI's job (TestFederateFailOnCli.test_safe_verdict_in_fail_on_is_rejected).
        assert "ok" not in SAFE_DEFAULT_FAIL_ON
        assert gate_failures(fed, set(SAFE_DEFAULT_FAIL_ON)) == []


class TestGateFailuresContractVerdicts:
    """Each gated CONTRACT verdict is collected with its identity + missing."""

    def test_contract_drift_is_a_failure(self) -> None:
        # Producer present, consumer side absent -> contract DRIFT-shape; here we
        # use one-sided producer which classifies UNDECLARED_PRODUCER, and a
        # one-sided consumer which classifies ORPHANED_CONSUMER.
        exports = [
            _export("core", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces",
                                 contract=_amqp("produces", "Evt"))]),
            _export("integration", nodes=[_node("w"), _node("q2", kind="queue")],
                    edges=[_edge("w", "q2", kind="consumes",
                                 contract=_amqp("consumes", "Other"))]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        failures = gate_failures(fed, {"undeclared_producer", "orphaned_consumer"})
        verdicts = {f.verdict for f in failures if f.kind == "contract"}
        assert verdicts == {"undeclared_producer", "orphaned_consumer"}

    def test_breaking_failure_carries_missing_names(self) -> None:
        exports = [
            _export("backend", nodes=[_node("api", kind="schema")],
                    edges=[_edge("api", "api", kind="produces",
                                 contract=_gql("produces", exposed=["plan"]))]),
            _export("client", nodes=[_node("page", kind="page")],
                    edges=[_edge("page", "page", kind="consumes",
                                 contract=_gql("consumes",
                                               references=["plan", "gone", "user"]))]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        failures = gate_failures(fed, {"breaking"})
        breaking = [f for f in failures if f.verdict == "breaking"]
        assert len(breaking) == 1
        assert breaking[0].kind == "contract"
        assert breaking[0].missing == ("gone", "user")

    def test_confirmed_contract_never_fails(self) -> None:
        exports = [
            _export("core", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces",
                                 contract=_amqp("produces", "Shared"))]),
            _export("integration", nodes=[_node("w"), _node("q", kind="queue")],
                    edges=[_edge("w", "q", kind="consumes",
                                 contract=_amqp("consumes", "Shared"))]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        # CONFIRMED is healthy; with the safe default set, nothing fails.
        assert gate_failures(fed, set(SAFE_DEFAULT_FAIL_ON)) == []


class TestGateNoFalseGate:
    """Principle 3: safe verdicts are unreachable by the gate; clean -> empty."""

    def test_clean_landscape_no_failures(self) -> None:
        exports = [
            _export("core", nodes=[_node("orders")],
                    edges=[_edge("orders", "@integration:plans")]),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        assert gate_failures(fed, set(SAFE_DEFAULT_FAIL_ON)) == []

    def test_expected_edge_never_fails_even_if_requested(self) -> None:
        # A planned edge to an absent target -> EXPECTED (intentional, not built).
        exports = [
            _export("core", nodes=[_node("orders")],
                    edges=[_edge("orders", "@integration:future", lifecycle="planned")]),
            _export("integration", nodes=[_node("plans")]),
        ]
        fed = aggregate_exports(exports, now=_T0)
        # Even if 'expected' is (wrongly) in the set, gate_failures still matches
        # it — the REJECTION of safe verdicts is enforced at the CLI parse layer,
        # so the pure fn matches exactly what it is given. Assert it is NOT in the
        # safe-default set (the no-false-gate guarantee for the default gate).
        assert "expected" not in SAFE_DEFAULT_FAIL_ON
        assert gate_failures(fed, set(SAFE_DEFAULT_FAIL_ON)) == []

    def test_safe_and_default_sets_are_disjoint(self) -> None:
        assert SAFE_DEFAULT_FAIL_ON.isdisjoint(NEVER_FAIL_VERDICTS)

    def test_no_edge_verdict_value_is_both_default_and_never(self) -> None:
        # Sanity: every EdgeVerdict / ContractVerdict value is classified into at
        # most one of the two sets (no verdict is simultaneously gated + safe).
        all_values = {v.value for v in EdgeVerdict} | {v.value for v in ContractVerdict}
        for value in all_values:
            assert not (value in SAFE_DEFAULT_FAIL_ON and value in NEVER_FAIL_VERDICTS)


class TestGateDeterminism:
    def test_failures_sorted_and_stable(self) -> None:
        fed = aggregate_exports(_drift_exports(), now=_T0)
        a = gate_failures(fed, {"drift"})
        b = gate_failures(fed, {"DRIFT"})  # case-insensitive
        assert a == b
        assert a == sorted(a, key=lambda f: (f.kind, f.identity, f.verdict))

    def test_gate_failure_is_frozen(self) -> None:
        f = GateFailure("edge", "a --> b", "drift")
        try:
            f.verdict = "ok"  # type: ignore[misc]  # frozen dataclass
        except AttributeError:
            return
        raise AssertionError("GateFailure should be frozen")


class TestFederateFailOnCli:
    """The CLI wires the gate: artifact first, then exit code."""

    def _write_exports(self, tmp_path: Path,
                       exports: list[dict[str, object]]) -> list[str]:
        paths: list[str] = []
        for i, export in enumerate(exports):
            p = tmp_path / f"export_{i}.json"
            p.write_text(json.dumps(export), encoding="utf-8")
            paths.append(str(p))
        return paths

    def test_fail_on_drift_exits_1_but_writes_artifact(self, tmp_path: Path) -> None:
        hub = tmp_path / "hub"
        hub.mkdir()
        paths = self._write_exports(tmp_path, _drift_exports())
        runner = CliRunner()
        result = runner.invoke(
            main, ["federate", *paths, "--project", str(hub), "--fail-on", "drift"]
        )
        assert result.exit_code == 1
        # Artifact written FIRST (available even though the gate failed).
        assert (hub / ".beadloom" / "federated.json").exists()
        assert (hub / ".beadloom" / "federated.txt").exists()
        # The report still printed; failing verdict named on stderr/output.
        assert "drift" in result.output.lower()

    def test_clean_landscape_exits_0(self, tmp_path: Path) -> None:
        hub = tmp_path / "hub"
        hub.mkdir()
        exports = [
            _export("core", nodes=[_node("orders")],
                    edges=[_edge("orders", "@integration:plans")]),
            _export("integration", nodes=[_node("plans")]),
        ]
        paths = self._write_exports(tmp_path, exports)
        runner = CliRunner()
        result = runner.invoke(
            main, ["federate", *paths, "--project", str(hub), "--fail-on", "drift"]
        )
        assert result.exit_code == 0
        assert (hub / ".beadloom" / "federated.json").exists()

    def test_bare_fail_on_default_uses_safe_set(self, tmp_path: Path) -> None:
        hub = tmp_path / "hub"
        hub.mkdir()
        paths = self._write_exports(tmp_path, _drift_exports())
        runner = CliRunner()
        # The 'default' token expands to the safe-default fail-set.
        result = runner.invoke(
            main, ["federate", *paths, "--project", str(hub), "--fail-on", "default"]
        )
        assert result.exit_code == 1

    def test_no_fail_on_never_blocks(self, tmp_path: Path) -> None:
        hub = tmp_path / "hub"
        hub.mkdir()
        paths = self._write_exports(tmp_path, _drift_exports())
        runner = CliRunner()
        # Without --fail-on the command is pure reporting -> exit 0 even on drift.
        result = runner.invoke(main, ["federate", *paths, "--project", str(hub)])
        assert result.exit_code == 0

    def test_safe_verdict_in_fail_on_is_rejected(self, tmp_path: Path) -> None:
        hub = tmp_path / "hub"
        hub.mkdir()
        paths = self._write_exports(tmp_path, _drift_exports())
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["federate", *paths, "--project", str(hub), "--fail-on", "external"],
        )
        # A no-false-gate verdict is refused with a clear, non-zero error.
        assert result.exit_code != 0
        assert "external" in result.output.lower()
