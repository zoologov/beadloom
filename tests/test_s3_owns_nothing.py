# beadloom:domain=application
"""S3 — what the system does when a declared thing owns nothing.

One sentence, three instances of it (BDL-061.50, from review ``.7`` MAJOR 3 and
``.5``'s unfiled findings (a), (b), (c)):

    **A declaration that owns nothing is named, with the reason, and never
    counted as checked** — and its corollary for the extractor, *an annotation
    the extractor cannot see is not an absent annotation.*

* **(c) the root** — a module-level ``# beadloom:`` annotation written inside a
  module DOCSTRING was invisible to :func:`extract_symbols`, which read comment
  nodes only. Five modules in this repo carry their annotation that way.
* **MAJOR 3, the wrong answer it produced** — ``sync-check`` called ``graph-reads``
  unchecked with the reason ``no_indexed_code`` while naming a file that is fully
  indexed. The real cause was that the ``#146`` fallback itself reads
  ``code_symbols``, so a module with zero top-level symbols (a pure re-export
  facade) is unreachable by BOTH the annotation path and the fallback.
* **(a)** — a node whose ``source:`` is a directory written WITHOUT a trailing
  slash owned no files at all: no ``depends_on`` edge, no sync pair, no symbol
  count, and no module-coverage either.
* **(b)** — ``deny`` rules resolved an import's SOURCE node through annotations
  only, so 22 of this repo's 128 import-source files were invisible to every
  deny rule.

Same equation as ``#146``, ``#174`` and ``#175``: *unverifiable is not clean.*
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.reindex import reindex
from beadloom.context_oracle.code_indexer import extract_symbols
from beadloom.graph.linter import lint as run_lint
from beadloom.infrastructure.repository import get_owning_ref_id
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixture: two annotated components, one symbol-less facade, one loose module
# ---------------------------------------------------------------------------

#: The shape five of this repo's own modules use, and the one the extractor
#: could not read: the annotation lines live INSIDE the module docstring.
_ALPHA_DOCSTRING_ANNOTATED = (
    '"""Alpha service.\n'
    "\n"
    "# beadloom:domain=app\n"
    "# beadloom:component=alpha\n"
    '"""\n'
    "\n\n"
    "def run() -> int:\n"
    "    return 1\n"
)

#: Same node, annotated the ordinary way — the regression guard for the form
#: that always worked.
_BETA_COMMENT_ANNOTATED = (
    '"""Beta tokens."""\n'
    "\n"
    "# beadloom:domain=app\n"
    "# beadloom:component=beta\n"
    "\n\n"
    "def verify() -> int:\n"
    "    return 2\n"
)

#: A pure re-export facade: annotated in its docstring and carrying ZERO
#: top-level symbols. This is ``application/graph_reads.py``'s shape, the file
#: MAJOR 3 reported as having no indexed code.
_FACADE = (
    '"""Facade over beta.\n'
    "\n"
    "# beadloom:domain=app\n"
    "# beadloom:component=facade\n"
    '"""\n'
    "\n"
    "from app.beta.tokens import verify\n"
    "\n"
    '__all__ = ["verify"]\n'
)

#: A module inside alpha's source directory carrying NO annotation anywhere —
#: the file a deny rule could not attribute to a node.
_ALPHA_PLAIN_IMPORTING_BETA = (
    '"""Alpha helper with no annotation of its own."""\n'
    "\n"
    "from app.beta import tokens\n"
    "\n\n"
    "def helper() -> int:\n"
    "    return tokens.verify()\n"
)

_NODES = """\
nodes:
  - ref_id: app
    kind: domain
    summary: The app domain
    source: src/app/
    docs:
      - components/app.md
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
  - ref_id: facade
    kind: component
    summary: Facade component
    source: src/app/facade.py
    docs:
      - components/facade.md
"""

_RULES = """\
version: 1
rules:
  - name: alpha-must-not-import-beta
    description: Alpha must not depend on beta
    severity: error
    deny:
      from: { ref_id: alpha }
      to: { ref_id: beta }
"""


