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

import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.application.source_derivation import yaml_directory_readers_in
from beadloom.onboarding.doc_generator import _load_graph_from_yaml, _patch_docs_field
from beadloom.onboarding.graph_files import each_graph_file
from beadloom.onboarding.scanner.doc_classify import _existing_graph
from beadloom.services.cli import main
from beadloom.services.commands.setup import _graph_file_of_each_node
from tests.adopter_project import typescript_project

# `init`'s own entry-point-by-mode table, imported rather than restated: BDL-067
# `.19` derives it from the command's source and checks it there, so a fifth
# branch or a third mode arrives in the cases below already carrying a run.
from tests.test_init_one_table_over_every_axis import THE_TABLE, Cell, _answering

if TYPE_CHECKING:
    from collections.abc import Callable

    from _pytest.tmpdir import TempPathFactory

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


#: A fifth reader, written five ways that `.24`'s derivation did not see. Each
#: body lists `.beadloom/_graph/` and parses what it finds, which is the whole of
#: what makes something a reader — and not one of them spells the two calls the
#: way `each_graph_file` happens to spell them. They are synthetic sources rather
#: than files in the tree because the point is what the DETECTOR does with a body
#: nobody has written yet.
A_FIFTH_READER_SPELLED_ANOTHER_WAY: dict[str, str] = {
    "iterdir": """
import yaml
def read(graph_dir):
    for path in graph_dir.iterdir():
        yaml.safe_load(path.read_text())
""",
    "rglob": """
import yaml
def read(graph_dir):
    for path in graph_dir.rglob("*.yml"):
        yaml.safe_load(path.read_text())
""",
    "a glob pattern held in a variable": """
import yaml
def read(graph_dir):
    pattern = "*.yml"
    for path in graph_dir.glob(pattern):
        yaml.safe_load(path.read_text())
""",
    "os.listdir": """
import os
import yaml
def read(graph_dir):
    for name in os.listdir(graph_dir):
        yaml.safe_load((graph_dir / name).read_text())
""",
    "yaml.load with a loader": """
import yaml
def read(graph_dir):
    for path in graph_dir.glob("*.yml"):
        yaml.load(path.read_text(), Loader=yaml.SafeLoader)
""",
    # BDL-068 `.1`. The sixth spelling, and the one the lift closes: both verbs
    # imported by name, so neither call is an attribute of anything. `.25`
    # matched `call.func.attr` alone, which is a claim about how a call is
    # PUNCTUATED rather than about what it does.
    "both verbs imported by name": """
from os import listdir
from yaml import safe_load
def read(graph_dir):
    for name in listdir(graph_dir):
        safe_load((graph_dir / name).read_text())
""",
}

#: Bodies that hold ONE half of the shape and must NOT be reported. A detector
#: that reports these is a detector whose failures are noise, and a noisy
#: derivation is one somebody exempts their way out of.
ONE_HALF_OF_THE_SHAPE: dict[str, str] = {
    "lists the directory and parses nothing": """
def read(graph_dir):
    return sorted(graph_dir.glob("*.yml"))
""",
    "parses YAML and lists nothing": """
import yaml
def read(path):
    return yaml.safe_load(path.read_text())
""",
}


