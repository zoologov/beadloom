# beadloom:domain=graph
"""S3b verify/harden: full module classification + the PROMOTED (error) coverage-lint.

BDL-051 Slice 3b / BEAD-15 (test). These tests harden the dev's S3b work
(`tests/test_module_coverage_hardening.py`, `tests/test_rule_engine.py`) WITHOUT
duplicating its passing cases. The dev's tests already pin: rule-is-error, the
live repo has zero coverage findings, dir-source-covers (tui), serialize
round-trips, exempt-glob nuances. This file adds the gaps the bead calls out:

* **error-level regression guard** — the whole point: an `error`-severity
  coverage rule + a NEW uncovered module must FAIL ``lint --strict`` (rc 1).
  The dev only proves the *clean* tree exits 0; this proves the gate actually
  bites (no future shadow code can slip in unnoticed).
* **dir-source coverage depth** — a dir source covers nested subtrees
  (``tui/screens/*``, ``tui/widgets/*``), does NOT over-cover siblings outside
  the dir, and nested/overlapping dir sources both count.
* **site-generation cluster** — all 9 ``application/site*.py`` are covered by the
  single ``site-generation`` node; none flagged; the node round-trips reindex.
* **every new node resolves** — ``ctx`` returns for a sample of new features +
  components; ``component``-kind nodes load/validate/serialize.
* **annotation <-> node consistency** — bidirectional: every annotation value
  names a declared node, and every new file-source node's file carries the
  matching annotation (or is the node's source).
* **sync-check** — the new SPEC/DOC pairs are tracked, and fresh in any checkout
  that holds a baseline to compare them against. A clean room holds neither
  baseline, and the freshness case declares that rather than failing there
  (BDL-UX #258); the decision is exercised in
  ``TestTheFreshnessSkipIsDecidedByTheBaseline``.
* **exempt still minimal** — exactly the 4 seeded globs, nothing newly hidden.

All deterministic, no network. Real-repo assertions use the live graph as-is.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.doc_sync.engine import BASELINE_NONE
from beadloom.graph.rule_engine import (
    ModuleCoverageRule,
    evaluate_module_coverage_rules,
)
from beadloom.infrastructure.db import create_schema
from beadloom.services.cli import main
from tests.support.freshness_baseline import (
    no_baseline_skip_reason,
    pairs_have_no_freshness_baseline,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


# The classes that run ``ctx``/``lint``/``sync-check`` against this repository's
# own graph take ``self_check_snapshot`` and pass it as ``--project``: a copy of
# the working tree indexed once per session, never the live index (BDL-074 A2).
# Until A1 a module-wide autouse fixture reindexed the LIVE index for every test
# here, the synthetic ones included; until A2 the classes that assert on this
# repository read it after reindexing it in place.


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    yield conn
    conn.close()


def _insert_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    symbol_name: str,
    annotations: dict[str, str],
) -> None:
    conn.execute(
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, "function", 1, 10, json.dumps(annotations), "h"),
    )


def _mc_rule(
    *,
    exempt: tuple[str, ...] = (),
    severity: str = "error",
) -> ModuleCoverageRule:
    return ModuleCoverageRule(
        name="module-coverage",
        description="every src module must be a node or exempt",
        source_root="src/beadloom/",
        min_symbols=1,
        exempt=exempt,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# THE REGRESSION GUARD: error severity actually FAILS lint --strict
# ---------------------------------------------------------------------------


class TestErrorLevelRegressionGuard:
    """The promoted (error) coverage-lint must FAIL the gate on a new shadow module.

    This is the entire point of S3b: once every module is classified, the rule is
    promoted warn -> error so any *future* uncovered module breaks CI. The dev's
    tests prove the clean tree exits 0; these prove the gate bites otherwise.
    """

    def _make_project(self, tmp_path: Path, *, severity: str) -> Path:
        """A synthetic project mirroring the real rule: one covered + one shadow module."""
        project = tmp_path / "proj"
        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (project / "docs").mkdir()
        (graph_dir / "services.yml").write_text(
            "version: 1\n"
            "nodes:\n"
            "  - ref_id: beadloom\n"
            "    kind: service\n"
            "    summary: root\n"
            "  - ref_id: graph\n"
            "    kind: domain\n"
            "    summary: graph domain\n"
            "    source: src/beadloom/graph/\n"
            "  - ref_id: graph-loader\n"
            "    kind: component\n"
            "    summary: loader\n"
            "    source: src/beadloom/graph/loader.py\n"
            "edges:\n"
            "  - src: graph\n"
            "    dst: beadloom\n"
            "    kind: part_of\n"
            "  - src: graph-loader\n"
            "    dst: graph\n"
            "    kind: part_of\n"
        )
        (graph_dir / "rules.yml").write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: module-coverage\n"
            "    description: every module must be a node or exempt\n"
            f"    severity: {severity}\n"
            "    module_coverage:\n"
            "      source_root: src/beadloom/\n"
            "      min_symbols: 1\n"
            "      exempt:\n"
            "        - '**/__init__.py'\n"
        )
        src = project / "src" / "beadloom" / "graph"
        src.mkdir(parents=True)
        (src / "loader.py").write_text(
            "# beadloom:component=graph-loader\ndef load():\n    pass\n"
        )
        # The SHADOW module: real code, no annotation, not a node source, not exempt.
        (src / "shadow.py").write_text("def secret():\n    return 1\n")
        return project

    def test_new_uncovered_module_fails_lint_strict_at_error(self, tmp_path: Path) -> None:
        """error severity + a new shadow module -> ``lint --strict`` exits NON-zero."""
        project = self._make_project(tmp_path, severity="error")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 1, result.output
        assert "shadow.py" in result.output

    def test_same_shadow_module_at_warn_does_not_fail_strict(self, tmp_path: Path) -> None:
        """Control: the IDENTICAL shadow at warn severity does NOT fail --strict (rc 0).

        Proves it is the *error* promotion — not merely the finding's presence —
        that fails the gate. This is the warn->error contrast the bead asks for.
        """
        project = self._make_project(tmp_path, severity="warn")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_finding_carries_error_severity_in_json(self, tmp_path: Path) -> None:
        """The shadow finding is emitted with severity ``error`` (not silently demoted)."""
        project = self._make_project(tmp_path, severity="error")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--format", "json", "--project", str(project)])
        # stdout, not output: plain `lint` now names on STDERR that its exit
        # code ignores error-severity violations without --strict (BDL-UX #147),
        # and CliRunner's `output` merges the two streams.
        payload = json.loads(result.stdout)
        coverage = [v for v in payload["violations"] if v["rule_name"] == "module-coverage"]
        assert coverage, payload
        assert all(v["severity"] == "error" for v in coverage)
        assert any("shadow.py" in str(v["file_path"]) for v in coverage)

    def test_covering_the_module_restores_green(self, tmp_path: Path) -> None:
        """Annotating the shadow module makes ``lint --strict`` pass again (rc 0).

        Demonstrates the gate is satisfiable by classification, not just by lowering
        severity — the closed loop S3b establishes.
        """
        project = self._make_project(tmp_path, severity="error")
        shadow = project / "src" / "beadloom" / "graph" / "shadow.py"
        shadow.write_text("# beadloom:component=graph-loader\ndef secret():\n    return 1\n")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# dir-source coverage: nested depth, no over-cover, overlapping/nested sources
# ---------------------------------------------------------------------------


class TestDirSourceCoverageDepth:
    """A directory `source` covers its whole subtree (deeply), but not outside it."""

    def test_dir_source_covers_deeply_nested_modules(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """tui/ (dir source) covers BOTH tui/screens/* and tui/widgets/* — nested depth."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        for path in (
            "src/beadloom/tui/screens/main_screen.py",
            "src/beadloom/tui/widgets/status_bar.py",
            "src/beadloom/tui/app.py",
        ):
            _insert_symbol(mem_db, path, "fn", {})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/tui/screens/main_screen.py" not in flagged
        assert "src/beadloom/tui/widgets/status_bar.py" not in flagged
        assert "src/beadloom/tui/app.py" not in flagged

    def test_dir_source_does_not_over_cover_siblings_outside(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """tui/ does NOT cover a sibling under a different dir (e.g. graph/), nor a prefix-twin.

        Guards against a naive ``startswith`` that would let ``tui/`` cover a
        sibling directory whose name merely starts with ``tui`` (``tui_extra/``).
        """
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/outside.py", "fn", {"domain": "graph"})
        _insert_symbol(mem_db, "src/beadloom/tui_extra/twin.py", "fn", {"domain": "graph"})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/graph/outside.py" in flagged
        assert "src/beadloom/tui_extra/twin.py" in flagged

    def test_file_source_node_covers_only_its_own_file(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A file-source node covers ONLY its file, not a sibling in the same dir."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph-loader", "component", "loader", "src/beadloom/graph/loader.py"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/loader.py", "fn", {})
        _insert_symbol(mem_db, "src/beadloom/graph/sibling.py", "fn", {"domain": "graph"})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/graph/loader.py" not in flagged
        assert "src/beadloom/graph/sibling.py" in flagged

    def test_overlapping_nested_dir_sources_both_cover(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A nested dir source inside an outer dir source: modules under either are covered."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui-widgets", "component", "widgets", "src/beadloom/tui/widgets/"),
        )
        _insert_symbol(mem_db, "src/beadloom/tui/widgets/deep/inner.py", "fn", {})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/tui/widgets/deep/inner.py" not in flagged


# ---------------------------------------------------------------------------
# site-generation cluster: all 9 site*.py covered by ONE node
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Every new node resolves via ctx; component kind loads/validates
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# annotation <-> node consistency (bidirectional)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# sync-check: new SPEC/DOC pairs tracked + fresh
# ---------------------------------------------------------------------------


class TestTheFreshnessSkipIsDecidedByTheBaseline:
    """The skip above must fire in a room and in no other checkout.

    A skip is the cheapest way to make a check quiet, so the decision behind
    this one is a function with its own cases rather than a condition nobody
    exercises. Every case here is synthetic: the point is which shapes of
    ``sync-check`` output license a skip, and that question needs no tree.
    """

    @staticmethod
    def _pair(
        baseline: str, *, status: str = "unverified", ref_id: str = "sync-check"
    ) -> dict[str, object]:
        """One pair in the shape ``sync-check --json`` emits."""
        return {
            "ref_id": ref_id,
            "status": status,
            "baseline": baseline,
            "doc_path": "domains/doc-sync/features/sync-check/SPEC.md",
            "code_path": "src/beadloom/doc_sync/engine.py",
            "reason": "no_baseline" if baseline == BASELINE_NONE else "ok",
        }

    def test_a_population_compared_against_nothing_has_no_baseline(self) -> None:
        """The room's own shape: every pair unverified against nothing."""
        pairs = [self._pair(BASELINE_NONE) for _ in range(3)]

        assert pairs_have_no_freshness_baseline(pairs) is True

    def test_an_unverified_pair_with_an_index_baseline_is_not_a_missing_baseline(
        self,
    ) -> None:
        """``sibling_symbols_changed`` is a finding about the tree, not a room.

        The tree carried 34 pairs in exactly this shape when this was written. A
        decision that read ``status`` instead of ``baseline`` would skip on them
        and take the whole check down with a verdict about the environment.
        """
        pairs = [self._pair("index", status="unverified")]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_a_stale_pair_with_a_git_baseline_is_not_a_missing_baseline(self) -> None:
        """The verdict this test exists to report still reaches the assertion."""
        pairs = [self._pair("git:HEAD", status="stale")]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_one_baselined_pair_among_unbaselined_ones_still_answers(self) -> None:
        """A checkout that compared anything is a checkout that can be judged."""
        pairs = [
            self._pair(BASELINE_NONE),
            self._pair(BASELINE_NONE),
            self._pair("index", status="ok"),
        ]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_an_empty_population_is_not_a_missing_baseline(self) -> None:
        """No pairs is a broken sample, and the caller must fail rather than skip."""
        assert pairs_have_no_freshness_baseline([]) is False

    def test_a_pair_that_reports_no_baseline_field_does_not_buy_a_skip(self) -> None:
        """A renamed or dropped field fails the check; it never quiets it.

        The decision reads one key. If that key ever stops being emitted, the
        wrong direction to fail in is silence.
        """
        pairs: list[dict[str, object]] = [{"ref_id": "sync-check", "status": "unverified"}]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_the_skip_reason_names_what_would_make_the_test_run(self) -> None:
        """The constraint the suite already enforces, applied to this skip.

        ``test_no_platform_xfail_waits_for_a_runner_that_will_not_come`` forbids
        a prediction nothing can adjudicate. The same rule in this shape: a skip
        that says only "it does not run here" is the ignored red with a quieter
        colour, so the reason names the count it saw, the baselines it wants and
        the two places that supply them.
        """
        reason = no_baseline_skip_reason([self._pair(BASELINE_NONE) for _ in range(4)])

        assert "4 sampled" in reason
        assert BASELINE_NONE in reason
        assert ".git" in reason
        assert "beadloom clean-room" in reason


# ---------------------------------------------------------------------------
# exempt stays minimal + honest (only the 4 seeded globs)
# ---------------------------------------------------------------------------


