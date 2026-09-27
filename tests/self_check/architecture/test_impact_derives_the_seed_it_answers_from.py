"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_impact_derives_the_seed_it_answers_from.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import io
import subprocess
import tarfile
from typing import TYPE_CHECKING

import pytest

from beadloom.application.impact import (
    impact_of,
)
from tests.test_impact_derives_the_seed_it_answers_from import (
    THE_COMMIT_POINT,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The tree the measurement was taken at: the parent of `acf4066`, BDL-067's
#: first dev bead. An ancestor of `main`, so a full clone has it.
THE_BDL067_TREE = "af26750dff2f158025124b8fa2f89fb884fe1180"


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


def _the_tree_at(repo: Path, commit: str, into: Path) -> Path:
    """The repository at *commit*, extracted under *into*.

    `git archive` rather than a checkout or a worktree: the tree is read, never
    entered, and nothing in the repository's own state moves. *repo* is the
    self-check snapshot, which carries this repository's history (BDL-074 A3).
    """
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


def _the_commit_is_in_this_checkout(repo: Path) -> bool:
    return (
        subprocess.run(  # noqa: S603 — fixed argv, no shell, no user input
            ["git", "-C", str(repo), "cat-file", "-e", f"{THE_BDL067_TREE}^{{commit}}"],  # noqa: S607
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


@pytest.fixture(scope="module")
def the_bdl067_tree(
    tmp_path_factory: pytest.TempPathFactory, self_check_snapshot: Path
) -> Path:
    """The repository as it stood on 2026-08-31, extracted once."""
    # Probed here rather than in a class-level `skipif` (BDL-074 A1): a marker is
    # evaluated at COLLECTION, outside any test, so its git read of this
    # repository's history could be attributed to no test the contact guard allows.
    if not _the_commit_is_in_this_checkout(self_check_snapshot):
        pytest.skip(
            f"{THE_BDL067_TREE[:8]} is not in this checkout. CI's `tests` job uses "
            "actions/checkout@v5 at the default depth of one, so this case does not "
            "run there; the synthetic classes above are the half that always does."
        )
    return _the_tree_at(self_check_snapshot, THE_BDL067_TREE, tmp_path_factory.mktemp("bdl067"))


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
