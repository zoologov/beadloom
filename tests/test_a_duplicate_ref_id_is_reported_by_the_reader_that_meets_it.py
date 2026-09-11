"""A ref_id carried by two nodes: which node survives, and what says so.

BDL-069 S2, the LOADER half of BDL-UX #214. `beadloom-cgco` closed the writer
half — a root node and the sole package no longer take one `ref_id` — and this
file is about the graphs that already exist: bootstrapped by an earlier release,
or written by hand. For those, the reduction to one node still happens, and the
whole question is whether a reader says which node it kept.

MEASURED at 390850ae, on `myapp` / `src/myapp/` built for the purpose:

* `load_graph` reported `Duplicate ref_id 'myapp', skipped` — five words naming
  neither node, neither file, and no consequence — and kept the FIRST node, the
  empty `service` root;
* `graph/diff.py` read the same file into a dict keyed by `ref_id` and kept the
  LAST, silently. So `beadloom diff` described a node change on the `domain`
  node the graph does not hold, and said nothing about why.

Two readers, two answers, one file. The rule is stated ONCE here —
`unique_by_ref_id` — and both readers call it, which is the shape `beadloom-cgco`
established on the writing side: four independent derivations of one name that
agreed by luck.

The fixtures are projects that are not this one. This repository cannot produce
the collision at all: `src/beadloom/` holds seven packages and none is named
`beadloom`.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

from beadloom.graph.diff import compute_diff, diff_to_dict, render_diff
from beadloom.graph.loader import (
    DuplicateRefId,
    NodeOrigin,
    load_graph,
    unique_by_ref_id,
)
from beadloom.infrastructure.db import create_schema, open_db

ROOT_NODE = {"ref_id": "ledger", "kind": "service", "summary": "root", "source": ""}
PACKAGE_NODE = {
    "ref_id": "ledger",
    "kind": "domain",
    "summary": "the package",
    "source": "src/ledger/",
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _project_with_graph(tmp_path: Path, files: dict[str, str]) -> Path:
    """A project that is not this one, holding the given graph files."""
    root = tmp_path / "ledger"
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (root / "src" / "ledger").mkdir(parents=True)
    (root / "src" / "ledger" / "__init__.py").write_text('"""x."""\n', encoding="utf-8")
    for name, text in files.items():
        (graph_dir / name).write_text(text, encoding="utf-8")
    return root


def _committed_project(tmp_path: Path, files: dict[str, str]) -> Path:
    root = _project_with_graph(tmp_path, files)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline")
    return root


def _load(root: Path) -> tuple[Any, list[tuple[str, str, str]]]:
    conn = open_db(root / ".beadloom" / "test.db")
    create_schema(conn)
    result = load_graph(root / ".beadloom" / "_graph", conn)
    rows = [
        (row["ref_id"], row["kind"], row["source"])
        for row in conn.execute("SELECT ref_id, kind, source FROM nodes").fetchall()
    ]
    conn.close()
    return result, rows


DUPLICATE_YAML = """\
nodes:
  - ref_id: ledger
    kind: service
    summary: root
    source: ""
  - ref_id: ledger
    kind: domain
    summary: the package
    source: src/ledger/
edges: []
"""

SINGLE_YAML = """\
nodes:
  - ref_id: ledger
    kind: service
    summary: root
    source: ""
