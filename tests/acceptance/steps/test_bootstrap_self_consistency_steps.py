"""Step implementations for `features/bootstrap_self_consistency.feature`.

BDL-067, closing BDL-UX #192. The `.1` steps run the real `bootstrap_project`
and the real linter over real directories; nothing there is stubbed, because a
stub would agree with whatever the bootstrap currently writes and that is the
thing under test.

The one `.2` step that does patch — `a bootstrap that writes the graph and then
forgets the edge its rules require` — patches for the opposite reason. `.1` made
a self-contradicting graph impossible to obtain honestly, so the divergence
`init` is asked to notice has to be CONSTRUCTED. It is constructed at the graph
only: the real bootstrap runs, the real `generate_rules` writes
`domain-needs-parent`, and the `part_of` edges are then taken back out of
`services.yml`. Nothing about `init`'s verdict is faked.

**FAKES PROVE FAKES.** Every fixture here is a project that is not Beadloom —
`orders-web`, `orders (web)`, `supply-chain/src/platform/orders`. None of those
names exists in this repository, so a fix that worked by recognising our own
tree would fail these.

The fixtures are built here rather than imported from `tests.adopter_project`,
which holds the same TypeScript shape. `tests/test_bead14_s4_binding.py` copies
`tests/acceptance/` out of the repository and runs it standalone to prove a
broken step binding reddens the suite, and in that copy the `tests` package is
not importable — an import of it turns that sabotage into a collection failure,
which proves nothing about the binding.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import lint
from beadloom.onboarding.scanner import bootstrap_project
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/bootstrap_self_consistency.feature")

#: A project name that survives `_sanitize_ref_id` only by losing characters.
#: The root's ref_id is written unsanitised, so an edge that recomputes the
#: name from the project instead of reading the node points at nothing.
PARENTHESISED_NAME = "orders (web)"

#: The rule `generate_rules` writes for any graph holding a domain, and the rule
#: BDL-UX #192's reporter read out of `lint --strict` after a green `init`. The
#: scenario asserts this exact string: "the command failed" is not the fact the
#: adopter needs, the name they will meet again in the Gate's output is.
THE_RULE = "domain-needs-parent"

#: A `rules.yml` the loader refuses, and the part of its complaint an adopter
#: needs to read. `bootstrap_project` never rewrites a rules file that is already
#: there, so a hand edit that will not parse is a file `init` can meet.
UNLOADABLE_RULES = "rules:\n  - name: hand-edited\n    require:\n      match: {}\n"
THE_LOADER_COMPLAINT = "missing required 'version' field"

#: The gate step's own name, which its `LintError` finding carries in `rule`.
#: Printed as though it were a rule, it names a rule no rules file contains.
THE_STEP_NAME = "lint"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _flat_project(root: Path) -> Path:
    """One source file directly under `src/` — no code-bearing subdirectory.

    The shape BDL-UX #192 was reported against, and the same shape
    `tests.adopter_project.typescript_project` builds: a Node manifest whose
    name the root node takes, and a single flat `src/index.ts`.
    """
    project = root / "orders-web"
    (project / "src").mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"name": "orders-web", "version": "0.4.1"}, indent=2) + "\n",
        encoding="utf-8",
    )
    (project / "src" / "index.ts").write_text("export const orders = [];\n", encoding="utf-8")
    return project


def _parenthesised_project(root: Path) -> Path:
    """The same flat shape under a name `_sanitize_ref_id` would rewrite.

    No manifest, so `_detect_project_name` falls back to the directory name and
    the root node's ref_id keeps its parentheses.
    """
    project = root / PARENTHESISED_NAME
    (project / "src").mkdir(parents=True)
    (project / "src" / "index.ts").write_text("export const orders = [];\n", encoding="utf-8")
    return project


def _nested_project(root: Path) -> Path:
    """A source dir with a code-bearing subdirectory whose child is a domain.

    `platform` and `orders` match no preset pattern, so both classify at the
    MONOLITH default kind `domain`. `orders` therefore has a classified parent
    and must keep it.
    """
    project = root / "supply-chain"
    orders = project / "src" / "platform" / "orders"
    orders.mkdir(parents=True)
    boot = project / "src" / "platform" / "boot.ts"
    boot.write_text("export const b = 1;\n", encoding="utf-8")
    (orders / "orders.ts").write_text("export const o = 1;\n", encoding="utf-8")
    return project


@given("a project whose only source file sits directly in its source directory")
def _given_flat(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _flat_project(tmp_path)


@given(
    "a project whose name carries parentheses and whose source file sits "
    "directly in its source directory"
)
def _given_parenthesised(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _parenthesised_project(tmp_path)


@given("a project whose source directory has code-bearing subdirectories")
def _given_nested(world: dict[str, Any], tmp_path: Path) -> None:
    world["project"] = _nested_project(tmp_path)


@when("the project is bootstrapped")
def _when_bootstrapped(world: dict[str, Any]) -> None:
    world["result"] = bootstrap_project(world["project"])


@when("the bootstrapped graph is linted")
def _when_linted(world: dict[str, Any]) -> None:
    world["lint"] = lint(world["project"], reindex=incremental_reindex)


@then("the lint reports no error-severity violation")
def _then_no_errors(world: dict[str, Any]) -> None:
    result = world["lint"]
    assert not result.has_errors, [
        (v.rule_name, v.from_ref_id, v.message) for v in result.violations
    ]


@then(parsers.parse("every node written with kind {kind} has an outgoing part_of edge"))
def _then_every_node_of_kind_is_parented(world: dict[str, Any], kind: str) -> None:
    nodes = world["result"]["nodes"]
    parented = {e["src"] for e in world["result"]["edges"] if e["kind"] == "part_of"}
    orphans = [n["ref_id"] for n in nodes if n["kind"] == kind and n["ref_id"] not in parented]
    assert not orphans, f"{kind} nodes with no part_of edge: {orphans}"
    # Guard: a graph with no node of this kind would pass the assertion above
    # without exercising anything.
    assert any(n["kind"] == kind for n in nodes), f"fixture produced no {kind} node"


@then("each of those edges names the root node by the ref_id the bootstrap wrote")
def _then_dst_is_the_written_root(world: dict[str, Any]) -> None:
    nodes = world["result"]["nodes"]
    root_ref_id = next(n["ref_id"] for n in nodes if n["kind"] == "service")
    domains = {n["ref_id"] for n in nodes if n["kind"] == "domain"}
    dsts = {
        e["dst"]
        for e in world["result"]["edges"]
        if e["kind"] == "part_of" and e["src"] in domains
    }
    assert dsts == {root_ref_id}, f"expected part_of -> {root_ref_id!r}, got {sorted(dsts)}"


@then("every edge the bootstrap wrote points at a node the bootstrap wrote")
def _then_edges_resolve(world: dict[str, Any]) -> None:
    ref_ids = {n["ref_id"] for n in world["result"]["nodes"]}
    dangling = [e for e in world["result"]["edges"] if e["dst"] not in ref_ids]
    assert not dangling, f"edges pointing at no node: {dangling}"


@then("no domain is attached to the root when its classifier already gave it a parent")
def _then_classified_parent_is_kept(world: dict[str, Any]) -> None:
    nodes = world["result"]["nodes"]
    root_ref_id = next(n["ref_id"] for n in nodes if n["kind"] == "service")
    part_of = [e for e in world["result"]["edges"] if e["kind"] == "part_of"]
    nested = [e for e in part_of if e["dst"] != root_ref_id]
    assert nested, f"fixture produced no classified parent: {part_of}"
    for edge in nested:
        siblings = [e for e in part_of if e["src"] == edge["src"]]
        assert len(siblings) == 1, f"{edge['src']} was attached twice: {siblings}"


@given("a bootstrap that writes the graph and then forgets the edge its rules require")
def _given_a_forgetful_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-create #192's shape on a bootstrap that can no longer produce it.

    Only the graph half is sabotaged: the real `generate_rules` still writes
    `domain-needs-parent`, and the real `bootstrap_project` still runs. The
    `part_of` edges are taken back out of `services.yml` afterwards, which is
    what makes this a test of `init`'s verdict rather than a second test of `.1`.

    `init --yes` binds `bootstrap_project` at import time in `init_flow`, so that
    binding is the one the patch has to reach.
    """
    real = bootstrap_project

    def forgetful(project_root: Path, **kwargs: Any) -> dict[str, Any]:
        result = real(project_root, **kwargs)
        services = project_root / ".beadloom" / "_graph" / "services.yml"
        data = yaml.safe_load(services.read_text(encoding="utf-8"))
        # `bootstrap_project` writes no `edges:` key when there are none, so the
        # sabotaged file keeps the shape the bug was reported against.
        data.pop("edges", None)
        services.write_text(
            yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        result["edges"] = []
        result["edges_generated"] = 0
        return result

    monkeypatch.setattr(
        "beadloom.onboarding.scanner.init_flow.bootstrap_project", forgetful
    )


@when("beadloom init is run on the project")
def _when_init_is_run(world: dict[str, Any]) -> None:
    world["init"] = CliRunner().invoke(
        main,
        ["init", "--yes", "--mode", "bootstrap", "--project", str(world["project"])],
    )


@then("the command does not report success")
def _then_init_failed(world: dict[str, Any]) -> None:
    result = world["init"]
    assert result.exit_code != 0, result.output


@then("the command names the rule the gate will name")
def _then_init_names_the_rule(world: dict[str, Any]) -> None:
    result = world["init"]
    assert THE_RULE in result.output, result.output


@given("a bootstrap that leaves behind a rules file the loader will not read")
def _given_an_unreadable_rules_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """The graph is untouched; what fails is reading the rules at all.

    That is the gate's `LintError` branch, where the finding's `rule` is the step
    name and the loader's complaint is in `why` — the shape `init` used to render
    as a rule name, telling the adopter a rule called `lint` had failed.
    """
    real = bootstrap_project

    def with_broken_rules(project_root: Path, **kwargs: Any) -> dict[str, Any]:
        result = real(project_root, **kwargs)
        rules = project_root / ".beadloom" / "_graph" / "rules.yml"
        rules.write_text(UNLOADABLE_RULES, encoding="utf-8")
        return result

    monkeypatch.setattr(
        "beadloom.onboarding.scanner.init_flow.bootstrap_project", with_broken_rules
    )


@when("beadloom init is run with no flags and its prompts are answered")
def _when_the_wizard_is_run(world: dict[str, Any]) -> None:
    """Plain `beadloom init`: choose the bootstrap mode, accept the graph.

    The doc-skeleton prompt is declined, which keeps the scenario about the
    verdict and off the skeleton writer.
    """
    with (
        patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "yes"]),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        world["init"] = CliRunner().invoke(
            main, ["init", "--project", str(world["project"])]
        )


