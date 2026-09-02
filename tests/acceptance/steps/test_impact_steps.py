"""Step implementations for `beadloom impact` (BDL-068 S1.2).

Against the real CLI and a real source tree on disk, deliberately: the whole
subject is what an AST derivation reads out of files, so a double would prove
the double's contract and nothing about the answer.

The fixture reproduces the shape BDL-067 met at `af26750d` in miniature -- one
command with four branches, one of which leaves through a call that never
returns; a commit point two hops below the command; and a SECOND writer that
commits through the same point and that the file under change never calls. That
second writer is the fact BDL-067 first answered in its fourth fix cycle, and the
fourth branch the one its ninth review found.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/impact.feature")

#: The sink the fixture commits through. Named here, in the TEST, and nowhere in
#: the production package -- which is the criterion this whole module exists for.
THE_SINK = "commit_yaml"

_ATOMIC = '''\
"""The one place this fixture puts a graph on disk."""
import yaml


def commit_yaml(path, payload):
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
'''

_BOOTSTRAP = '''\
"""The file the change was being made in."""
from pkg.atomic import commit_yaml


def bootstrap_project(root, name):
    if name:
        commit_yaml(root / "graph.yml", {"nodes": [{"ref_id": name}]})
        return True
    return False
'''

_IMPORTER = '''\
"""The second writer, which the file under change never calls."""
from pkg.atomic import commit_yaml


def import_docs(root, docs):
    commit_yaml(root / "docs.yml", {"nodes": list(docs)})
'''

_SETUP = '''\
"""The command, with four branches and two ways out."""
import sys

from pkg.bootstrap import bootstrap_project
from pkg.importer import import_docs


def interactive(root):
    return bootstrap_project(root, "asked")


def run(root, non_interactive, bootstrap, import_path):
    if non_interactive:
        bootstrap_project(root, "declared")
        return
    if bootstrap:
        bootstrap_project(root, "bootstrapped")
        sys.exit(0)
    if import_path:
        import_docs(root, [import_path])
    interactive(root)
'''

_LONELY = '''\
"""A module whose axes live entirely inside it."""


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

_MODULES = {
    "atomic": _ATOMIC,
    "bootstrap": _BOOTSTRAP,
    "importer": _IMPORTER,
    "setup": _SETUP,
    "lonely": _LONELY,
}


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """A source tree with the shape `af26750d` had, and a graph over it."""
    root = tmp_path / "proj"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    for name, body in _MODULES.items():
        (root / "src" / "pkg" / f"{name}.py").write_text(body, encoding="utf-8")
    (root / "docs").mkdir()
    nodes = []
    for name in _MODULES:
        (root / "docs" / f"{name}.md").write_text(
            f"# {name}\n\nWhat {name} does.\n", encoding="utf-8"
        )
        nodes.append(
            {
                "ref_id": name,
                "kind": "feature",
                "summary": f"the {name} module",
                "source": f"src/pkg/{name}.py",
                "docs": [f"{name}.md"],
            }
        )
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(yaml.dump({"nodes": nodes}), encoding="utf-8")
    return {"root": root, "argv": None, "result": None, "human": None}


def _run(world: dict[str, Any], target: str, *, as_json: bool = True) -> None:
    argv = ["impact", target, "--project", str(world["root"])]
    world["argv"] = [*argv, "--json"] if as_json else argv
    world["result"] = CliRunner().invoke(main, [*argv, "--json"])
    world["human"] = CliRunner().invoke(main, argv)


def _payload(world: dict[str, Any]) -> dict[str, Any]:
    result = world["result"]
    assert result.exit_code == 0, result.output + str(result.exception)
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


@given("a project whose command commits through a helper two hops away")
def given_command_project(world: dict[str, Any]) -> None:
    assert (world["root"] / "src" / "pkg" / "setup.py").exists()


@given("a project whose module reaches no declared effect sink")
def given_lonely_project(world: dict[str, Any]) -> None:
    assert (world["root"] / "src" / "pkg" / "lonely.py").exists()


@given("the project is indexed")
def given_indexed(world: dict[str, Any]) -> None:
    reindex(world["root"])


@when("impact runs against the file holding that command")
def when_run_setup(world: dict[str, Any]) -> None:
    _run(world, "src/pkg/setup.py")


@when("impact runs against the file the change was being made in")
def when_run_bootstrap(world: dict[str, Any]) -> None:
    _run(world, "src/pkg/bootstrap.py")


@when("impact runs against that module")
def when_run_lonely(world: dict[str, Any]) -> None:
    _run(world, "src/pkg/lonely.py")


@when("impact runs against the file holding that command with --json")
def when_run_setup_json(world: dict[str, Any]) -> None:
    _run(world, "src/pkg/setup.py")


@then("the answer names the derived seed")
def then_names_seed(world: dict[str, Any]) -> None:
    assert [seed["name"] for seed in _payload(world)["seeds"]] == [THE_SINK]
    assert THE_SINK in world["human"].output


@then("the answer names the rule the seed came from")
def then_names_rule(world: dict[str, Any]) -> None:
    payload = _payload(world)
    assert payload["seed_rule"]["name"]
    assert payload["seed_rule"]["statement"]
    assert payload["seeds"][0]["effect"] == "serialises-yaml"
    assert payload["seed_rule"]["name"] in world["human"].output


@then("no argument of the run named the seed")
def then_no_argument_named_it(world: dict[str, Any]) -> None:
    assert all(THE_SINK not in argument for argument in world["argv"])


@then("the derived seed is the helper that performs the effect itself")
def then_seed_is_the_sink(world: dict[str, Any]) -> None:
    seed = _payload(world)["seeds"][0]
    assert seed["name"] == THE_SINK
    assert seed["path"].endswith("atomic.py")


@then("the first-hop name it goes through is not reported as a seed")
def then_first_hop_not_a_seed(world: dict[str, Any]) -> None:
    names = {seed["name"] for seed in _payload(world)["seeds"]}
    assert "bootstrap_project" not in names
    assert "import_docs" not in names


@then("the co-writers include the writer that file never calls")
def then_second_writer(world: dict[str, Any]) -> None:
    payload = _payload(world)
    written = {site["name"] for site in payload["co_writers"]["sites"]}
    assert {"bootstrap_project", "import_docs"} <= written
    source = (world["root"] / "src" / "pkg" / "bootstrap.py").read_text(encoding="utf-8")
    assert "import_docs" not in source
    assert "import_docs" in world["human"].output


@then("the co-writers axis reads unresolved rather than empty")
def then_co_writers_unresolved(world: dict[str, Any]) -> None:
    co_writers = _payload(world)["co_writers"]
    assert co_writers["resolved"] is False
    assert co_writers["sites"] == []
    assert "unresolved" in world["human"].output


@then("the unresolved population says no seed rule found a sink")
def then_no_seed_reported(world: dict[str, Any]) -> None:
    kinds = {entry["kind"] for entry in _payload(world)["unresolved"]}
    assert "no-seed" in kinds


@then("the answer still reports that module's branches and exit forms")
def then_lonely_still_answers(world: dict[str, Any]) -> None:
    commands = {command["name"]: command for command in _payload(world)["commands"]}
    assert len(commands["measure"]["branches"]) == 3
    assert len(commands["measure"]["exits"]) >= 2


@then("the exit forms of that command include the call that never returns")
def then_exit_forms(world: dict[str, Any]) -> None:
    commands = {command["name"]: command for command in _payload(world)["commands"]}
    assert len(commands["run"]["branches"]) == 4
    assert "sys.exit(0)" in commands["run"]["exits"]
    assert "return" in commands["run"]["exits"]


@then("each found site names the graph node that owns it")
def then_sites_carry_a_node(world: dict[str, Any]) -> None:
    payload = _payload(world)
    sites = payload["co_writers"]["sites"] + payload["commands"]
    assert sites
    assert all(site["node"] for site in sites)
    assert {site["node"] for site in payload["co_writers"]["sites"]} == {
        "bootstrap",
        "importer",
    }


@then("the answer says the change leaves the target's own node")
def then_leaves_the_node(world: dict[str, Any]) -> None:
    boundary = _payload(world)["boundary"]
    assert boundary["target_node"] == "setup"
    assert boundary["leaves_the_target_node"] is True
    assert sorted(boundary["nodes_touched"]) == ["bootstrap", "importer", "setup"]


@then("the unresolved population says the boundary had no index to read")
def then_boundary_unresolved(world: dict[str, Any]) -> None:
    kinds = {entry["kind"] for entry in _payload(world)["unresolved"]}
    assert "no-graph-index" in kinds


@then("the JSON carries the seed, the rule and the unresolved population")
def then_json_shape(world: dict[str, Any]) -> None:
    payload = _payload(world)
    assert set(payload) >= {
        "target",
        "root",
        "seed_rule",
        "seeds",
        "co_writers",
        "callers",
        "commands",
        "boundary",
        "unresolved",
    }
