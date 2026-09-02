"""Every reader `init` reaches parses `.beadloom/_graph/` through one policy.

BDL-067 `.24`, the review of `.23`'s major 3. `.21` removed
`generate_skeletons`' node-list parameter, so the `--bootstrap` branch stopped
passing its own nodes and started reading the tree — and the reader it now
reaches, `_load_graph_from_yaml`, called `yaml.safe_load` with no `try`. The
same commit added exactly that guard to two sibling readers and listed "the
unreadable-YAML guards" in its own message as delivered. MEASURED by the review
on a project carrying one hand-edited `.beadloom/_graph/legacy.yml` that does
not parse: `beadloom init --bootstrap` printed a raw `yaml.parser.ParserError`
traceback at the adopter.

The traceback is the instance. The shape is that `init` held FOUR readers of the
same directory with four skip policies — `_load_graph_from_yaml`,
`_existing_graph`, `_graph_file_of_each_node`, `_patch_docs_field` — which is the
one-invariant-in-N-bodies shape `.21` consolidated for the WRITERS, standing on
the readers. So the cases below are stated over the policy and not over the one
reader that was short of it: a fifth body is what these tests exist to fail on.

`rules.yml` is not a graph file — it holds no nodes — and every reader skipped
it already. `imported.yml` is skipped by ONE reader, `_existing_graph`, because
that run is about to replace it; that is the one genuine difference between the
callers, and it is a parameter of the shared policy rather than a second body.
"""

from __future__ import annotations

import ast
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from click.testing import CliRunner

from beadloom.onboarding.doc_generator import _load_graph_from_yaml, _patch_docs_field
from beadloom.onboarding.graph_files import each_graph_file
from beadloom.onboarding.scanner.doc_classify import _existing_graph
from beadloom.services.cli import main
from beadloom.services.commands.setup import _graph_file_of_each_node
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    from collections.abc import Callable

#: The file that does not parse. A hand-edited graph file is the reproduction
#: the review measured, and the one `init` meets in the field.
THE_UNREADABLE_FILE = "legacy.yml"
UNPARSEABLE_YAML = "nodes:\n  - ref_id: ledger\n   kind: domain\n  bad: [\n"

#: The other shape a graph file can take that is not a mapping. `data.get` on a
#: top-level list raises `AttributeError`, which no `except yaml.YAMLError`
#: catches, so it is a second way for a reader to traceback at the adopter.
A_TOP_LEVEL_LIST = "- ref_id: ledger\n- ref_id: payments\n"

#: The readable file beside it, so every case below can also assert that the
#: skip is a SKIP and not an abandonment of the whole directory. Its one node is
#: an unparented `service`, which is the only shape all four readers can report:
#: `_existing_graph` answers with the graph's root and not with its nodes.
THE_READABLE_NODE = "orders"
A_READABLE_GRAPH_FILE = {
    "nodes": [
        {"ref_id": THE_READABLE_NODE, "kind": "service", "summary": "Readable."},
    ]
}


def _a_tree_holding_one_unreadable_graph_file(tmp_path: Path, text: str) -> Path:
    project = typescript_project(tmp_path).root
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / THE_UNREADABLE_FILE).write_text(text, encoding="utf-8")
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump(A_READABLE_GRAPH_FILE, sort_keys=False), encoding="utf-8"
    )
    return project


#: Each reader `init` reaches, as the question it answers, together with the
#: ref_ids it saw. Stated as one table because the policy is one policy: a
#: reader added with a skip policy of its own belongs in this table and will
#: fail here rather than at an adopter.
READERS: dict[str, Callable[[Path], set[str]]] = {
    "_load_graph_from_yaml": lambda project: {
        str(node["ref_id"]) for node in _load_graph_from_yaml(project)[0]
    },
    "_existing_graph": lambda project: {
        root
        for root in [_existing_graph(project / ".beadloom" / "_graph")[0]]
        if root is not None
    },
    "_graph_file_of_each_node": lambda project: set(_graph_file_of_each_node(project)),
    "_patch_docs_field": lambda project: _docs_patched(project),
}