class TestTheSkipPolicyLivesInOneBody:
    """Derived from the source, so a fifth policy cannot be added quietly.

    A graph-file reader is a function that both LISTS a directory and PARSES
    YAML — the two halves of the shape, which is what makes this a derivation
    rather than a list of four names somebody keeps up to date.

    BDL-067 `.25` WIDENED both halves, and the reason is the bead's own claim
    that a fifth reader must fail here "on the day it is written". `.24` asked
    for `glob` with the literal `"*.yml"` and for `yaml.safe_load` by name, which
    is how `each_graph_file` is spelled and not what makes a body a reader:
    MEASURED, five bodies that read the directory pass that detector untouched
    (`A_FIFTH_READER_SPELLED_ANOTHER_WAY`), and each of them would carry a sixth
    skip policy into the product.

    BDL-068 `.1` lifted the derivation itself into
    `application/source_derivation/body_shapes.py`, where the trade-off of
    widening it is stated with the measurement that justified it. The cases here
    are unchanged and are what holds that code to the shape: they are the tree it
    goes red on. The sixth spelling — both verbs imported by name, so neither
    call is an attribute of anything — was added with the lift and was RED
    against `.25`'s detector before it.
    """

    #: Where `init`'s own readers live. `rules_gen` and `agents_md` parse
    #: `rules.yml` by name and never walk the directory, so the derivation does
    #: not reach them and does not need to exempt them.
    SEARCHED = (
        Path("src/beadloom/onboarding"),
        Path("src/beadloom/services/commands/setup.py"),
    )
    THE_ONE_BODY = Path("src/beadloom/onboarding/graph_files.py")

    def _readers_in_source(self, source: str, label: str) -> list[str]:
        """The derivation's answer, labelled with where it was asked."""
        return [f"{label}::{name}" for name in yaml_directory_readers_in(source)]

    def _readers_in(self, module: Path) -> list[str]:
        return self._readers_in_source(module.read_text(encoding="utf-8"), str(module))

    def _every_module(self) -> list[Path]:
        modules: list[Path] = []
        for where in self.SEARCHED:
            modules.extend(sorted(where.rglob("*.py")) if where.is_dir() else [where])
        return modules

    def test_the_derivation_finds_the_shared_reader(self) -> None:
        """Anti-vacuity: the detector detects the one body that should match."""
        assert self._readers_in(self.THE_ONE_BODY), self.THE_ONE_BODY

    @pytest.mark.parametrize("spelling", sorted(A_FIFTH_READER_SPELLED_ANOTHER_WAY))
    def test_a_reader_spelled_another_way_is_still_a_reader(self, spelling: str) -> None:
        """The five routes `.24`'s narrower shape let through, one case each."""
        source = A_FIFTH_READER_SPELLED_ANOTHER_WAY[spelling]

        assert self._readers_in_source(source, spelling) == [f"{spelling}::read"]

    @pytest.mark.parametrize("spelling", sorted(ONE_HALF_OF_THE_SHAPE))
    def test_half_the_shape_is_not_a_reader(self, spelling: str) -> None:
        """The other side of widening: what it must still refuse to name."""
        assert self._readers_in_source(ONE_HALF_OF_THE_SHAPE[spelling], spelling) == []

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


#: A graph file carrying a value YAML types and JSON does not. `added: 2026-09-02`
#: loads as a `datetime.date`, and it is a shape a hand-edited graph file really
#: takes. It is not unreadable — `each_graph_file` yields it, and the four
#: readers above are fine with it — so it belongs to this class for a different
#: reason: it is the third way one hand-edited file ends `init` in a traceback,
#: and it dies in a different reader from the other two.
A_DATE_YAML_TYPES_AND_JSON_DOES_NOT = (
    "nodes:\n"
    "  - ref_id: ledger\n"
    "    kind: domain\n"
    "    summary: Dated by hand.\n"
    "    added: 2026-09-02\n"
)


@dataclass(frozen=True)
class AGraphFileInitCannotSurvive:
    """One hand-edited graph file, and where `init` ends up because of it."""

    #: How it is spelled, for the test id.
    name: str
    #: What is in the file.
    text: str
    #: What reaches the adopter.
    raises: type[BaseException]
    #: The frame it is raised in, as the traceback spells it. Named rather than
    #: merely counted, because the finding is that it is ONE reader for the two
    #: unreadable shapes and a second for the third — not four readers, and not
    #: any of `init`'s own.
    the_reader_it_dies_in: str


THE_SHAPES = (
    AGraphFileInitCannotSurvive(
        name="does-not-parse",
        text=UNPARSEABLE_YAML,
        raises=yaml.YAMLError,
        the_reader_it_dies_in="read_declared_docs",
    ),
    AGraphFileInitCannotSurvive(
        name="a-top-level-list",
        text=A_TOP_LEVEL_LIST,
        raises=AttributeError,
        the_reader_it_dies_in="read_declared_docs",
    ),
    AGraphFileInitCannotSurvive(
        name="a-date-scalar",
        text=A_DATE_YAML_TYPES_AND_JSON_DOES_NOT,
        raises=TypeError,
        the_reader_it_dies_in="load_graph",
    ),
)

