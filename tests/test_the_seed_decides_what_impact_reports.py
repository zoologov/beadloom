"""The derivations answer about their SEED, not about the tree they are pointed at.

BDL-068 `.3`, and the reason it was sequenced ahead of `beadloom impact`. The epic's
case for being ranked first is that an axes artifact would have prevented BDL-067,
and that claim was unmeasured. This module is the measurement, kept as a check
rather than as a paragraph.

**What was measured.** The lifted derivations were run against the tree as it stood
at BDL-067's first dev bead — `af26750d`, the parent of `acf4066`, 2026-08-31 22:29
+0300 — and asked whether they would have listed BOTH writers of graph nodes and
FOUR entry points of `init`. Neither fact was known that day: the second writer was
first answered in BDL-067's fourth fix cycle, the fourth entry point by its ninth
review, and "three entry points" was said throughout the epic.

**The answer, and it is partial.** Seeded with the commit point every graph YAML
routes through, the derivations list both writers and all four branches on that
tree. Seeded with the function the first dev bead was actually changing, they list
no writers and three branches — the wrong number, delivered as a clean list. So the
facts were within reach on the day and the seed that reaches them is not the seed
that day had: BDL-067's own instrument was seeded narrowly until its fifteenth bead.

That makes seed derivation the load-bearing part of `beadloom impact` rather than an
implementation detail of it, which is what S1.2's acceptance was rewritten to say.

Two cases, because they answer different questions and one of them can vanish:

- :class:`TestTheSeedDecidesTheAnswer` reproduces the shape on a tree this module
  builds, so it runs on every leg of every job and cannot skip.
- :class:`TestTheMeasurementAtTheBdl067Tree` re-runs the original measurement
  against the real commit. It SKIPS where the commit is not in the checkout, which
  is CI's `tests` job: it uses `actions/checkout@v5` at the default depth of one.
  The skip is declared here rather than discovered later, and it is why the
  synthetic case exists beside it rather than instead of it.
"""

from __future__ import annotations

import inspect
import io
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import beadloom
from beadloom.application.source_derivation import (
    PUTS_BYTES_ON_DISK,
    call_sites_in,
    callables_that_reach,
    functions_that_serialise_yaml_to_disk,
    functions_to_their_calls,
    writers_that_build,
)
from beadloom.infrastructure.atomic_io import write_yaml_atomic

if TYPE_CHECKING:
    from beadloom.application.source_derivation import CallSite

#: The tree the measurement was taken at: the parent of `acf4066`, which is
#: BDL-067's first dev bead. It is an ancestor of `main`, so a full clone has it.
THE_BDL067_TREE = "af26750dff2f158025124b8fa2f89fb884fe1180"

#: The commit point every graph YAML routes through, read off the function object
#: so a rename fails here rather than leaving a scan that finds no writer at all.
THE_COMMIT_POINT = write_yaml_atomic.__name__

#: The function BDL-067's first dev bead was changing, and therefore the seed a
#: derivation pointed at that bead's target would have taken without being told.
THE_FUNCTION_UNDER_CHANGE = "bootstrap_project"

#: The marker names a function that does not exist on the 2026-08-31 tree, because
#: `_verdict_on_the_generated_graph` was written inside BDL-067. Every
#: `reaches_marker` there is therefore False, which is that tree's true state. The
#: branch COUNT does not depend on it: guards are read off the call sites.
A_MARKER_THAT_TREE_HAS_NOT_GOT = "_verdict_on_the_generated_graph"

#: Terminator names are resolved through this. Faithful for the tree under
#: examination: `setup.py` imports `sys` at module level and declares no
#: `NoReturn` helper, so `sys.exit` is the only way out that is not a `return`.
THE_RESOLVER = SimpleNamespace(sys=sys)

#: What the derivations report at `af26750d`, per seed. Measured on macOS
#: (Darwin 25.6.0, CPython 3.13.7), in the foreground, with the lifted package
#: imported from `430d9ae`. The two rows are the whole finding.
THE_WIDE_SEED_ANSWER = (2, 4)
THE_NARROW_SEED_ANSWER = (0, 3)


