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

#: A PEP 420 layout, built rather than assumed. `src/ns` carries no
#: `__init__.py`; its two subpackages do. BDL-068 `.15` measured that the sweep
#: stopped at the first subpackage on a tree of this shape and reported the
#: caller one directory across as `none found.` — resolved, empty and wrong.
_NAMESPACE_WRITER = '''\
"""The file the change is being made in."""
import yaml


def helper(data, path):
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
'''

_NAMESPACE_CALLER = '''\
"""The caller, in the subpackage next door."""
from ns.sub.writer import helper


def run(flag, data, path):
    if flag:
        helper(data, path)
    else:
        helper({}, path)
'''

#: A `.py` file saved mid-edit. BDL-UX #255 reached `ast.parse` through the
#: TARGET rather than through the sweep, and the sweep has kept a failure like
#: this one since the package was written -- so the crash was one keystroke away
#: from a file whose suffix is right.
_HALF_SAVED = """\
\"\"\"A module saved half-way through an edit.\"\"\"


def broken(
"""

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
    return {
        "root": root,
        "home": tmp_path,
        "argv": None,
        "result": None,
        "human": None,
        "other": None,
    }


def _run(
    world: dict[str, Any], target: str, *, as_json: bool = True, root: str | None = None
) -> None:
    argv = ["impact", target, "--project", str(world["root"])]
    if root is not None:
        argv += ["--root", str(world["root"] / root)]
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


@given("a project whose package carries no __init__.py file")
def given_namespace_project(world: dict[str, Any]) -> None:
    """A PEP 420 tree, the layout this repository does not have anywhere."""
    root = world["home"] / "namespaced"
    for part in ("sub", "cli"):
        (root / "src" / "ns" / part).mkdir(parents=True)
        (root / "src" / "ns" / part / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "ns" / "sub" / "writer.py").write_text(
        _NAMESPACE_WRITER, encoding="utf-8"
    )
    (root / "src" / "ns" / "cli" / "main.py").write_text(
        _NAMESPACE_CALLER, encoding="utf-8"
    )
    assert not (root / "src" / "ns" / "__init__.py").exists()
    world["root"] = root


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


@when("impact runs against the file in one of its subpackages")
def when_run_namespace(world: dict[str, Any]) -> None:
    _run(world, "src/ns/sub/writer.py")


@when("impact runs against that file and again against the symbol it defines")
def when_run_both_spellings(world: dict[str, Any]) -> None:
    _run(world, "src/ns/sub/writer.py")
    by_path = _payload(world)
    _run(world, "helper")
    world["other"] = by_path


@when("impact runs against that file over a root that does not hold it")
def when_run_narrowed(world: dict[str, Any]) -> None:
    _run(world, "src/ns/sub/writer.py", root="src/ns/cli")


@then("the callers include the function in the neighbouring subpackage")
def then_caller_across_the_namespace(world: dict[str, Any]) -> None:
    callers = _payload(world)["callers"]
    assert callers["resolved"] is True
    assert [site["name"] for site in callers["sites"]] == ["run"]
    assert "src/ns/cli/main.py" in world["human"].output


@then("the swept root is the namespace package rather than the subpackage")
def then_swept_root_is_the_namespace(world: dict[str, Any]) -> None:
    assert _payload(world)["root"] == "src/ns"


@then("both runs name the same callers")
def then_both_spellings_agree(world: dict[str, Any]) -> None:
    by_symbol = _payload(world)
    by_path = world["other"]
    assert [site["name"] for site in by_symbol["callers"]["sites"]] == [
        site["name"] for site in by_path["callers"]["sites"]
    ]
    assert by_symbol["callers"]["sites"]


@then("the callers axis reads unresolved rather than empty")
def then_callers_unresolved(world: dict[str, Any]) -> None:
    callers = _payload(world)["callers"]
    assert callers["resolved"] is False
    assert f"- unresolved: {callers['reason']}" in world["human"].output


