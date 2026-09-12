"""What each reader of `.beadloom/_graph/` reads for, measured rather than assumed.

BDL-069 S2's first task. `graph_files.each_graph_file` was declared "the one
policy every reader of this directory holds", and a grep for the epic found six
other bodies walking the same directory. The planning question was posed as a
choice — route the six through the policy, or admit the policy is one reader of
seven — and BOTH answers assume the six read the graph AS A GRAPH. At least two
do not: `change_detection._scan_project_files` hashes bytes and
`setup._graph_files_now` digests them, and for those `each_graph_file` is
inapplicable by nature rather than by oversight.

So the classification is an experiment, not a reading. Each reader is asked the
same question over two directories that hold THE SAME NODES and DIFFERENT BYTES
— a YAML comment, which changes every byte-derived answer and no node-derived
one — and then over two that hold different nodes, which every reader must
notice. A reader whose answer moves on the comment reads bytes; one whose answer
moves only on the nodes reads nodes. The observable is the reader's OWN whole
answer rendered as text, not a projection chosen to make the classification come
out: `_scan_project_files` answers in hashes because hashes are what it returns.

Two readers answer by mutating the tree rather than by returning — the
`update_node_in_yaml` writer and the `link` command — so for those the observable
is which ref_ids they found, read off the tree afterwards. That is stated here
rather than in a comment at the call site because it is the one place this
table's answers are not uniform.

The routing that follows is checked in the same module, because a classification
nothing acts on is a note. A reader that parses nodes goes through
`each_graph_file` or names that policy in its own docstring with the reason it
cannot; a reader that does not parse nodes is named in `graph_files.py`'s
docstring as outside the population, so the policy's own sentence cannot claim
more than it holds.
"""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from beadloom.application.reindex.change_detection import _scan_project_files
from beadloom.application.reindex.indexing import read_declared_docs
from beadloom.application.source_derivation.body_shapes import (
    LISTS_A_DIRECTORY,
    PARSES_YAML,
    bodies_calling,
)
from beadloom.application.source_derivation.calls import called_names
from beadloom.application.source_derivation.source_tree import (
    FoundFunction,
    functions_in,
    module_tree,
    sweep_modules,
)
from beadloom.graph.diff import compute_diff
from beadloom.graph.loader import load_graph, update_node_in_yaml
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main
from beadloom.services.commands.setup import _graph_files_now

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable

_SRC = Path("src/beadloom")
_THE_POLICY = _SRC / "onboarding" / "graph_files.py"

#: The nodes every experiment below is run over. Two of them, so an answer that
#: names one node is told apart from one that names the directory. The `docs:`
#: entry is what makes `read_declared_docs` answer at all.
THE_NODES = [
    {
        "ref_id": "orders",
        "kind": "service",
        "summary": "The readable node.",
        "docs": ["services/orders/README.md"],
    },
    {
        "ref_id": "ledger",
        "kind": "domain",
        "summary": "The other one.",
        "docs": ["domains/ledger/README.md"],
    },
]

#: The ref_ids the two mutating readers are probed with: both real nodes and one
#: that is in no graph, so "found everything" and "found anything" differ.
PROBE_REFS = ("orders", "ledger", "not-a-node")

#: A file that does not parse, and one that parses to something `data.get` will
#: not accept. Both are shapes a hand-edited graph file really takes, and both
#: are what `each_graph_file` guards.
UNPARSEABLE_YAML = "nodes:\n  - ref_id: ledger\n   kind: domain\n  bad: [\n"
A_TOP_LEVEL_LIST = "- ref_id: ledger\n- ref_id: payments\n"

_GIT_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": "/usr/bin:/bin:/usr/local/bin",
}


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        check=False,
        encoding="utf-8",
        env=_GIT_ENV,
    )


def a_project(root: Path, *, nodes: list[dict[str, object]], trailer: str = "") -> Path:
    """A project whose graph directory holds *nodes*, plus *trailer* bytes.

    *trailer* is appended as a YAML comment, so the file's bytes differ and the
    mapping it parses to does not. That is the whole of the first experiment.

    The tree is a git repository with an EMPTY graph committed, because
    `compute_diff` reads the previous side at a ref and has no answer without
    one. Committing the graph empty makes every node in it a node the diff
    reports as added, which is that reader's whole answer over this tree.
    """
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (graph_dir / "services.yml").write_text("nodes: []\n", encoding="utf-8")
    _git(root, "init")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "an empty graph")
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump({"nodes": nodes}, sort_keys=False) + trailer, encoding="utf-8"
    )
    return root


