# beadloom:domain=application
"""S2 regressions — the three checks that reported success without checking.

Each test here reproduces a measured false green, not a hypothetical one:

* **#142** — an incremental ``reindex`` never re-extracted imports, so
  ``lint --strict`` on the documented ``reindex && lint`` loop reported a clean
  boundary while the working tree held a real violation.
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

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.graph.linter import lint as run_lint
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

# The annotation deliberately sits INSIDE the module docstring — the shape the
# dogfood project hit in #146. It was invisible to the extractor (tree-sitter
# sees a string node, not a comment), so the symbol rows carried no annotation
# and every annotation-keyed reader silently saw nothing. SINCE BDL-061.50 the
# extractor READS this form, so these fixtures are genuinely annotated and #146's
# source-owned fallback is exercised instead by `gamma` below (a node that
# declares docs and owns no file at all) and by the unannotated modules in
# tests/test_s3_owns_nothing.py.
_ALPHA_CLEAN = (
    '"""Alpha service.\n\n# beadloom:component=alpha\n"""\n\n\n'
    "def run() -> int:\n    return 1\n"
)
_ALPHA_VIOLATING = (
    '"""Alpha service.\n\n# beadloom:component=alpha\n"""\n\n'
    "from app.beta import tokens\n\n\ndef run() -> int:\n    return tokens.verify()\n"
)
_BETA = (
    '"""Beta tokens.\n\n# beadloom:component=beta\n"""\n\n\n'
    "def verify() -> int:\n    return 2\n"
)

_NODES_YML = """\
nodes:
  - ref_id: alpha
    kind: component
    summary: Alpha component
    source: src/app/alpha/
    docs:
      - components/alpha.md
  - ref_id: beta
    kind: component
    summary: Beta component
    source: src/app/beta/
    docs:
      - components/beta.md
"""

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


def _services_yml(*, extra_nodes: str = "", edges: str = "edges: []\n") -> str:
    """Assemble a services.yml from the node block, optional extras, and edges."""
    return _NODES_YML + extra_nodes + edges

_RULES_YML = """\
version: 1
rules:
  - name: alpha-no-beta-import
    description: Alpha must not import beta
    severity: error
    forbid_import:
      from: 'src/app/alpha/*'
      to: 'app/beta*'
"""


def _make_project(root: Path) -> Path:
    """Two component nodes, each with a doc, and a boundary rule between them."""
    project = root / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs" / "components").mkdir(parents=True)
    (project / ".beadloom" / "config.yml").write_text("scan_paths:\n  - src\ndocs_dir: docs\n")
    (project / ".beadloom" / "_graph" / "services.yml").write_text(_services_yml())
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(_RULES_YML)
    (project / "docs" / "components" / "alpha.md").write_text(
        "# Alpha\n\nThe `service` module runs alpha.\n"
    )
    (project / "docs" / "components" / "beta.md").write_text(
        "# Beta\n\nThe `tokens` module verifies beta.\n"
    )
    (project / "src" / "app" / "alpha").mkdir(parents=True)
    (project / "src" / "app" / "beta").mkdir(parents=True)
    (project / "src" / "app" / "__init__.py").write_text("")
    (project / "src" / "app" / "alpha" / "__init__.py").write_text("")
    (project / "src" / "app" / "beta" / "__init__.py").write_text("")
    (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_CLEAN)
    (project / "src" / "app" / "beta" / "tokens.py").write_text(_BETA)
    return project


def _db(project: Path) -> Path:
    return project / ".beadloom" / "beadloom.db"


def _query(project: Path, sql: str, params: tuple[str, ...] = ()) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(_db(project))
    try:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# #142 — a boundary violation introduced after an INCREMENTAL reindex
# ---------------------------------------------------------------------------