@then("the unresolved population names the target that fell outside the sweep")
def then_target_outside_reported(world: dict[str, Any]) -> None:
    gap = next(
        entry
        for entry in _payload(world)["unresolved"]
        if entry["kind"] == "target-outside-the-sweep"
    )
    assert "src/ns/sub/writer.py" in gap["detail"]
    assert "src/ns/cli" in gap["where"]


@then("the unresolved population says the sweep is narrower than the project")
def then_narrower_sweep_reported(world: dict[str, Any]) -> None:
    gap = next(
        entry
        for entry in _payload(world)["unresolved"]
        if entry["kind"] == "sweep-narrower-than-the-project"
    )
    assert "src/ns/cli" in gap["detail"]
    assert "src/ns" in gap["where"]


@then("the branches of the command that calls the target are reported too")
def then_caller_branches(world: dict[str, Any]) -> None:
    commands = {command["name"]: command for command in _payload(world)["commands"]}
    assert len(commands["run"]["branches"]) == 4
    assert commands["run"]["seat"] == "caller"
    assert commands["bootstrap_project"]["seat"] == "target"


@then("every branch count says which seat it was taken from")
def then_every_count_names_its_seat(world: dict[str, Any]) -> None:
    commands = _payload(world)["commands"]
    assert commands
    assert all(command["seat"] in {"target", "caller"} for command in commands)
    assert "caller's seat" in world["human"].output


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
    # The human text is asserted on the LINE that carries the difference, not on
    # the word: BDL-068 `.7` measured that `render_impact` always prints an
    # `## unresolved (N)` heading, so `"unresolved" in output` held for every
    # answer and could not fail. An empty population reads `- none found.`, an
    # unresolved one reads its reason, and only the second may appear here.
    assert f"- unresolved: {co_writers['reason']}" in world["human"].output


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


@given("a project holding a Python file that does not parse")
def given_a_half_saved_module(world: dict[str, Any]) -> None:
    """A `.py` file that reaches the same `ast.parse` the document reaches.

    The suffix is the only thing that separates it from the document above, and
    both ended BDL-UX #255 the same way, so the fix is checked over both rather
    than over the shape that happened to be reported.
    """
    (world["root"] / "src" / "pkg" / "half_saved.py").write_text(_HALF_SAVED, encoding="utf-8")


@when("impact runs against a document in that project")
def when_run_document(world: dict[str, Any]) -> None:
    _run(world, "docs/lonely.md")


@when("impact runs against that file")
def when_run_half_saved(world: dict[str, Any]) -> None:
    _run(world, "src/pkg/half_saved.py")


@when("impact runs against the package holding it")
def when_run_the_whole_package(world: dict[str, Any]) -> None:
    _run(world, "src/pkg")


@then("the run ends with an answer rather than a traceback")
def then_an_answer_rather_than_a_traceback(world: dict[str, Any]) -> None:
    result = world["result"]
    assert result.exception is None, result.exception
    assert result.exit_code == 0, result.output
    assert "Traceback" not in world["human"].output


@then("the unresolved population names the target it could not read")
def then_unreadable_target_reported(world: dict[str, Any]) -> None:
    gaps = [
        entry for entry in _payload(world)["unresolved"] if entry["kind"] == "unreadable-target"
    ]
    assert gaps, _payload(world)["unresolved"]
    assert all(gap["where"] for gap in gaps)
    assert all(gap["detail"] for gap in gaps)
    assert "[unreadable-target]" in world["human"].output


@then("the answer still reports the branches of the files that did parse")
def then_the_readable_files_still_answer(world: dict[str, Any]) -> None:
    """The unreadable file costs the answer that file and no other.

    Recall over precision, applied to the fix itself: refusing the whole answer
    because one file of a package did not parse would trade a traceback for a
    silence, which is the trade this epic exists to refuse.
    """
    commands = {command["name"]: command for command in _payload(world)["commands"]}
    assert "half_saved" not in {command["path"] for command in _payload(world)["commands"]}
    assert len(commands["run"]["branches"]) == 4
    assert "sys.exit(0)" in commands["run"]["exits"]