#: `init`'s own four readers, by the names a traceback would carry. None of them
#: may appear in a frame below: that is the half of this class that measures what
#: `.24` fixed, as opposed to the half that measures what it did not.
THE_READERS_THIS_EPIC_CONSOLIDATED = (
    "_load_graph_from_yaml",
    "_patch_docs_field",
    "_graph_file_of_each_node",
    "_existing_graph",
)

THE_RUNS = tuple((cell, shape) for cell in THE_TABLE for shape in THE_SHAPES)
RUN_IDS = [f"{cell.name}-{shape.name}" for cell, shape in THE_RUNS]


def _a_tree_every_branch_can_be_pointed_at(tmp_path: Path, text: str) -> Path:
    """The tree above, plus the `docs/` the `--import` branch is given.

    `EntryPoint.argv` hands `--import` a path, and click checks it exists, so a
    branch axis that omits the directory measures the flag parser rather than the
    command.
    """
    project = _a_tree_holding_one_unreadable_graph_file(tmp_path, text)
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "payments.md").write_text("# Payments\n\nAn adopter's doc.\n", encoding="utf-8")
    return project


@dataclass(frozen=True)
class BranchOutcome:
    """What one branch did with one hand-edited file."""

    exit_code: int
    output: str
    raised: BaseException | None
    frames: tuple[str, ...]
    #: The file's bytes afterwards, so "it refused the tree" can be told apart
    #: from "it read the tree and survived".
    the_file_afterwards: str | None


def _perform(project_root: Path, cell: Cell, shape: AGraphFileInitCannotSurvive) -> BranchOutcome:
    with _answering(cell, reinit=True):
        result = CliRunner().invoke(
            main,
            ["init", *cell.entry.argv(cell.mode, project_root), "--project", str(project_root)],
        )
    raised = result.exception
    frames = (
        tuple(frame.name for frame in traceback.extract_tb(raised.__traceback__))
        if raised is not None and not isinstance(raised, SystemExit)
        else ()
    )
    unreadable = project_root / ".beadloom" / "_graph" / THE_UNREADABLE_FILE
    return BranchOutcome(
        exit_code=result.exit_code,
        output=str(result.output),
        raised=raised,
        frames=frames,
        the_file_afterwards=(
            unreadable.read_text(encoding="utf-8") if unreadable.is_file() else None
        ),
    )


@pytest.fixture(scope="module")
def branch_runs(tmp_path_factory: TempPathFactory) -> dict[str, BranchOutcome]:
    """Every (branch, shape), run once and read from several angles.

    Module-scoped for the reason the sibling table gives: a cell costs a full
    `init`, and each case below reads an immutable record of a completed run
    rather than sharing state with the others.
    """
    performed: dict[str, BranchOutcome] = {}
    for (cell, shape), run_id in zip(THE_RUNS, RUN_IDS, strict=True):
        root = _a_tree_every_branch_can_be_pointed_at(
            tmp_path_factory.mktemp(run_id.replace("-", "_")), shape.text
        )
        performed[run_id] = _perform(root, cell, shape)
    return performed


