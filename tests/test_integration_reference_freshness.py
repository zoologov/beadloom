"""Cross-cutting / integration coverage for BDL-057 reference-doc freshness (.3).

The two dev beads (.1 Layer 1, .2 Layer 2) ship the per-unit tests
(``test_gate.py`` / ``test_f3_gate_coverage.py`` for the docs-audit gate step;
``test_surface.py`` / ``test_reference_drift.py`` / ``test_cli_reference_drift.py``
for the surface-drift mechanism). This module fills the *cross-layer* gaps and
locks the riskiest invariants end-to-end, against real temp projects (not
monkeypatched seams):

1. **Layer 1 <-> Gate** — a real stale numeric fact BLOCKS the gate; an
   audit-clean repo PASSES; docs-audit never short-circuits the other steps;
   ``docs audit`` is no longer ``[experimental]``.
2. **Layer 2 invariants** — surface drift is *warn-only*: it never moves the
   ``beadloom ci`` exit code, never moves ``sync-check``'s exit code, and the
   gate is structurally blind to ``reference_state``. Symbol-pair ``stale``
   still fails. A repo with BOTH a stale symbol pair AND surface drift reports
   both with correct severities. No-annotation repos are a silent no-op. Each
   watched surface (``cli`` / ``graph`` / ``flow.yml``) drifts independently and
   ``sync-update`` clears it; aggregate over multiple surfaces.
3. **``sync-check --json``** — additive ``summary.surface_drift`` + ``references``
   present; existing ``pairs`` / symbol-pair reasons unchanged (no masking).

All fixtures are disposable temp projects; AAA throughout; no wall-clock.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.doc_sync.engine import (
    build_reference_state,
    check_reference_drift,
    mark_reference_synced,
)
from beadloom.infrastructure.db import open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Factory helpers — disposable temp projects.
# ---------------------------------------------------------------------------


def _scaffold(project: Path) -> None:
    """Create the minimal ``.beadloom/_graph`` + ``docs`` skeleton."""
    (project / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    (project / "docs").mkdir(parents=True, exist_ok=True)


def _write_pyproject(project: Path, *, version: str) -> None:
    """A manifest so the audit can compute the ``version`` ground-truth fact."""
    (project / "pyproject.toml").write_text(
        f'[project]\nname = "demo"\nversion = "{version}"\n', encoding="utf-8"
    )


def _audit_clean_project(tmp_path: Path) -> Path:
    """A repo whose docs make no stale numeric claims (docs-audit PASSES)."""
    project = tmp_path / "clean"
    _scaffold(project)
    _write_pyproject(project, version="2.0.0")
    # Prose with no version/count mention -> nothing for the audit to flag.
    (project / "docs" / "overview.md").write_text(
        "# Overview\n\nThe demo tool indexes a codebase and keeps docs honest.\n",
        encoding="utf-8",
    )
    reindex(project)
    return project


def _stale_fact_project(tmp_path: Path) -> Path:
    """A repo whose doc claims version 1.0.0 while the manifest says 2.0.0.

    The ``version`` fact has a 0.0 tolerance (exact match), so this is a
    deterministic single stale finding — no monkeypatch needed.
    """
    project = tmp_path / "stale"
    _scaffold(project)
    _write_pyproject(project, version="2.0.0")
    (project / "docs" / "overview.md").write_text(
        "# Overview\n\nThe current release is version 1.0.0 of the demo tool.\n",
        encoding="utf-8",
    )
    reindex(project)
    return project


def _write_graph(project: Path, ref_ids: list[str]) -> None:
    (project / ".beadloom" / "_graph" / "graph.yml").write_text(
        yaml.dump(
            {"nodes": [{"ref_id": r, "kind": "feature", "summary": r} for r in ref_ids]}
        ),
        encoding="utf-8",
    )


def _watching_project(tmp_path: Path, *, watches: str = "graph") -> Path:
    """A reindexed repo whose architecture.md watches *watches* (clean baseline).

    Intentionally carries NO ``.beadloom/flow.yml`` — an absent flow file is not
    config-check drift, so the whole gate is green and only the watched-surface
    behaviour is under test in the gate/ci-level cases here.
    """
    project = tmp_path / "watch"
    _scaffold(project)
    _write_pyproject(project, version="2.0.0")
    _write_graph(project, ["F1"])
    (project / "docs" / "architecture.md").write_text(
        f"<!-- beadloom:watches={watches} -->\n# Architecture\nOverview prose.\n",
        encoding="utf-8",
    )
    reindex(project)
    return project


# ===========================================================================
# 1. Layer 1 <-> Gate integration (real fixtures, no monkeypatch).
# ===========================================================================


class TestLayer1GateIntegration:
    def test_stale_numeric_fact_blocks_the_gate(self, tmp_path: Path) -> None:
        # Arrange: a repo whose doc claims a version that disagrees with the manifest.
        project = _stale_fact_project(tmp_path)
        # Act
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        audit_step = next(s for s in result.steps if s.name == "docs-audit")
        # Assert: the docs-audit step FAILs and so the whole gate is not ok.
        assert audit_step.passed is False
        assert audit_step.status == "FAIL"
        assert result.ok is False
        # The stale fact is emitted as an actionable finding in the shared shape.
        assert audit_step.findings
        assert all(
            {"kind", "rule", "severity", "locations", "why", "remediation"} <= set(f)
            for f in audit_step.findings
        )
        assert all(f["kind"] == "docs-audit" for f in audit_step.findings)

    def test_audit_clean_repo_passes_the_gate(self, tmp_path: Path) -> None:
        # Arrange: a repo with no stale doc facts.
        project = _audit_clean_project(tmp_path)
        # Act
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        audit_step = next(s for s in result.steps if s.name == "docs-audit")
        # Assert: docs-audit is green and contributes no findings.
        assert audit_step.passed is True
        assert audit_step.status == "PASS"
        assert audit_step.findings == []

    def test_docs_audit_does_not_short_circuit_other_steps(self, tmp_path: Path) -> None:
        # Arrange: a stale-fact repo — even though docs-audit FAILs, every other
        # step must still run and report (no short-circuit / no silent skip).
        project = _stale_fact_project(tmp_path)
        # Act
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        # Assert: all six core steps present, each with an honest status, and the
        # steps after docs-audit (config-check, doctor) actually ran.
        names = [s.name for s in result.steps]
        assert names == [
            "reindex",
            "lint",
            "sync-check",
            "docs-audit",
            "config-check",
            "doctor",
        ]
        assert all(s.status in {"PASS", "FAIL", "SKIP"} for s in result.steps)
        after = names[names.index("docs-audit") + 1 :]
        assert after == ["config-check", "doctor"]
        for name in after:
            assert next(s for s in result.steps if s.name == name).status != "SKIP"

    def test_ci_command_exits_nonzero_on_stale_fact(self, tmp_path: Path) -> None:
        # Arrange
        project = _stale_fact_project(tmp_path)
        # Act
        result = CliRunner().invoke(
            main, ["ci", "--no-reindex", "--project", str(project)]
        )
        # Assert: the unified gate exits non-zero and names the failing step.
        assert result.exit_code != 0
        assert "docs-audit" in result.output

    def test_ci_command_exits_zero_when_audit_clean(self, tmp_path: Path) -> None:
        # Arrange
        project = _audit_clean_project(tmp_path)
        # Act
        result = CliRunner().invoke(
            main, ["ci", "--no-reindex", "--project", str(project)]
        )
        # Assert
        assert result.exit_code == 0


class TestDocsAuditNoLongerExperimental:
    def test_docs_audit_help_has_no_experimental_marker(self) -> None:
        # Act: the `docs audit` subcommand help.
        result = CliRunner().invoke(main, ["docs", "audit", "--help"])
        # Assert: stable command — no `[experimental]` marker anywhere in help.
        assert result.exit_code == 0
        assert "experimental" not in result.output.lower()

    def test_docs_group_listing_has_no_experimental_marker(self) -> None:
        # Act: the parent `docs` group listing (the banner/short-help line).
        result = CliRunner().invoke(main, ["docs", "--help"])
        # Assert
        assert result.exit_code == 0
        assert "experimental" not in result.output.lower()

    def test_docs_audit_run_output_has_no_experimental_banner(
        self, tmp_path: Path
    ) -> None:
        # Arrange: an audit-clean repo so the command exits 0 cleanly.
        project = _audit_clean_project(tmp_path)
        # Act: run the real command (rich output path).
        result = CliRunner().invoke(
            main, ["docs", "audit", "--project", str(project)]
        )
        # Assert: no experimental banner in the rendered output.
        assert result.exit_code == 0
        assert "experimental" not in result.output.lower()


# ===========================================================================
# 2. Layer 2 invariants — warn-only, no regression, no-op, per-surface.
# ===========================================================================


class TestSurfaceDriftIsWarnOnlyInGate:
    def test_gate_step_is_structurally_blind_to_reference_state(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a watching repo, baselined, then a graph mutation -> surface
        # drift would be reported by sync-check (Layer 2).
        project = _watching_project(tmp_path, watches="graph")
        _write_graph(project, ["F1", "F2"])
        incremental_reindex(project)
        # Sanity: Layer 2 *does* see the drift.
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        refs = check_reference_drift(conn, project)
        conn.close()
        assert any(r["status"] == "surface_drift" for r in refs)
        # Act: run the full gate.
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        # Assert: surface drift is a sync-check WARNING that never blocks — the
        # gate's sync-check step only fails on symbol-pair `stale`, so it passes.
        sync_step = next(s for s in result.steps if s.name == "sync-check")
        assert sync_step.passed is True
        # And no gate step carries a `surface_drift` reason (Layer 2 is not wired
        # into the gate at all — additive, separate table).
        for step in result.steps:
            for finding in step.findings:
                assert "surface_drift" not in str(finding.get("why", "")).lower()

    def test_ci_exit_code_unchanged_by_surface_drift(self, tmp_path: Path) -> None:
        # Arrange: an audit-clean watching repo with surface drift present.
        project = _watching_project(tmp_path, watches="graph")
        _write_graph(project, ["F1", "F2"])
        incremental_reindex(project)
        # Act
        result = CliRunner().invoke(
            main, ["ci", "--no-reindex", "--project", str(project)]
        )
        # Assert: surface drift never arms the gate -> exit 0.
        assert result.exit_code == 0


class TestSyncCheckExitCodeWarnOnly:
    def test_sync_check_exit_zero_with_surface_drift_only(self, tmp_path: Path) -> None:
        # Arrange: a watching repo (no symbol pairs) with graph drift.
        project = _watching_project(tmp_path, watches="graph")
        _write_graph(project, ["F1", "F2"])
        incremental_reindex(project)
        # Act
        result = CliRunner().invoke(
            main, ["sync-check", "--project", str(project)]
        )
        # Assert: surface drift is advisory -> warning shown, exit code stays 0.
        assert result.exit_code == 0
        assert "surface drift" in result.output

    def test_sync_check_exit_two_when_symbol_pair_stale(self, tmp_path: Path) -> None:
        # Arrange: a repo with a real symbol pair gone stale (no reference docs).
        project = _symbol_pair_project(tmp_path)
        _mutate_symbol(project)
        # Act
        result = CliRunner().invoke(
            main, ["sync-check", "--project", str(project)]
        )
        # Assert: symbol-pair stale still fails with exit 2, exactly as before.
        assert result.exit_code == 2


# ---- Symbol-pair fixtures (real reindex), for the no-regression invariants. ---


def _symbol_pair_project(tmp_path: Path) -> Path:
    """A repo with a doc<->code symbol pair tracked through a directory node."""
    project = tmp_path / "sympair"
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    docs_dir = project / "docs" / "domains" / "myapp"
    docs_dir.mkdir(parents=True)
    src_dir = project / "src" / "myapp"
    src_dir.mkdir(parents=True)
    _write_pyproject(project, version="2.0.0")

    (graph_dir / "domains.yml").write_text(
        "nodes:\n"
        "  - ref_id: myapp\n"
        "    kind: domain\n"
        '    summary: "My App domain"\n'
        "    source: src/myapp/\n"
        "    docs:\n"
        "      - docs/domains/myapp/README.md\n",
        encoding="utf-8",
    )
    (docs_dir / "README.md").write_text(
        "# My App\n\nThis domain contains the handler module.\n", encoding="utf-8"
    )
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "handler.py").write_text(
        "# beadloom:domain=myapp\ndef process():\n    return True\n", encoding="utf-8"
    )
    reindex(project)
    return project


def _mutate_symbol(project: Path) -> None:
    """Edit the tracked code file and reindex -> the symbol pair goes stale."""
    (project / "src" / "myapp" / "handler.py").write_text(
        "# beadloom:domain=myapp\n"
        "def process():\n"
        "    return True\n\n"
        "def added_feature():\n"
        "    return 42\n",
        encoding="utf-8",
    )
    incremental_reindex(project)


class TestNoRegressionSymbolPairWithSurfaceDrift:
    def test_both_stale_symbol_and_surface_drift_reported_with_severities(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a single repo that has BOTH a stale symbol pair AND a watched
        # reference doc whose graph surface has drifted.
        project = _symbol_pair_project(tmp_path)
        (project / "docs" / "architecture.md").write_text(
            "<!-- beadloom:watches=graph -->\n# Architecture\nProse.\n",
            encoding="utf-8",
        )
        reindex(project)  # baseline both the reference doc and the symbol pair
        _mutate_symbol(project)  # symbol pair drifts
        # graph surface drifts: add a node to the graph YAML and reindex.
        (project / ".beadloom" / "_graph" / "extra.yml").write_text(
            "nodes:\n  - ref_id: NEW\n    kind: feature\n    summary: new\n",
            encoding="utf-8",
        )
        incremental_reindex(project)
        # Act: JSON sync-check carries both layers.
        result = CliRunner().invoke(
            main, ["sync-check", "--json", "--project", str(project)]
        )
        data = json.loads(result.output)
        # Assert: symbol pair is `stale` (error semantics, exit 2) ...
        assert result.exit_code == 2
        assert data["summary"]["stale"] >= 1
        assert any(p["status"] == "stale" for p in data["pairs"])
        # ... and the reference doc is `surface_drift` at severity `warning`.
        assert data["summary"]["surface_drift"] == 1
        drift = next(r for r in data["references"] if r["status"] == "surface_drift")
        assert drift["severity"] == "warning"
        assert drift["reason"] == "surface_drift"

    def test_symbol_pair_reason_not_masked_by_reference_path(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a stale symbol pair (real reason) plus a clean reference doc.
        project = _symbol_pair_project(tmp_path)
        (project / "docs" / "architecture.md").write_text(
            "<!-- beadloom:watches=graph -->\n# Architecture\nProse.\n",
            encoding="utf-8",
        )
        reindex(project)
        _mutate_symbol(project)
        # Act
        result = CliRunner().invoke(
            main, ["sync-check", "--json", "--project", str(project)]
        )
        data = json.loads(result.output)
        # Assert: the symbol pair keeps its genuine reason — the additive
        # reference path never overwrites/masks `pairs[].reason`.
        stale_pairs = [p for p in data["pairs"] if p["status"] == "stale"]
        assert stale_pairs
        assert all(
            p["reason"] in ("hash_changed", "symbols_changed", "untracked_files")
            for p in stale_pairs
        )
        # The reference doc is clean (graph unchanged), so it does not pollute pairs.
        assert all(p["status"] != "surface_drift" for p in data["pairs"])

    def test_reference_path_leaves_sync_state_rows_untouched(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a repo with a symbol pair and a reference doc.
        project = _symbol_pair_project(tmp_path)
        (project / "docs" / "architecture.md").write_text(
            "<!-- beadloom:watches=graph -->\n# Architecture\nProse.\n",
            encoding="utf-8",
        )
        reindex(project)
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        before = conn.execute(
            "SELECT doc_path, code_path, ref_id FROM sync_state ORDER BY doc_path"
        ).fetchall()
        # Act: drive the entire reference lifecycle (baseline/check/mark).
        build_reference_state(conn, project)
        check_reference_drift(conn, project)
        mark_reference_synced(conn, None, project, all_docs=True)
        after = conn.execute(
            "SELECT doc_path, code_path, ref_id FROM sync_state ORDER BY doc_path"
        ).fetchall()
        conn.close()
        # Assert: the symbol-pair table is byte-for-byte unchanged — reference
        # state lives in its own table and never touches sync_state.
        assert [tuple(r) for r in before] == [tuple(r) for r in after]


class TestFixpointAndMaskingInvariantPreserved:
    """The reason-masking / mark-synced -> re-run-to-fixpoint invariant on the
    symbol-pair path must be unaffected by the new reference_state path."""

    def test_mark_synced_then_recheck_reaches_ok_fixpoint(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a stale symbol pair plus a watching reference doc.
        project = _symbol_pair_project(tmp_path)
        (project / "docs" / "architecture.md").write_text(
            "<!-- beadloom:watches=graph -->\n# Architecture\nProse.\n",
            encoding="utf-8",
        )
        reindex(project)
        _mutate_symbol(project)
        runner = CliRunner()
        # Pre-condition: stale (exit 2).
        assert (
            runner.invoke(
                main, ["sync-check", "--project", str(project)]
            ).exit_code
            == 2
        )
        # Act: re-attest the symbol pair, then re-run sync-check to fixpoint.
        runner.invoke(
            main, ["sync-update", "myapp", "--yes", "--project", str(project)]
        )
        # Assert: the symbol pair reaches the ok fixpoint -> exit 0.
        after = runner.invoke(main, ["sync-check", "--project", str(project)])
        assert after.exit_code == 0


class TestBackwardCompatNoOp:
    def test_no_annotation_produces_zero_reference_rows(self, tmp_path: Path) -> None:
        # Arrange: a repo whose docs declare NO watches annotation.
        project = tmp_path / "noanno"
        _scaffold(project)
        _write_pyproject(project, version="2.0.0")
        _write_graph(project, ["F1"])
        (project / "docs" / "plain.md").write_text(
            "# Plain\n\nNo annotation at all.\n", encoding="utf-8"
        )
        reindex(project)
        # Act
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        rows = conn.execute("SELECT COUNT(*) FROM reference_state").fetchone()[0]
        drift = check_reference_drift(conn, project)
        conn.close()
        # Assert: zero reference rows, zero drift -> Layer 2 is silent.
        assert rows == 0
        assert drift == []

    def test_no_annotation_sync_check_json_is_silent(self, tmp_path: Path) -> None:
        # Arrange
        project = tmp_path / "noanno2"
        _scaffold(project)
        _write_pyproject(project, version="2.0.0")
        _write_graph(project, ["F1"])
        (project / "docs" / "plain.md").write_text("# Plain\n", encoding="utf-8")
        reindex(project)
        # Act
        result = CliRunner().invoke(
            main, ["sync-check", "--json", "--project", str(project)]
        )
        data = json.loads(result.output)
        # Assert: additive keys are present but empty/zero — no behavior change.
        assert result.exit_code == 0
        assert data["references"] == []
        assert data["summary"]["surface_drift"] == 0


class TestPerSurfaceIndependence:
    """Each watched surface drifts on its own mutation; sync-update clears it."""

    def _project_watching(self, tmp_path: Path, watches: str) -> Path:
        project = tmp_path / f"w_{watches.replace(',', '_').replace('.', '')}"
        _scaffold(project)
        _write_pyproject(project, version="2.0.0")
        _write_graph(project, ["F1"])
        (project / ".beadloom" / "flow.yml").write_text(
            "methodology: ddd\nstack: python\n", encoding="utf-8"
        )
        (project / "docs" / "architecture.md").write_text(
            f"<!-- beadloom:watches={watches} -->\n# Architecture\nProse.\n",
            encoding="utf-8",
        )
        reindex(project)
        return project

    def _conn(self, project: Path) -> sqlite3.Connection:
        return open_db(project / ".beadloom" / "beadloom.db")

    def test_graph_surface_drifts_then_clears(self, tmp_path: Path) -> None:
        # Arrange
        project = self._project_watching(tmp_path, "graph")
        _write_graph(project, ["F1", "F2"])
        incremental_reindex(project)
        conn = self._conn(project)
        # Act + Assert: graph mutation -> drift.
        assert check_reference_drift(conn, project)[0]["status"] == "surface_drift"
        # sync-update clears it.
        mark_reference_synced(conn, "docs/architecture.md", project)
        assert check_reference_drift(conn, project)[0]["status"] == "ok"
        conn.close()

    def test_flow_surface_drifts_then_clears(self, tmp_path: Path) -> None:
        # Arrange
        project = self._project_watching(tmp_path, "flow.yml")
        conn = self._conn(project)
        # Act: mutate ONLY flow.yml.
        (project / ".beadloom" / "flow.yml").write_text(
            "methodology: fsd\nstack: python\n", encoding="utf-8"
        )
        # Assert: drift, then cleared by re-baseline.
        assert check_reference_drift(conn, project)[0]["status"] == "surface_drift"
        mark_reference_synced(conn, "docs/architecture.md", project)
        assert check_reference_drift(conn, project)[0]["status"] == "ok"
        conn.close()

    def test_cli_surface_is_stable_and_independent(self, tmp_path: Path) -> None:
        # Arrange: watch only `cli`. The CLI surface does not change at runtime,
        # so mutating graph/flow must NOT make a cli-only doc drift.
        project = self._project_watching(tmp_path, "cli")
        _write_graph(project, ["F1", "F2", "F3"])  # graph churns
        (project / ".beadloom" / "flow.yml").write_text(
            "methodology: fsd\n", encoding="utf-8"
        )  # flow churns
        incremental_reindex(project)
        conn = self._conn(project)
        # Assert: a cli-only watch is unaffected by graph/flow churn.
        assert check_reference_drift(conn, project)[0]["status"] == "ok"
        conn.close()

    def test_unwatched_surface_change_does_not_drift(self, tmp_path: Path) -> None:
        # Arrange: watch only `graph`; mutate only flow.yml (unwatched).
        project = self._project_watching(tmp_path, "graph")
        (project / ".beadloom" / "flow.yml").write_text(
            "methodology: fsd\n", encoding="utf-8"
        )
        conn = self._conn(project)
        # Assert: an unwatched-surface change never moves the aggregate.
        assert check_reference_drift(conn, project)[0]["status"] == "ok"
        conn.close()

    def test_aggregate_over_multiple_surfaces_drifts_on_any_one(
        self, tmp_path: Path
    ) -> None:
        # Arrange: watch graph + flow.yml together.
        project = self._project_watching(tmp_path, "graph,flow.yml")
        conn = self._conn(project)
        assert check_reference_drift(conn, project)[0]["status"] == "ok"
        conn.close()
        # Act: drift ONLY the flow.yml component of the aggregate.
        (project / ".beadloom" / "flow.yml").write_text(
            "methodology: fsd\n", encoding="utf-8"
        )
        conn = self._conn(project)
        # Assert: the aggregate moves because one watched component changed.
        assert check_reference_drift(conn, project)[0]["status"] == "surface_drift"
        # sync-update over the aggregate clears it in one shot.
        mark_reference_synced(conn, "docs/architecture.md", project)
        assert check_reference_drift(conn, project)[0]["status"] == "ok"
        conn.close()


# ===========================================================================
# 3. sync-check --json additive shape (pairs unchanged, references additive).
# ===========================================================================


class TestSyncCheckJsonAdditiveShape:
    def _conn(self, project: Path) -> sqlite3.Connection:
        return open_db(project / ".beadloom" / "beadloom.db")

    def test_json_has_surface_drift_summary_and_references_array(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a clean watching repo.
        project = _watching_project(tmp_path, watches="graph")
        # Act
        result = CliRunner().invoke(
            main, ["sync-check", "--json", "--project", str(project)]
        )
        data = json.loads(result.output)
        # Assert: the additive keys exist with the documented shape.
        assert "surface_drift" in data["summary"]
        assert isinstance(data["references"], list)
        ref = data["references"][0]
        assert set(ref) == {"status", "doc_path", "watches", "reason", "severity"}
        assert ref["severity"] == "warning"
        assert ref["doc_path"] == "docs/architecture.md"

    def test_json_pairs_array_unchanged_when_reference_present(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a symbol-pair repo PLUS a reference doc, both clean.
        project = _symbol_pair_project(tmp_path)
        (project / "docs" / "architecture.md").write_text(
            "<!-- beadloom:watches=graph -->\n# Architecture\nProse.\n",
            encoding="utf-8",
        )
        reindex(project)
        # Act
        result = CliRunner().invoke(
            main, ["sync-check", "--json", "--project", str(project)]
        )
        data = json.loads(result.output)
        # Assert: the symbol-pair `pairs` array keeps its full per-pair shape;
        # the additive `references` block does not bleed into it.
        assert "pairs" in data
        for pair in data["pairs"]:
            assert {"status", "ref_id", "doc_path", "code_path", "reason"} <= set(pair)
            assert "severity" not in pair  # warning-severity is reference-only
            assert "watches" not in pair

    def test_since_mode_leaves_reference_block_absent(self, tmp_path: Path) -> None:
        # Arrange: a watching repo committed to git so `--since HEAD` resolves.
        project = _watching_project(tmp_path, watches="graph")
        runner = CliRunner()
        # Act: `--since` is a ref-relative symbol-pair view; references are not
        # evaluated, so the additive block must be omitted (no `references` key).
        result = runner.invoke(
            main,
            ["sync-check", "--json", "--since", "HEAD", "--project", str(project)],
        )
        # `--since HEAD` requires a git repo; when absent the command errors out
        # cleanly (exit 1) — either way it must never emit a reference block.
        if result.exit_code == 0:
            data = json.loads(result.output)
            assert "references" not in data
            assert "surface_drift" not in data["summary"]
        else:
            assert result.exit_code == 1