edges: []
"""


class TestTheRuleIsStatedOnce:
    """`unique_by_ref_id` — the one body that decides which node survives."""

    def test_a_graph_with_no_duplicate_keeps_every_node_and_reports_nothing(self) -> None:
        pairs = [("services.yml", ROOT_NODE), ("services.yml", {"ref_id": "api"})]
        kept, duplicates = unique_by_ref_id(pairs)
        assert kept == [ROOT_NODE, {"ref_id": "api"}]
        assert duplicates == []

    def test_the_first_node_under_a_ref_id_is_the_one_kept(self) -> None:
        kept, duplicates = unique_by_ref_id(
            [("services.yml", ROOT_NODE), ("services.yml", PACKAGE_NODE)]
        )
        assert kept == [ROOT_NODE]
        assert [d.ref_id for d in duplicates] == ["ledger"]
        assert duplicates[0].kept.kind == "service"
        assert duplicates[0].dropped.kind == "domain"

    def test_the_finding_names_where_each_node_was_read_and_what_it_declared(self) -> None:
        _, duplicates = unique_by_ref_id(
            [("services.yml", ROOT_NODE), ("imported.yml", PACKAGE_NODE)]
        )
        finding = duplicates[0]
        assert finding.kept == NodeOrigin(where="services.yml", kind="service", source="")
        assert finding.dropped == NodeOrigin(
            where="imported.yml", kind="domain", source="src/ledger/"
        )

    def test_three_nodes_under_one_ref_id_report_two_drops_against_one_kept_node(self) -> None:
        third = {"ref_id": "ledger", "kind": "component", "source": "src/ledger/cli.py"}
        kept, duplicates = unique_by_ref_id(
            [("a.yml", ROOT_NODE), ("b.yml", PACKAGE_NODE), ("c.yml", third)]
        )
        assert kept == [ROOT_NODE]
        assert len(duplicates) == 2
        assert {d.kept.where for d in duplicates} == {"a.yml"}
        assert [d.dropped.where for d in duplicates] == ["b.yml", "c.yml"]

    def test_a_node_with_no_ref_id_is_left_to_the_caller(self) -> None:
        """The missing-ref_id finding is each reader's own; this body does not take it."""
        kept, duplicates = unique_by_ref_id([("a.yml", {"kind": "domain"}), ("a.yml", {})])
        assert kept == [{"kind": "domain"}, {}]
        assert duplicates == []

    def test_a_node_that_is_not_a_mapping_is_kept_and_reported_by_nobody_here(self) -> None:
        """A hand-written `- ledger` under `nodes:` parses to a string, not a dict.

        The reduction has nothing to say about it: the reader that inserts it
        is the one that can say what is wrong with it, and this body must not
        swallow it on the way past.
        """
        not_a_mapping: Any = "ledger"
        kept, duplicates = unique_by_ref_id([("a.yml", not_a_mapping), ("a.yml", ROOT_NODE)])
        assert kept == ["ledger", ROOT_NODE]
        assert duplicates == []


class TestTheReportSaysWhatTheDropCosts:
    """The sentence an adopter reads, and the one fact #214 turns on."""

    def test_the_dropped_node_carries_the_source_and_the_kept_one_does_not(self) -> None:
        finding = DuplicateRefId(
            ref_id="ledger",
            kept=NodeOrigin(where="services.yml", kind="service", source=""),
            dropped=NodeOrigin(where="services.yml", kind="domain", source="src/ledger/"),
        )
        described = finding.describe()
        assert "Duplicate ref_id 'ledger'" in described
        assert "kept services.yml (kind=service, no source)" in described
        assert "dropped services.yml (kind=domain, source 'src/ledger/')" in described
        assert "the node that carries the source is the one dropped" in described
        assert "nothing under 'src/ledger/' is owned, checked or counted" in described

    def test_both_nodes_carry_a_source_and_only_the_dropped_one_is_named_as_lost(self) -> None:
        finding = DuplicateRefId(
            ref_id="ledger",
            kept=NodeOrigin(where="a.yml", kind="domain", source="src/ledger/"),
            dropped=NodeOrigin(where="b.yml", kind="domain", source="src/other/"),
        )
        described = finding.describe()
        assert "nothing under 'src/other/' is owned, checked or counted" in described
        assert "the node that carries the source is the one dropped" not in described

    def test_neither_node_carries_a_source_and_the_report_claims_no_lost_files(self) -> None:
        finding = DuplicateRefId(
            ref_id="ledger",
            kept=NodeOrigin(where="a.yml", kind="service", source=""),
            dropped=NodeOrigin(where="b.yml", kind="service", source=""),
        )
        described = finding.describe()
        assert described.endswith("only the kept node is in the graph")
        assert "owned, checked or counted" not in described


