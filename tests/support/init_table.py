"""The one table of init's entry points against every axis, and how a cell is answered."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tests.support.init_verdict import (
    THE_MODES,
    THE_MODES_THAT_BOOTSTRAP,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class EntryPoint:
    """One branch of `init` that writes a graph file, and the modes it declares.

    `guard` is the branch's identity as `init`'s own source spells it, and it is
    what binds this table to `tests/test_init_branches_that_reach_the_bootstrap.
    py`'s enumerator. A branch is not a binding and not a flag spelling: `.6`
    exists because two bindings were counted as two branches for four waves while
    the branch a human adopter meets first went unjudged.
    """

    #: How it is spelled on the command line, for the test id. The three that
    #: reach the bootstrap use the names `THE_BRANCHES` uses, so the sabotage
    #: binding can be looked up there instead of restated here.
    name: str
    #: The `if` conditions the branch sits under, outermost first, as the source
    #: spells them. The empty tuple is the fallthrough wizard.
    guard: tuple[str, ...]
    #: Every mode this branch can be asked for. Two branches take `--mode` and
    #: offer whatever the flag offers; the other two declare one mode each, and
    #: `test_a_fixed_mode_branch_declares_the_mode_its_writers_are` checks that
    #: declaration against the writers found under the guard.
    modes: tuple[str, ...]
    #: Whether this branch can WRITE a graph file in a run that also meets one
    #: it did not write. `--yes` is the one that cannot, and it fails both halves
    #: rather than one: without `--force` `non_interactive_init` returns
    #: `skipped`, so the inherited file survives a run that wrote nothing, and
    #: with `--force` the directory is deleted before anything runs. Measured
    #: over every branch in `TestWhichBranchesCanMeetAFileTheyDidNotWrite`, as
    #: the conjunction rather than as either half.
    can_meet_a_file_it_did_not_write: bool

    def argv(self, mode: str, project_root: Path) -> tuple[str, ...]:
        if self.name == "--yes":
            return ("--yes", "--mode", mode)
        if self.name == "--bootstrap":
            return ("--bootstrap",)
        if self.name == "--import":
            return ("--import", str(project_root / "docs"))
        return ()

    def prompts(self, mode: str, *, reinit: bool) -> tuple[str, ...]:
        """The wizard's answers, in order; empty for the branches that ask none.

        The re-init answer comes first when `.beadloom/` is already there:
        `overwrite` keeps the directory and the files inside it, which is what
        makes the wizard able to meet a rules file it did not write. The graph
        review is asked only when the run produced nodes to review, so only the
        modes that bootstrap answer it, and the answer is always `yes` -- `edit`
        is the one answer that takes no verdict and it is the sibling module's.
        """
        if self.name != "wizard":
            return ()
        answers = ["overwrite"] if reinit else []
        answers.append(mode)
        if mode in THE_MODES_THAT_BOOTSTRAP:
            answers.append("yes")
        return tuple(answers)


#: Every branch of `init` that writes a graph file, with the modes it offers.
#: `--bootstrap` and `--import` are branches with one mode rather than flags with
#: none: each calls exactly one node-creating writer, and that is what makes the
#: cell count 8 rather than 12.
THE_ENTRY_POINTS = (
    EntryPoint("--yes", ("non_interactive",), THE_MODES, can_meet_a_file_it_did_not_write=False),
    EntryPoint(
        "--bootstrap", ("bootstrap",), ("bootstrap",), can_meet_a_file_it_did_not_write=True
    ),
    EntryPoint("--import", ("import_path",), ("import",), can_meet_a_file_it_did_not_write=True),
    EntryPoint("wizard", (), THE_MODES, can_meet_a_file_it_did_not_write=True),
)


@dataclass(frozen=True)
class Cell:
    """One (entry point, mode) the command offers."""

    entry: EntryPoint
    mode: str

    @property
    def name(self) -> str:
        return f"{self.entry.name}-{self.mode}"

    @property
    def writes_its_own_rules(self) -> bool:
        """Whether this cell's run authors `rules.yml`.

        Only `bootstrap_project` writes rules, so only the modes that bootstrap
        can contradict a rule of their own. The list is the sibling module's, and
        it checks itself against the files each mode leaves.
        """
        return self.mode in THE_MODES_THAT_BOOTSTRAP


#: The table: every mode every branch offers.
THE_TABLE = tuple(Cell(entry, mode) for entry in THE_ENTRY_POINTS for mode in entry.modes)


def answering_cell(cell: Cell, *, reinit: bool) -> Any:
    from contextlib import nullcontext
    from unittest.mock import patch

    prompts = cell.entry.prompts(cell.mode, reinit=reinit)
    if not prompts:
        return nullcontext()

    class _Answers:
        def __enter__(self) -> None:
            self._prompt = patch("rich.prompt.Prompt.ask", side_effect=list(prompts))
            # Accepted rather than declined: `--yes` has no such prompt and always
            # generates, so a declining wizard would be compared against a run
            # that did strictly more work (`.18`).
            self._confirm = patch("rich.prompt.Confirm.ask", return_value=True)
            self._prompt.start()
            self._confirm.start()

        def __exit__(self, *exc: object) -> None:
            self._confirm.stop()
            self._prompt.stop()

    return _Answers()