def _docs_patched(project: Path) -> set[str]:
    """`_patch_docs_field`'s answer, read off the file it wrote rather than returned.

    It returns nothing, so the only observable is the tree. The ref_ids it saw
    are the ones whose node now carries the `docs:` it was handed.
    """
    graph_dir = project / ".beadloom" / "_graph"
    _patch_docs_field(graph_dir, {THE_READABLE_NODE: "docs/domains/orders/README.md"})
    data = yaml.safe_load((graph_dir / "services.yml").read_text(encoding="utf-8"))
    return {str(n["ref_id"]) for n in data["nodes"] if "docs" in n}


class TestNoReaderTracebacksOnAFileItCannotParse:
    """One policy, asked of every reader, over both shapes of unreadable file."""

    def test_a_file_that_does_not_parse_is_skipped_by_every_reader(
        self, tmp_path: Path
    ) -> None:
        for name, ask in READERS.items():
            project = _a_tree_holding_one_unreadable_graph_file(
                tmp_path / name, UNPARSEABLE_YAML
            )
            assert THE_READABLE_NODE in ask(project), name

    def test_a_file_that_is_not_a_mapping_is_skipped_by_every_reader(
        self, tmp_path: Path
    ) -> None:
        """A top-level list parses fine and then raises on `data.get`."""
        for name, ask in READERS.items():
            project = _a_tree_holding_one_unreadable_graph_file(
                tmp_path / name, A_TOP_LEVEL_LIST
            )
            assert THE_READABLE_NODE in ask(project), name

    def test_the_traceback_the_review_measured_is_gone_and_a_second_one_is_not(
        self, tmp_path: Path
    ) -> None:
        """The review's own reproduction, end to end, and what it did not reach.

        MEASURED on this tree, `beadloom init --bootstrap`, after the four
        readers above were consolidated: the `yaml.parser.ParserError` no longer
        comes from `doc_generator._load_graph_from_yaml`, which is the frame the
        review named and the one `.21` made reachable. The command still ends in
        a `ParserError`, raised one step later by
        `application/reindex/indexing.read_declared_docs`, which globs the same
        directory and parses it with no guard.

        RECORDED, NOT ENDORSED, and deliberately not fixed here. That reader is
        not one of `init`'s four, it is in another domain, and `--bootstrap`
        reached it before `.21` as well — so it is not what this epic broke, and
        BDL-067 `.24` was scoped to what this epic broke. It is also not alone:
        `graph/loader.py`, `graph/diff.py`, `reindex/change_detection.py` and
        `services/commands/index_ops.py` walk the same directory. Naming the
        whole class is a planning decision, and this case fails the moment
        somebody makes it — which is the point of pinning it rather than leaving
        the epic reading as though the traceback were gone.
        """
        project = _a_tree_holding_one_unreadable_graph_file(tmp_path, UNPARSEABLE_YAML)

        result = CliRunner().invoke(
            main, ["init", "--bootstrap", "--project", str(project)]
        )

        raised = result.exception
        assert isinstance(raised, yaml.YAMLError), result.output
        frames = [frame.name for frame in traceback.extract_tb(raised.__traceback__)]
        assert "_load_graph_from_yaml" not in frames, frames
        assert "_patch_docs_field" not in frames, frames
        assert "_graph_file_of_each_node" not in frames, frames
        assert "read_declared_docs" in frames, frames


