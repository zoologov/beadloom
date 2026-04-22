"""F3 enforcement — coverage + cross-cutting attestations (BDL-039 F3 BEAD-07).

This module closes the COVERAGE + CROSS-CUTTING gaps left after the six F3 dev
beads, without changing production code. It targets:

* error / edge branches in ``application/gate.py`` (missing DB, unreadable /
  malformed hub export, the stale-sync + missing-names finding projections);
* error / edge branches in ``onboarding/config_sync.py`` (no-marker AGENTS.md
  region, unreadable AGENTS.md / adapter files);
* the no-false-gate guarantee, *exhaustively* (every ``NEVER_FAIL_VERDICTS``
  token, individually, can never arm the gate; user prose never trips
  config-check);
* byte-stable determinism of ``beadloom ci --format json`` / ``github`` and of
  ``gate_failures`` across repeated runs;
* no regression in the additive surface (v1 + v2 exports still federate; bare /
  empty / whitespace ``--fail-on`` resolves to the safe set);
* the honest-gate invariant (every step is reported; no step is silently
  dropped even when an earlier one fails).

All fixtures inject ``now`` / ``exported_at`` — no wall-clock assertions, AAA.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, ClassVar

from click.testing import CliRunner

from beadloom.application.gate import (
    GateResult,
    GateStep,
    _config_finding,
    _gate_failure_finding,
    _simple_finding,
    _sync_finding,
    run_ci_gate,
)
from beadloom.graph.contracts import ContractVerdict
from beadloom.graph.federation import (
    NEVER_FAIL_VERDICTS,
    SAFE_DEFAULT_FAIL_ON,
    EdgeVerdict,
    GateFailure,
    aggregate_exports,
    gate_failures,
    serialize_federation,
)
from beadloom.onboarding.config_sync import check_config_drift
from beadloom.onboarding.scanner import (
    _RULES_ADAPTER_TEMPLATE,
    _RULES_CONFIGS,
    generate_agents_md,
)
from beadloom.services.cli import _parse_fail_on, main

if TYPE_CHECKING:
    from pathlib import Path

_T0 = "2026-06-01T00:00:00+00:00"  # injected reference time (never wall-clock)


# ---------------------------------------------------------------------------
# Shared synthetic export builders (mirrors the F3 gate test fixtures).
# ---------------------------------------------------------------------------


def _export(repo: str, *, schema_version: int = 1, **extra: object) -> dict[str, object]:
    """A minimal, deterministic satellite export artifact."""
    base: dict[str, object] = {
        "schema_version": schema_version,
        "repo": repo,
        "exported_at": _T0,
        "nodes": [{"ref_id": "svc", "kind": "service", "name": repo}],
        "edges": [],
        "contracts": [],
        "lifecycle": {},
    }
    base.update(extra)
    return base


def _write_unsatisfiable_rule(project_root: Path) -> None:
    """Write a require-rule that no node satisfies -> a deterministic violation."""
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "rules.yml").write_text(
        "rules:\n"
        "  - name: nonexistent-domain-needs-parent\n"
        "    require: {}\n"
        "    description: domain nonexistent-domain\n",
        encoding="utf-8",
    )


def _clean_project(project_root: Path) -> None:
    """A project whose every gate step passes (no rules => no lint violations)."""
    (project_root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(project_root)


def _write_clean_exports(tmp_path: Path) -> list[Path]:
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    p1.write_text(json.dumps(_export("a")), encoding="utf-8")
    p2.write_text(json.dumps(_export("b")), encoding="utf-8")
    return [p1, p2]


# ---------------------------------------------------------------------------
# gate.py — error / edge branches (sync DB missing, export read errors).
# ---------------------------------------------------------------------------


class TestGateErrorBranches:
    def test_sync_check_missing_db_fails_with_actionable_finding(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a project with no beadloom.db at all. The orchestrator's lint
        # step would create the DB first, so we exercise the sync-check step in
        # isolation — the defensive missing-DB branch (an honest FAIL, not a
        # silent green).
        from beadloom.application.gate import _step_sync_check

        assert not (tmp_path / ".beadloom" / "beadloom.db").exists()
        # Act
        sync_step = _step_sync_check(tmp_path)
        # Assert: the missing DB is an honest FAIL with a "run reindex" hint.
        assert sync_step.passed is False
        assert sync_step.summary == "database missing"
        assert sync_step.findings[0]["remediation"] == "run `beadloom reindex` first"

    def test_unreadable_hub_export_fails_federate_step(self, tmp_path: Path) -> None:
        # Arrange: a hub export path that does not exist (OSError on read).
        _clean_project(tmp_path)
        missing = tmp_path / "does_not_exist.json"
        # Act
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=[missing], no_reindex=False
        )
        fed_step = next(s for s in result.steps if s.name == "federate")
        # Assert
        assert fed_step.passed is False
        assert fed_step.summary == "export read error"
        assert "cannot read" in str(fed_step.findings[0]["why"])

    def test_malformed_json_export_fails_federate_step(self, tmp_path: Path) -> None:
        # Arrange: a syntactically invalid JSON export (JSONDecodeError).
        _clean_project(tmp_path)
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        # Act
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=[bad], no_reindex=False
        )
        fed_step = next(s for s in result.steps if s.name == "federate")
        # Assert
        assert fed_step.passed is False
        assert fed_step.summary == "export read error"

    def test_non_object_export_fails_with_malformed_summary(
        self, tmp_path: Path
    ) -> None:
        # Arrange: valid JSON but not a dict (a JSON array).
        _clean_project(tmp_path)
        arr = tmp_path / "arr.json"
        arr.write_text("[1, 2, 3]", encoding="utf-8")
        # Act
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=[arr], no_reindex=False
        )
        fed_step = next(s for s in result.steps if s.name == "federate")
        # Assert
        assert fed_step.passed is False
        assert fed_step.summary == "malformed export"
        assert "not a JSON object" in str(fed_step.findings[0]["why"])


# ---------------------------------------------------------------------------
# gate.py — finding projections (shared agent-actionable shape).
# ---------------------------------------------------------------------------


class TestFindingProjections:
    _SHAPE: ClassVar[set[str]] = {
        "kind", "rule", "severity", "locations", "why", "remediation",
    }

    def test_sync_finding_carries_doc_location_and_ref(self) -> None:
        # Act
        finding = _sync_finding(
            {"doc_path": "docs/x.md", "reason": "hash", "ref_id": "graph.x"}
        )
        # Assert: shared shape with a file location and a sync-update hint.
        assert set(finding) >= self._SHAPE
        assert finding["locations"] == [{"file": "docs/x.md"}]
        assert "graph.x" in str(finding["why"])
        assert "sync-update graph.x" in str(finding["remediation"])

    def test_sync_finding_without_doc_path_has_no_location(self) -> None:
        finding = _sync_finding({"reason": "stale", "ref_id": "r"})
        assert finding["locations"] == []

    def test_config_finding_without_file_has_no_location(self) -> None:
        finding = _config_finding("", "drifted")
        assert finding["locations"] == []
        assert set(finding) >= self._SHAPE

    def test_gate_failure_finding_with_missing_names(self) -> None:
        # Arrange: a BREAKING contract failure carrying missing names.
        failure = GateFailure("contract", "PublicAPI", "breaking", ("plan", "tier"))
        # Act
        finding = _gate_failure_finding(failure, "align the client")
        # Assert: the missing names are spelled into the 'why'.
        assert "missing: plan, tier" in str(finding["why"])
        assert finding["remediation"] == "align the client"

    def test_gate_failure_finding_without_missing_names(self) -> None:
        failure = GateFailure("edge", "a --> b", "drift")
        finding = _gate_failure_finding(failure, None)
        assert "missing:" not in str(finding["why"])
        assert finding["remediation"] is None

    def test_simple_finding_is_step_level(self) -> None:
        finding = _simple_finding("reindex", "error", "boom", None)
        assert finding["locations"] == []
        assert finding["kind"] == "reindex"
        assert set(finding) >= self._SHAPE


# ---------------------------------------------------------------------------
# config_sync.py — error / edge branches.
# ---------------------------------------------------------------------------


def _make_conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


class TestConfigSyncEdgeBranches:
    def test_agents_md_without_custom_markers_is_fully_managed(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a fresh AGENTS.md (no custom markers) then corrupt its body.
        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
        generate_agents_md(tmp_path)
        agents = tmp_path / ".beadloom" / "AGENTS.md"
        agents.write_text("totally stale, no markers\n", encoding="utf-8")
        # Act
        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()
        # Assert: whole-file comparison (no markers) reports drift.
        assert any(d.file == ".beadloom/AGENTS.md" for d in drifts)

    def test_unreadable_agents_md_is_skipped_not_crash(self, tmp_path: Path) -> None:
        # Arrange: AGENTS.md is a directory -> read_text raises OSError.
        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".beadloom" / "AGENTS.md").mkdir()
        # Act
        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()
        # Assert: unreadable file is skipped (is_file() is False for a dir).
        assert all(d.file != ".beadloom/AGENTS.md" for d in drifts)

    def test_unreadable_adapter_is_skipped(self, tmp_path: Path) -> None:
        # Arrange: a recognized adapter path that is a directory (unreadable).
        cfg = next(iter(_RULES_CONFIGS.values()))
        (tmp_path / cfg["path"]).mkdir(parents=True)
        # Act
        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()
        # Assert: directory is not a file -> skipped, never crashes.
        assert all(d.file != cfg["path"] for d in drifts)

    def test_fresh_adapter_template_is_not_drift(self, tmp_path: Path) -> None:
        # Arrange: write the exact current adapter template -> in sync.
        cfg = next(iter(_RULES_CONFIGS.values()))
        (tmp_path / cfg["path"]).write_text(_RULES_ADAPTER_TEMPLATE, encoding="utf-8")
        # Act
        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()
        # Assert
        assert all(d.file != cfg["path"] for d in drifts)


# ---------------------------------------------------------------------------
# No false gates (HARD) — exhaustive over NEVER_FAIL_VERDICTS.
# ---------------------------------------------------------------------------


def _edge_with_verdict(verdict: str) -> dict[str, object]:
    return {"src": "a", "dst": "b", "kind": "depends_on", "verdict": verdict}


def _contract_with_verdict(verdict: str) -> dict[str, object]:
    return {"contract_key": "amqp:evt", "verdict": verdict}


class TestNoFalseGateExhaustive:
    def test_clean_landscape_ci_exits_zero(self, tmp_path: Path) -> None:
        # Arrange + Act: a clean repo with clean hub exports.
        _clean_project(tmp_path)
        paths = _write_clean_exports(tmp_path)
        result = CliRunner().invoke(
            main,
            ["ci", "--project", str(tmp_path), "--hub", str(paths[0]),
             "--hub", str(paths[1]), "--fail-on", "default"],
        )
        # Assert
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_clean_landscape_federate_fail_on_exits_zero(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        hub = tmp_path / "hub"
        hub.mkdir()
        paths = _write_clean_exports(tmp_path)
        # Act
        result = CliRunner().invoke(
            main,
            ["federate", str(paths[0]), str(paths[1]),
             "--project", str(hub), "--fail-on", "default"],
        )
        # Assert
        assert result.exit_code == 0

    def test_every_never_fail_verdict_is_inert_under_safe_default(self) -> None:
        # Arrange: a federated graph whose edges + contracts each carry one
        # NEVER_FAIL verdict.  Act: gate with the safe default.  Assert: empty.
        for verdict in sorted(NEVER_FAIL_VERDICTS):
            fed = aggregate_exports(
                [
                    _export(
                        "core",
                        edges=[_edge_with_verdict(verdict)],
                        contracts=[_contract_with_verdict(verdict)],
                    ),
                    _export("other"),
                ],
                now=_T0,
            )
            # Patch the computed verdicts to the safe one under test (the
            # aggregator would otherwise overwrite them); the gate reads
            # whatever verdict the federated edge/contract carries.
            for edge in fed.edges:
                edge["verdict"] = verdict
            for contract in fed.contracts:
                contract["verdict"] = verdict
            assert gate_failures(fed, set(SAFE_DEFAULT_FAIL_ON)) == [], verdict

    def test_no_never_fail_verdict_can_be_armed_via_cli(self, tmp_path: Path) -> None:
        # Every NEVER_FAIL token, passed explicitly to --fail-on, is rejected.
        for verdict in sorted(NEVER_FAIL_VERDICTS):
            hub = tmp_path / f"hub_{verdict}"
            hub.mkdir()
            paths = _write_clean_exports(tmp_path)
            result = CliRunner().invoke(
                main,
                ["federate", str(paths[0]), str(paths[1]),
                 "--project", str(hub), "--fail-on", verdict],
            )
            # Refused with a clear, non-zero error — never silently armed.
            assert result.exit_code != 0, verdict
            assert verdict in result.output.lower(), verdict

    def test_editing_user_claude_prose_does_not_trip_config_check(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a CLAUDE.md with auto markers freshly refreshed, then edit
        # ONLY the human prose outside the markers.
        from beadloom.onboarding.scanner import refresh_claude_md

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "CLAUDE.md").write_text(
            "# Project\n\n## 0.1 Project: x\n\n"
            "- **Current version:** 9.9.9\n\n"
            "original human prose\n",
            encoding="utf-8",
        )
        refresh_claude_md(tmp_path)
        on_disk = (claude_dir / "CLAUDE.md").read_text(encoding="utf-8")
        # Edit only the trailing human prose, never the auto-managed region.
        (claude_dir / "CLAUDE.md").write_text(
            on_disk + "\n\nNEW user-authored note that beadloom must ignore.\n",
            encoding="utf-8",
        )
        # Act
        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()
        # Assert: prose edits never produce a CLAUDE.md drift (#73 class).
        assert all(d.file != ".claude/CLAUDE.md" for d in drifts)


# ---------------------------------------------------------------------------
# Determinism — byte-stable output across repeated runs.
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_ci_json_byte_stable_across_runs(self, tmp_path: Path) -> None:
        # Arrange: a repo with a deterministic, always-failing require rule.
        _write_unsatisfiable_rule(tmp_path)
        generate_agents_md(tmp_path)
        runner = CliRunner()
        args = ["ci", "--format", "json", "--no-reindex", "--project", str(tmp_path)]
        # Reindex once up front so both runs see identical on-disk state.
        runner.invoke(main, ["reindex", "--project", str(tmp_path)])
        # Act: same command twice.
        out1 = runner.invoke(main, args).output
        out2 = runner.invoke(main, args).output
        # Assert: byte-identical output (sorted, stable findings).
        assert out1 == out2
        steps1 = json.loads(out1)["steps"]
        findings1 = [f for s in steps1 for f in s["findings"]]
        assert findings1  # a violation was actually surfaced

    def test_ci_github_byte_stable_across_runs(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        paths = _write_clean_exports(tmp_path)
        runner = CliRunner()
        args = [
            "ci", "--format", "github", "--no-reindex", "--project", str(tmp_path),
            "--hub", str(paths[0]), "--hub", str(paths[1]),
        ]
        out1 = runner.invoke(main, args).output
        out2 = runner.invoke(main, args).output
        assert out1 == out2

    def test_gate_failures_stable_under_edge_reordering(self) -> None:
        # Arrange: two federated graphs differing only by edge order.
        edges = [
            _edge_with_verdict("drift"),
            {"src": "x", "dst": "y", "kind": "depends_on", "verdict": "drift"},
        ]
        fed = aggregate_exports([_export("c", edges=edges), _export("o")], now=_T0)
        for e in fed.edges:
            e["verdict"] = "drift"
        # Act
        a = gate_failures(fed, {"drift"})
        fed.edges.reverse()
        b = gate_failures(fed, {"drift"})
        # Assert: identical sorted output regardless of input order.
        assert a == b
        assert a == sorted(a, key=lambda f: (f.kind, f.identity, f.verdict))


# ---------------------------------------------------------------------------
# --fail-on parsing edge cases (empty / whitespace / unknown token).
# ---------------------------------------------------------------------------


class TestParseFailOn:
    def test_empty_string_resolves_to_safe_default(self) -> None:
        # An empty CSV (no tokens) falls back to the safe default set.
        assert _parse_fail_on("") == set(SAFE_DEFAULT_FAIL_ON)

    def test_whitespace_and_commas_resolve_to_safe_default(self) -> None:
        assert _parse_fail_on("  ,  , ") == set(SAFE_DEFAULT_FAIL_ON)

    def test_default_token_resolves_to_safe_default(self) -> None:
        assert _parse_fail_on("default") == set(SAFE_DEFAULT_FAIL_ON)

    def test_unknown_token_is_kept_verbatim(self) -> None:
        # An unknown verdict token is not a NEVER_FAIL token -> kept (case-folded).
        assert _parse_fail_on("breaking, DRIFT") == {"breaking", "drift"}

    def test_default_mixed_with_explicit_drops_default_keeps_rest(self) -> None:
        # 'default' alongside explicit tokens is discarded; explicit tokens win.
        assert _parse_fail_on("default,breaking") == {"breaking"}


# ---------------------------------------------------------------------------
# No regression — v1 + v2 exports still federate; additive surface intact.
# ---------------------------------------------------------------------------


class TestNoRegression:
    def test_v1_and_v2_exports_federate_together(self) -> None:
        # Arrange: a v1 (schema_version=1) and a v2 (schema_version=2) export.
        v1 = _export("legacy", schema_version=1)
        v2 = _export("modern", schema_version=2)
        # Act
        fed = aggregate_exports([v1, v2], now=_T0)
        # Assert: both satellites present; serialization succeeds.
        repos = {str(s.get("repo")) for s in fed.repos}
        assert {"legacy", "modern"} <= repos
        assert serialize_federation(fed)

    def test_federate_without_fail_on_is_pure_reporting(self, tmp_path: Path) -> None:
        # The additive --fail-on must not change the no-flag behavior: exit 0.
        hub = tmp_path / "hub"
        hub.mkdir()
        paths = _write_clean_exports(tmp_path)
        result = CliRunner().invoke(
            main, ["federate", str(paths[0]), str(paths[1]), "--project", str(hub)]
        )
        assert result.exit_code == 0
        assert (hub / ".beadloom" / "federated.json").exists()

    def test_no_default_or_never_value_overlap(self) -> None:
        # Sanity (regression guard): the safe-default fail-set never overlaps the
        # never-fail set — additive verdict changes cannot quietly arm a verdict.
        assert SAFE_DEFAULT_FAIL_ON.isdisjoint(NEVER_FAIL_VERDICTS)
        all_values = {v.value for v in EdgeVerdict} | {
            v.value for v in ContractVerdict
        }
        for value in all_values:
            assert not (
                value in SAFE_DEFAULT_FAIL_ON and value in NEVER_FAIL_VERDICTS
            )


# ---------------------------------------------------------------------------
# Honest gate — every step reported, none silently dropped.
# ---------------------------------------------------------------------------


class TestHonestGate:
    _ALL_STEPS: ClassVar[set[str]] = {"reindex", "lint", "sync-check", "config-check"}

    def test_all_steps_reported_even_when_lint_fails(self, tmp_path: Path) -> None:
        # Arrange: an unsatisfiable rule -> lint FAILs, but no short-circuit.
        _write_unsatisfiable_rule(tmp_path)
        generate_agents_md(tmp_path)
        # Act
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=[], no_reindex=False
        )
        # Assert: every step still present; the lint step is the one that failed.
        names = {s.name for s in result.steps}
        assert names >= self._ALL_STEPS
        assert any(s.name == "lint" and not s.passed for s in result.steps)
        assert result.ok is False

    def test_federate_step_present_when_hub_given(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        paths = _write_clean_exports(tmp_path)
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=paths, no_reindex=False
        )
        names = [s.name for s in result.steps]
        assert names == ["reindex", "lint", "sync-check", "config-check", "federate"]

    def test_every_step_has_a_nonempty_status(self, tmp_path: Path) -> None:
        # Honesty invariant: no step ever reports an ambiguous/empty status.
        _clean_project(tmp_path)
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=[], no_reindex=True
        )
        assert all(s.status in {"PASS", "FAIL", "SKIP"} for s in result.steps)
        # The skipped reindex is honestly SKIP, not a silent green.
        assert any(s.name == "reindex" and s.status == "SKIP" for s in result.steps)

    def test_gateresult_findings_concatenates_in_step_order(self) -> None:
        # Arrange: a hand-built result with findings on two steps.
        s1 = GateStep("lint", passed=False, findings=[{"rule": "r1"}])
        s2 = GateStep("federate", passed=False, findings=[{"rule": "r2"}])
        result = GateResult(steps=[s1, s2])
        # Assert: findings preserve step order (deterministic aggregation).
        assert [f["rule"] for f in result.findings] == ["r1", "r2"]
