"""Tests for the unified CI gate — ``application/gate.py`` + ``beadloom ci``.

BDL-039 F3 BEAD-04. The gate composes reindex -> lint --strict -> sync-check ->
config-check -> (optional) federate --fail-on into ONE ``GateResult`` with a
single exit code, reporting every step that ran and its honest PASS/FAIL/SKIP
result, with findings emitted in the shared json/github shape across all steps.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import GateResult, GateStep, run_ci_gate
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


# ---------------------------------------------------------------------------
# Helpers — build a clean / dirty fixture project
# ---------------------------------------------------------------------------


def _write_rules_yml(project_root: Path, *, domains: list[str]) -> None:
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    rules = "rules:\n"
    for d in domains:
        rules += (
            f"  - name: {d}-needs-parent\n"
            f"    require: {{}}\n"
            f"    description: domain {d}\n"
        )
    (graph_dir / "rules.yml").write_text(rules, encoding="utf-8")


def _clean_project(project_root: Path) -> None:
    """A project whose every gate step passes (no rules => no lint violations)."""
    (project_root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(project_root)


def _export(repo: str) -> dict[str, object]:
    """Minimal satellite export artifact (no breaks)."""
    return {
        "schema_version": 1,
        "repo": repo,
        "exported_at": "2026-06-01T00:00:00+00:00",
        "nodes": [{"ref_id": "svc", "kind": "service", "name": repo}],
        "edges": [],
        "contracts": [],
        "lifecycle": {},
    }


def _breaking_exports(tmp_path: Path) -> list[Path]:
    """Two exports where a GraphQL consumer references a field the producer dropped."""
    producer = {
        "schema_version": 1,
        "repo": "backend",
        "exported_at": "2026-06-01T00:00:00+00:00",
        "nodes": [{"ref_id": "api", "kind": "schema", "summary": "api"}],
        "edges": [
            {
                "src": "api",
                "dst": "api",
                "kind": "produces",
                "lifecycle": "active",
                "contract": {
                    "protocol": "graphql",
                    "schema": "PublicAPI",
                    "direction": "produces",
                    "exposed": ["plan"],
                },
            }
        ],
    }
    consumer = {
        "schema_version": 1,
        "repo": "ui",
        "exported_at": "2026-06-01T00:00:00+00:00",
        "nodes": [{"ref_id": "client", "kind": "page", "summary": "client"}],
        "edges": [
            {
                "src": "client",
                "dst": "client",
                "kind": "consumes",
                "lifecycle": "active",
                "contract": {
                    "protocol": "graphql",
                    "schema": "PublicAPI",
                    "direction": "consumes",
                    "references": ["plan", "removedField"],
                },
            }
        ],
    }
    p1 = tmp_path / "backend.json"
    p2 = tmp_path / "ui.json"
    p1.write_text(json.dumps(producer), encoding="utf-8")
    p2.write_text(json.dumps(consumer), encoding="utf-8")
    return [p1, p2]


# ---------------------------------------------------------------------------
# run_ci_gate — orchestrator unit behaviour
# ---------------------------------------------------------------------------


class TestRunCiGate:
    def test_clean_repo_all_steps_pass_ok_true(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert isinstance(result, GateResult)
        assert result.ok is True
        # reindex, lint, sync-check, docs-audit, config-check, doctor all ran.
        names = [s.name for s in result.steps]
        assert names == [
            "reindex",
            "lint",
            "sync-check",
            "docs-audit",
            "config-check",
            "doctor",
        ]
        assert all(s.passed for s in result.steps)
        assert all(s.status == "PASS" for s in result.steps)
        assert result.findings == []

    def test_docs_audit_step_runs_directly_after_sync_check(
        self, tmp_path: Path
    ) -> None:
        """The gate MUST run docs-audit immediately after sync-check."""
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        names = [s.name for s in result.steps]
        assert "docs-audit" in names
        assert names.index("docs-audit") == names.index("sync-check") + 1

    def test_docs_audit_clean_passes(self, tmp_path: Path) -> None:
        """A repo with no stale doc facts passes the docs-audit step."""
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        audit_step = next(s for s in result.steps if s.name == "docs-audit")
        assert audit_step.passed is True
        assert audit_step.status == "PASS"
        assert audit_step.findings == []

    def test_docs_audit_stale_fact_fails_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A single stale doc fact (stale>0) fails the docs-audit step and the gate."""
        import beadloom.application.gate as gate_mod
        from beadloom.doc_sync.audit import AuditFinding, AuditResult, Fact
        from beadloom.doc_sync.scanner import Mention

        def _fake_run_audit(
            project_root: object, db: object, *, scan_paths: object = None
        ) -> AuditResult:
            fact = Fact(name="version", value="2.0.0", source="pyproject.toml")
            mention = Mention(
                fact_name="version",
                value="1.0.0",
                file=tmp_path / "README.md",
                line=3,
                context="version line",
            )
            stale = AuditFinding(
                mention=mention, fact=fact, status="stale", tolerance=0.0
            )
            return AuditResult(facts={"version": fact}, findings=[stale], unmatched=[])

        monkeypatch.setattr(gate_mod, "_run_audit", _fake_run_audit)
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        audit_step = next(s for s in result.steps if s.name == "docs-audit")
        assert audit_step.passed is False
        assert audit_step.status == "FAIL"
        assert result.ok is False
        # The failing step carries a finding in the shared shape.
        assert any(f.get("rule") for f in audit_step.findings)
        assert all(
            {"kind", "rule", "severity", "locations", "why", "remediation"} <= set(f)
            for f in audit_step.findings
        )

    def test_docs_audit_fresh_fact_does_not_fail_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fresh findings (no stale) keep the docs-audit step green."""
        import beadloom.application.gate as gate_mod
        from beadloom.doc_sync.audit import AuditFinding, AuditResult, Fact
        from beadloom.doc_sync.scanner import Mention

        def _fake_run_audit(
            project_root: object, db: object, *, scan_paths: object = None
        ) -> AuditResult:
            fact = Fact(name="version", value="2.0.0", source="pyproject.toml")
            mention = Mention(
                fact_name="version",
                value="2.0.0",
                file=tmp_path / "README.md",
                line=3,
                context="version line",
            )
            fresh = AuditFinding(
                mention=mention, fact=fact, status="fresh", tolerance=0.0
            )
            return AuditResult(facts={"version": fact}, findings=[fresh], unmatched=[])

        monkeypatch.setattr(gate_mod, "_run_audit", _fake_run_audit)
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        audit_step = next(s for s in result.steps if s.name == "docs-audit")
        assert audit_step.passed is True
        assert audit_step.findings == []

    def test_doctor_step_runs(self, tmp_path: Path) -> None:
        """The gate MUST run beadloom doctor (graph integrity) as a step."""
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        doctor_step = next(s for s in result.steps if s.name == "doctor")
        assert doctor_step.passed is True
        assert doctor_step.status == "PASS"

    def test_doctor_error_fails_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A doctor ERROR-severity check fails the gate with a doctor FAIL step."""
        import beadloom.application.gate as gate_mod
        from beadloom.application.doctor import Check, Severity

        def _fake_run_checks(conn: object, *, project_root: object = None) -> list[Check]:
            return [Check("graph_integrity", Severity.ERROR, "broken edge: a -> missing")]

        monkeypatch.setattr(gate_mod, "_run_doctor_checks", _fake_run_checks)
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        doctor_step = next(s for s in result.steps if s.name == "doctor")
        assert doctor_step.passed is False
        assert doctor_step.status == "FAIL"
        assert result.ok is False
        assert any(f.get("rule") for f in doctor_step.findings)

    def test_doctor_warning_does_not_fail_gate(self, tmp_path: Path) -> None:
        """Doctor WARNING/INFO checks must NOT block CI (no false gate)."""
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        doctor_step = next(s for s in result.steps if s.name == "doctor")
        # The Beadloom-style clean fixture has warnings but no errors -> PASS.
        assert doctor_step.passed is True

    def test_no_reindex_skips_step_one(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=True)
        reindex_step = next(s for s in result.steps if s.name == "reindex")
        assert reindex_step.status == "SKIP"
        assert reindex_step.passed is True  # a skipped step does not fail the gate
        assert result.ok is True

    def test_lint_violation_fails_gate_and_collects_finding(self, tmp_path: Path) -> None:
        # A require-rule that cannot be satisfied -> an error-level violation.
        _write_rules_yml(tmp_path, domains=["nonexistent-domain"])
        generate_agents_md(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        lint_step = next(s for s in result.steps if s.name == "lint")
        assert lint_step.passed is False
        assert lint_step.status == "FAIL"
        assert result.ok is False
        # The failing step still has at least one finding in the shared shape.
        assert any(f.get("rule") for f in lint_step.findings)
        # All other steps still ran (no short-circuit).
        assert {"reindex", "lint", "sync-check", "config-check"} <= {
            s.name for s in result.steps
        }

    def test_config_drift_fails_gate(self, tmp_path: Path) -> None:
        _write_rules_yml(tmp_path, domains=["graph"])
        generate_agents_md(tmp_path)
        # Drift the graph after generating AGENTS.md.
        _write_rules_yml(tmp_path, domains=["graph", "contracts"])
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        cfg_step = next(s for s in result.steps if s.name == "config-check")
        assert cfg_step.passed is False
        assert result.ok is False

    def test_hub_breaking_fails_gate(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        exports = _breaking_exports(tmp_path)
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=exports, no_reindex=False
        )
        fed_step = next(s for s in result.steps if s.name == "federate")
        assert fed_step.passed is False
        assert result.ok is False
        assert fed_step.findings  # the breaking verdict surfaced as a finding

    def test_hub_clean_passes(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        p1 = tmp_path / "a.json"
        p2 = tmp_path / "b.json"
        p1.write_text(json.dumps(_export("a")), encoding="utf-8")
        p2.write_text(json.dumps(_export("b")), encoding="utf-8")
        result = run_ci_gate(
            tmp_path, fail_on=None, hub_exports=[p1, p2], no_reindex=False
        )
        assert result.ok is True
        assert any(s.name == "federate" and s.passed for s in result.steps)

    def test_no_hub_skips_federate_step(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert all(s.name != "federate" for s in result.steps)

    def test_deterministic(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        r1 = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        r2 = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert [s.name for s in r1.steps] == [s.name for s in r2.steps]
        assert [s.status for s in r1.steps] == [s.status for s in r2.steps]


# ---------------------------------------------------------------------------
# GateStep / GateResult model
# ---------------------------------------------------------------------------


class TestGateModel:
    def test_step_status_strings(self) -> None:
        assert GateStep("lint", passed=True, skipped=False).status == "PASS"
        assert GateStep("lint", passed=False, skipped=False).status == "FAIL"
        assert GateStep("reindex", passed=True, skipped=True).status == "SKIP"

    def test_ok_requires_all_steps_pass(self) -> None:
        ok = GateResult(steps=[GateStep("a", passed=True), GateStep("b", passed=True)])
        assert ok.ok is True
        bad = GateResult(steps=[GateStep("a", passed=True), GateStep("b", passed=False)])
        assert bad.ok is False


# ---------------------------------------------------------------------------
# beadloom ci CLI
# ---------------------------------------------------------------------------


class TestCiCommand:
    def test_clean_repo_exits_zero_and_names_every_step(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        result = CliRunner().invoke(main, ["ci", "--project", str(tmp_path)])
        assert result.exit_code == 0
        for step in ("reindex", "lint", "sync-check", "config-check", "doctor"):
            assert step in result.output
        assert "PASS" in result.output

    def test_lint_violation_exits_one(self, tmp_path: Path) -> None:
        _write_rules_yml(tmp_path, domains=["nonexistent-domain"])
        generate_agents_md(tmp_path)
        result = CliRunner().invoke(main, ["ci", "--project", str(tmp_path)])
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_no_reindex_reports_skip(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        result = CliRunner().invoke(
            main, ["ci", "--no-reindex", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "SKIP" in result.output

    def test_json_format_uniform_across_steps(self, tmp_path: Path) -> None:
        _write_rules_yml(tmp_path, domains=["nonexistent-domain"])
        generate_agents_md(tmp_path)
        result = CliRunner().invoke(
            main, ["ci", "--format", "json", "--project", str(tmp_path)]
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "ok" in data and data["ok"] is False
        assert "steps" in data
        step_names = {s["name"] for s in data["steps"]}
        assert {"reindex", "lint", "sync-check", "config-check"} <= step_names
        # Every finding uses the shared agent-actionable shape.
        all_findings = [f for s in data["steps"] for f in s["findings"]]
        assert all_findings
        for f in all_findings:
            assert {"kind", "rule", "severity", "locations", "why", "remediation"} <= set(
                f
            )

    def test_github_format_emits_annotations(self, tmp_path: Path) -> None:
        _write_rules_yml(tmp_path, domains=["nonexistent-domain"])
        generate_agents_md(tmp_path)
        result = CliRunner().invoke(
            main, ["ci", "--format", "github", "--project", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "::error" in result.output


# ---------------------------------------------------------------------------
# GitHub annotation format — valid workflow-command shape
# ---------------------------------------------------------------------------


class TestGithubAnnotationFormat:
    def test_finding_with_location_emits_valid_file_line(self) -> None:
        """Annotations MUST use `file=<path>,line=<n>` — not the invalid
        `file=<path:line>` colon shape that GitHub does not parse."""
        from beadloom.services.cli import _format_gate_github

        finding = {
            "kind": "forbid_import",
            "rule": "tui-no-direct-infra",
            "severity": "error",
            "locations": [{"file": "src/beadloom/tui/app.py", "line": 12}],
            "why": "tui imports infrastructure directly",
            "remediation": "route through application",
        }
        result = GateResult(
            steps=[GateStep("lint", passed=False, findings=[finding], summary="1 error")]
        )
        out = _format_gate_github(result)
        # Correct workflow-command shape: file=<path>,line=<n>
        assert "file=src/beadloom/tui/app.py,line=12" in out
        # The invalid colon-joined shape must NOT appear.
        assert "file=src/beadloom/tui/app.py:12" not in out
        assert "::error " in out

    def test_finding_without_line_emits_file_only(self) -> None:
        from beadloom.services.cli import _format_gate_github

        finding = {
            "kind": "config-check",
            "rule": "config-drift",
            "severity": "error",
            "locations": [{"file": ".beadloom/AGENTS.md"}],
            "why": "agent-config drift",
            "remediation": "run setup-rules --refresh",
        }
        result = GateResult(
            steps=[GateStep("config-check", passed=False, findings=[finding])]
        )
        out = _format_gate_github(result)
        assert "file=.beadloom/AGENTS.md::" in out
        assert ",line=" not in out.split("file=.beadloom/AGENTS.md")[1].split("::")[0]

    def test_graph_level_finding_omits_file_param(self) -> None:
        from beadloom.services.cli import _format_gate_github

        finding = {
            "kind": "require",
            "rule": "domain-needs-parent",
            "severity": "error",
            "locations": [],
            "why": "missing parent",
            "remediation": None,
        }
        result = GateResult(steps=[GateStep("lint", passed=False, findings=[finding])])
        out = _format_gate_github(result)
        assert "::error::" in out
        assert "file=" not in out

    def test_hub_breaking_exits_one(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        exports = _breaking_exports(tmp_path)
        result = CliRunner().invoke(
            main,
            ["ci", "--hub", str(exports[0]), "--hub", str(exports[1]),
             "--project", str(tmp_path)],
        )
        assert result.exit_code == 1
        assert "federate" in result.output