class TestTheSkipPolicyLivesInOneBody:
    """Derived from the source, so a fifth policy cannot be added quietly.

    A graph-file reader is a function that both walks `glob("*.yml")` and calls
    `yaml.safe_load` — the two halves of the shape, which is what makes this a
    derivation rather than a list of four names somebody keeps up to date.
    """

    #: Where `init`'s own readers live. `rules_gen` and `agents_md` parse
    #: `rules.yml` by name and never walk the directory, so the derivation does
    #: not reach them and does not need to exempt them.
    SEARCHED = (
        Path("src/beadloom/onboarding"),
        Path("src/beadloom/services/commands/setup.py"),
    )
    THE_ONE_BODY = Path("src/beadloom/onboarding/graph_files.py")

    def _readers_in(self, module: Path) -> list[str]:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        found: list[str] = []
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
            walks = any(
                isinstance(c.func, ast.Attribute)
                and c.func.attr == "glob"
                and any(
                    isinstance(a, ast.Constant) and a.value == "*.yml" for a in c.args
                )
                for c in calls
            )
            parses = any(
                isinstance(c.func, ast.Attribute) and c.func.attr == "safe_load"
                for c in calls
            )
            if walks and parses:
                found.append(f"{module}::{fn.name}")
        return found

    def _every_module(self) -> list[Path]:
        modules: list[Path] = []
        for where in self.SEARCHED:
            modules.extend(sorted(where.rglob("*.py")) if where.is_dir() else [where])
        return modules

    def test_the_derivation_finds_the_shared_reader(self) -> None:
        """Anti-vacuity: the detector detects the one body that should match."""
        assert self._readers_in(self.THE_ONE_BODY), self.THE_ONE_BODY

    def test_no_other_module_walks_the_graph_directory_and_parses_it(self) -> None:
        elsewhere = [
            name
            for module in self._every_module()
            if module != self.THE_ONE_BODY
            for name in self._readers_in(module)
        ]
        assert elsewhere == [], elsewhere


class TestTheOneDifferenceBetweenCallersIsAParameter:
    """`imported.yml` is skipped by one caller, and it says so in a parameter."""

    def test_the_shared_reader_skips_the_rules_file_for_every_caller(
        self, tmp_path: Path
    ) -> None:
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "rules.yml").write_text("version: 1\nrules: []\n", encoding="utf-8")
        (graph_dir / "services.yml").write_text(
            yaml.safe_dump(A_READABLE_GRAPH_FILE, sort_keys=False), encoding="utf-8"
        )

        seen = [path.name for path, _ in each_graph_file(graph_dir)]

        assert seen == ["services.yml"]

    def test_a_caller_that_must_not_read_a_file_names_it(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        for name in ("imported.yml", "services.yml"):
            (graph_dir / name).write_text(
                yaml.safe_dump(A_READABLE_GRAPH_FILE, sort_keys=False), encoding="utf-8"
            )

        both = [path.name for path, _ in each_graph_file(graph_dir)]
        one = [
            path.name
            for path, _ in each_graph_file(
                graph_dir, also_skip=frozenset({"imported.yml"})
            )
        ]

        assert both == ["imported.yml", "services.yml"]
        assert one == ["services.yml"]

    def test_a_missing_directory_is_no_graph_files_rather_than_an_error(
        self, tmp_path: Path
    ) -> None:
        assert list(each_graph_file(tmp_path / "nothing" / "here")) == []

    def test_every_file_yielded_is_a_mapping(self, tmp_path: Path) -> None:
        """The guarantee the callers rely on instead of re-checking it."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "a.yml").write_text("", encoding="utf-8")
        (graph_dir / "b.yml").write_text(A_TOP_LEVEL_LIST, encoding="utf-8")
        (graph_dir / "c.yml").write_text(UNPARSEABLE_YAML, encoding="utf-8")
        (graph_dir / "d.yml").write_text(
            yaml.safe_dump(A_READABLE_GRAPH_FILE, sort_keys=False), encoding="utf-8"
        )

        yielded: list[tuple[str, Any]] = [
            (path.name, data) for path, data in each_graph_file(graph_dir)
        ]

        assert [name for name, _ in yielded] == ["a.yml", "d.yml"]
        assert all(isinstance(data, dict) for _, data in yielded)
