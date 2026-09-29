# beadloom:domain=application
"""S2 regressions — the three checks that reported success without checking.

Each test here reproduces a measured false green, not a hypothetical one:

* **#142** — an incremental ``reindex`` never re-extracted imports, so
  ``lint --strict`` on the documented ``reindex && lint`` loop reported a clean
  boundary while the working tree held a real violation. Its tests are the
  reindex's, under ``tests/integration/application/reindex/`` (split by node,
  BDL-074 ``beadloom-2mj3.7``).
* **#146** — a node that declares ``docs:`` but whose files carry no matching
  annotation contributed NO sync pairs at all, so ``sync-check`` printed a
  green line meaning "nothing was looked at".
* **#147** — ``lint``, a verb that reads as a check, wrote to the index it
  inspects; and its supposedly read-only ``--no-reindex`` form reported
  "0 violations" against an index that did not exist, creating it in passing.

Each test is written to bite on the pre-fix code: see the bead comments for the
measured before/after.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.reindex import reindex
from beadloom.services.cli import main
from tests.support.boundary_break_project import (
    ALPHA_CLEAN,
    ALPHA_VIOLATING,
    index_db,
    make_project,
    query,
    services_yml,
)

if TYPE_CHECKING:
    from pathlib import Path

# A component that declares a doc and a source directory holding no code — the
# residue that must be REPORTED rather than counted as clean.
_GAMMA_NODE_YML = """\
  - ref_id: gamma
    kind: component
    summary: Gamma component
    source: src/app/gamma/
    docs:
      - components/gamma.md
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# #146 — a node that declares docs is never silently unchecked
# ---------------------------------------------------------------------------


class TestDeclaredDocsAreGenuinelyChecked:
    """"Clean" from sync-check must mean "checked", never "no pairs exist"."""

    def test_component_node_contributes_a_sync_pair(self, tmp_path: Path) -> None:
        """A component declaring docs + source gets pairs even with no annotation."""
        project = make_project(tmp_path)
        reindex(project)

        pairs = query(project, "SELECT ref_id, code_path FROM sync_state WHERE ref_id = 'alpha'")
        assert pairs == [("alpha", "src/app/alpha/service.py")]

    def test_component_doc_goes_stale_when_its_code_changes(self, tmp_path: Path) -> None:
        """The pair is real: editing the code makes the component doc stale."""
        project = make_project(tmp_path)
        reindex(project)
        (project / "src" / "app" / "alpha" / "service.py").write_text(
            ALPHA_CLEAN.replace("return 1", "return 42")
        )

        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--json", "--project", str(project)])
        payload = json.loads(result.stdout)
        stale = [p for p in payload["pairs"] if p["status"] == "stale" and p["ref_id"] == "alpha"]
        assert stale, payload
        # It must be the PAIR that went stale — a coverage-gap entry carries no
        # code_path and would let this pass without any pairing at all.
        assert stale[0]["code_path"] == "src/app/alpha/service.py"
        assert stale[0]["reason"] == "hash_changed"
        assert result.exit_code == 2

    def test_a_node_with_no_indexed_code_is_reported_not_hidden(self, tmp_path: Path) -> None:
        """A doc-declaring node that yields no pair is NAMED, not silently green."""
        project = make_project(tmp_path)
        graph = project / ".beadloom" / "_graph" / "services.yml"
        graph.write_text(services_yml(extra_nodes=_GAMMA_NODE_YML))
        (project / "docs" / "components" / "gamma.md").write_text("# Gamma\n")
        reindex(project)

        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--json", "--project", str(project)])
        payload = json.loads(result.stdout)
        assert payload["summary"]["unchecked"] == 1
        assert [u["ref_id"] for u in payload["unchecked"]] == ["gamma"]

    def test_unchecked_nodes_never_change_the_exit_code(self, tmp_path: Path) -> None:
        """The new signal is advisory — no adopter's green project turns red."""
        project = make_project(tmp_path)
        graph = project / ".beadloom" / "_graph" / "services.yml"
        graph.write_text(services_yml(extra_nodes=_GAMMA_NODE_YML))
        (project / "docs" / "components" / "gamma.md").write_text("# Gamma\n")
        reindex(project)

        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "gamma" in result.output
        assert "not checked" in result.output


# ---------------------------------------------------------------------------
# #147 — lint has a genuinely read-only path
# ---------------------------------------------------------------------------


class TestLintReadOnlyPath:
    """``lint --no-reindex`` reads the index; it never writes it, nor invents it."""

    def test_no_reindex_leaves_the_database_byte_identical(self, tmp_path: Path) -> None:
        """Measured the way #147 measured it: sha256 of beadloom.db before/after.

        The index is put in ``journal_mode=delete`` first — the shape a database
        restored from a copy or an artifact has. ``open_db`` unconditionally sets
        WAL, which rewrites the file header, so the pre-fix read-only claim held
        only for a database that happened to already be in WAL.
        """
        project = make_project(tmp_path)
        reindex(project)
        conn = sqlite3.connect(index_db(project))
        conn.execute("PRAGMA journal_mode=delete")
        conn.close()
        for sidecar in (project / ".beadloom").glob("beadloom.db-*"):
            sidecar.unlink()

        before = _sha256(index_db(project))
        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--no-reindex", "--strict", "--project", str(project)]
        )

        assert _sha256(index_db(project)) == before, "a read-only lint wrote to the index"
        assert result.exit_code == 0, result.output

    def test_no_reindex_on_a_missing_index_refuses_instead_of_reporting_clean(
        self, tmp_path: Path
    ) -> None:
        """No index is not a clean project — and lint must not create one."""
        project = make_project(tmp_path)
        reindex(project)
        for artifact in (project / ".beadloom").glob("beadloom.db*"):
            artifact.unlink()

        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--no-reindex", "--strict", "--project", str(project)]
        )

        assert result.exit_code == 2, result.output
        assert not index_db(project).exists(), "a read-only lint created the index it was reading"
        assert "0 violations" not in result.output

    def test_no_reindex_still_reports_a_real_violation(self, tmp_path: Path) -> None:
        """Read-only must not mean blind: the violation in the index is reported."""
        project = make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_VIOLATING)
        reindex(project)

        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--no-reindex", "--strict", "--project", str(project)]
        )
        assert result.exit_code == 1
        assert "alpha-no-beta-import" in result.output

    def test_plain_lint_names_the_exit_code_it_is_not_using(self, tmp_path: Path) -> None:
        """Exit 0 with error violations printed is the #147 compounding false green.

        The exit code is NOT changed (that would turn an adopter's green project
        red on upgrade); the omission is named on stderr instead.
        """
        project = make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_VIOLATING)
        reindex(project)

        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--no-reindex", "--project", str(project)], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "--strict" in result.stderr

    def test_a_read_only_lint_does_not_disturb_a_concurrent_index(
        self, tmp_path: Path
    ) -> None:
        """The whole point of read-only: two copies stay identical across a lint."""
        project = make_project(tmp_path)
        reindex(project)
        pristine = tmp_path / "pristine.db"
        shutil.copy2(index_db(project), pristine)

        runner = CliRunner()
        runner.invoke(main, ["lint", "--no-reindex", "--project", str(project)])

        assert _sha256(index_db(project)) == _sha256(pristine)
