"""`init` must not report success over a graph that fails the rules it wrote.

BDL-067 `.2`, the half of BDL-UX #192 that prevents the CLASS rather than the
instance. `.1` closed the instance: `bootstrap_project` now holds a post-condition
that every `domain` node it writes carries a `part_of` edge, so a virgin bootstrap
no longer contradicts the `domain-needs-parent` rule it writes one step later.

That is exactly why the divergence here is **constructed rather than awaited**. A
test that waited for the bootstrap to forget an edge again would pass today for the
reason `.1` landed and would say nothing about what `init` does when a *future*
divergence appears. So `_a_bootstrap_that_forgets_the_edge` wraps the real
`bootstrap_project`, lets it write the real graph and the real rules, and then
strips the `part_of` edges back out of `services.yml` — re-creating the exact shape
#192 was reported against (`Graph: 2 nodes, 0 edges`, then `domain-needs-parent` at
error severity) on top of a fixed bootstrap.

The cases are parametrised over `THE_BRANCHES` — the branches of `init` that write
a bootstrap graph — and not over the bindings they reach `bootstrap_project`
through. The distinction is the reason BDL-067 `.6` exists: this module used to be
parametrised over two bindings under a comment calling them "the two ways `init`
reaches the bootstrap", the default wizard shares the `--yes` binding, and so the
one branch a human adopter meets first went four green waves with no verdict at all
(reproduced by the review of `.4`: wizard rc 0, `lint --strict` rc 1, `ci` rc 1).

The fixture is a project that is not us (`orders-web`, a flat `src/index.ts`), so a
verdict that worked by recognising Beadloom's own tree would fail these.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.services.cli import main
from beadloom.services.commands import setup as init_command

#: The line the wizard prints to withdraw its completion claim, imported rather
#: than spelled again here: a reword should not leave this module asserting the
#: presence and the position of a string nobody prints.
from beadloom.services.commands.setup import (
    WITHDRAWN_COMPLETION_CLAIM as THE_WITHDRAWAL,
)
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The rule `generate_rules` writes for every graph that holds a domain, and the
#: rule BDL-UX #192's reporter read out of `lint --strict` after a green `init`.
THE_RULE = "domain-needs-parent"

#: The two BINDINGS of `bootstrap_project`, which are not the branches and must
#: not be counted as though they were. `init --yes` and the default wizard both
#: run inside `init_flow`, which binds the function at import time, so ONE patch
#: sabotages both; `init --bootstrap` imports it from the package inside the
#: command body and has to be sabotaged separately.
INIT_FLOW_BINDING = "beadloom.onboarding.scanner.init_flow.bootstrap_project"
PACKAGE_BINDING = "beadloom.onboarding.bootstrap_project"


@dataclass(frozen=True)
class InitBranch:
    """One branch of `init` that writes a bootstrap graph, and how to reach it.

    A branch is a path through the `init` command body; a binding is a name
    `bootstrap_project` is reachable under. Two branches can share one binding,
    and two of these three do — which is why this type carries both and why the
    parametrisation is over branches.
    """

    #: How the branch is spelled on the command line, for the test id.
    name: str
    #: The arguments that select it. Empty for the default wizard.
    argv: tuple[str, ...]
    #: The name of `bootstrap_project` this branch calls.
    binding: str
    #: The `if` conditions in `init`'s body the branch sits under, as the source
    #: spells them, outermost first. Empty for the fallthrough wizard. This is
    #: what `tests/test_init_branches_that_reach_the_bootstrap.py` matches the
    #: tuple below against the command's own source, so a fourth branch fails a
    #: test instead of merely going untested (BDL-067 `.7`).
    guard: tuple[str, ...]
    #: The wizard's answers, in order: init mode, then the graph review.
    prompts: tuple[str, ...] = field(default_factory=tuple)


#: Every branch of `init` that reaches `bootstrap_project`. Three branches, two
#: bindings. A fourth branch belongs in this tuple on the day it is written.
THE_BRANCHES = (
    InitBranch(
        "--yes", ("--yes", "--mode", "bootstrap"), INIT_FLOW_BINDING, ("non_interactive",)
    ),
    InitBranch("--bootstrap", ("--bootstrap",), PACKAGE_BINDING, ("bootstrap",)),
    InitBranch("wizard", (), INIT_FLOW_BINDING, (), prompts=("bootstrap", "yes")),
)

#: The same branch as `wizard`, answering the graph review with `edit` — the one
#: bootstrap path `init` deliberately takes no verdict on. It is not in
#: `THE_BRANCHES` because it is not a fourth branch: it is the third one, asked a
#: different question.
THE_WIZARD_THAT_EDITS = InitBranch(
    "wizard-edit", (), INIT_FLOW_BINDING, (), prompts=("bootstrap", "edit")
)

BRANCH_IDS = [branch.name for branch in THE_BRANCHES]


def _the_modes_the_flag_offers() -> tuple[str, ...]:
    """The `--mode` values, read off the command's own `click.Choice`.

    Not written out, for the reason `THE_BRANCHES` is checked against `init`'s
    source in `tests/test_init_branches_that_reach_the_bootstrap.py`: a mode
    added to the flag and not to a tuple here would be a mode with no case, and
    a case that is not written is a case that does not fail.

    It lives in this module rather than in `tests/test_init_agrees_across_its_
    modes.py`, which is where BDL-067 `.15` wrote it, because `.17` needs the
    same axis here and that module already imports from this one. One derivation
    of one fact, in the module the other imports.
    """
    option = next(p for p in init_command.init.params if p.name == "init_mode")
    choices = getattr(option.type, "choices", ())
    return tuple(str(choice) for choice in choices)


#: Every mode `init` accepts, derived once at import.
THE_MODES = _the_modes_the_flag_offers()

#: A `rules.yml` the loader refuses: no `version` key. This is what a hand edit
#: leaves behind, and `bootstrap_project` never rewrites a rules file that is
#: already there, so `init` can meet it.
UNLOADABLE_RULES = "rules:\n  - name: hand-edited\n    require:\n      match: {}\n"

#: The part of the loader's complaint an adopter needs to see.
THE_PARSE_ERROR = "missing required 'version' field"

#: A `rules.yml` the ADOPTER wrote: valid, loadable, and failed by any graph the
#: bootstrap writes. `generate_rules` dropped `service-needs-parent` for exactly
#: the reason it fails here — the root service node has no parent by definition
#: — so a project carrying a hand-written rule of that name is a project whose
#: red verdict is its own. This is the review's reproduction of BDL-067 `.9`,
#: moved into the suite.
THE_ADOPTERS_RULE = "service-needs-parent"
A_RULES_FILE_THE_ADOPTER_WROTE = """\
version: 1
rules:
  - name: service-needs-parent
    description: Every service must have a part_of edge
    require:
      for:
        kind: service
      has_edge_to: {}
      edge_kind: part_of
