"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_the_seed_decides_what_impact_reports.py``;
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

from beadloom.application.source_derivation import (
    writers_that_build,
)
from tests.test_the_seed_decides_what_impact_reports import (
    THE_COMMIT_POINT,
    THE_NARROW_SEED_ANSWER,
    THE_WIDE_SEED_ANSWER,
    _counted,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The tree the measurement was taken at: the parent of `acf4066`, which is
#: BDL-067's first dev bead. It is an ancestor of `main`, so a full clone has it.
THE_BDL067_TREE = "af26750dff2f158025124b8fa2f89fb884fe1180"


#: The function BDL-067's first dev bead was changing, and therefore the seed a
#: derivation pointed at that bead's target would have taken without being told.
THE_FUNCTION_UNDER_CHANGE = "bootstrap_project"


def _the_tree_at(repo: Path, commit: str, into: Path) -> Path:
    """`src/beadloom` as it stood at *commit*, extracted under *into*.

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
    return into / "src" / "beadloom"


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
def the_tree(
    tmp_path_factory: pytest.TempPathFactory, self_check_snapshot: Path
) -> Path:
    """`src/beadloom` at the tree the measurement was taken on, extracted once."""
    # Probed here rather than in a class-level `skipif` (BDL-074 A1): a marker is
    # evaluated at COLLECTION, outside any test, so its git read of this
    # repository's history could be attributed to no test the contact guard allows.
    if not _the_commit_is_in_this_checkout(self_check_snapshot):
        pytest.skip(
            f"{THE_BDL067_TREE[:8]} is not in this checkout. CI's `tests` job uses "
            "actions/checkout@v5 at the default depth of one, so this case does not "
            "run there; TestTheSeedDecidesTheAnswer is the half that always does."
        )
    return _the_tree_at(self_check_snapshot, THE_BDL067_TREE, tmp_path_factory.mktemp("bdl067"))


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