class TestTheLoaderReportsWhatItReduced:
    """`load_graph` — one of the six readers that never reach `each_graph_file`."""

    def test_the_report_names_both_nodes_instead_of_the_ref_id_alone(self, tmp_path: Path) -> None:
        root = _project_with_graph(tmp_path, {"services.yml": DUPLICATE_YAML})
        result, _ = _load(root)
        assert len(result.errors) == 1
        reported = result.errors[0]
        assert "kept services.yml (kind=service, no source)" in reported
        assert "dropped services.yml (kind=domain, source 'src/ledger/')" in reported

    def test_the_graph_still_loads_because_the_finding_is_a_report(self, tmp_path: Path) -> None:
        root = _project_with_graph(tmp_path, {"services.yml": DUPLICATE_YAML})
        result, rows = _load(root)
        assert result.nodes_loaded == 1
        assert rows == [("ledger", "service", "")]

    def test_the_finding_stays_in_the_channel_that_already_carried_it(
        self, tmp_path: Path
    ) -> None:
        """`errors`, where a duplicate was recorded before this bead.

        The `beadloom ci` reindex leg fails on a non-empty `errors`, and it did
        so over a duplicate at 390850ae too (measured: rc 1,
        `reindex FAIL: 1 reindex error(s)`). Moving the finding to `warnings`
        would clear a Gate that was already red, and promoting it to an
        exception would redden a graph that already loads. The verdict this
        report feeds is therefore the verdict the graph already earned.
        """
        root = _project_with_graph(tmp_path, {"services.yml": DUPLICATE_YAML})
        result, _ = _load(root)
        assert [e for e in result.errors if "Duplicate ref_id" in e]
        assert result.warnings == []

    def test_two_files_sharing_a_ref_id_are_reported_with_both_file_names(
        self, tmp_path: Path
    ) -> None:
        root = _project_with_graph(
            tmp_path, {"services.yml": SINGLE_YAML, "imported.yml": DUPLICATE_YAML}
        )
        result, rows = _load(root)
        reported = "\n".join(result.errors)
        assert "kept imported.yml" in reported
        assert "dropped imported.yml" in reported
        assert "dropped services.yml" in reported
        assert rows == [("ledger", "service", "")]

    def test_a_node_with_no_ref_id_is_still_reported_as_missing_one(self, tmp_path: Path) -> None:
        root = _project_with_graph(
            tmp_path, {"services.yml": "nodes:\n  - kind: domain\nedges: []\n"}
        )
        result, rows = _load(root)
        assert result.errors == ["Node missing ref_id, skipped"]
        assert rows == []


