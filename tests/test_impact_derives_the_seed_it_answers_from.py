"""`beadloom impact` answers over a seed it derived, and says which one (BDL-068 S1.2).

BDL-068 `.3` measured, at the tree BDL-067's first dev bead started from, that the
same derivations report TWO writers and FOUR branches under one seed and NONE and
THREE under another. Three is the number that epic carried for nine review passes.
Neither answer is wrong about what it was asked; both are clean, and only one is
true about the change. So the criterion this module exists for is not "does the
command find the writers" — a tool with `write_yaml_atomic` hardcoded finds them,
and that authored list is what the epic exists to remove. It is: **does the
command derive its seed from the target, name it, and say so when it has none.**

Three groups, and they run in different rooms on purpose:

- :class:`TestTheSeedRuleIsDerivedAndNamed` and
  :class:`TestATargetWithNoSeedIsUnresolvedRatherThanEmpty` build the shape in a
  tmp directory, so they run on every leg of every job.
- :class:`TestTheAcceptanceTargetsAtTheBdl067Tree` re-runs the bead's two
  acceptance targets against the real historical commit through `git archive` —
  the tree is read, never entered. It SKIPS where the commit is not in the
  checkout, which is CI's `tests` job at `actions/checkout@v5`'s default depth of
  one. The skip is declared here rather than discovered later.
"""

from __future__ import annotations

import ast
import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from beadloom.application.impact import (
    THE_EFFECT_RULES,
    impact_of,
)
from beadloom.application.impact.seeds import sinks_under
from beadloom.application.source_derivation import (
    PUTS_BYTES_ON_DISK,
    sweep_modules,
)
from beadloom.infrastructure.atomic_io import write_yaml_atomic

#: The tree the measurement was taken at: the parent of `acf4066`, BDL-067's
#: first dev bead. An ancestor of `main`, so a full clone has it.
THE_BDL067_TREE = "af26750dff2f158025124b8fa2f89fb884fe1180"

#: The commit point every graph YAML routes through, read off the product's own
#: function object. It is named HERE, in the test, and nowhere in the production
#: package -- which :class:`TestNoProductionLiteralNamesTheCommitPoint` checks.
THE_COMMIT_POINT = write_yaml_atomic.__name__

#: The four entry points of `init` on that tree. The fallthrough is the one its
#: ninth review found, and the one a binding-shaped count cannot see.
THE_FOUR_ENTRY_POINTS = {
    ("non_interactive",),
    ("bootstrap",),
    ("import_path",),
    (),
}

#: The two writers of graph nodes. The second was first answered in BDL-067's
#: fourth fix cycle, and the file under change never calls it.
THE_TWO_WRITERS = {"bootstrap_project", "import_docs"}

#: The production modules that must never spell the commit point.
THE_PRODUCTION_SURFACE = (
    Path("src/beadloom/application/impact"),
    Path("src/beadloom/services/commands/impact.py"),
)

#: The sink puts its bytes down the way this product's own commit point does --
#: through `os.fdopen(...).write` and `Path.replace` -- so the tree reproduces
#: BDL-068 `.3`'s finding rather than restating it: a rule stated over
#: `PUTS_BYTES_ON_DISK` walks straight past the thing it exists to protect.
_THE_SINK_TWO_HOPS_DOWN = '''\
import os
import tempfile
from pathlib import Path

import yaml


def commit_yaml(path, payload):
    handle, temporary = tempfile.mkstemp()
    with os.fdopen(handle, "w") as stream:
        stream.write(yaml.safe_dump(payload))
    Path(temporary).replace(path)
'''

_THE_FIRST_HOP = '''\
from tree.sink import commit_yaml


def build_graph(root, name):
    commit_yaml(root / "graph.yml", {"nodes": [name]})
'''

_THE_COMMAND = '''\
import sys

from tree.writer import build_graph


def run(root, declared, bootstrapped):
    if declared:
        build_graph(root, "declared")
        return
    if bootstrapped:
        build_graph(root, "bootstrapped")
        sys.exit(0)
    build_graph(root, "asked")
'''