@then("the command says what the loader could not read")
def _then_init_names_the_loader_complaint(world: dict[str, Any]) -> None:
    result = world["init"]
    assert THE_LOADER_COMPLAINT in result.output, result.output


@then("the command does not offer the gate step's own name as a rule")
def _then_init_does_not_name_the_step(world: dict[str, Any]) -> None:
    result = world["init"]
    named = [line for line in result.output.splitlines() if line == f"  {THE_STEP_NAME}"]
    assert not named, result.output


@when("beadloom init is run with no flags and the graph review is answered with edit")
def _when_the_wizard_is_asked_to_edit(world: dict[str, Any]) -> None:
    """Plain `beadloom init`, choosing to edit the graph by hand.

    The same wizard and the same sabotage as the scenario above. Only the answer
    to the graph review differs, which is what makes the pair a claim about the
    answer rather than about the branch.
    """
    with (
        patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "edit"]),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        world["init"] = CliRunner().invoke(
            main, ["init", "--project", str(world["project"])]
        )


@then("the command reports success")
def _then_init_succeeded(world: dict[str, Any]) -> None:
    result = world["init"]
    assert result.exit_code == 0, result.output


@then("the command tells the user to re-index after editing")
def _then_init_asks_for_a_reindex(world: dict[str, Any]) -> None:
    """Also the guard against a vacuous green.

    A zero from a wizard that fell over before the review prompt would satisfy
    the assertion above while saying nothing about the carve-out. The re-index
    instruction is printed only on the `edit` answer, so it is the evidence that
    the branch under test is the branch that ran.
    """
    result = world["init"]
    assert "beadloom reindex" in result.output, result.output