def _make_project(root: Path, *, nodes: str = _NODES, rules: str = _RULES) -> Path:
    project = root / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs" / "components").mkdir(parents=True)
    (project / ".beadloom" / "config.yml").write_text("scan_paths:\n  - src\ndocs_dir: docs\n")
    (project / ".beadloom" / "_graph" / "services.yml").write_text(nodes + "edges: []\n")
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(rules)
    for name in ("app", "alpha", "beta", "facade"):
        (project / "docs" / "components" / f"{name}.md").write_text(f"# {name}\n")
    (project / "src" / "app" / "alpha").mkdir(parents=True)
    (project / "src" / "app" / "beta").mkdir(parents=True)
    (project / "src" / "app" / "__init__.py").write_text("")
    (project / "src" / "app" / "alpha" / "__init__.py").write_text("")
    (project / "src" / "app" / "beta" / "__init__.py").write_text("")
    (project / "src" / "app" / "alpha" / "service.py").write_text(_ALPHA_DOCSTRING_ANNOTATED)
    (project / "src" / "app" / "beta" / "tokens.py").write_text(_BETA_COMMENT_ANNOTATED)
    (project / "src" / "app" / "facade.py").write_text(_FACADE)
    return project


def _query(project: Path, sql: str, params: tuple[str, ...] = ()) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    try:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _annotations_of(project: Path, file_path: str) -> list[dict[str, str]]:
    rows = _query(
        project, "SELECT annotations FROM code_symbols WHERE file_path = ?", (file_path,)
    )
    return [json.loads(str(row[0])) for row in rows]


def _sync_check_json(project: Path) -> dict[str, object]:
    result = CliRunner().invoke(main, ["sync-check", "--json", "--project", str(project)])
    return dict(json.loads(result.stdout))


# ---------------------------------------------------------------------------
# (c) THE ROOT — the extractor reads a module docstring's annotation lines
# ---------------------------------------------------------------------------


class TestDocstringAnnotationsAreRead:
    """An annotation the extractor cannot see is not an absent annotation."""

    def test_a_docstring_annotation_reaches_every_symbol(self, tmp_path: Path) -> None:
        """The shape five of this repo's modules use, read at last."""
        module = tmp_path / "service.py"
        module.write_text(_ALPHA_DOCSTRING_ANNOTATED)

        symbols = extract_symbols(module)

        assert [s["symbol_name"] for s in symbols] == ["run"]
        assert symbols[0]["annotations"] == {"domain": "app", "component": "alpha"}

    def test_every_annotation_line_in_the_docstring_is_read_not_only_the_first(
        self, tmp_path: Path
    ) -> None:
        """A docstring is many lines; reading one of them would be a new blind spot."""
        module = tmp_path / "many.py"
        module.write_text(
            '"""Doc.\n\n# beadloom:domain=app\n\nProse in between.\n\n'
            '# beadloom:feature=many\n"""\n\n\ndef f() -> int:\n    return 1\n'
        )

        symbols = extract_symbols(module)

        assert symbols[0]["annotations"] == {"domain": "app", "feature": "many"}

    def test_an_indented_example_inside_a_docstring_is_not_an_annotation(
        self, tmp_path: Path
    ) -> None:
        """Non-vacuity guard: documenting the syntax must not declare ownership.

        Writing an indented code sample is how prose SHOWS an annotation. If any
        ``beadloom:``-shaped text in a docstring counted, every module that
        documents the convention would silently claim a node.
        """
        module = tmp_path / "prose.py"
        module.write_text(
            '"""How to annotate.\n\nWrite it at the top of the module::\n\n'
            '    # beadloom:domain=not-mine\n"""\n\n\ndef f() -> int:\n    return 1\n'
        )

        symbols = extract_symbols(module)

        assert symbols[0]["annotations"] == {}

    def test_a_non_comment_example_inside_a_docstring_is_not_an_annotation(
        self, tmp_path: Path
    ) -> None:
        """Measured on this repo: ``doc_sync/surface.py`` documents the in-doc
        HTML-comment form ``<!-- beadloom:watches=... -->`` inside its docstring.
        Reading it as an annotation would attach the module to whatever node
        ``cli`` names."""
        module = tmp_path / "surface.py"
        module.write_text(
            '"""Surface drift.\n\nA doc opts in with::\n\n'
            '    <!-- beadloom:watches=cli,graph -->\n"""\n\n\ndef f() -> int:\n    return 1\n'
        )

        symbols = extract_symbols(module)

        assert symbols[0]["annotations"] == {}

    def test_a_comment_annotation_is_still_read(self, tmp_path: Path) -> None:
        """Regression guard for the form that always worked."""
        module = tmp_path / "tokens.py"
        module.write_text(_BETA_COMMENT_ANNOTATED)

        symbols = extract_symbols(module)

        assert symbols[0]["annotations"] == {"domain": "app", "component": "beta"}

    def test_a_symbol_comment_still_overrides_the_module_docstring(
        self, tmp_path: Path
    ) -> None:
        """Precedence is unchanged: the nearest annotation wins, the rest is inherited."""
        module = tmp_path / "mixed.py"
        module.write_text(
            '"""Doc.\n\n# beadloom:domain=app\n# beadloom:component=alpha\n"""\n\n'
            "# beadloom:component=special\n"
            "def f() -> int:\n    return 1\n"
        )

        symbols = extract_symbols(module)

        assert symbols[0]["annotations"] == {"domain": "app", "component": "special"}

    def test_the_index_carries_the_docstring_annotation_end_to_end(
        self, tmp_path: Path
    ) -> None:
        """Not only the extractor: the row a deny rule and a sync pair read."""
        project = _make_project(tmp_path)
        reindex(project)

        assert _annotations_of(project, "src/app/alpha/service.py") == [
            {"domain": "app", "component": "alpha"}
        ]