"""

#: The sentence that is true only when the bootstrap authored `rules.yml`, and
#: the request that follows it. Both are asserted present in one class and absent
#: in another, so the fix has to DISTINGUISH the two cases rather than delete the
#: sentence.
THE_BLAME = "defect in Beadloom's bootstrap"
THE_BUG_REPORT_REQUEST = "please report it"

#: What the adopter is told instead: the file was already there, so the rule is
#: theirs. The path is named because it is the file they have to open.
THE_RULES_PATH = ".beadloom/_graph/rules.yml"
THE_FILE_WAS_ALREADY_THERE = "did not write"

#: The wizard's success claim, printed by `interactive_init` before `init` takes
#: the verdict, and therefore printed even when the verdict is red.
THE_COMPLETION_CLAIM = "Initialization complete!"

#: The first word of the failure report, used to place the withdrawal line.
THE_FAILURE_REPORT = "Error:"

#: The branches that can meet a `rules.yml` this command did not write. `--yes`
#: is not one of them and cannot be made into one: `non_interactive_init` returns
#: `skipped` when `.beadloom/` is already there, and under `--force` it deletes
#: the whole directory, so the rules file that branch meets is always the one it
#: just wrote. The wizard answers the re-init prompt with `overwrite`, which
#: keeps the directory and the rules file inside it. Both halves of that
#: exclusion are tested in `TestWhyTheYesBranchCannotMeetAnAdoptersRulesFile`,
#: so this tuple is short for a checked reason rather than for a stated one.
THE_BRANCHES_OVER_AN_ADOPTERS_RULES_FILE = (
    InitBranch("--bootstrap", ("--bootstrap",), PACKAGE_BINDING, ("bootstrap",)),
    InitBranch(
        "wizard", (), INIT_FLOW_BINDING, (), prompts=("overwrite", "bootstrap", "yes")
    ),
)

ADOPTER_BRANCH_IDS = [b.name for b in THE_BRANCHES_OVER_AN_ADOPTERS_RULES_FILE]


def _a_rules_file_the_adopter_wrote(project_root: Path) -> None:
    """Put a valid rules file in place before `init` runs.

    That is the whole fixture: nothing is patched, the real `bootstrap_project`
    and the real linter run. `bootstrap_project` writes `rules.yml` only when the
    file is not already there, so the rule that fails is one this command did not
    write — which is the case the message got wrong.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "rules.yml").write_text(
        A_RULES_FILE_THE_ADOPTER_WROTE, encoding="utf-8"
    )


