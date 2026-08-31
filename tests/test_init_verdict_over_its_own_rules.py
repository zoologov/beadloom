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
    #: The wizard's answers, in order: init mode, then the graph review.
    prompts: tuple[str, ...] = field(default_factory=tuple)


#: Every branch of `init` that reaches `bootstrap_project`. Three branches, two
#: bindings. A fourth branch belongs in this tuple on the day it is written.
THE_BRANCHES = (
    InitBranch("--yes", ("--yes", "--mode", "bootstrap"), INIT_FLOW_BINDING),
    InitBranch("--bootstrap", ("--bootstrap",), PACKAGE_BINDING),
    InitBranch("wizard", (), INIT_FLOW_BINDING, prompts=("bootstrap", "yes")),
)

BRANCH_IDS = [branch.name for branch in THE_BRANCHES]

#: A `rules.yml` the loader refuses: no `version` key. This is what a hand edit
#: leaves behind, and `bootstrap_project` never rewrites a rules file that is
#: already there, so `init` can meet it.
UNLOADABLE_RULES = "rules:\n  - name: hand-edited\n    require:\n      match: {}\n"

#: The part of the loader's complaint an adopter needs to see.
THE_PARSE_ERROR = "missing required 'version' field"


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

        _init(project.root, branch)

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

        result = _init(project.root, branch)

        assert "  lint" not in result.output.splitlines()

    def test_it_does_not_blame_the_bootstrap_for_a_hand_edited_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        """The graph the bootstrap wrote is not what failed here."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_whose_rules_file_will_not_load(monkeypatch, branch.binding)

        result = _init(project.root, branch)

        assert "defect in Beadloom's bootstrap" not in result.output

    def test_the_command_does_not_exit_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: InitBranch
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_whose_rules_file_will_not_load(monkeypatch, branch.binding)

        result = _init(project.root, branch)

        assert result.exit_code != 0, result.output