# ---------------------------------------------------------------------------
# MAJOR 3 — a symbol-less module is CHECKED, not mislabelled as absent code
# ---------------------------------------------------------------------------


class TestASymbollessModuleIsChecked:
    """``graph_reads.py``'s shape: fully indexed, zero symbols, zero pairs."""

    def test_a_facade_with_no_symbols_contributes_a_sync_pair(self, tmp_path: Path) -> None:
        """The file is indexed; a checker that keys on symbols never opened it."""
        project = _make_project(tmp_path)
        reindex(project)

        pairs = _query(
            project, "SELECT code_path FROM sync_state WHERE ref_id = 'facade'"
        )
        assert pairs == [("src/app/facade.py",)]

    def test_that_pair_is_real_editing_the_facade_makes_its_doc_stale(
        self, tmp_path: Path
    ) -> None:
        """A pair that cannot go stale is a pair that checks nothing."""
        project = _make_project(tmp_path)
        reindex(project)
        (project / "src" / "app" / "facade.py").write_text(
            _FACADE.replace("__all__", "__ALL__")
        )

        result = CliRunner().invoke(
            main, ["sync-check", "--json", "--project", str(project)]
        )
        payload = json.loads(result.stdout)
        stale = [
            p for p in payload["pairs"] if p["ref_id"] == "facade" and p["status"] == "stale"
        ]

        assert stale, payload
        assert result.exit_code == 2

    def test_no_node_is_reported_unchecked_for_a_file_that_is_indexed(
        self, tmp_path: Path
    ) -> None:
        """MAJOR 3 in one line: the reason named missing code in a file the index holds."""
        project = _make_project(tmp_path)
        reindex(project)

        payload = _sync_check_json(project)
        unchecked = payload["unchecked"]

        assert unchecked == [], unchecked


class TestTheUncheckedReasonNamesTheRealCause:
    """What is left is genuinely uncheckable — and says which kind."""

    def test_a_source_directory_holding_no_code_says_so(self, tmp_path: Path) -> None:
        project = _make_project(
            tmp_path,
            nodes=_NODES
            + "  - ref_id: gamma\n"
            "    kind: component\n"
            "    summary: Gamma component\n"
            "    source: src/app/gamma/\n"
            "    docs:\n"
            "      - components/gamma.md\n",
        )
        (project / "src" / "app" / "gamma").mkdir()
        (project / "docs" / "components" / "gamma.md").write_text("# gamma\n")
        reindex(project)

        payload = _sync_check_json(project)
        reasons = {u["ref_id"]: u["reason"] for u in payload["unchecked"]}

        assert reasons == {"gamma": "no_indexed_code"}

    def test_a_container_whose_files_all_belong_to_nested_nodes_says_that_instead(
        self, tmp_path: Path
    ) -> None:
        """The distinction the two words exist for: index the code, or nothing.

        The nested files here carry NO top-level symbol, which is what makes the
        old symbol-keyed test wrong: it called them absent.
        """
        project = _make_project(
            tmp_path,
            nodes=_NODES
            + "  - ref_id: zeta\n"
            "    kind: component\n"
            "    summary: Zeta container\n"
            "    source: src/app/zeta/\n"
            "    docs:\n"
            "      - components/zeta.md\n"
            "  - ref_id: zeta-sub\n"
            "    kind: component\n"
            "    summary: Zeta sub\n"
            "    source: src/app/zeta/sub/\n"
            "    docs:\n"
            "      - components/zeta-sub.md\n",
        )
        (project / "src" / "app" / "zeta" / "sub").mkdir(parents=True)
        (project / "src" / "app" / "zeta" / "sub" / "reexport.py").write_text(
            "from app.beta.tokens import verify\n\n__all__ = ['verify']\n"
        )
        (project / "docs" / "components" / "zeta.md").write_text("# zeta\n")
        (project / "docs" / "components" / "zeta-sub.md").write_text("# zeta-sub\n")
        reindex(project)

        payload = _sync_check_json(project)
        reasons = {u["ref_id"]: u["reason"] for u in payload["unchecked"]}

        assert reasons == {"zeta": "files_owned_by_nested_nodes"}