def _strip_part_of_edges(project_root: Path) -> None:
    """Remove every `part_of` edge from the graph the bootstrap just wrote."""
    services = project_root / ".beadloom" / "_graph" / "services.yml"
    data = yaml.safe_load(services.read_text(encoding="utf-8"))
    kept = [e for e in data.get("edges", []) if e.get("kind") != "part_of"]
    if kept:
        data["edges"] = kept
    else:
        # `bootstrap_project` writes no `edges:` key at all when there are none,
        # so the sabotaged file keeps the shape #192 was reported against.
        data.pop("edges", None)
    services.write_text(
        yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _a_bootstrap_that_forgets_the_edge(monkeypatch: pytest.MonkeyPatch, binding: str) -> None:
    """Patch one binding of `bootstrap_project` into a self-contradicting one.

    The rules half is untouched: the real `generate_rules` still writes
    `domain-needs-parent`. Only the graph half loses the edge that rule requires.
    """
    real = bootstrap_project

    def forgetful(project_root: Path, **kwargs: Any) -> dict[str, Any]:
        result = real(project_root, **kwargs)
        _strip_part_of_edges(project_root)
        result["edges"] = [e for e in result["edges"] if e["kind"] != "part_of"]
        result["edges_generated"] = len(result["edges"])
        return result

    monkeypatch.setattr(binding, forgetful)


def _a_bootstrap_whose_rules_file_will_not_load(
    monkeypatch: pytest.MonkeyPatch, binding: str
) -> None:
    """Patch one binding so the rules file on disk is one the loader rejects.

    The graph is untouched and would pass; what fails is reading the rules at
    all. That is the case the Gate reports through its `LintError` branch, where
    the finding's `rule` is the step's own name and the reason is in `why`.
    """
    real = bootstrap_project

    def with_broken_rules(project_root: Path, **kwargs: Any) -> dict[str, Any]:
        result = real(project_root, **kwargs)
        rules = project_root / ".beadloom" / "_graph" / "rules.yml"
        rules.write_text(UNLOADABLE_RULES, encoding="utf-8")
        return result

    monkeypatch.setattr(binding, with_broken_rules)


@contextmanager
def _answering(branch: InitBranch) -> Iterator[None]:
    """Answer the wizard's prompts; a no-op for the branches that ask nothing."""
    if not branch.prompts:
        yield
        return
    with (
        patch("rich.prompt.Prompt.ask", side_effect=list(branch.prompts)),
        # Declining the doc-skeleton prompt keeps the case about the verdict.
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        yield


def _init(project_root: Path, branch: InitBranch) -> Any:
    with _answering(branch):
        return CliRunner().invoke(
            main, ["init", *branch.argv, "--project", str(project_root)]
        )


def _the_branch_reported(result: Any) -> Any:
    """Fail unless the branch reported at all, then hand the result back.

    Three of the cases below are negative claims — what the output does NOT say —
    and against the pre-`.6` tree the wizard branch printed nothing whatsoever.
    A negative claim about an empty string holds for free, so those three passed
    over the unfixed wizard while saying nothing about it (named by `.6`'s own
    completion note, closed here as BDL-067 `.7`). A non-zero rc is the cheapest
    proof that the reporter ran, and it is what turns the assertion that follows
    into a claim.
    """
    assert result.exit_code != 0, (
        "the branch exited 0, so it reported nothing and the assertion below "
        f"would hold vacuously. Output: {result.output!r}"
    )
    return result


def _lint_strict(project_root: Path) -> int:
    return CliRunner().invoke(
        main, ["lint", "--strict", "--project", str(project_root)]
    ).exit_code


@pytest.mark.parametrize("branch", THE_BRANCHES, ids=BRANCH_IDS)
class TestInitOverAGraphThatFailsItsOwnRules:
    """The graph on disk contradicts the rules on disk, in every init branch."""

    def test_the_command_does_not_exit_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, branch.binding)

        result = _init(project.root, branch)

        assert result.exit_code != 0, result.output

    def test_it_names_the_rule_the_gate_will_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """Not "something is wrong" — the string the adopter will read again."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, branch.binding)

        result = _init(project.root, branch)

        assert THE_RULE in result.output

    def test_the_verdict_agrees_with_lint_strict_on_the_same_tree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """The claim is agreement with the Gate, not merely a non-zero number."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, branch.binding)

        init_rc = _init(project.root, branch).exit_code

        assert (init_rc != 0) == (_lint_strict(project.root) != 0)

    def test_the_graph_is_still_on_disk_to_be_repaired(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """A non-zero rc reports the defect; it does not withdraw the scaffold."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, branch.binding)

        _the_branch_reported(_init(project.root, branch))

        assert (project.root / ".beadloom" / "_graph" / "services.yml").is_file()
        assert (project.root / ".beadloom" / "_graph" / "rules.yml").is_file()


@pytest.mark.parametrize("branch", THE_BRANCHES, ids=BRANCH_IDS)
class TestInitOverAGraphThatPassesItsOwnRules:
    """The everyday path stays green — the check is a verdict, not a tax."""

    def test_an_unsabotaged_init_still_exits_zero(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")

        result = _init(project.root, branch)

        assert result.exit_code == 0, result.output

    def test_it_does_not_name_a_rule_nothing_violated(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")

        result = _init(project.root, branch)

        assert THE_RULE not in result.output

    def test_lint_strict_agrees_that_the_tree_is_clean(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")

        init_rc = _init(project.root, branch).exit_code

        assert (init_rc != 0) == (_lint_strict(project.root) != 0)


@pytest.mark.parametrize("branch", THE_BRANCHES, ids=BRANCH_IDS)
class TestInitOverARulesFileThatWillNotLoad:
    """The rules did not load, so the verdict has no rule name to give.

    BDL-067 `.6`, the review's minor 4. The Gate reports an unloadable
    `rules.yml` as a finding whose `rule` is the literal `lint` — the step's own
    name — and puts the loader's complaint in `why`. `init` printed the name and
    dropped the text, so an adopter whose hand-edited rules file will not parse
    was told that a rule called `lint` had failed.
    """

    def test_it_says_what_is_wrong_with_the_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_whose_rules_file_will_not_load(monkeypatch, branch.binding)

        result = _init(project.root, branch)

        assert THE_PARSE_ERROR in result.output

    def test_it_does_not_offer_lint_as_the_name_of_a_rule(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """`  lint` in the rule list is a name no rules file contains."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_whose_rules_file_will_not_load(monkeypatch, branch.binding)

        result = _the_branch_reported(_init(project.root, branch))

        assert "  lint" not in result.output.splitlines()

    def test_it_does_not_blame_the_bootstrap_for_a_hand_edited_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """The graph the bootstrap wrote is not what failed here."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_whose_rules_file_will_not_load(monkeypatch, branch.binding)

        result = _the_branch_reported(_init(project.root, branch))

        assert "defect in Beadloom's bootstrap" not in result.output

    def test_the_command_does_not_exit_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_whose_rules_file_will_not_load(monkeypatch, branch.binding)

        result = _init(project.root, branch)

        assert result.exit_code != 0, result.output


class TestTheOneBootstrapPathThatTakesNoVerdict:
    """`edit` is a deliberate carve-out, and a deliberate thing is testable.

    Answering the wizard's graph review with `edit` hands `services.yml` to the
    user, tells them to run `beadloom reindex` and returns before anything has
    re-indexed. Judging the tree there would report a state the user is in the
    middle of leaving, so `init` skips the verdict on exactly that answer and on
    nothing else (BDL-067 `.6`). Written down here so the carve-out is a decision
    with a test rather than a condition someone can delete or widen unnoticed.

    Declared, because it matters more than it costs: this case does NOT fail
    against the pre-`.6` tree and cannot be made to. There the wizard took no
    verdict on any answer, so its behaviour on `edit` was identical and there is
    no edit to the old source that this case distinguishes. It guards the future,
    not the fix — and its companion, `test_the_command_does_not_exit_zero`
    parametrised at `wizard`, is what proves the other answers are judged.
    """

    def test_the_edit_answer_exits_zero_over_a_graph_that_fails_its_rules(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, THE_WIZARD_THAT_EDITS.binding)

        result = _init(project.root, THE_WIZARD_THAT_EDITS)

        # Anti-vacuity: an rc of 0 from a wizard that never reached the review
        # prompt would prove nothing about the carve-out.
        assert "beadloom reindex" in result.output, result.output
        assert result.exit_code == 0, result.output

    def test_the_same_answers_but_yes_are_judged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The carve-out is the answer, not the wizard: `yes` still gets a verdict."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, THE_WIZARD_THAT_EDITS.binding)

        result = _init(project.root, THE_BRANCHES[-1])

        assert result.exit_code != 0, result.output
        assert THE_RULE in result.output


@pytest.mark.parametrize(
    "branch", THE_BRANCHES_OVER_AN_ADOPTERS_RULES_FILE, ids=ADOPTER_BRANCH_IDS
)
class TestInitOverARulesFileTheAdopterWrote:
    """The rules the graph fails are the adopter's, so Beadloom is not to blame.

    BDL-067 `.9`, the review's major 1 on `.8`. `bootstrap_project` writes
    `rules.yml` only when the file is not already there, so on a re-init — or on
    a project whose rules came from an earlier Beadloom or from a hand edit — the
    failing rule is the adopter's own. `init` told them it was "a defect in
    Beadloom's bootstrap" and asked them to report it. `.6` already held the fact
    this rests on and wrote it down for the unloadable-rules branch
    (`_report_rules_that_would_not_load`) without carrying it across to the
    branch it invalidates.

    Nothing here is patched. The graph the bootstrap writes is correct and would
    pass its own rules; what fails is a rule the command did not write.
    """

    def test_the_command_still_does_not_exit_zero(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        """The verdict is about agreement with the Gate, not about authorship."""
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)

        result = _init(project.root, branch)

        assert result.exit_code != 0, result.output

    def test_it_names_the_rule_the_adopter_wrote(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)

        result = _init(project.root, branch)

        assert THE_ADOPTERS_RULE in result.output, result.output

    def test_it_does_not_blame_the_bootstrap(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)

        result = _the_branch_reported(_init(project.root, branch))

        assert THE_BLAME not in result.output, result.output

    def test_it_does_not_ask_for_a_bug_report(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        """The cost the finding names: adopters filing our tracker with their own rules."""
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)

        result = _the_branch_reported(_init(project.root, branch))

        assert THE_BUG_REPORT_REQUEST not in result.output, result.output

    def test_it_says_the_rules_file_was_already_there(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        """Dropping the blame is half an answer; the adopter needs the reason."""
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)

        result = _the_branch_reported(_init(project.root, branch))

        assert THE_FILE_WAS_ALREADY_THERE in result.output, result.output
        assert THE_RULES_PATH in result.output, result.output

    def test_the_graph_is_still_on_disk_to_be_repaired(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)

        _the_branch_reported(_init(project.root, branch))

        assert (project.root / ".beadloom" / "_graph" / "services.yml").is_file()


@pytest.mark.parametrize("branch", THE_BRANCHES, ids=BRANCH_IDS)
class TestInitOverRulesTheBootstrapItselfWrote:
    """The other side of the distinction: when it IS ours, it still says so.

    Without this the fix could be "delete the sentence", which loses the one
    thing the sentence is for. Here `bootstrap_project` runs on a virgin project
    and writes `rules.yml` itself, so `rules_generated` is non-zero and the graph
    it wrote alongside those rules is the thing at fault.
    """

    def test_it_does_blame_the_bootstrap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, branch.binding)

        result = _the_branch_reported(_init(project.root, branch))

        assert THE_BLAME in result.output, result.output
        assert THE_BUG_REPORT_REQUEST in result.output, result.output


@pytest.mark.parametrize("branch", THE_BRANCHES, ids=BRANCH_IDS)
class TestEveryBranchWithdrawsTheClaimItHasAlreadyMade:
    """Each branch announces a scaffold above the verdict, so each withdraws it.

    BDL-067 `.17`, the review of `.16`'s major 3. Until `.17` the withdrawal was
    a `claim_to_withdraw` argument and one of the call sites passed it, and the
    constant's own docstring said the `--bootstrap` branch "takes its verdict
    first and never makes the claim". It makes it: four check marks, then the
    error, no withdrawal — measured by the review over an adopter's own
    `rules.yml`. `--yes` makes it too, `Initialized beadloom (mode: ...)` and its
    summary. The false sentence is why the omission read as a decision for two
    waves.

    So this class is parametrised over `THE_BRANCHES` rather than written about
    the wizard, and the line is printed by `_verdict_on_the_generated_graph`
    itself rather than passed in — a caller that forgets it is not a shape the
    code has.

    The claim each branch makes is spelled differently in each branch, so it is
    not written out per branch here: the anti-vacuity case asserts only that the
    branch printed SOMETHING before the withdrawal, which is the fact the
    withdrawal depends on and the one a fourth branch would also have to fail.
    `THE_COMPLETION_CLAIM` stays as the wizard's own case, because that exact
    string is what BDL-067 `.9` was reported against.
    """

    def _over_a_failing_graph(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> Any:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, branch.binding)
        return _the_branch_reported(_init(project.root, branch))

    def test_the_branch_claims_something_before_the_withdrawal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """Anti-vacuity: a branch that announced nothing needs no withdrawal."""
        result = self._over_a_failing_graph(tmp_path, monkeypatch, branch)

        withdrawn = result.output.find(THE_WITHDRAWAL)
        assert withdrawn != -1, result.output
        announced = [
            line for line in result.output[:withdrawn].splitlines() if line.strip()
        ]
        assert announced, (
            f"the {branch.name} branch printed nothing before the withdrawal, so "
            "there is no claim for it to withdraw and this case asserts nothing"
        )

    def test_the_claim_is_withdrawn_before_the_failure_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        result = self._over_a_failing_graph(tmp_path, monkeypatch, branch)

        withdrawn = result.output.find(THE_WITHDRAWAL)
        reported = result.output.index(THE_FAILURE_REPORT)

        assert withdrawn != -1, result.output
        assert withdrawn < reported, result.output

    def test_the_claim_is_withdrawn_over_a_rules_file_that_will_not_load_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """The other shape of red, and the same withdrawal, on every branch.

        `_verdict_on_the_generated_graph` prints the withdrawal before it chooses
        between the two report shapes, so an unloadable `rules.yml` gets it as
        well. Only the evaluated-rules shape was covered by BDL-067 `.9`: moving
        the withdrawal into the `else` would have left `init` announcing a
        scaffold and then reporting that the rules file could not be read, which
        is the same defect on the branch `.6` was written for.

        The last two assertions are BDL-067 `.12`, the review's major 1 on `.11`.
        Until then this test owned only the line's POSITION, and the wording it
        was pinning in place said the graph "does not pass the rules it is
        checked against" — on the one branch where no rule is evaluated at all
        and where the next two lines say so. They are stated over the line as the
        adopter reads it rather than over the imported constant, so that a second
        withdrawal string introduced later is judged too.
        """
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_whose_rules_file_will_not_load(monkeypatch, branch.binding)

        result = _the_branch_reported(_init(project.root, branch))

        # Anti-vacuity: with no parse error there is nothing to place the line
        # against, and the ordering below would be about lines that never came.
        assert THE_PARSE_ERROR in result.output, result.output
        withdrawn = result.output.find(THE_WITHDRAWAL)
        reported = result.output.index(THE_FAILURE_REPORT)

        assert withdrawn != -1, result.output
        assert withdrawn < reported, result.output

        the_line = result.output[withdrawn:].splitlines()[0]
        assert "rule" not in the_line.lower(), the_line
        assert not the_line.rstrip().endswith(":"), the_line

    def test_a_green_run_withdraws_nothing(
        self, tmp_path: Path, branch: InitBranch
    ) -> None:
        """The withdrawal is part of the failure report, not part of the tail."""
        project = typescript_project(tmp_path / "orders-web")

        result = _init(project.root, branch)

        assert result.exit_code == 0, result.output
        assert THE_WITHDRAWAL not in result.output, result.output


class TestTheWizardsOwnCompletionClaimIsTheOneItWithdraws:
    """The wizard's tail is the string BDL-067 `.9` was reported against.

    Kept as its own case after the class above widened to every branch: the
    generic claim there is "the branch printed something first", and this one
    names what the wizard printed, so a wizard that stopped saying
    `Initialization complete!` before a red verdict is still a change somebody
    has to notice.
    """

    def test_the_claim_it_withdraws_is_actually_made(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, INIT_FLOW_BINDING)

        result = _the_branch_reported(_init(project.root, THE_BRANCHES[-1]))

        claimed = result.output.index(THE_COMPLETION_CLAIM)
        withdrawn = result.output.find(THE_WITHDRAWAL)
        reported = result.output.index(THE_FAILURE_REPORT)

        assert withdrawn != -1, result.output
        assert claimed < withdrawn < reported, result.output


#: `--yes`, spelled with `--force`. Not a fourth branch and not in
#: `THE_BRANCHES`: it is the first one, given the flag that changes what it finds
#: on disk rather than which path it takes.
THE_YES_BRANCH_THAT_FORCES = InitBranch(
    "--yes --force",
    ("--yes", "--force", "--mode", "bootstrap"),
    INIT_FLOW_BINDING,
    ("non_interactive",),
)


class TestWhyTheYesBranchCannotMeetAnAdoptersRulesFile:
    """The exclusion above is a claim about `init`, so it is tested like one.

    `THE_BRANCHES_OVER_AN_ADOPTERS_RULES_FILE` holds two of the three branches,
    and the reason the third is absent lives in a comment. That is the shape of
    the mistake this whole epic came from: BDL-067 `.6` exists because a comment
    calling two bindings "the two ways `init` reaches the bootstrap" was believed
    for four waves while the branch a human adopter meets first went unjudged.
    `.7` answered it by checking the branch list against `init`'s own source.
    These two cases do the same for the exclusion — if either half of it stops
    holding, the next author is told to widen the parametrisation instead of
    inheriting a comment that is no longer true.

    Declared, because the bead asks for it: neither case fails against the
    pre-`.9` tree, and neither can be made to. `.9` changed what the verdict
    prints, and both cases are about a branch that reaches no verdict at all
    (`skipped` returns first) or that meets a rules file it wrote itself. They
    guard the exclusion, not the fix.
    """

    def test_yes_over_an_existing_beadloom_directory_takes_no_verdict(
        self, tmp_path: Path
    ) -> None:
        """Half one: it returns on `skipped`, before the verdict is taken."""
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)
        # Anti-vacuity: the tree this runs over is demonstrably red, so a green
        # `--yes` is the absence of a verdict rather than the absence of a fault.
        red = _the_branch_reported(
            _init(project.root, THE_BRANCHES_OVER_AN_ADOPTERS_RULES_FILE[0])
        )
        assert THE_ADOPTERS_RULE in red.output, red.output

        result = _init(project.root, THE_BRANCHES[0])

        assert result.exit_code == 0, result.output
        assert "already exists" in result.output, result.output
        assert THE_ADOPTERS_RULE not in result.output, result.output

    def test_yes_with_force_replaces_the_adopters_rules_file_with_its_own(
        self, tmp_path: Path
    ) -> None:
        """Half two: `--force` deletes `.beadloom/`, rules file included.

        So the rules this branch is judged against are always the ones it just
        wrote, which is why it belongs in `TestInitOverRulesTheBootstrapItselfWrote`
        and not in the adopter-authored cases.
        """
        project = typescript_project(tmp_path / "orders-web")
        _a_rules_file_the_adopter_wrote(project.root)
        rules = project.root / ".beadloom" / "_graph" / "rules.yml"
        assert THE_ADOPTERS_RULE in rules.read_text(encoding="utf-8")

        result = _init(project.root, THE_YES_BRANCH_THAT_FORCES)

        assert result.exit_code == 0, result.output
        assert THE_ADOPTERS_RULE not in rules.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# BDL-067 `.14` — the run that writes a SECOND graph file, and the words the
# report uses about it. The review of `.13`, minors 1, 2 and 3.
# ---------------------------------------------------------------------------

#: A document whose text matches none of `classify_doc`'s patterns, so it falls
#: through to the `other` branch and is written as a `domain` node.
AN_UNCLASSIFIABLE_DOCUMENT = "# Payments\n\nHow money moves through the shop.\n"

#: The graph file the import step writes, and the file the report used to point
#: away from: a node from `imported.yml` was reported against `services.yml`.
THE_IMPORT_FILE = ".beadloom/_graph/imported.yml"
THE_BOOTSTRAP_FILE = ".beadloom/_graph/services.yml"

#: The orphan the import sabotage adds. Added rather than carved out of what
#: `import_docs` writes, so the instrument says the same thing before and after
#: the post-condition landed.
THE_ADDED_ORPHAN = "ledger"


def _docs_the_classifier_cannot_place(project_root: Path) -> None:
    docs = project_root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "payments.md").write_text(AN_UNCLASSIFIABLE_DOCUMENT, encoding="utf-8")


def _an_import_that_adds_an_orphan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Append one parentless `domain` to `imported.yml` after the real import.

    `init` writes `domain-needs-parent` at error severity in the same run, so a
    verdict that reads everything `init` wrote must exit 1. The reindex used to
    sit inside the bootstrap block, ahead of the file this writes, so the verdict
    judged an index that predated it and reported clean.
    """
    from beadloom.onboarding.scanner.doc_classify import import_docs as real

    def adds_an_orphan(project_root: Path, docs_dir: Path) -> list[dict[str, str]]:
        results = real(project_root, docs_dir)
        imported = project_root / ".beadloom" / "_graph" / "imported.yml"
        data = yaml.safe_load(imported.read_text(encoding="utf-8")) if imported.exists() else {}
        data = data or {"nodes": []}
        data.setdefault("nodes", []).append(
            {"ref_id": THE_ADDED_ORPHAN, "kind": "domain", "summary": "No parent."}
        )
        imported.write_text(
            yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return results

    monkeypatch.setattr("beadloom.onboarding.scanner.init_flow.import_docs", adds_an_orphan)


def _the_nodes_the_index_holds(project_root: Path) -> set[str]:
    """The ref_ids in the SQLite index, which is what `lint_step` reads.

    Read off the index rather than off the YAML on disk: the two disagree
    exactly when a run wrote a graph file and did not re-index, which is the
    state a verdict must not be taken in.
    """
    import sqlite3

    with sqlite3.connect(project_root / ".beadloom" / "beadloom.db") as conn:
        return {row[0] for row in conn.execute("SELECT ref_id FROM nodes")}


def _init_over_code_and_docs(project_root: Path) -> Any:
    return CliRunner().invoke(
        main, ["init", "--yes", "--mode", "both", "--project", str(project_root)]
    )


class TestTheVerdictSeesEveryGraphFileTheCommandWrote:
    """`--mode both` writes two graph files, and both are judged.

    The defect this closes is not a missing check but a check pointed at a stale
    index: `lint_step` reads the index without re-indexing, and the reindex ran
    before the import step wrote its file. The wizard, which re-indexes after
    importing, exited 1 on the same project shape where `--yes` exited 0 — two
    halves of one command disagreeing, which is what `lint_step` was made public
    to prevent.
    """

    def test_a_graph_the_import_step_wrote_is_not_reported_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web").root
        _docs_the_classifier_cannot_place(project)
        _an_import_that_adds_an_orphan(monkeypatch)

        result = _init_over_code_and_docs(project)

        assert result.exit_code != 0, result.output
        assert THE_RULE in result.output, result.output

    def test_the_verdict_agrees_with_lint_strict_on_the_same_tree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The adopter's next command, which is where the disagreement showed."""
        project = typescript_project(tmp_path / "orders-web").root
        _docs_the_classifier_cannot_place(project)
        _an_import_that_adds_an_orphan(monkeypatch)

        verdict = _init_over_code_and_docs(project).exit_code

        assert verdict != 0
        assert _lint_strict(project) != 0

    def test_an_unsabotaged_run_over_code_and_docs_is_green_both_ways(
        self, tmp_path: Path
    ) -> None:
        """The reviewer's reproduction, end to end: rc 0 and then rc 0."""
        project = typescript_project(tmp_path / "orders-web").root
        _docs_the_classifier_cannot_place(project)

        result = _init_over_code_and_docs(project)

        assert result.exit_code == 0, result.output
        assert "Imported:" in result.output, result.output
        assert _lint_strict(project) == 0


class TestEveryRunThatWroteAGraphFileIsJudged:
    """A run is judged because it WROTE a graph file, not because it bootstrapped.

    BDL-067 `.17`, the review of `.16`'s major 2. The guard used to be
    `if "bootstrap" in result`, and the class it replaces here asserted that an
    import-only run took no verdict. The reason given was the report's headline —
    both halves of it opened with "the graph this command just wrote", so a run
    that wrote no bootstrap graph had nothing to speak about. That reason is now
    gone: the headline is chosen from what this run actually wrote, so a run may
    report on a graph it did not write and say so.

    What the old guard cost was measured, two commands on one tree:
    `init --yes --mode import` left unparented domains in `imported.yml` and
    exited 0; the wizard's re-init does not delete `.beadloom/`, so the next run
    wrote `domain-needs-parent` and met them. #192's shape was deferred by one
    command rather than prevented, and the run that reported it was not the run
    that wrote the nodes.

    The population is every mode the flag offers, read off the flag, plus the
    `--import` branch, which is a branch of the command rather than a mode. The
    old class ranged over one mode and one alternative, which is how it read as a
    decision about `import` rather than as a decision about writers.

    STATED LIMIT, because part 2(a) does not reach its own stated goal. Judging
    every writing run does not make the import-only run report its own orphans:
    on a virgin tree that run writes no `rules.yml`, so `lint_step` evaluates
    nothing and passes. The verdict is taken and is honestly green. What the
    change buys is that no branch is excluded by an accident of another module,
    and that the run which does meet the rule describes it truthfully. Closing
    the deferral itself needs the parent post-condition stated over the graph on
    disk rather than over each writer's own output, which is a behaviour change
    beyond this bead.
    """

    def _verdicts_taken(self, monkeypatch: pytest.MonkeyPatch) -> list[Path]:
        taken: list[Path] = []

        def record(project_root: Path, **kwargs: Any) -> None:
            taken.append(project_root)

        monkeypatch.setattr(
            "beadloom.services.commands.setup._verdict_on_the_generated_graph", record
        )
        return taken

    def test_the_modes_axis_is_not_empty(self) -> None:
        """Anti-vacuity: an empty `THE_MODES` would run no case below."""
        assert set(THE_MODES) >= {"bootstrap", "import", "both"}, THE_MODES

    @pytest.mark.parametrize("mode", THE_MODES, ids=list(THE_MODES))
    def test_every_mode_takes_a_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
    ) -> None:
        project = typescript_project(tmp_path / "orders-web").root
        _docs_the_classifier_cannot_place(project)
        taken = self._verdicts_taken(monkeypatch)

        result = CliRunner().invoke(
            main, ["init", "--yes", "--mode", mode, "--project", str(project)]
        )

        assert result.exit_code == 0, result.output
        # Anti-vacuity: the run wrote a graph file, so "it was judged" is a claim
        # about a writing run and not about one that did nothing.
        assert list((project / ".beadloom" / "_graph").glob("*.yml")), result.output
        assert taken == [project], f"mode {mode!r} wrote a graph file unjudged"

    def test_the_import_branch_takes_a_verdict_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`--import` is a branch, not a mode, and it writes `imported.yml`."""
        project = typescript_project(tmp_path / "orders-web").root
        _docs_the_classifier_cannot_place(project)
        taken = self._verdicts_taken(monkeypatch)

        result = CliRunner().invoke(
            main, ["init", "--import", str(project / "docs"), "--project", str(project)]
        )

        assert result.exit_code == 0, result.output
        assert (project / ".beadloom" / "_graph" / "imported.yml").is_file(), result.output
        assert taken == [project], result.output

    def test_the_import_branch_reindexes_what_it_wrote_before_judging_it(
        self, tmp_path: Path
    ) -> None:
        """The verdict is only worth the index it reads.

        `lint_step` reads the index without rebuilding it, so a branch that
        writes a graph file and judges an index that predates it reports on a
        tree nobody has. That is the stale-index defect BDL-067 `.14` closed on
        `--yes --mode both`, and the `--import` branch carried it until `.17`
        gave it a verdict at all — it used to tell the adopter to re-index by
        hand instead. Stated over the node the run wrote, so the claim is that
        the index HOLDS it rather than that some command ran.
        """
        project = typescript_project(tmp_path / "orders-web").root
        _docs_the_classifier_cannot_place(project)

        result = CliRunner().invoke(
            main, ["init", "--import", str(project / "docs"), "--project", str(project)]
        )

        assert result.exit_code == 0, result.output
        assert "payments" in _the_nodes_the_index_holds(project)


class TestTheReportNamesTheFileEachViolatingNodeCameFrom:
    """Where to open, per node, rather than one file named by habit.

    Measured by the review of `.13`: the violating node was `payments`, from
    `imported.yml`, and the report sent the adopter to `services.yml` and
    `rules.yml`, neither of which contains it. The post-condition above removes
    that case; naming the file removes the shape, so the next writer's node is
    reported against its own file rather than the bootstrap's.
    """

    def test_a_node_from_the_import_file_is_reported_against_that_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web").root
        _docs_the_classifier_cannot_place(project)
        _an_import_that_adds_an_orphan(monkeypatch)

        result = _the_branch_reported(_init_over_code_and_docs(project))

        named = [
            line for line in result.output.splitlines() if THE_ADDED_ORPHAN in line
        ]
        assert named, result.output
        assert all(THE_IMPORT_FILE in line for line in named), named

    def test_a_node_from_the_bootstrap_file_is_reported_against_that_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The other file, so the claim is about attribution and not a constant."""
        project = typescript_project(tmp_path / "orders-web").root
        _a_bootstrap_that_forgets_the_edge(monkeypatch, INIT_FLOW_BINDING)

        result = _the_branch_reported(
            _init(project, THE_BRANCHES[0])
        )

        named = [line for line in result.output.splitlines() if THE_RULE in line]
        assert named, result.output
        assert any(THE_BOOTSTRAP_FILE in line for line in named), named


def _the_formats_ci_offers() -> tuple[str, ...]:
    """The `--format` values, read off `ci`'s own `click.Choice`.

    Derived for the reason `THE_MODES` is: a fourth renderer added to the flag
    and not to a list here would be a renderer with no case, and `init`'s promise
    about what `beadloom ci` prints is a promise about whichever one runs.
    """
    from beadloom.services.commands.federation import ci

    option = next(p for p in ci.params if p.name == "fmt")
    choices = getattr(option.type, "choices", ())
    return tuple(str(choice) for choice in choices)


#: Every rendering `beadloom ci` can produce, derived once at import.
THE_GATE_FORMATS = _the_formats_ci_offers()


class TestTheReportPromisesWhatEveryRendererPrints:
    """The line pre-empts the adopter's next command, so it must survive it.

    BDL-067 `.17`, the review of `.16`'s minor. The class this replaces rendered
    the Gate through `_format_gate_rich` and asserted `init` quoted that line
    back. `ci` picks `rich` only on a TTY and `github` otherwise, and the github
    renderer builds its own step line rather than calling `gate_step_line` — so
    the instrument introduced to stop this line drifting was itself scoped to one
    of three renderings, and wrong in exactly the scripted context `--yes` serves.
    Measured in one non-TTY shell: `init` promised
    `[FAIL] lint: 2 error(s), 0 warning(s)`; `ci` on the same tree printed
    `::notice::lint FAIL: 2 error(s), 0 warning(s)`.

    So the report states the two FACTS every renderer reads off the step — its
    name and its summary — instead of quoting one renderer's spelling, and the
    cases below range over every format the flag offers. A renderer that stopped
    printing the step's summary would fail here rather than making the promise
    false for whoever met it.
    """

    def _a_failing_step(self, project_root: Path) -> Any:
        from beadloom.application.gate import lint_step

        step = lint_step(project_root)
        assert not step.passed, "the fixture is green, so there is no promise to check"
        return step

    def _the_report(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, INIT_FLOW_BINDING)
        return project.root, _the_branch_reported(_init(project.root, THE_BRANCHES[0]))

    def test_the_format_axis_is_not_empty(self) -> None:
        """Anti-vacuity: one renderer is the assumption this class was written for."""
        assert len(THE_GATE_FORMATS) > 1, THE_GATE_FORMATS

    def test_the_report_states_the_step_name_and_its_summary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_root, result = self._the_report(tmp_path, monkeypatch)
        step = self._a_failing_step(project_root)

        assert step.name in result.output, result.output
        assert step.summary in result.output, result.output

    @pytest.mark.parametrize("fmt", THE_GATE_FORMATS, ids=list(THE_GATE_FORMATS))
    def test_every_renderer_prints_the_facts_the_report_promised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fmt: str
    ) -> None:
        from beadloom.application.gate import GateResult
        from beadloom.services.commands.federation import _format_gate

        project_root, _ = self._the_report(tmp_path, monkeypatch)
        step = self._a_failing_step(project_root)

        rendered = _format_gate(GateResult(steps=[step]), fmt)

        assert step.name in rendered, (fmt, rendered)
        assert step.summary in rendered, (fmt, rendered)

    @pytest.mark.parametrize("fmt", THE_GATE_FORMATS, ids=list(THE_GATE_FORMATS))
    def test_the_report_quotes_no_renderer_s_own_step_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fmt: str
    ) -> None:
        """The defect, stated directly: a quoted spelling is one renderer's.

        Any line a renderer builds for the step is that renderer's shape, and
        quoting it makes the promise false wherever a different one runs. This
        fails against the pre-`.17` report for `github` and `json`, which is the
        case the review measured.
        """
        from beadloom.application.gate import GateResult
        from beadloom.services.commands.federation import _format_gate

        project_root, result = self._the_report(tmp_path, monkeypatch)
        step = self._a_failing_step(project_root)

        rendered = _format_gate(GateResult(steps=[step]), fmt)
        lines_about_the_step = [
            line.strip() for line in rendered.splitlines() if step.name in line.strip()
        ]
        # Anti-vacuity: a renderer that never mentions the step would make the
        # claim below hold over an empty list.
        assert lines_about_the_step, (fmt, rendered)

        quoted = [line for line in lines_about_the_step if line in result.output]
        assert quoted == [], (fmt, quoted, result.output)