def _conn(root: Path) -> sqlite3.Connection:
    db_path = root / ".beadloom" / "probe.db"
    conn = open_db(db_path)
    create_schema(conn)
    return conn


def _asked_of_update_node_in_yaml(root: Path) -> str:
    """Which ref_ids the writer found, read off the tree it wrote.

    It answers `True`/`False` per ref_id rather than about the directory, so it
    is asked once per probe ref and the answer is the set it accepted.
    """
    graph_dir = root / ".beadloom" / "_graph"
    conn = _conn(root)
    try:
        found = [
            ref
            for ref in PROBE_REFS
            if update_node_in_yaml(graph_dir, conn, ref, summary="probed")
        ]
    finally:
        conn.close()
    return repr(found)


def _asked_of_load_graph(root: Path) -> str:
    conn = _conn(root)
    try:
        result = load_graph(root / ".beadloom" / "_graph", conn)
        loaded = sorted(str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes"))
    finally:
        conn.close()
    return repr((result.nodes_loaded, loaded, result.errors))


def _asked_of_compute_diff(root: Path) -> str:
    diff = compute_diff(root, since="HEAD")
    return repr(sorted(f"{change.change_type}:{change.ref_id}" for change in diff.nodes))


def _asked_of_scan_project_files(root: Path) -> str:
    scanned = _scan_project_files(root, root / "docs")
    return repr(sorted((rel, h) for rel, (h, kind) in scanned.items() if kind == "graph"))


def _asked_of_read_declared_docs(root: Path) -> str:
    return repr(read_declared_docs(root / ".beadloom" / "_graph", root, root / "docs"))


def _asked_of_link(root: Path) -> str:
    """Which ref_ids `beadloom link` found, by whether it exited 0 for each."""
    runner = CliRunner()
    found = [
        ref
        for ref in PROBE_REFS
        if runner.invoke(
            main, ["link", ref, "https://example.invalid/1", "--project", str(root)]
        ).exit_code
        == 0
    ]
    return repr(found)


def _asked_of_graph_files_now(root: Path) -> str:
    return repr(sorted(_graph_files_now(root).items()))


@dataclass(frozen=True)
class AReaderOfTheGraphDirectory:
    """One body that walks `.beadloom/_graph/`, and what this table claims of it.

    *reads_for* is the CLAIM; the experiments below are what check it. *routed*
    says whether the body goes through `each_graph_file`, and it is derived from
    the source rather than trusted, so a body that stops routing fails here.
    """

    #: The body, as a traceback spells it.
    name: str
    #: Where the epic's grep found it, so its list and this table are comparable.
    where: str
    #: The reader's whole answer over a project root, rendered as text.
    ask: Callable[[Path], str]
    #: `nodes` or `bytes` — checked by `TestWhatEachReaderReadsFor`.
    reads_for: str
    #: Whether it calls `each_graph_file`. Node readers that do not must name the
    #: policy in their own docstring with the reason.
    routed: bool


THE_READERS: tuple[AReaderOfTheGraphDirectory, ...] = (
    AReaderOfTheGraphDirectory(
        name="update_node_in_yaml",
        where="src/beadloom/graph/loader.py",
        ask=_asked_of_update_node_in_yaml,
        reads_for="nodes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="load_graph",
        where="src/beadloom/graph/loader.py",
        ask=_asked_of_load_graph,
        reads_for="nodes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="compute_diff",
        where="src/beadloom/graph/diff.py",
        ask=_asked_of_compute_diff,
        reads_for="nodes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="_scan_project_files",
        where="src/beadloom/application/reindex/change_detection.py",
        ask=_asked_of_scan_project_files,
        reads_for="bytes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="read_declared_docs",
        where="src/beadloom/application/reindex/indexing.py",
        ask=_asked_of_read_declared_docs,
        reads_for="nodes",
        routed=True,
    ),
    AReaderOfTheGraphDirectory(
        name="link",
        where="src/beadloom/services/commands/index_ops.py",
        ask=_asked_of_link,
        reads_for="nodes",
        routed=True,
    ),
    AReaderOfTheGraphDirectory(
        name="_graph_files_now",
        where="src/beadloom/services/commands/setup.py",
        ask=_asked_of_graph_files_now,
        reads_for="bytes",
        routed=False,
    ),
)

BY_NAME = {reader.name: reader for reader in THE_READERS}
NODE_READERS = tuple(r for r in THE_READERS if r.reads_for == "nodes")
BYTE_READERS = tuple(r for r in THE_READERS if r.reads_for == "bytes")


class TestWhatEachReaderReadsFor:
    """The classification, by experiment: bytes move, or nodes move, or both."""

    @pytest.mark.parametrize("reader", THE_READERS, ids=[r.name for r in THE_READERS])
    def test_a_node_reader_ignores_a_comment_and_a_byte_reader_does_not(
        self, reader: AReaderOfTheGraphDirectory, tmp_path: Path
    ) -> None:
        """Same nodes, different bytes. This is the whole classification."""
        plain = reader.ask(a_project(tmp_path / "plain", nodes=THE_NODES))
        commented = reader.ask(
            a_project(tmp_path / "commented", nodes=THE_NODES, trailer="# a comment\n")
        )

        if reader.reads_for == "nodes":
            assert plain == commented, (reader.name, plain, commented)
        else:
            assert plain != commented, (reader.name, plain)

    @pytest.mark.parametrize("reader", THE_READERS, ids=[r.name for r in THE_READERS])
    def test_every_reader_notices_a_node_that_is_not_there(
        self, reader: AReaderOfTheGraphDirectory, tmp_path: Path
    ) -> None:
        """Anti-vacuity for the case above: an observable that never moves proves nothing."""
        both = reader.ask(a_project(tmp_path / "both", nodes=THE_NODES))
        one = reader.ask(a_project(tmp_path / "one", nodes=THE_NODES[:1]))

        assert both != one, (reader.name, both)

    def test_the_classification_is_not_all_of_one_kind(self) -> None:
        """Both classes are populated, so the two cases above are both live."""
        assert [r.name for r in BYTE_READERS] == ["_scan_project_files", "_graph_files_now"]
        assert len(NODE_READERS) == 5


class TestEveryNodeReaderHoldsTheSkipPolicy:
    """A graph file that will not parse is skipped, not raised at the adopter.

    BDL-UX #220, whose measurement is the reason this bead exists: on a project
    carrying one hand-edited `.beadloom/_graph/legacy.yml`, `init` ended in a
    `yaml.parser.ParserError` raised in `read_declared_docs`, and a top-level
    list ended it in an `AttributeError` no `except yaml.YAMLError` catches.

    `load_graph` and `compute_diff` are asked the same question and answer it
    differently on purpose: each REPORTS the file it could not read rather than
    passing over it, which is a guard and not the absence of one. So the case
    below is over what reaches the caller — no traceback, and the readable node
    still named — rather than over how each reader spells its guard.
    """

    @pytest.mark.parametrize(
        "text", [UNPARSEABLE_YAML, A_TOP_LEVEL_LIST], ids=["does-not-parse", "a-top-level-list"]
    )
    @pytest.mark.parametrize("reader", NODE_READERS, ids=[r.name for r in NODE_READERS])
    def test_a_file_it_cannot_parse_does_not_reach_the_caller(
        self, reader: AReaderOfTheGraphDirectory, text: str, tmp_path: Path
    ) -> None:
        root = a_project(tmp_path / reader.name, nodes=THE_NODES)
        (root / ".beadloom" / "_graph" / "legacy.yml").write_text(text, encoding="utf-8")

        answer = reader.ask(root)

        assert "orders" in answer, (reader.name, answer)

    @pytest.mark.parametrize("reader", NODE_READERS, ids=[r.name for r in NODE_READERS])
    def test_the_rules_file_is_not_read_as_a_graph_file(
        self, reader: AReaderOfTheGraphDirectory, tmp_path: Path
    ) -> None:
        """`rules.yml` holds rules and no nodes, and no reader may name one."""
        root = a_project(tmp_path / reader.name, nodes=THE_NODES)
        (root / ".beadloom" / "_graph" / "rules.yml").write_text(
            yaml.safe_dump({"version": 1, "rules": [{"id": "not-a-node"}]}), encoding="utf-8"
        )

        answer = reader.ask(root)

        assert "not-a-node" not in answer, (reader.name, answer)


def _names(text: str, name: str) -> bool:
    """Whether *text* names *name* as a whole word.

    Substring containment is not enough and was not a hypothetical: the policy's
    docstring mentions `_load_graph_from_yaml`, which contains `load_graph`, so a
    plain `in` reported the loader's exemption as recorded before it was. A DOT
    before the name is allowed, because a docstring names a function the way an
    import does — `graph.loader.load_graph` — and only a word character in front
    of it means a different name.
    """
    return re.search(rf"(?<!\w){re.escape(name)}\b", text) is not None


def _bodies_in(module: Path) -> dict[str, frozenset[str]]:
    """Every function in *module* by name, with the names its own body calls."""
    return {
        function.name: called_names(function) for function in functions_in(module_tree(module))
    }


def _docstrings_in(module: Path) -> dict[str, str]:
    """Every function in *module* by name, with the docstring it carries."""
    return {
        function.name: ast.get_docstring(function) or ""
        for function in functions_in(module_tree(module))
    }


class TestTheRoutingFollowsTheClassification:
    """Every node reader goes through the policy, or names it and says why not.

    Derived from the source, so a body that quietly stops routing fails here
    rather than at an adopter. The two exemptions are not a category — they are
    two functions whose docstrings must say the word, and the case reads them.
    """

    @pytest.mark.parametrize(
        "reader",
        [r for r in NODE_READERS if r.routed],
        ids=[r.name for r in NODE_READERS if r.routed],
    )
    def test_a_routed_reader_calls_the_policy(self, reader: AReaderOfTheGraphDirectory) -> None:
        assert "each_graph_file" in _bodies_in(Path(reader.where))[reader.name], reader.name

    @pytest.mark.parametrize(
        "reader",
        [r for r in NODE_READERS if not r.routed],
        ids=[r.name for r in NODE_READERS if not r.routed],
    )
    def test_a_reader_that_cannot_route_names_the_policy_where_it_reads(
        self, reader: AReaderOfTheGraphDirectory
    ) -> None:
        """An exemption is a sentence in the body that holds it, or it is silence."""
        assert "each_graph_file" in _docstrings_in(Path(reader.where))[reader.name], reader.name

    @pytest.mark.parametrize(
        "reader",
        [r for r in NODE_READERS if not r.routed],
        ids=[r.name for r in NODE_READERS if not r.routed],
    )
    def test_an_exemption_is_recorded_by_the_policy_as_well(
        self, reader: AReaderOfTheGraphDirectory
    ) -> None:
        """Both ends, because one end alone is how a claim outlives its reason.

        The body says why it cannot route; the policy says which bodies do not
        route through it. A reader that stated only the first would leave
        `graph_files.py` free to keep claiming every reader of the directory.
        """
        assert _names(_THE_POLICY.read_text(encoding="utf-8"), reader.name), reader.name

    @pytest.mark.parametrize("reader", BYTE_READERS, ids=[r.name for r in BYTE_READERS])
    def test_a_reader_outside_the_population_is_named_by_the_policy(
        self, reader: AReaderOfTheGraphDirectory
    ) -> None:
        """`graph_files.py` states the population it holds, and names what it does not."""
        policy = _THE_POLICY.read_text(encoding="utf-8")

        assert _names(policy, reader.name), reader.name


def _the_one_body_shape() -> tuple[FoundFunction, ...]:
    """Every body under `src/` that lists a directory AND parses YAML itself."""
    return bodies_calling(sweep_modules(_SRC), LISTS_A_DIRECTORY, and_also=PARSES_YAML)


class TestTheDerivationAndItsCeiling:
    """What `yaml_directory_readers_in`'s shape can see of this table, and what it cannot."""

    def test_the_derivation_names_the_policy_and_the_one_body_exempt_from_it(self) -> None:
        """The shape is *lists a directory AND parses YAML*, both in ONE body.

        Two names, and each is there for a stated reason. `each_graph_file` is
        the policy. `update_node_in_yaml` is the one node reader that restates
        the guards inline, because it is in `graph` and cannot import them; it is
        named here rather than exempted from the derivation, so the day the cycle
        is broken and it routes, this case is what notices.
        """
        named = {found.name for found in _the_one_body_shape()}

        assert named == {"each_graph_file", "update_node_in_yaml"}

    def test_the_two_readers_that_delegate_their_parse_are_invisible_to_it(self) -> None:
        """The ceiling, measured rather than assumed.

        `load_graph` hands its parse to `parse_graph_file` and `compute_diff`
        hands its own to `_parse_yaml_content`, so neither body calls a YAML
        loader and the one-body shape walks past both. They are in this module's
        table because the table was built by asking what each body READS FOR,
        which is a question no call-name shape answers — and it is why the grep
        the epic opened with found seven readers where this derivation finds two.
        """
        named = {found.name for found in _the_one_body_shape()}

        assert {"load_graph", "compute_diff"}.isdisjoint(named)