# ---------------------------------------------------------------------------
# (a) a directory source written WITHOUT a trailing slash
# ---------------------------------------------------------------------------

#: ``alpha`` loses its trailing slash, and ``delta`` is a second no-slash
#: directory node whose only module carries NO annotation — so nothing but
#: ownership can reach it.
_NODES_NO_SLASH = _NODES.replace("source: src/app/alpha/", "source: src/app/alpha") + (
    "  - ref_id: delta\n"
    "    kind: component\n"
    "    summary: Delta component\n"
    "    source: src/app/delta\n"
    "    docs:\n"
    "      - components/delta.md\n"
)


def _make_no_slash_project(root: Path, *, rules: str = _RULES) -> Path:
    project = _make_project(root, nodes=_NODES_NO_SLASH, rules=rules)
    (project / "src" / "app" / "delta").mkdir()
    (project / "src" / "app" / "delta" / "helper.py").write_text(
        '"""Delta helper with no annotation."""\n\n\ndef helper() -> int:\n    return 4\n'
    )
    (project / "docs" / "components" / "delta.md").write_text("# delta\n")
    return project


class TestADirectorySourceWithoutASlash:
    """Zero of this repo's 67 sourced nodes hit this, which is why it is silent."""

    def test_it_owns_the_files_beneath_it(self, tmp_path: Path) -> None:
        project = _make_no_slash_project(tmp_path)
        reindex(project)
        conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
        conn.row_factory = sqlite3.Row
        try:
            owner = get_owning_ref_id(conn, "src/app/alpha/service.py")
        finally:
            conn.close()

        assert owner == "alpha"

    def test_it_derives_the_depends_on_edge_of_a_file_beneath_it(
        self, tmp_path: Path
    ) -> None:
        """Deliberately asserted on an UNANNOTATED file: with an annotation the
        pair and the edge arrive by the other key, and the test would pass while
        ownership stayed broken."""
        project = _make_no_slash_project(tmp_path)
        (project / "src" / "app" / "alpha" / "plain.py").write_text(
            _ALPHA_PLAIN_IMPORTING_BETA
        )
        reindex(project)

        assert ("alpha", "beta") in _query(
            project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        )

    def test_it_contributes_a_sync_pair_for_a_file_that_carries_no_annotation(
        self, tmp_path: Path
    ) -> None:
        """``delta``'s module is unannotated, so ONLY ownership can pair it."""
        project = _make_no_slash_project(tmp_path)
        reindex(project)

        assert _query(
            project, "SELECT code_path FROM sync_state WHERE ref_id = 'delta'"
        ) == [("src/app/delta/helper.py",)]

    def test_it_covers_its_modules_for_module_coverage(self, tmp_path: Path) -> None:
        """Found while reading: the coverage rule also required the slash, so an
        adopter's whole subtree read as uncovered — an error-severity false RED."""
        project = _make_no_slash_project(
            tmp_path,
            rules=_RULES
            + "  - name: modules-need-a-node\n"
            "    description: Every module belongs to a node\n"
            "    severity: error\n"
            "    module_coverage:\n"
            "      source_root: src/app/\n"
            "      exempt: ['**/__init__.py']\n",
        )
        (project / "src" / "app" / "alpha" / "extra.py").write_text(
            '"""Extra."""\n\n\ndef g() -> int:\n    return 3\n'
        )
        reindex(project)

        offenders = [
            v.file_path
            for v in run_lint(project).violations
            if v.rule_name == "modules-need-a-node"
        ]

        assert offenders == []

    def test_a_file_source_is_never_widened_into_a_directory(self, tmp_path: Path) -> None:
        """Non-vacuity guard: normalising by stat, not by guessing."""
        project = _make_project(tmp_path)
        reindex(project)

        assert _query(
            project, "SELECT source FROM nodes WHERE ref_id = 'facade'"
        ) == [("src/app/facade.py",)]

    def test_a_source_path_that_exists_nowhere_is_reported(self, tmp_path: Path) -> None:
        """The residual "owns nothing": a declaration pointing at no path at all."""
        project = _make_project(
            tmp_path,
            nodes=_NODES
            + "  - ref_id: ghost\n"
            "    kind: component\n"
            "    summary: Ghost component\n"
            "    source: src/app/ghost/\n"
            "    docs:\n"
            "      - components/ghost.md\n",
        )
        (project / "docs" / "components" / "ghost.md").write_text("# ghost\n")

        result = reindex(project)

        assert [w for w in result.warnings if "ghost" in w], result.warnings