class TestIncrementalReindexRefreshesImports:
    """The documented ``reindex && lint`` loop must catch a fresh violation."""

    def test_violation_added_to_existing_file_is_caught(self, tmp_path: Path) -> None:
        """Edit a file into a boundary break -> incremental reindex -> lint sees it."""
        project = _make_project(tmp_path)
        reindex(project)
        assert run_lint(project).violations == [], "baseline must be clean"

        (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_VIOLATING)
        incremental_reindex(project)

        result = run_lint(project)
        indexed = _query(project, "SELECT file_path, import_path FROM code_imports")
        assert [v.rule_name for v in result.violations] == ["alpha-no-beta-import"], (
            f"incremental reindex left the import graph stale: {indexed}"
        )

    def test_violation_in_a_new_file_is_caught(self, tmp_path: Path) -> None:
        """An ADDED file's imports reach the index too, not only a changed one."""
        project = _make_project(tmp_path)
        reindex(project)

        (project / "src" / "app" / "alpha" / "extra.py").write_text(_ALPHA_VIOLATING)
        incremental_reindex(project)

        result = run_lint(project)
        assert [v.file_path for v in result.violations] == ["src/app/alpha/extra.py"]

    def test_removed_import_stops_being_reported(self, tmp_path: Path) -> None:
        """The refresh works in both directions — a fixed violation goes away."""
        project = _make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_VIOLATING)
        reindex(project)
        assert run_lint(project).violations != []

        (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_CLEAN)
        incremental_reindex(project)

        assert run_lint(project).violations == []
        assert _query(project, "SELECT file_path FROM code_imports") == []

    def test_deleted_file_drops_its_imports_and_edge(self, tmp_path: Path) -> None:
        """Deleting the offending file removes both its imports and its edge."""
        project = _make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_VIOLATING)
        reindex(project)
        assert ("alpha", "beta") in _query(
            project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        )

        (project / "src" / "app" / "alpha" / "service.py").unlink()
        incremental_reindex(project)

        assert _query(project, "SELECT file_path FROM code_imports") == []
        assert (
            _query(project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'")
            == []
        )

    def test_declared_edge_survives_an_incremental_refresh(self, tmp_path: Path) -> None:
        """Refreshing DERIVED edges must not delete a YAML-declared one."""
        project = _make_project(tmp_path)
        graph = project / ".beadloom" / "_graph" / "services.yml"
        graph.write_text(
            _services_yml(edges="edges:\n  - src: beta\n    dst: alpha\n    kind: depends_on\n")
        )
        reindex(project)
        assert ("beta", "alpha") in _query(
            project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        )

        (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_VIOLATING)
        incremental_reindex(project)

        assert ("beta", "alpha") in _query(
            project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        ), "a declared depends_on edge was collateral damage of the derived-edge refresh"


# ---------------------------------------------------------------------------
# #146 — a node that declares docs is never silently unchecked
# ---------------------------------------------------------------------------


class TestDeclaredDocsAreGenuinelyChecked:
    """"Clean" from sync-check must mean "checked", never "no pairs exist"."""

    def test_component_node_contributes_a_sync_pair(self, tmp_path: Path) -> None:
        """A component declaring docs + source gets pairs even with no annotation."""
        project = _make_project(tmp_path)
        reindex(project)

        pairs = _query(project, "SELECT ref_id, code_path FROM sync_state WHERE ref_id = 'alpha'")
        assert pairs == [("alpha", "src/app/alpha/service.py")]

    def test_component_doc_goes_stale_when_its_code_changes(self, tmp_path: Path) -> None:
        """The pair is real: editing the code makes the component doc stale."""
        project = _make_project(tmp_path)
        reindex(project)
        (project / "src" / "app" / "alpha" / "service.py").write_text(
            _ALPHA_CLEAN.replace("return 1", "return 42")
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
        project = _make_project(tmp_path)
        graph = project / ".beadloom" / "_graph" / "services.yml"
        graph.write_text(_services_yml(extra_nodes=_GAMMA_NODE_YML))
        (project / "docs" / "components" / "gamma.md").write_text("# Gamma\n")
        reindex(project)

        runner = CliRunner()
        result = runner.invoke(main, ["sync-check", "--json", "--project", str(project)])
        payload = json.loads(result.stdout)
        assert payload["summary"]["unchecked"] == 1
        assert [u["ref_id"] for u in payload["unchecked"]] == ["gamma"]

    def test_unchecked_nodes_never_change_the_exit_code(self, tmp_path: Path) -> None:
        """The new signal is advisory — no adopter's green project turns red."""
        project = _make_project(tmp_path)
        graph = project / ".beadloom" / "_graph" / "services.yml"
        graph.write_text(_services_yml(extra_nodes=_GAMMA_NODE_YML))
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
        project = _make_project(tmp_path)
        reindex(project)
        conn = sqlite3.connect(_db(project))
        conn.execute("PRAGMA journal_mode=delete")
        conn.close()
        for sidecar in (project / ".beadloom").glob("beadloom.db-*"):
            sidecar.unlink()

        before = _sha256(_db(project))
        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--no-reindex", "--strict", "--project", str(project)]
        )

        assert _sha256(_db(project)) == before, "a read-only lint wrote to the index"
        assert result.exit_code == 0, result.output

    def test_no_reindex_on_a_missing_index_refuses_instead_of_reporting_clean(
        self, tmp_path: Path
    ) -> None:
        """No index is not a clean project — and lint must not create one."""
        project = _make_project(tmp_path)
        reindex(project)
        for artifact in (project / ".beadloom").glob("beadloom.db*"):
            artifact.unlink()

        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--no-reindex", "--strict", "--project", str(project)]
        )

        assert result.exit_code == 2, result.output
        assert not _db(project).exists(), "a read-only lint created the index it was reading"
        assert "0 violations" not in result.output

    def test_no_reindex_still_reports_a_real_violation(self, tmp_path: Path) -> None:
        """Read-only must not mean blind: the violation in the index is reported."""
        project = _make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_VIOLATING)
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
        project = _make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_VIOLATING)
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
        project = _make_project(tmp_path)
        reindex(project)
        pristine = tmp_path / "pristine.db"
        shutil.copy2(_db(project), pristine)

        runner = CliRunner()
        runner.invoke(main, ["lint", "--no-reindex", "--project", str(project)])

        assert _sha256(_db(project)) == _sha256(pristine)