# ---------------------------------------------------------------------------
# BDL-UX #284 — a row names the files its node owns and this derivation did not read
# ---------------------------------------------------------------------------

_MANIFEST = '''\
"""The target: reads a manifest and nothing else."""


def read_manifest(root):
    return (root / "manifest.txt").read_text()
'''

_GENERATOR = '''\
"""The caller, which renders a template its own node owns."""
from pathlib import Path

from app.manifest import read_manifest

TEMPLATES = Path(__file__).parent / "templates"


def render_domain(root):
    name = read_manifest(root)
    return (TEMPLATES / "domain.md.txt").read_text().format(name=name)
'''

_OWNED_TEMPLATE = "src/app/skel/templates/domain.md.txt"


@given("a project whose caller renders a template its own node owns")
def given_templated_project(world: dict[str, Any]) -> None:
    root = world["home"] / "templated"
    files = {
        "pyproject.toml": '[project]\nname = "app"\nversion = "0.1.0"\n',
        "src/app/__init__.py": "",
        "src/app/skel/__init__.py": "",
        "src/app/manifest.py": _MANIFEST,
        "src/app/skel/generator.py": _GENERATOR,
        _OWNED_TEMPLATE: "# {name}\n\n## Source\n",
        "docs/manifest.md": "# manifest\n\nReads the manifest.\n",
        "docs/skel.md": "# skel\n\nRenders the skeleton.\n",
    }
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    nodes = [
        {
            "ref_id": "manifest",
            "kind": "feature",
            "summary": "reads the manifest",
            "source": "src/app/manifest.py",
            "docs": ["manifest.md"],
        },
        {
            "ref_id": "skel",
            "kind": "feature",
            "summary": "renders the skeleton from its templates",
            "source": "src/app/skel/",
            "docs": ["skel.md"],
        },
    ]
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(yaml.dump({"nodes": nodes}), encoding="utf-8")
    world["root"] = root


@when("impact renders the Axes section for the target that caller calls")
def when_render_the_section(world: dict[str, Any]) -> None:
    argv = ["impact", "src/app/manifest.py", "--project", str(world["root"])]
    world["section"] = CliRunner().invoke(main, [*argv, "--section"])
    _run(world, "src/app/manifest.py")


def _section_row(world: dict[str, Any], axis: str, node: str) -> dict[str, str]:
    result = world["section"]
    assert result.exit_code == 0, result.output + str(result.exception)
    lines = result.stdout.splitlines()
    header = next(line for line in lines if line.startswith("| Axis |"))
    names = [cell.strip() for cell in header.strip("|").split("|")]
    row = next(line for line in lines if line.startswith(f"| {axis} | {node} |"))
    return dict(zip(names, (cell.strip() for cell in row.strip("|").split("|")), strict=True))


@then("the caller's row names the template its node owns")
def then_caller_row_names_the_template(world: dict[str, Any]) -> None:
    row = _section_row(world, "callers", "skel")
    assert row["Owns unread"] == f"1 — `{_OWNED_TEMPLATE}`"


@then("the target's row states that its node owns no file the derivation could not read")
def then_target_row_states_none(world: dict[str, Any]) -> None:
    assert _section_row(world, "branches", "manifest")["Owns unread"] == "none"


@then("the unresolved population names the node that owns the unread template")
def then_unresolved_names_the_owner(world: dict[str, Any]) -> None:
    gaps = [
        entry
        for entry in _payload(world)["unresolved"]
        if entry["kind"] == "node-owns-unread-files"
    ]
    assert [gap["where"] for gap in gaps] == [_OWNED_TEMPLATE]
    assert "skel" in gaps[0]["detail"]
    assert "node-owns-unread-files" in world["human"].output