class TestWhatEveryBranchOfInitDoesWithAFileItCannotHandle:
    """The branch axis of BDL-067 `.25`'s major 2, stated as what was measured.

    The bead asks for a case in which a project carrying an unreadable
    `.beadloom/_graph/*.yml` "must not traceback out of ANY init branch". That is
    not what the product does, and this class says so rather than asserting it.
    MEASURED, over every cell of `init`'s own entry-point by mode table: every
    branch that can meet a graph file it did not write — `--bootstrap`,
    `--import` and both modes of the wizard — still ends in a traceback, on all
    three shapes, and always in a reader that is not one of the four this epic
    consolidated. `--yes` cannot meet the file at all, and says so.

    So the residue `.24` pinned for ONE branch and ONE shape is here pinned as
    the class it is: 12 runs, two frames, both outside `onboarding`
    (`application/reindex/indexing.read_declared_docs` and `graph/loader
    .load_graph`). It is filed as `beadloom-l22o` / BDL-UX #220 and is out of
    this bead's scope; these cases exist so that closing it fails a test with a
    measurement attached, and so the epic cannot be read as though `init` had
    stopped tracebacking on a hand-edited graph file.

    The axis is `THE_TABLE`, imported rather than restated, so a fifth branch or
    a third mode arrives here already carrying a case — and that table is itself
    checked against `init`'s own source by the module it comes from.
    """

    def test_every_cell_of_the_table_has_a_run(
        self, branch_runs: dict[str, BranchOutcome]
    ) -> None:
        """The two enumerations, bound: no branch and no shape goes unrun."""
        assert set(branch_runs) == set(RUN_IDS)
        assert {cell.name for cell in THE_TABLE} == {cell.name for cell, _ in THE_RUNS}
        assert len(branch_runs) == len(THE_TABLE) * len(THE_SHAPES)

    @pytest.mark.parametrize(
        ("cell", "shape"),
        [(cell, shape) for cell, shape in THE_RUNS if cell.entry.can_meet_a_file_it_did_not_write],
        ids=[
            run_id
            for (cell, _), run_id in zip(THE_RUNS, RUN_IDS, strict=True)
            if cell.entry.can_meet_a_file_it_did_not_write
        ],
    )
    def test_a_branch_that_meets_the_file_dies_outside_this_epics_readers(
        self,
        branch_runs: dict[str, BranchOutcome],
        cell: Cell,
        shape: AGraphFileInitCannotSurvive,
    ) -> None:
        """Both halves in one case: what `.24` fixed, and what it did not reach.

        The frames are asserted rather than the message because there is no
        message — a traceback is what the adopter is handed. The day
        `beadloom-l22o` is closed this case fails, which is the point of it.
        """
        outcome = branch_runs[f"{cell.name}-{shape.name}"]

        assert isinstance(outcome.raised, shape.raises), outcome.output
        assert shape.the_reader_it_dies_in in outcome.frames, outcome.frames
        for reader in THE_READERS_THIS_EPIC_CONSOLIDATED:
            assert reader not in outcome.frames, (reader, outcome.frames)

    def test_the_whole_residue_is_two_readers_and_neither_is_ours(
        self, branch_runs: dict[str, BranchOutcome]
    ) -> None:
        """The class, counted: 12 runs, two frames, no branch of its own.

        Stated as a set rather than per run because the finding is that the
        branch does not matter — every branch that reads the tree reaches the
        same two unguarded readers, which is why this is one planning decision
        and not four.
        """
        died_in = {
            shape.the_reader_it_dies_in
            for cell, shape in THE_RUNS
            if cell.entry.can_meet_a_file_it_did_not_write
            for outcome in [branch_runs[f"{cell.name}-{shape.name}"]]
            if outcome.raised is not None
        }

        assert died_in == {"read_declared_docs", "load_graph"}

    @pytest.mark.parametrize(
        ("cell", "shape"),
        [
            (cell, shape)
            for cell, shape in THE_RUNS
            if not cell.entry.can_meet_a_file_it_did_not_write
        ],
        ids=[
            run_id
            for (cell, _), run_id in zip(THE_RUNS, RUN_IDS, strict=True)
            if not cell.entry.can_meet_a_file_it_did_not_write
        ],
    )
    def test_the_branch_that_cannot_meet_the_file_says_so_and_leaves_it_alone(
        self,
        branch_runs: dict[str, BranchOutcome],
        cell: Cell,
        shape: AGraphFileInitCannotSurvive,
    ) -> None:
        """`--yes` is green here for a reason that is not a guard working.

        It refuses the tree: `non_interactive_init` returns `skipped` when
        `.beadloom/` is already there, so the file is never read. The message is
        asserted, and so is the file's content afterwards — a run that had read
        the tree and survived would be a different fact from a run that declined
        to look, and only the second one is true.
        """
        outcome = branch_runs[f"{cell.name}-{shape.name}"]

        assert outcome.raised is None, outcome.frames
        assert outcome.exit_code == 0, outcome.output
        assert "Warning: .beadloom/ already exists. Use --force to overwrite." in outcome.output, (
            outcome.output
        )
        assert outcome.the_file_afterwards == shape.text
