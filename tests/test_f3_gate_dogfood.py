"""F3 dogfood — the gate BLOCKS each break-class (BDL-039 F3 BEAD-06).

The F3 success criterion is: *a CI gate blocks a boundary violation /
cross-service break / drifted agent-config regardless of which tool or human
wrote the code.* This module proves it with committed, anonymized, byte-stable
fixtures under ``tests/fixtures/f3_gate/`` — synthetic role-named artifacts that
do NOT derive from any private repo — and asserts, for each of the three
break-classes, BOTH the non-zero exit AND that the output is agent-actionable
(a remediation hint / the missing GraphQL name / which file drifted).

This formalizes the live signal already seen during BEAD-04, where the gate
caught a real stale auto-managed section in Beadloom's own AGENTS.md.

Determinism: the committed export fixtures carry injected ``exported_at`` /
``commit_sha``; the gate is invoked with ``now`` pinned where the API allows.
The boundary + config-drift fixtures are COPIED into ``tmp_path`` before the
gate runs, because the gate writes ``.beadloom/`` artifacts — the committed
fixtures themselves are never mutated.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.graph.federation import (
    aggregate_exports,
    gate_failure_remediation,
    gate_failures,
)
from beadloom.onboarding.config_sync import check_config_drift
from beadloom.services.cli import main

_FIXTURES = Path(__file__).parent / "fixtures" / "f3_gate"
_T0 = "2026-06-01T00:00:00+00:00"  # injected reference "now"


def _copy_fixture(name: str, dest: Path) -> Path:
    """Copy a committed fixture project into a writable ``dest`` and return it."""
    project = dest / name
    shutil.copytree(_FIXTURES / name, project)
    return project


def _load_breaking_exports() -> list[dict[str, object]]:
    """Load the two committed satellite exports forming the BREAKING landscape."""
    base = _FIXTURES / "breaking_landscape"
    producer = json.loads((base / "producer.json").read_text(encoding="utf-8"))
    consumer = json.loads((base / "consumer.json").read_text(encoding="utf-8"))
    return [producer, consumer]


# ---------------------------------------------------------------------------
# (a) Boundary violation — lint / run_ci_gate blocks + carries remediation.
# ---------------------------------------------------------------------------


class TestGateBlocksBoundaryViolation:
    """A deliberate cross-module import breach must fail the gate, with a hint."""

    def test_gate_blocks_and_emits_remediation(self, tmp_path: Path) -> None:
        # Arrange: a fixture project whose checkout module imports catalog
        # directly, breaching a committed ``forbid_import`` boundary rule.
        project = _copy_fixture("boundary_project", tmp_path)

        # Act: the unified gate reindexes then lints --strict.
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)

        # Assert: the gate BLOCKS (non-zero verdict) on the lint step.
        assert result.ok is False
        lint_step = next(s for s in result.steps if s.name == "lint")
        assert lint_step.passed is False
        assert lint_step.status == "FAIL"
        # And the finding is agent-actionable: it names the rule and how to fix.
        findings = [f for f in lint_step.findings if f.get("rule") == "checkout-no-import-catalog"]
        assert findings, "the forbidden import must surface as a finding"
        remediation = findings[0].get("remediation")
        assert isinstance(remediation, str)
        assert "remove the import" in remediation

    def test_cli_ci_exits_nonzero_on_boundary_breach(self, tmp_path: Path) -> None:
        # Arrange.
        project = _copy_fixture("boundary_project", tmp_path)
        # Act: invoke the gate through the CLI in github-annotation format.
        result = CliRunner().invoke(
            main, ["ci", "--format", "github", "--project", str(project)]
        )
        # Assert: non-zero exit + an inline annotation an agent/CI can act on.
        assert result.exit_code == 1
        assert "::error" in result.output
        assert "checkout-no-import-catalog" in result.output


# ---------------------------------------------------------------------------
# (b) Cross-service BREAKING — federate gate blocks + names the missing field.
# ---------------------------------------------------------------------------


class TestGateBlocksCrossServiceBreaking:
    """A consumer referencing a GraphQL name absent from the producer's SDL."""

    def test_gate_failures_names_missing_graphql_name(self) -> None:
        # Arrange: two committed satellite exports — producer exposes
        # {account, plan}; consumer references {plan, subscriptionTier}.
        exports = _load_breaking_exports()
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        failures = gate_failures(fed, {"breaking"})
        # Assert: a BREAKING contract failure naming the missing name.
        breaking = [f for f in failures if f.verdict == "breaking"]
        assert len(breaking) == 1
        assert breaking[0].kind == "contract"
        assert breaking[0].missing == ("subscriptionTier",)
        # And the remediation hint is agent-actionable (names the missing name).
        hint = gate_failure_remediation(breaking[0])
        assert hint is not None
        assert "subscriptionTier" in hint

    def test_ci_hub_gate_blocks_with_nonzero_exit(self, tmp_path: Path) -> None:
        # Arrange: write the committed exports next to a clean hub project.
        hub = tmp_path / "hub"
        hub.mkdir()
        exports = _load_breaking_exports()
        paths: list[Path] = []
        for export in exports:
            repo = str(export["repo"])
            p = tmp_path / f"{repo}.json"
            p.write_text(json.dumps(export), encoding="utf-8")
            paths.append(p)
        # Act: the unified gate runs the landscape gate over the fixtures.
        result = run_ci_gate(hub, fail_on=None, hub_exports=paths, no_reindex=False)
        # Assert: the federate step BLOCKS, naming the break.
        assert result.ok is False
        fed_step = next(s for s in result.steps if s.name == "federate")
        assert fed_step.passed is False
        names = " ".join(str(f.get("why", "")) + str(f.get("remediation", ""))
                          for f in fed_step.findings)
        assert "subscriptionTier" in names

    def test_cli_ci_hub_exits_nonzero(self, tmp_path: Path) -> None:
        # Arrange.
        hub = tmp_path / "hub"
        hub.mkdir()
        producer = _FIXTURES / "breaking_landscape" / "producer.json"
        consumer = _FIXTURES / "breaking_landscape" / "consumer.json"
        # Act.
        result = CliRunner().invoke(
            main,
            ["ci", "--hub", str(producer), "--hub", str(consumer),
             "--project", str(hub)],
        )
        # Assert: a non-zero exit naming the federate step.
        assert result.exit_code == 1
        assert "federate" in result.output