# ---------------------------------------------------------------------------
# (b) deny rules see every indexed file, and say what they could not attribute
# ---------------------------------------------------------------------------


class TestDenyRulesSeeEveryIndexedFile:
    """The ``#146`` disease in the linter: annotation-keyed source resolution."""

    def test_a_file_with_no_annotation_still_triggers_its_owner_s_deny_rule(
        self, tmp_path: Path
    ) -> None:
        """Ownership is how the depends_on edge is already derived; the deny rule
        used a different key, so the edge existed and the rule stayed silent."""
        project = _make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "plain.py").write_text(
            _ALPHA_PLAIN_IMPORTING_BETA
        )
        reindex(project)

        result = run_lint(project)

        errors = [(v.rule_name, v.file_path) for v in result.violations if v.severity == "error"]

        assert errors == [("alpha-must-not-import-beta", "src/app/alpha/plain.py")]

    def test_a_docstring_annotated_file_triggers_its_deny_rule(self, tmp_path: Path) -> None:
        """``.5``'s measured case: the edge existed, the rule did not fire."""
        project = _make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(
            _ALPHA_DOCSTRING_ANNOTATED.replace(
                "def run() -> int:\n    return 1\n",
                "from app.beta import tokens\n\n\ndef run() -> int:\n    return tokens.verify()\n",
            )
        )
        reindex(project)

        result = run_lint(project)

        assert [v.rule_name for v in result.violations if v.severity == "error"] == [
            "alpha-must-not-import-beta"
        ]

    def test_lint_states_how_many_scanned_files_it_could_not_attribute(
        self, tmp_path: Path
    ) -> None:
        """A green count is not a checked count: a file owned by no node is
        invisible to every deny rule, so the scanned count must say so."""
        project = _make_project(tmp_path)
        (project / "src" / "loose").mkdir(parents=True)
        (project / "src" / "loose" / "thing.py").write_text(
            "from app.beta import tokens\n\n\ndef t() -> int:\n    return tokens.verify()\n"
        )
        reindex(project)

        result = run_lint(project)

        assert result.files_unattributed == 1

    def test_the_unattributed_count_is_zero_when_every_file_has_an_owner(
        self, tmp_path: Path
    ) -> None:
        """Non-vacuity guard: the number is a measurement, not a constant."""
        project = _make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "plain.py").write_text(
            _ALPHA_PLAIN_IMPORTING_BETA
        )
        reindex(project)

        assert run_lint(project).files_unattributed == 0

    def test_the_unattributed_count_is_carried_in_json_and_named_on_the_header(
        self, tmp_path: Path
    ) -> None:
        """Reportable, not merely computed — exit codes and --json only (#148)."""
        project = _make_project(tmp_path)
        (project / "src" / "loose").mkdir(parents=True)
        (project / "src" / "loose" / "thing.py").write_text(
            "from app.beta import tokens\n\n\ndef t() -> int:\n    return tokens.verify()\n"
        )
        reindex(project)

        runner = CliRunner()
        as_json = runner.invoke(
            main, ["lint", "--no-reindex", "--format", "json", "--project", str(project)]
        )
        payload = json.loads(as_json.stdout)
        human = runner.invoke(main, ["lint", "--no-reindex", "--project", str(project)])

        assert payload["summary"]["files_unattributed"] == 1
        assert "attributable to no node" in human.output