_THE_LONELY_MODULE = '''\
def note(what):
    return what


def measure(a, b):
    if a:
        note("a")
        return 1
    if b:
        note("b")
        raise ValueError("b")
    note("neither")
    return 0
'''

_THE_UNREADABLE_MODULE = "def broken(:\n"

_THE_DISPATCHING_MODULE = '''\
def dispatch(target, name, table, key):
    getattr(target, name)()
    table[key]()
'''


@pytest.fixture()
def a_tree(tmp_path: Path) -> Path:
    """A project whose command reaches its commit point through a helper."""
    package = tmp_path / "src" / "tree"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    for name, body in (
        ("sink", _THE_SINK_TWO_HOPS_DOWN),
        ("writer", _THE_FIRST_HOP),
        ("command", _THE_COMMAND),
        ("lonely", _THE_LONELY_MODULE),
        ("dispatching", _THE_DISPATCHING_MODULE),
    ):
        (package / f"{name}.py").write_text(body, encoding="utf-8")
    return tmp_path


class TestTheSeedRuleIsDerivedAndNamed:
    """The seed comes from the target, and the answer says which rule found it."""

    def test_the_seed_is_the_sink_and_not_the_name_the_target_calls(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/command.py", project_root=a_tree)
        assert [seed.name for seed in answer.seeds] == ["commit_yaml"]
        assert "build_graph" not in {seed.name for seed in answer.seeds}

    def test_the_answer_names_the_rule_and_the_rule_names_its_effect(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/command.py", project_root=a_tree)
        assert answer.seed_rule
        assert answer.seed_rule_statement
        assert answer.seeds[0].effect == "serialises-yaml"
        assert answer.seeds[0].path.name == "sink.py"

    def test_a_writer_the_target_never_calls_is_in_the_co_writers(
        self, a_tree: Path
    ) -> None:
        (a_tree / "src" / "tree" / "second.py").write_text(
            "from tree.sink import commit_yaml\n\n\n"
            'def import_docs(root, docs):\n    commit_yaml(root / "d.yml", list(docs))\n',
            encoding="utf-8",
        )
        answer = impact_of("src/tree/writer.py", project_root=a_tree)
        written = {site.name for site in answer.co_writers.sites}
        assert {"build_graph", "import_docs"} <= written
        assert "import_docs" not in (a_tree / "src" / "tree" / "writer.py").read_text(
            encoding="utf-8"
        )

    def test_the_branches_are_the_ones_that_reach_the_seed(self, a_tree: Path) -> None:
        answer = impact_of("src/tree/command.py", project_root=a_tree)
        run = next(command for command in answer.commands if command.name == "run")
        assert {branch.guard for branch in run.branches} == {
            ("declared",),
            ("bootstrapped",),
            (),
        }
        assert run.narrowed_to_the_seeds is True

    def test_the_exit_forms_include_the_one_that_is_not_a_return(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/command.py", project_root=a_tree)
        run = next(command for command in answer.commands if command.name == "run")
        assert "sys.exit(0)" in run.exits
        assert "return" in run.exits


class TestATargetWithNoSeedIsUnresolvedRatherThanEmpty:
    """A clean list is trusted and stopped at, so an absent population says so."""

    def test_the_co_writer_axis_reports_unresolved_and_not_an_empty_list(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/lonely.py", project_root=a_tree)
        assert answer.seeds == ()
        assert answer.co_writers.resolved is False
        assert answer.co_writers.sites == ()
        assert answer.co_writers.reason

    def test_the_unresolved_population_carries_the_missing_seed_as_a_kind(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/lonely.py", project_root=a_tree)
        assert "no-seed" in {gap.kind for gap in answer.unresolved}

    def test_a_module_whose_axes_live_inside_it_still_gets_an_answer(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/lonely.py", project_root=a_tree)
        measure = next(
            command for command in answer.commands if command.name == "measure"
        )
        assert len(measure.branches) == 3
        assert measure.narrowed_to_the_seeds is False
        assert len(measure.exits) >= 2

    def test_a_target_that_names_nothing_is_an_error_and_not_an_empty_answer(
        self, a_tree: Path
    ) -> None:
        from beadloom.application.impact import NoSuchTargetError

        with pytest.raises(NoSuchTargetError):
            impact_of("no_such_symbol_anywhere", project_root=a_tree)


class TestTheUnresolvedPopulationIsAFieldAndNotAnOmission:
    """What the derivation cannot read travels with the answer."""

    def test_a_module_that_does_not_parse_is_named(self, a_tree: Path) -> None:
        (a_tree / "src" / "tree" / "unreadable.py").write_text(
            _THE_UNREADABLE_MODULE, encoding="utf-8"
        )
        answer = impact_of("src/tree/command.py", project_root=a_tree)
        gaps = [gap for gap in answer.unresolved if gap.kind == "unparsed-module"]
        assert [gap.where for gap in gaps] == ["unreadable.py"]

    def test_dynamic_dispatch_and_a_call_through_a_variable_are_named(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/dispatching.py", project_root=a_tree)
        kinds = {gap.kind for gap in answer.unresolved}
        assert {"dynamic-dispatch", "call-through-a-variable"} <= kinds

    def test_an_absent_index_is_reported_rather_than_read_as_inside(
        self, a_tree: Path
    ) -> None:
        answer = impact_of("src/tree/command.py", project_root=a_tree)
        assert answer.boundary.resolved is False
        assert "no-graph-index" in {gap.kind for gap in answer.unresolved}


class TestNoProductionLiteralNamesTheCommitPoint:
    """The seed is derived, so nothing in production may spell it or be handed it."""

    def test_no_production_module_spells_the_commit_point(self) -> None:
        for path in _the_production_modules():
            assert THE_COMMIT_POINT not in _spelled_in_code(path), (
                f"{path} names {THE_COMMIT_POINT} in code. A hardcoded commit "
                "point satisfies every other criterion here and is the authored "
                "list BDL-068 exists to remove."
            )

    def test_no_production_module_takes_a_commit_point_argument(self) -> None:
        for path in _the_production_modules():
            assert "commit_point" not in _spelled_in_code(path)


class TestTheEffectRulesAreNotStatedOverTheDiskWriteVerbs:
    """`PUTS_BYTES_ON_DISK` is excluded by design, and the exclusion is checked."""

    def test_no_declared_effect_uses_the_disk_write_verbs(self) -> None:
        for rule in THE_EFFECT_RULES:
            assert rule.verbs != PUTS_BYTES_ON_DISK
            assert rule.and_also != PUTS_BYTES_ON_DISK

    def test_the_disk_write_verbs_walk_past_the_sink_the_declared_rule_finds(
        self, a_tree: Path
    ) -> None:
        """Not a restatement of `.3`'s gap record: this is the rule choice biting.

        `.3` measured that the product's own commit point is outside
        `PUTS_BYTES_ON_DISK` and handed the narrowing to `.7`. What is checked
        here is the consequence for THIS command, on a tree whose sink writes the
        way that one does: the declared rule finds it and the disk-write
        vocabulary does not, so which vocabulary the seed rule is stated over
        decides the whole answer.
        """
        from beadloom.application.source_derivation import bodies_calling

        sweep = sweep_modules(a_tree / "src" / "tree")
        assert "commit_yaml" in set(sinks_under(sweep))
        assert "commit_yaml" not in {
            body.name for body in bodies_calling(sweep, PUTS_BYTES_ON_DISK)
        }


def _spelled_in_code(path: Path) -> set[str]:
    """Every identifier and every non-docstring string constant in *path*.

    Docstrings are excluded deliberately. `seeds.py` CITES the commit point in
    prose, because the measurement that excluded `PUTS_BYTES_ON_DISK` is stated
    in terms of it and a rule whose reason has been deleted is a rule nobody can
    argue with. What must not exist is a place where the name DECIDES something.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    documented = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    spelled: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            spelled.add(node.id)
        elif isinstance(node, ast.Attribute):
            spelled.add(node.attr)
        elif isinstance(node, ast.arg | ast.keyword) and node.arg is not None:
            spelled.add(node.arg)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            spelled.add(node.name)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node not in documented
        ):
            spelled.add(node.value)
    return spelled


def _the_production_modules() -> list[Path]:
    repo = Path(__file__).resolve().parents[1]
    found: list[Path] = []
    for relative in THE_PRODUCTION_SURFACE:
        path = repo / relative
        found.extend(sorted(path.rglob("*.py")) if path.is_dir() else [path])
    assert found, "the production surface resolved to nothing to read"
    return found


def _the_tree_at(commit: str, into: Path) -> Path:
    """The repository at *commit*, extracted under *into*.

    `git archive` rather than a checkout or a worktree: the tree is read, never
    entered, and nothing in the repository's own state moves.
    """
    repo = Path(__file__).resolve().parents[1]
    archive = subprocess.run(  # noqa: S603 — fixed argv, no shell, no user input
        ["git", "-C", str(repo), "archive", commit, "src/beadloom"],  # noqa: S607
        capture_output=True,
        check=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        for member in bundle.getmembers():
            if not member.isfile():
                continue
            target = into / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = bundle.extractfile(member)
            if extracted is not None:
                target.write_bytes(extracted.read())
    return into


def _the_commit_is_in_this_checkout() -> bool:
    repo = Path(__file__).resolve().parents[1]
    return (
        subprocess.run(  # noqa: S603 — fixed argv, no shell, no user input
            ["git", "-C", str(repo), "cat-file", "-e", f"{THE_BDL067_TREE}^{{commit}}"],  # noqa: S607
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


@pytest.fixture(scope="module")
def the_bdl067_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The repository as it stood on 2026-08-31, extracted once."""
    return _the_tree_at(THE_BDL067_TREE, tmp_path_factory.mktemp("bdl067"))


@pytest.mark.skipif(
    not _the_commit_is_in_this_checkout(),
    reason=(
        f"{THE_BDL067_TREE[:8]} is not in this checkout. CI's `tests` job uses "
        "actions/checkout@v5 at the default depth of one, so this case does not "
        "run there; the synthetic classes above are the half that always does."
    ),
)
class TestTheAcceptanceTargetsAtTheBdl067Tree:
    """The bead's two acceptance targets, run at the commit it names them at.

    No invocation below passes a commit point, and no production module spells
    one — the class above checks the second half over the same files.
    """

    def test_bootstrap_lists_both_writers_of_graph_nodes(
        self, the_bdl067_tree: Path
    ) -> None:
        answer = impact_of(
            "src/beadloom/onboarding/scanner/bootstrap.py",
            project_root=the_bdl067_tree,
        )
        assert [seed.name for seed in answer.seeds] == [THE_COMMIT_POINT]
        assert answer.seeds[0].effect == "serialises-yaml"
        assert answer.co_writers.resolved is True
        assert {site.name for site in answer.co_writers.sites} >= THE_TWO_WRITERS

    def test_setup_lists_four_entry_points_of_init_and_the_way_out_that_is_not_a_return(
        self, the_bdl067_tree: Path
    ) -> None:
        answer = impact_of(
            "src/beadloom/services/commands/setup.py", project_root=the_bdl067_tree
        )
        assert THE_COMMIT_POINT in {seed.name for seed in answer.seeds}
        init = next(command for command in answer.commands if command.name == "init")
        assert {branch.guard for branch in init.branches} == THE_FOUR_ENTRY_POINTS
        assert "sys.exit(0)" in init.exits
        assert "return" in init.exits

    def test_the_commit_point_is_two_hops_down_and_the_first_hop_is_not_a_seed(
        self, the_bdl067_tree: Path
    ) -> None:
        answer = impact_of(
            "src/beadloom/services/commands/setup.py", project_root=the_bdl067_tree
        )
        found = {seed.name for seed in answer.seeds}
        assert THE_COMMIT_POINT in found
        assert found.isdisjoint({"bootstrap_project", "import_docs", "interactive_init"})

    def test_the_answer_names_the_root_it_swept_and_the_gaps_it_left(
        self, the_bdl067_tree: Path
    ) -> None:
        answer = impact_of(
            "src/beadloom/onboarding/scanner/bootstrap.py",
            project_root=the_bdl067_tree,
        )
        assert answer.root == "src/beadloom"
        assert "unresolved-terminator-name" in {gap.kind for gap in answer.unresolved}