def _branches_of(
    source: str, root: Path, seed: str, command: str
) -> set[tuple[str, ...]]:
    """The distinct branches of *command* that reach anything reaching *seed*.

    The guards themselves rather than their number, because a count cannot say
    WHICH branch a narrow seed lost and that is the half worth knowing.
    """
    sites: tuple[CallSite, ...] = call_sites_in(
        source,
        callables_that_reach(root, seed),
        command=command,
        marker=A_MARKER_THAT_TREE_HAS_NOT_GOT,
        resolving_in=THE_RESOLVER,
    )
    return {site.guard for site in sites}


def _counted(source: str, root: Path, seed: str, command: str) -> tuple[int, int]:
    """The pair the finding is stated in: writers found, branches found."""
    writers = writers_that_build(root, key="nodes", commit_point=seed)
    return len(writers), len(_branches_of(source, root, seed, command))


A_TREE_SHAPED_LIKE_THE_ONE_MEASURED = {
    "atomic.py": """
import yaml


def commit_point(path, data):
    text = yaml.dump(data)
    path.write_text(text)
""",
    "writer_a.py": """
from atomic import commit_point


def writer_a(root):
    payload = {"nodes": [], "edges": []}
    commit_point(root / "a.yml", payload)
""",
    "writer_b.py": """
from atomic import commit_point


def writer_b(root):
    payload = {"nodes": []}
    commit_point(root / "b.yml", payload)
""",
    "flows.py": """
from writer_a import writer_a


def first_flow(root):
    writer_a(root)


def second_flow(root):
    writer_a(root)


def wizard(root):
    writer_a(root)
""",
    "command.py": """
import sys


def run(*, first, second, third, root):
    if first:
        first_flow(root)
        return
    if second:
        second_flow(root)
        return
    if third:
        writer_b(root)
        return
    result = wizard(root)
    if result is None:
        sys.exit(0)
""",
}


@pytest.fixture
def a_tree_like_the_one_measured(tmp_path: Path) -> Path:
    """A tree with the shape `af26750d` had, and nothing else.

    Four branches of one command. Three of them reach the first writer through a
    helper or directly; the fourth reaches a SECOND writer that the first one
    never calls. That last branch is `--import`, and it is the branch a narrow
    seed cannot see.
    """
    root = tmp_path / "package"
    root.mkdir()
    for name, source in A_TREE_SHAPED_LIKE_THE_ONE_MEASURED.items():
        (root / name).write_text(source, encoding="utf-8")
    return root


class TestTheSeedDecidesTheAnswer:
    """The finding, on a tree this module builds, so it runs everywhere."""

    def test_the_commit_point_finds_both_writers_and_every_branch(
        self, a_tree_like_the_one_measured: Path
    ) -> None:
        source = (a_tree_like_the_one_measured / "command.py").read_text(encoding="utf-8")

        assert (
            _counted(source, a_tree_like_the_one_measured, "commit_point", "run")
            == THE_WIDE_SEED_ANSWER
        )

    def test_the_function_under_change_finds_neither(
        self, a_tree_like_the_one_measured: Path
    ) -> None:
        """The same tree, the same derivation, the wrong seed, a clean answer.

        Three branches and no writers, reported with no sign that a fourth branch
        and a second writer exist. A clean list is trusted and stopped at, and
        that is how BDL-067 spent an epic saying "three entry points".
        """
        source = (a_tree_like_the_one_measured / "command.py").read_text(encoding="utf-8")

        assert (
            _counted(source, a_tree_like_the_one_measured, "writer_a", "run")
            == THE_NARROW_SEED_ANSWER
        )

    def test_the_branch_the_narrow_seed_cannot_see_is_the_second_writers(
        self, a_tree_like_the_one_measured: Path
    ) -> None:
        """Which branch is lost, not merely how many — a count hides which one."""
        source = (a_tree_like_the_one_measured / "command.py").read_text(encoding="utf-8")

        wide = _branches_of(source, a_tree_like_the_one_measured, "commit_point", "run")
        narrow = _branches_of(source, a_tree_like_the_one_measured, "writer_a", "run")

        assert wide - narrow == {("third",)}


