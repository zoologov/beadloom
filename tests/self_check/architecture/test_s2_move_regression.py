"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_s2_move_regression.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    ImportBoundaryRule,
    evaluate_import_boundary_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

    from beadloom.graph.rules import Violation


_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]


def _insert_import(
    conn: sqlite3.Connection, file_path: str, import_path: str
) -> None:
    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        (file_path, 1, import_path, None, "h"),
    )


def _crossings(violations: list[Violation]) -> list[Violation]:
    """Only the boundary breaches.

    Since BDL-UX #150 the evaluator also reports a rule that CANNOT match anything
    in the index (``rule_type == "rule_liveness"``, always ``warn``). In these
    one-import fixtures the sibling char-class rule legitimately matches nothing, so
    that advisory is expected noise here — the subject of these tests is which
    crossings the two globs catch.
    """
    return [v for v in violations if v.rule_type == "forbid_import"]


@pytest.fixture()
def boundary_rules() -> list[ImportBoundaryRule]:
    """Load the two real ai_agents char-class forbid_import rules from the live
    project rules.yml so the test exercises the SHIPPED patterns, not a copy."""
    rules = load_rules(_REPO_ROOT / ".beadloom" / "_graph" / "rules.yml")
    ai = [
        r
        for r in rules
        if isinstance(r, ImportBoundaryRule)
        and r.name in {"core-no-import-ai-agents", "application-no-import-ai-agents"}
    ]
    assert len(ai) == 2, f"expected the 2 ai_agents boundary rules, got {ai}"
    return ai


# Every core source dir that the char-class globs are meant to cover.
_CORE_DIRS = [
    "application",
    "context_oracle",
    "doc_sync",
    "graph",
    "infrastructure",
    "onboarding",
    "services",
    "tui",
]


def _beadloom_ctx_json(ref_id: str, root: Path) -> dict[str, object]:
    """Resolve the ``beadloom`` console script to an absolute path (no partial
    path -> no S607) and return the parsed ``ctx --json`` bundle.

    Run in *root*, the self-check snapshot (BDL-074 A2): run in this repository,
    ``ctx`` read — and could rebuild — the live index."""
    import json
    import shutil

    exe = shutil.which("beadloom")
    assert exe is not None, "beadloom console script not on PATH"
    proc = subprocess.run(  # noqa: S603 - resolved absolute path, fixed argv
        [exe, "ctx", ref_id, "--json"],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    parsed: dict[str, object] = json.loads(proc.stdout)
    return parsed


class TestAiAgentsBoundaryRule:
    @pytest.fixture()
    def conn(self, tmp_path: Path) -> Iterator[sqlite3.Connection]:
        db = open_db(tmp_path / "b.db")
        create_schema(db)
        yield db
        db.close()

    @pytest.mark.parametrize("core_dir", _CORE_DIRS)
    def test_core_importing_ai_agents_is_forbidden(
        self,
        conn: sqlite3.Connection,
        boundary_rules: list[ImportBoundaryRule],
        core_dir: str,
    ) -> None:
        """Every core domain/service importing ai_agents IS flagged — the two
        char-class globs together cover every core source dir."""
        _insert_import(
            conn,
            f"src/beadloom/{core_dir}/foo.py",
            "beadloom.ai_agents.ai_techwriter.runner",
        )
        conn.commit()
        violations = _crossings(evaluate_import_boundary_rules(conn, boundary_rules))
        assert len(violations) >= 1, f"{core_dir} -> ai_agents not flagged"
        assert violations[0].severity == "error"

    def test_ai_agents_importing_itself_is_allowed(
        self, conn: sqlite3.Connection, boundary_rules: list[ImportBoundaryRule]
    ) -> None:
        """ai_agents internal imports must NOT false-positive (the a[!i]* and
        [!a]* classes both exclude the ``ai_agents`` dir)."""
        _insert_import(
            conn,
            "src/beadloom/ai_agents/ai_techwriter/runner.py",
            "beadloom.ai_agents.ai_techwriter.seams",
        )
        conn.commit()
        violations = _crossings(evaluate_import_boundary_rules(conn, boundary_rules))
        assert violations == []

    def test_ai_agents_importing_application_is_allowed(
        self, conn: sqlite3.Connection, boundary_rules: list[ImportBoundaryRule]
    ) -> None:
        """ai_agents is a leaf CONSUMER — it MAY import the core read-APIs
        (e.g. application). The rule only forbids the reverse direction."""
        _insert_import(
            conn,
            "src/beadloom/ai_agents/ai_techwriter/packet.py",
            "beadloom.application.reindex",
        )
        _insert_import(
            conn,
            "src/beadloom/ai_agents/ai_techwriter/scope.py",
            "beadloom.context_oracle.builder",
        )
        conn.commit()
        violations = _crossings(evaluate_import_boundary_rules(conn, boundary_rules))
        assert violations == []

    def test_core_importing_core_is_not_flagged(
        self, conn: sqlite3.Connection, boundary_rules: list[ImportBoundaryRule]
    ) -> None:
        """The rule only fires on a ``to`` of ai_agents — ordinary core->core
        imports are untouched."""
        _insert_import(
            conn,
            "src/beadloom/application/reindex.py",
            "beadloom.graph.loader",
        )
        conn.commit()
        assert _crossings(evaluate_import_boundary_rules(conn, boundary_rules)) == []

    def test_exactly_one_rule_fires_per_core_dir(
        self,
        conn: sqlite3.Connection,
        boundary_rules: list[ImportBoundaryRule],
    ) -> None:
        """The two char-class globs are DISJOINT (application matched only by
        a[!i]*, everything-else only by [!a]*) — no core->ai_agents import is
        double-counted."""
        _insert_import(
            conn,
            "src/beadloom/application/reindex.py",
            "beadloom.ai_agents.ai_techwriter.runner",
        )
        _insert_import(
            conn,
            "src/beadloom/graph/loader.py",
            "beadloom.ai_agents.ai_techwriter.runner",
        )
        conn.commit()
        violations = _crossings(evaluate_import_boundary_rules(conn, boundary_rules))
        # one per import, never doubled by overlapping patterns.
        assert len(violations) == 2
        by_file = {v.file_path for v in violations}
        assert by_file == {
            "src/beadloom/application/reindex.py",
            "src/beadloom/graph/loader.py",
        }


class TestGraphResolution:
    def test_ai_techwriter_feature_resolves(self, self_check_snapshot: Path) -> None:
        bundle = _beadloom_ctx_json("ai-techwriter", self_check_snapshot)
        focus = bundle["focus"]
        assert isinstance(focus, dict)
        assert focus["ref_id"] == "ai-techwriter"
        graph = bundle["graph"]
        assert isinstance(graph, dict)
        node_ids = {n["ref_id"] for n in graph["nodes"]}
        assert "ai_agents" in node_ids
        assert "ai-techwriter" in node_ids

    def test_feature_is_part_of_ai_agents_domain(self, self_check_snapshot: Path) -> None:
        graph = _beadloom_ctx_json("ai-techwriter", self_check_snapshot)["graph"]
        assert isinstance(graph, dict)
        edges = graph["edges"]
        assert any(
            e["src"] == "ai-techwriter"
            and e["dst"] == "ai_agents"
            and e["kind"] == "part_of"
            for e in edges
        )
