"""`sync-update <doc> --check` must report, never re-baseline (BDL-UX #189).

Measured on this repository while inspecting surface drift: `beadloom sync-update
docs/services/cli.md --check` printed "Re-baselined reference doc …" and the next
`sync-check --json` reported one fewer drifted reference than the run before it.
The flag whose whole contract is "tell me, do not change anything" destroyed the
evidence it was asked to describe — BDL-UX #147 (`lint` mutating its index) in a
different command, and #163 (re-attestation without evidence) reached by accident
rather than by choice.

The cause was ordering: in the non-`--yes` path the reference-doc branch ran
*before* the `if check_only:` guard, so `--check` was honoured only when the
argument resolved to symbol pairs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_DOC = "docs/architecture.md"


def _project_with_a_reference_doc(root: Path) -> Path:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "widget.py").write_text(
        "def render() -> str:\n    return 'x'\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "widget"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "architecture.md").write_text(
        "<!-- beadloom:watches=cli,graph -->\n\n# Architecture\n\nThe CLI surface.\n",
        encoding="utf-8",
    )
    return root


def _baseline(conn_path: Path) -> list[tuple[str, str, str]]:
    from beadloom.infrastructure.db import open_db

    conn = open_db(conn_path)
    try:
        return [
            (r["doc_path"], r["aggregate_hash"], r["status"])
            for r in conn.execute(
                "SELECT doc_path, aggregate_hash, status FROM reference_state "
                "ORDER BY doc_path"
            ).fetchall()
        ]
    finally:
        conn.close()


class TestCheckDoesNotWrite:
    def test_check_on_a_reference_doc_leaves_the_baseline_untouched(
        self, tmp_path: Path
    ) -> None:
        root = _project_with_a_reference_doc(tmp_path / "widget")
        runner = CliRunner()
        assert (
            runner.invoke(
                main, ["init", "--yes", "--mode", "bootstrap", "--project", str(root)]
            ).exit_code
            == 0
        )
        db = root / ".beadloom" / "beadloom.db"
        before = _baseline(db)
        assert before, "fixture must produce a tracked reference doc"

        result = runner.invoke(
            main, ["sync-update", _DOC, "--check", "--project", str(root)]
        )

        assert result.exit_code == 0
        assert "Re-baselined" not in result.output
        assert _baseline(db) == before

    def test_check_reports_the_docs_watches_and_its_drift_status(
        self, tmp_path: Path
    ) -> None:
        root = _project_with_a_reference_doc(tmp_path / "widget")
        runner = CliRunner()
        runner.invoke(
            main, ["init", "--yes", "--mode", "bootstrap", "--project", str(root)]
        )

        result = runner.invoke(
            main, ["sync-update", _DOC, "--check", "--project", str(root)]
        )

        assert _DOC in result.output
        assert "watches" in result.output.lower()

    def test_without_check_the_reference_doc_is_still_re_baselined(
        self, tmp_path: Path
    ) -> None:
        """TESTS MUST BITE: the guard must not disable the command it guards."""
        root = _project_with_a_reference_doc(tmp_path / "widget")
        runner = CliRunner()
        runner.invoke(
            main, ["init", "--yes", "--mode", "bootstrap", "--project", str(root)]
        )

        result = runner.invoke(
            main, ["sync-update", _DOC, "--project", str(root)]
        )

        assert "Re-baselined" in result.output