class TestTheDiskWriteShapeWalksPastTheCommitPoint:
    """A second measurement from `.3`, recorded because it bounds the seed rule.

    A seed rule stated over *reaches a body that puts bytes on disk* cannot find
    this product's own commit point: `write_yaml_atomic` puts its bytes down
    through `os.fdopen(...).write` and `Path.replace`, and the shape spells
    `write_text`, `write_bytes` and `open`. Measured at `af26750d`: 268 names reach
    a body in that set and the commit point is not one of them.

    This pins a GAP, not a property. When it goes red the gap has closed and this
    class is deleted rather than repaired — closing it is `.7`'s, which already
    owns the same shape's other half (narrowing the set to `{write_text}` survives
    the whole suite). Repairing it here would have meant measuring the repair.
    """

    def test_the_commit_points_own_body_names_none_of_the_three_spellings(self) -> None:
        """The direct cause: `fdopen`, `write` and `replace` are not in the set."""
        package = Path(inspect.getfile(beadloom)).parent
        calls = functions_to_their_calls(package)

        assert calls[THE_COMMIT_POINT] & PUTS_BYTES_ON_DISK == set(), (
            f"{THE_COMMIT_POINT} now names one of {sorted(PUTS_BYTES_ON_DISK)}; the "
            "gap this class records may have closed — re-measure and delete it"
        )

    def test_the_shipped_sweep_does_not_name_the_commit_point(self) -> None:
        """The consequence, in the derivation `.1` lifted.

        `functions_that_serialise_yaml_to_disk` is the check that the commit point
        is the only way a graph file reaches disk. It does not name the commit
        point itself, whose stated purpose is to serialise YAML to disk — so the
        sweep is narrower than the sentence it is described by.
        """
        package = Path(inspect.getfile(beadloom)).parent

        assert THE_COMMIT_POINT not in functions_that_serialise_yaml_to_disk(package)


def _the_tree_at(commit: str, into: Path) -> Path:
    """`src/beadloom` as it stood at *commit*, extracted under *into*.

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
    return into / "src" / "beadloom"


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
def the_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """`src/beadloom` at the tree the measurement was taken on, extracted once."""
    return _the_tree_at(THE_BDL067_TREE, tmp_path_factory.mktemp("bdl067"))


@pytest.mark.skipif(
    not _the_commit_is_in_this_checkout(),
    reason=(
        f"{THE_BDL067_TREE[:8]} is not in this checkout. CI's `tests` job uses "
        "actions/checkout@v5 at the default depth of one, so this case does not "
        "run there; TestTheSeedDecidesTheAnswer is the half that always does."
    ),
)
class TestTheMeasurementAtTheBdl067Tree:
    """The original measurement, re-run against the real commit."""

    def test_the_commit_point_lists_both_writers_and_four_entry_points(
        self, the_tree: Path
    ) -> None:
        source = (the_tree / "services" / "commands" / "setup.py").read_text(
            encoding="utf-8"
        )

        assert (
            _counted(source, the_tree, THE_COMMIT_POINT, "init") == THE_WIDE_SEED_ANSWER
        )

    def test_the_function_under_change_lists_no_writer_and_three(
        self, the_tree: Path
    ) -> None:
        source = (the_tree / "services" / "commands" / "setup.py").read_text(
            encoding="utf-8"
        )

        assert (
            _counted(source, the_tree, THE_FUNCTION_UNDER_CHANGE, "init")
            == THE_NARROW_SEED_ANSWER
        )

    def test_the_writers_the_commit_point_finds_are_the_two_that_were_true(
        self, the_tree: Path
    ) -> None:
        """The names, not the count: two wrong writers would pass a count."""
        found = writers_that_build(the_tree, key="nodes", commit_point=THE_COMMIT_POINT)

        assert set(found) == {"bootstrap_project", "import_docs"}