class TestTheReportReachesAReaderThatIsNotTheLoader:
    """`graph-diff`, named: it reaches neither `each_graph_file` nor `load_graph`."""

    def test_each_side_that_carries_the_duplicate_reports_it_where_it_read_it(
        self, tmp_path: Path
    ) -> None:
        """The graph is committed AND in the tree, so both sides hold it.

        Two findings, not one: a comparison has two sides, and a report that
        collapsed them would say nothing about which side a reader can repair.
        """
        root = _committed_project(tmp_path, {"services.yml": DUPLICATE_YAML})
        diff = compute_diff(root, "HEAD")
        assert [d.ref_id for d in diff.duplicates] == ["ledger", "ledger"]
        assert [d.kept.where for d in diff.duplicates] == [
            "services.yml",
            "HEAD:.beadloom/_graph/services.yml",
        ]

    def test_the_diff_keeps_the_node_the_loader_keeps(self, tmp_path: Path) -> None:
        """Measured at 390850ae: it kept the LAST, so the two readers disagreed."""
        root = _committed_project(tmp_path, {"services.yml": SINGLE_YAML})
        (root / ".beadloom" / "_graph" / "services.yml").write_text(
            DUPLICATE_YAML, encoding="utf-8"
        )
        diff = compute_diff(root, "HEAD")
        result, rows = _load(root)
        assert rows == [("ledger", "service", "")]
        assert [n.kind for n in diff.nodes if n.ref_id == "ledger"] == []
        assert diff.duplicates[0].kept.kind == "service"
        assert diff.duplicates[0].describe() in result.errors

    def test_a_duplicate_at_the_git_ref_is_reported_with_the_ref_it_was_read_at(
        self, tmp_path: Path
    ) -> None:
        """Both sides of the comparison are guarded, or the guard invents changes."""
        root = _committed_project(tmp_path, {"services.yml": DUPLICATE_YAML})
        (root / ".beadloom" / "_graph" / "services.yml").write_text(SINGLE_YAML, encoding="utf-8")
        diff = compute_diff(root, "HEAD")
        wheres = {d.dropped.where for d in diff.duplicates}
        assert wheres == {"HEAD:.beadloom/_graph/services.yml"}

    def test_the_duplicate_does_not_make_an_unchanged_graph_look_changed(
        self, tmp_path: Path
    ) -> None:
        """`has_changes` decides `beadloom diff`'s exit code; a report is not a change."""
        root = _committed_project(tmp_path, {"services.yml": DUPLICATE_YAML})
        diff = compute_diff(root, "HEAD")
        assert diff.duplicates
        assert not diff.has_changes

    def test_the_report_is_printed_even_when_there_is_nothing_else_to_print(
        self, tmp_path: Path
    ) -> None:
        root = _committed_project(tmp_path, {"services.yml": DUPLICATE_YAML})
        diff = compute_diff(root, "HEAD")
        buffer = io.StringIO()
        render_diff(diff, Console(file=buffer, width=200, no_color=True))
        printed = buffer.getvalue()
        assert "Duplicate ref_id 'ledger'" in printed
        assert "No graph changes since HEAD." in printed

    def test_the_json_form_carries_the_report_the_text_form_prints(self, tmp_path: Path) -> None:
        root = _committed_project(tmp_path, {"services.yml": DUPLICATE_YAML})
        payload = diff_to_dict(compute_diff(root, "HEAD"))
        assert payload["duplicates"] == [
            {
                "ref_id": "ledger",
                "kept": {"where": where, "kind": "service", "source": ""},
                "dropped": {"where": where, "kind": "domain", "source": "src/ledger/"},
            }
            for where in ("services.yml", "HEAD:.beadloom/_graph/services.yml")
        ]

    def test_a_graph_with_no_duplicate_reports_none(self, tmp_path: Path) -> None:
        root = _committed_project(tmp_path, {"services.yml": SINGLE_YAML})
        diff = compute_diff(root, "HEAD")
        assert diff.duplicates == ()
        assert diff_to_dict(diff)["duplicates"] == []


class TestWhereTheReportIsNot:
    """The placement, asserted rather than left to a docstring."""

    def test_neither_reader_reaches_the_skip_policy(self) -> None:
        """`each_graph_file` is in `onboarding`; `graph` may not import it.

        This is what makes the placement load-bearing rather than a preference:
        a duplicate report inside the policy would reach neither of the two
        readers exercised above, and `no-dependency-cycles` refuses the import
        that would let it.
        """
        from beadloom.graph import diff as diff_module
        from beadloom.graph import loader as loader_module

        for module in (loader_module, diff_module):
            source = Path(module.__file__ or "")
            assert source.is_file()
            text = source.read_text(encoding="utf-8")
            code = "\n".join(
                line for line in text.splitlines() if not line.lstrip().startswith("#")
            )
            assert "from beadloom.onboarding" not in code
            assert "import beadloom.onboarding" not in code

    def test_the_policy_does_not_state_the_duplicate_rule_a_second_time(self) -> None:
        """One body decides which node survives; `graph_files` re-exports nothing of it."""
        from beadloom.onboarding import graph_files

        assert not hasattr(graph_files, "unique_by_ref_id")
        assert not hasattr(graph_files, "DuplicateRefId")


@pytest.mark.parametrize("name", ["DuplicateRefId", "NodeOrigin", "unique_by_ref_id"])
def test_the_vocabulary_is_public_where_the_parse_is(name: str) -> None:
    import beadloom.graph as graph_package

    assert name in graph_package.__all__
    assert hasattr(graph_package, name)