# ---------------------------------------------------------------------------
# (c) Drifted agent-config — config-check blocks + names which file.
# ---------------------------------------------------------------------------


class TestGateBlocksConfigDrift:
    """A stale auto-managed CLAUDE.md section must fail the gate (the BEAD-04 class)."""

    def _materialize_drifted_project(self, tmp_path: Path) -> Path:
        # The committed template carries a stale auto-managed block; the test
        # materializes it as .claude/CLAUDE.md in a writable project.
        project = tmp_path / "drifted"
        claude_dir = project / ".claude"
        claude_dir.mkdir(parents=True)
        drifted = (
            _FIXTURES / "config_drift_project" / "claude_md_drifted.txt"
        ).read_text(encoding="utf-8")
        (claude_dir / "CLAUDE.md").write_text(drifted, encoding="utf-8")
        return project

    def test_check_config_drift_reports_which_file(self, tmp_path: Path) -> None:
        # Arrange.
        project = self._materialize_drifted_project(tmp_path)
        # Act.
        conn = sqlite3.connect(":memory:")
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()
        # Assert: the drift names the offending file (agent-actionable: which file).
        claude_drifts = [d for d in drifts if d.file == ".claude/CLAUDE.md"]
        assert len(claude_drifts) == 1
        assert claude_drifts[0].reason

    def test_gate_blocks_on_config_drift(self, tmp_path: Path) -> None:
        # Arrange.
        project = self._materialize_drifted_project(tmp_path)
        # Act: the unified gate runs config-check.
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        # Assert: the gate BLOCKS on the config-check step.
        assert result.ok is False
        cfg_step = next(s for s in result.steps if s.name == "config-check")
        assert cfg_step.passed is False
        assert cfg_step.status == "FAIL"

    def test_cli_ci_exits_nonzero_on_config_drift(self, tmp_path: Path) -> None:
        # Arrange.
        project = self._materialize_drifted_project(tmp_path)
        # Act.
        result = CliRunner().invoke(
            main, ["ci", "--format", "json", "--project", str(project)]
        )
        # Assert: non-zero exit + the config-check step reported as failing.
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False
        cfg = next(s for s in data["steps"] if s["name"] == "config-check")
        assert cfg["status"] == "FAIL"
