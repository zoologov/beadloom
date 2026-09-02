"""Every answer to the wizard's graph review that leaves a graph file is judged.

BDL-067 `.21`, major 2 of the review of `.20`, and the sixth instance of
BDL-UX #192 — this one on the branch a human adopter meets first.

`interactive_init` writes `services.yml` and `rules.yml` BEFORE it asks "Proceed
with this graph?". So `cancel` never meant "nothing was written": it meant "the
graph is on disk and this command will not tell you whether it passes the rules
it wrote beside it". Measured by the review on a tree carrying an adopter's own
error-severity rule the bootstrap graph fails: the wizard answering
overwrite/bootstrap/CANCEL exited 0, and `beadloom lint --strict` on the same
tree exited 1. Answering `yes` on that same tree exited 1 with the full report.

WHY THE OTHER INSTRUMENTS DID NOT SEE IT, which is the finding rather than a
detail. `tests/test_init_branches_that_reach_the_bootstrap.py` reads `init`'s
source and walks what runs after each writing call, stopping at `Return` and
`Raise`; the cancelled path left through `sys.exit(0)`, which is neither, so the
walk stepped over it and found the verdict below. The identical defect read
guarded when the terminator was `sys.exit` and unguarded when it was `return`.
That module now knows about `sys.exit`, and `init` no longer contains one.

The axis this module adds is behavioural and answers a question no syntax can:
the wizard's review answers are read off `init_flow`'s own `Prompt.ask` choices,
each is RUN, and each that leaves a file under `.beadloom/_graph/` must be
judged. A fourth answer joins the parametrisation on the day it is written,
whatever form its way out of the command takes.

The fixture is a project that is not us, carrying a rules file the adopter wrote
— so the red is the adopter's own rule and not one Beadloom authored, which is
the case the wizard was silent about.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from beadloom.onboarding.scanner import init_flow
from beadloom.services.cli import main
from beadloom.services.commands.setup import (
    WITHDRAWN_COMPLETION_CLAIM as THE_WITHDRAWAL,
)
from tests.adopter_project import typescript_project
from tests.test_init_verdict_over_its_own_rules import (
    A_RULES_FILE_THE_ADOPTER_WROTE,
    THE_ADOPTERS_RULE,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

#: The prompt whose answers this module enumerates, by the words it puts to the
#: adopter. Naming it is how the derivation stays about ONE prompt — the wizard
#: asks three — and a reword fails `test_the_review_prompt_is_still_asked`
#: rather than silently leaving the enumeration empty.
THE_REVIEW_QUESTION = "Proceed with this graph?"

#: The answer that deliberately takes no verdict, with the reason it is allowed
#: to and the sentence it owes the adopter instead. `edit` hands the graph over
#: to be edited by hand and tells the reader to run `beadloom reindex`
#: afterwards, so the tree is unfinished by agreement and nothing has re-indexed
#: since — judging it would report a state the adopter is in the middle of
#: leaving. `cancel` was never such a case: it makes no agreement and asks for
#: nothing.
THE_ANSWER_THAT_IS_NOT_JUDGED = "edit"
WHAT_THE_CARVE_OUT_OWES_THE_ADOPTER = "beadloom reindex"

#: What the wizard must not do over files it has already written: end without
#: naming them. The three answers say different things; all three have written
#: the graph into this directory by the time they say it.
WHERE_THE_FILES_ARE = ".beadloom/_graph"
# The tail of the path the `edit` answer names. It is asserted CONTIGUOUSLY:
# rich hard-wraps at the console width, and a path split across two lines is a
# path the adopter cannot copy out of the message that exists to name it.
THE_FILE_THE_EDIT_ANSWER_NAMES = ".beadloom/_graph/services.yml"


def _the_review_answers() -> tuple[str, ...]:
    """The choices `init_flow` offers at the graph review, read off its source.

    Not written down here, for the reason `THE_MODES` is read off the flag's own
    `click.Choice`: an answer added to the prompt and not to a tuple in a test
    module is an answer with no case, and a case that is not written is a case
    that does not fail.
    """
    source = Path(inspect.getfile(init_flow)).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        first = node.args[0] if node.args else None
        if not (isinstance(first, ast.Constant) and first.value == THE_REVIEW_QUESTION):
            continue
        choices = next(kw for kw in node.keywords if kw.arg == "choices")
        if not isinstance(choices.value, ast.List):
            return ()
        return tuple(
            element.value
            for element in choices.value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        )
    return ()


#: Every answer the wizard accepts at the graph review, derived once at import.
THE_REVIEW_ANSWERS = _the_review_answers()


def _a_tree_the_adopters_rule_fails(tmp_path: Path) -> Path:
    """A project that is not us, with a rules file the adopter wrote already on it.

    Nothing is patched: the real `bootstrap_project` runs and writes the real
    graph, and `generate_rules` leaves the existing `rules.yml` alone — so the
    rule that fails is the adopter's, which is what the wizard said nothing about.
    """
    project = typescript_project(tmp_path).root
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "rules.yml").write_text(A_RULES_FILE_THE_ADOPTER_WROTE, encoding="utf-8")
    return project


def _wizard(project_root: Path, answer: str, *, re_initialising: bool) -> Any:
    """Run `init` as the default wizard, answering the review with *answer*.

    `overwrite` is the answer to the re-init prompt, which is only asked when
    `.beadloom/` is already there — which is what carrying an adopter's own rules
    file means. Overwrite is the answer that KEEPS that file: `--force` deletes
    the directory, which would delete the rule the case is about.
    """
    answers = (["overwrite"] if re_initialising else []) + ["bootstrap", answer]
    with (
        patch("rich.prompt.Prompt.ask", side_effect=answers),
        # Declining the doc-skeleton prompt keeps the case about the verdict.
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        return CliRunner().invoke(main, ["init", "--project", str(project_root)])


def _wizard_cancelling_the_re_init(project_root: Path) -> Any:
    """Answer the FIRST prompt with `cancel` — the run that writes nothing."""
    with patch("rich.prompt.Prompt.ask", side_effect=["cancel"]):
        return CliRunner().invoke(main, ["init", "--project", str(project_root)])


def _graph_files(project_root: Path) -> set[str]:
    graph_dir = project_root / ".beadloom" / "_graph"
    return {path.name for path in graph_dir.glob("*.yml")} if graph_dir.is_dir() else set()


#: How many lines of an answer's own closing message are read. The wizard ends
#: each answer with two or three lines; five is enough to hold the longest of
#: them and short enough that a mention further up — the re-init prompt names
#: `.beadloom/` too — cannot satisfy the case by accident.
THE_CLOSING_MESSAGE = 5


@pytest.fixture
def answered(tmp_path: Path) -> Iterator[Any]:
    """A factory: run the wizard over a rule the adopter wrote, on a fresh tree."""

    def run(answer: str) -> tuple[Any, set[str]]:
        project = _a_tree_the_adopters_rule_fails(tmp_path / answer)
        result = _wizard(project, answer, re_initialising=True)
        return result, _graph_files(project)

    yield run


@pytest.fixture
def answered_on_a_green_tree(tmp_path: Path) -> Iterator[Any]:
    """The same, over a project whose only rules are the ones this run writes.

    Every answer ends normally here, so what each one says LAST is its own
    closing message rather than a failure report the verdict printed after it.
    """

    def run(answer: str) -> tuple[Any, str]:
        project = typescript_project(tmp_path / answer).root
        result = _wizard(project, answer, re_initialising=False)
        lines = [line for line in result.output.splitlines() if line.strip()]
        return result, "\n".join(lines[-THE_CLOSING_MESSAGE:])

    yield run


class TestTheEnumerationItself:
    """The instrument, before anything is trusted to it."""

    def test_the_review_prompt_is_still_asked(self) -> None:
        """An empty derivation would make every case below vacuous."""
        assert THE_REVIEW_ANSWERS, (
            f"no `Prompt.ask` in {init_flow.__name__} asks "
            f"{THE_REVIEW_QUESTION!r}, so the parametrisation below is empty and "
            "asserts nothing about any answer"
        )

    def test_it_finds_the_three_answers_the_wizard_offers(self) -> None:
        """Derived, and stated so a fourth answer is visible in the diff."""
        assert set(THE_REVIEW_ANSWERS) == {"yes", "edit", "cancel"}

    def test_the_declared_carve_out_is_an_answer_the_wizard_has(self) -> None:
        """A carve-out for an answer nobody can give excuses nothing and hides that."""
        assert THE_ANSWER_THAT_IS_NOT_JUDGED in THE_REVIEW_ANSWERS


class TestEveryAnswerThatLeavesAGraphFileIsJudged:
    """The claim, over the answers rather than over the one that was reported."""

    @pytest.mark.parametrize("answer", THE_REVIEW_ANSWERS)
    def test_the_answer_leaves_the_graph_on_disk(
        self, answer: str, answered: Any
    ) -> None:
        """The premise the case below rests on, measured rather than assumed.

        `bootstrap_project` has written `services.yml` and left the adopter's
        `rules.yml` in place before the review prompt is put, so no answer to it
        can mean "nothing was written". An answer that genuinely wrote nothing
        would be owed no verdict, and this is where that would show.
        """
        _, files = answered(answer)

        assert "services.yml" in files

    @pytest.mark.parametrize(
        "answer", [a for a in THE_REVIEW_ANSWERS if a != THE_ANSWER_THAT_IS_NOT_JUDGED]
    )
    def test_the_answer_takes_the_verdict_on_what_it_left(
        self, answer: str, answered: Any
    ) -> None:
        """rc 1 and the adopter's own rule named, whatever the answer was.

        This is the assertion the `cancel` answer failed: rc 0, no report, and a
        tree the adopter's next `beadloom ci` calls red.
        """
        result, _ = answered(answer)

        assert result.exit_code == 1, result.output
        assert THE_ADOPTERS_RULE in result.output
        assert THE_WITHDRAWAL in result.output

    def test_the_declared_carve_out_hands_the_work_back_instead(
        self, answered: Any
    ) -> None:
        """A skip that says nothing is a silent skip under a better name."""
        result, _ = answered(THE_ANSWER_THAT_IS_NOT_JUDGED)

        assert result.exit_code == 0, result.output
        assert WHAT_THE_CARVE_OUT_OWES_THE_ADOPTER in result.output

    @pytest.mark.parametrize("answer", THE_REVIEW_ANSWERS)
    def test_the_answer_names_the_files_it_left_in_what_it_says_last(
        self, answer: str, answered_on_a_green_tree: Any
    ) -> None:
        """A run that wrote files and names none of them is the false message again.

        "Cancelled." over a graph and a rules file the command had already
        written is the fourth false user-facing statement this epic has filed,
        and the one an adopter meets by answering the prompt the way the prompt
        invites. The claim is about the CLOSING message rather than about the
        output: `.beadloom/` appears further up on any re-init, so a case over
        the whole transcript would have passed over "Cancelled." saying nothing.
        """
        result, closing = answered_on_a_green_tree(answer)

        assert result.exit_code == 0, result.output
        assert WHERE_THE_FILES_ARE in closing, closing

    def test_the_path_it_names_survives_the_render_whole(
        self, answered_on_a_green_tree: Any
    ) -> None:
        """A path the render broke in half is a path nobody can copy.

        `rich` hard-wraps at the console width — 80 when the output is not a
        terminal — and inserts a real newline wherever the line runs out, token
        or no token. Whether it lands inside `.beadloom/_graph/services.yml`
        depends on how long the project's own path happens to be, so this was
        green on macOS for nine consecutive runs and red on all six CI legs,
        whose temporary prefix is 68 characters and leaves exactly 12 before the
        break. The claim here is about what the message HANDS the adopter, which
        is why it is asserted contiguously rather than by any substring that a
        wrap could leave intact. `edit` is reused rather than given a second name:
        it is the same answer, and two names for one fact are two things that can
        disagree.
        """
        result, _ = answered_on_a_green_tree(THE_ANSWER_THAT_IS_NOT_JUDGED)

        assert result.exit_code == 0, result.output
        assert THE_FILE_THE_EDIT_ANSWER_NAMES in result.output, result.output


class TestARunThatWroteNothingTakesNoVerdict:
    """The other half of the same rule, and the one that keeps it honest.

    `interactive_init` answers `cancelled` to two different questions. The graph
    review is asked after the graph is written; the re-init prompt is asked
    before anything is, and answering it `cancel` leaves the adopter's tree
    exactly as it was. Judging that run would report an existing tree's failures
    as the outcome of a command that touched nothing, under a withdrawal line
    ("The scaffold above was written") that would be false.

    So the verdict asks the tree, not the branch: it is taken when this run wrote
    a file under `.beadloom/_graph/` and skipped when it did not. That is one
    fact read in one place, which is why removing the `cancelled` carve-out from
    `init` does not put this case at risk — and this class is what says so.
    """

    def test_cancelling_the_re_init_prompt_writes_nothing(self, tmp_path: Path) -> None:
        project = _a_tree_the_adopters_rule_fails(tmp_path / "untouched")
        before = (project / ".beadloom" / "_graph" / "rules.yml").read_text(encoding="utf-8")

        _wizard_cancelling_the_re_init(project)

        assert _graph_files(project) == {"rules.yml"}
        assert (project / ".beadloom" / "_graph" / "rules.yml").read_text(
            encoding="utf-8"
        ) == before

    def test_cancelling_the_re_init_prompt_takes_no_verdict(self, tmp_path: Path) -> None:
        """rc 0 and no report over a tree whose own rules a lint would fail."""
        project = _a_tree_the_adopters_rule_fails(tmp_path / "unjudged")

        result = _wizard_cancelling_the_re_init(project)

        assert result.exit_code == 0, result.output
        assert THE_WITHDRAWAL not in result.output
        assert THE_ADOPTERS_RULE not in result.output
