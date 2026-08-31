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

The fixture is a project that is not us (`orders-web`, a flat `src/index.ts`), so a
verdict that worked by recognising Beadloom's own tree would fail these.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.services.cli import main
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    from pathlib import Path

#: The rule `generate_rules` writes for every graph that holds a domain, and the
#: rule BDL-UX #192's reporter read out of `lint --strict` after a green `init`.
THE_RULE = "domain-needs-parent"

#: The two ways `init` reaches the bootstrap. `init --yes` goes through
#: `non_interactive_init`, which binds `bootstrap_project` at import time;
#: `init --bootstrap` imports it from the package inside the command body. They
#: are different names for the same function and must be sabotaged separately.
BOOTSTRAP_BINDINGS = {
    "--yes": "beadloom.onboarding.scanner.init_flow.bootstrap_project",
    "--bootstrap": "beadloom.onboarding.bootstrap_project",
}


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


def _init(project_root: Path, flag: str) -> Any:
    args = ["init", flag, "--project", str(project_root)]
    if flag == "--yes":
        args[2:2] = ["--mode", "bootstrap"]
    return CliRunner().invoke(main, args)


def _lint_strict(project_root: Path) -> int:
    return CliRunner().invoke(
        main, ["lint", "--strict", "--project", str(project_root)]
    ).exit_code


@pytest.mark.parametrize("flag", sorted(BOOTSTRAP_BINDINGS))
class TestInitOverAGraphThatFailsItsOwnRules:
    """The graph on disk contradicts the rules on disk, in both init branches."""

    def test_the_command_does_not_exit_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, BOOTSTRAP_BINDINGS[flag])

        result = _init(project.root, flag)

        assert result.exit_code != 0, result.output

    def test_it_names_the_rule_the_gate_will_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str
    ) -> None:
        """Not "something is wrong" — the string the adopter will read again."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, BOOTSTRAP_BINDINGS[flag])

        result = _init(project.root, flag)

        assert THE_RULE in result.output

    def test_the_verdict_agrees_with_lint_strict_on_the_same_tree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str
    ) -> None:
        """The claim is agreement with the Gate, not merely a non-zero number."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, BOOTSTRAP_BINDINGS[flag])

        init_rc = _init(project.root, flag).exit_code

        assert (init_rc != 0) == (_lint_strict(project.root) != 0)

    def test_the_graph_is_still_on_disk_to_be_repaired(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str
    ) -> None:
        """A non-zero rc reports the defect; it does not withdraw the scaffold."""
        project = typescript_project(tmp_path / "orders-web")
        _a_bootstrap_that_forgets_the_edge(monkeypatch, BOOTSTRAP_BINDINGS[flag])

        _init(project.root, flag)

        assert (project.root / ".beadloom" / "_graph" / "services.yml").is_file()
        assert (project.root / ".beadloom" / "_graph" / "rules.yml").is_file()


@pytest.mark.parametrize("flag", sorted(BOOTSTRAP_BINDINGS))
class TestInitOverAGraphThatPassesItsOwnRules:
    """The everyday path stays green — the check is a verdict, not a tax."""

    def test_an_unsabotaged_init_still_exits_zero(self, tmp_path: Path, flag: str) -> None:
        project = typescript_project(tmp_path / "orders-web")

        result = _init(project.root, flag)

        assert result.exit_code == 0, result.output

    def test_it_does_not_name_a_rule_nothing_violated(
        self, tmp_path: Path, flag: str
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")

        result = _init(project.root, flag)

        assert THE_RULE not in result.output

    def test_lint_strict_agrees_that_the_tree_is_clean(
        self, tmp_path: Path, flag: str
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")

        init_rc = _init(project.root, flag).exit_code

        assert (init_rc != 0) == (_lint_strict(project.root) != 0)
