"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_module_coverage_hardening.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.graph.rule_engine import (
    ModuleCoverageRule,
    load_rules,
)
from beadloom.infrastructure.db import create_schema
from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Iterator


#: This repository's own rules.yml, named from this file rather than from the
#: working directory (BDL-074 A1). A tracked source file, read as text.
_REAL_RULES_YML = Path(__file__).resolve().parents[3] / ".beadloom" / "_graph" / "rules.yml"


@pytest.fixture()
def mem_db() -> Iterator[sqlite3.Connection]:
    """Empty in-memory DB with the full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    yield conn
    conn.close()


class TestRealRepoCoveragePromoted:
    """BDL-051 S3b / BEAD-14: every module is classified, so the rule is `error`."""

    def test_live_repo_module_coverage_rule_is_error(self) -> None:
        """The repo's `module-coverage` rule has been PROMOTED from warn to error."""
        rules = load_rules(_REAL_RULES_YML)
        mc = [r for r in rules if isinstance(r, ModuleCoverageRule)]
        assert len(mc) == 1
        assert mc[0].severity == "error"

    def test_live_repo_has_zero_module_coverage_findings(
        self, self_check_snapshot: Path
    ) -> None:
        """`module-coverage` reports ZERO findings over the live src tree (no shadow code)."""
        runner = CliRunner()
        # The self-check snapshot's index reflects the working tree it was
        # copied from, so we read it (--no-reindex) without re-mutating it for
        # the session's other self-checks. This keeps the assertion
        # order-independent (surfaced by pytest-randomly in S1; BDL-074 A2).
        result = runner.invoke(
            main,
            ["lint", "--format", "json", "--project", str(self_check_snapshot), "--no-reindex"],
        )
        assert result.exit_code in (0, 1), result.output
        payload = json.loads(result.stdout)
        findings = payload["violations"]
        coverage = [f for f in findings if f.get("rule_name") == "module-coverage"]
        assert coverage == [], coverage


class TestSerializeRoundTrip:
    def test_real_rules_yml_module_coverage_loads_into_db(
        self, mem_db: sqlite3.Connection
    ) -> None:
        """The repo's real rules.yml round-trips: module-coverage lands as module_coverage."""
        from beadloom.application.reindex import ReindexResult, _load_rules_into_db

        rules_path = _REAL_RULES_YML
        result = ReindexResult()
        _load_rules_into_db(rules_path, mem_db, result)
        mem_db.commit()
        assert result.errors == []
        row = mem_db.execute(
            "SELECT rule_type FROM rules WHERE name = ?", ("module-coverage",)
        ).fetchone()
        assert row is not None
        assert row["rule_type"] == "module_coverage"


class TestUnregisteredFeatureCandidateRetired:
    def test_no_active_unregistered_rule_in_real_rules_yml(self) -> None:
        """The repo's rules.yml carries NO active unregistered_feature_candidate rule."""
        rules_path = _REAL_RULES_YML
        rules = load_rules(rules_path)
        type_names = {type(r).__name__ for r in rules}
        assert "UnregisteredFeatureCandidateRule" not in type_names

    def test_real_rules_yml_has_module_coverage_rule(self) -> None:
        """The successor module-coverage rule IS present in the real rules.yml.

        Post-S3b (BEAD-14): every module is classified, so the rule has been
        PROMOTED from warn to error (any future shadow module fails CI).
        """
        rules_path = _REAL_RULES_YML
        rules = load_rules(rules_path)
        mc = [r for r in rules if isinstance(r, ModuleCoverageRule)]
        assert len(mc) == 1
        assert mc[0].name == "module-coverage"
        assert mc[0].severity == "error"
        # The minimally-seeded exempt list is visible (not a silent escape hatch).
        assert "**/__init__.py" in mc[0].exempt


class TestRealRepoCoverageGuard:
    """Post-S3b (BEAD-14): every module is classified, so the live tree has ZERO
    coverage findings. The formerly-shadow modules are now covered by a node."""

    def _real_coverage_findings(self, repo_root: Path) -> set[str]:
        runner = CliRunner()
        # --no-reindex: the self-check snapshot is indexed once, when it is
        # built, so we read it without re-mutating it.
        result = runner.invoke(
            main,
            ["lint", "--format", "porcelain", "--project", str(repo_root), "--no-reindex"],
        )
        assert result.exit_code == 0, result.output
        flagged: set[str] = set()
        for line in result.output.splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[0] == "module-coverage":
                flagged.add(parts[3])
        return flagged

    def test_formerly_shadow_modules_now_covered(self, self_check_snapshot: Path) -> None:
        """The modules classified in S3b are no longer flagged (they have nodes now)."""
        flagged = self._real_coverage_findings(self_check_snapshot)
        for covered in (
            "src/beadloom/graph/loader.py",
            "src/beadloom/infrastructure/db.py",
            "src/beadloom/doc_sync/engine.py",
        ):
            assert covered not in flagged, f"{covered} should be covered post-S3b"

    def test_coverage_lint_reports_no_findings(self, self_check_snapshot: Path) -> None:
        """Every src module is classified — the coverage lint reports zero findings."""
        flagged = self._real_coverage_findings(self_check_snapshot)
        assert flagged == set(), flagged
