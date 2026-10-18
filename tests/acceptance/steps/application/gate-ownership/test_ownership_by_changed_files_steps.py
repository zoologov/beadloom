"""Step implementations for `application/gate-ownership/ownership_by_changed_files.feature`.

BDL-083 S1c (``beadloom-b23f``). Thin: each step commits onto a real checkout of the
monorepo fixture and runs the real ``beadloom ci`` over it, because the finding is about
what one command's output says. The one double is the tracker adapter
(``BdWorkTracker``): a scenario must not need a beads database in a temporary
directory, nor claim a bead in the author's real tracker.
"""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.guards.contract import ClaimedBead
from beadloom.services.cli import main
from tests.support.committed_project import commit_project, git
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/gate-ownership/ownership_by_changed_files.feature")

#: The widget the monorepo fixture's adopter broke, the import that broke it, and its node.
_WIDGET = "frontend/src/widgets/kpi-panel/ui/KpiPanel.ts"
_APP_IMPORT = "import '@/app/styles'\n"
_WIDGET_NODE = "widgets-kpi-panel"

#: A file of the shared layer, which the second work item's bead changed.
_SHARED_FILE = "frontend/src/shared/lib/percent.ts"

#: The rule a layer violation on the fixture is reported under.
_LAYER_RULE = "fsd-layers"

#: A committer identity, so a commit does not depend on the machine's git configuration.
_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {"workdir": tmp_path, "root": None, "claimed": [], "outputs": {}}


def _commit(root: Path, path: str, text: str, message: str) -> None:
    """Prepend *text* to *path* and commit it with *message*."""
    target = root / path
    target.write_text(text + target.read_text(encoding="utf-8"), encoding="utf-8")
    git(root, "add", path)
    git(root, *_IDENTITY, "commit", "-q", "-m", message)


def _claim(monkeypatch: pytest.MonkeyPatch, world: dict[str, Any], bead: ClaimedBead) -> None:
    """Add *bead* to the beads the service-layer tracker reports claimed."""
    from beadloom.services import guard_probes

    world["claimed"].append(bead)
    claimed = tuple(world["claimed"])
    monkeypatch.setattr(guard_probes.BdWorkTracker, "claimed_beads", lambda _self: claimed)


def _ci(world: dict[str, Any], output_format: str) -> str:
    result = CliRunner().invoke(
        main, ["ci", "--project", str(world["root"]), "--format", output_format]
    )
    return result.stdout


@given("the monorepo fixture on a working branch cut from the trunk")
def _the_monorepo(world: dict[str, Any]) -> None:
    # Copied from the checkout the package under test ships from, as the composed-hooks
    # scenarios do: `tests.support.monorepo_fixture` finds this repository's root when it
    # is imported, and a copied suite has none.
    root = world["workdir"] / "metrics-desk"
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    commit_project(root)
    git(root, "branch", "-M", "main")
    git(root, "switch", "-q", "-c", "features/W")
    world["root"] = root


@given("bead A's commit makes a widget import the app layer")
def _bead_a_breaks_the_layers(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _commit(world["root"], _WIDGET, _APP_IMPORT, "the widget reads the app styles (bd-a)")
    _claim(
        monkeypatch,
        world,
        ClaimedBead(id="bd-a", title="bd-a", declaration="refs: widgets-kpi-panel"),
    )


@given("bead B, whose refs name the node that covers the whole frontend, is claimed beside A")
def _bead_b_beside(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _claim(monkeypatch, world, ClaimedBead(id="bd-b", title="bd-b", declaration="refs: frontend"))


@given("an older commit of the branch makes a widget import the app layer")
def _an_older_commit(world: dict[str, Any]) -> None:
    _commit(world["root"], _WIDGET, _APP_IMPORT, "the first work item's widget (bd-f1)")


@given("bead F2, whose refs name the node that covers the whole frontend, is claimed alone")
def _bead_f2_alone(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _claim(
        monkeypatch, world, ClaimedBead(id="bd-f2", title="bd-f2", declaration="refs: frontend")
    )


@given("F2's commit changes a file of the shared layer")
def _f2_commits(world: dict[str, Any]) -> None:
    _commit(world["root"], _SHARED_FILE, "// rounded down\n", "the shared ratio (bd-f2)")


@when("the gate reports on the checkout")
def _run_the_gate(world: dict[str, Any]) -> None:
    world["outputs"]["rich"] = _ci(world, "rich")
    world["outputs"]["json"] = _ci(world, "json")


@when("the gate reports on the checkout in every format")
def _run_every_format(world: dict[str, Any]) -> None:
    for output_format in ("rich", "github", "json"):
        world["outputs"][output_format] = _ci(world, output_format)


def _ownership(world: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(world["outputs"]["json"])
    ownership: dict[str, Any] = payload["ownership"]
    return ownership


def _rows(world: dict[str, Any], **match: object) -> list[dict[str, Any]]:
    rows = _ownership(world)["findings"]
    return [row for row in rows if all(row.get(k) == v for k, v in match.items())]


@then("the report names A as the owner of the layer finding")
def _a_owns_it(world: dict[str, Any]) -> None:
    layer = _rows(world, rule=_LAYER_RULE, node=_WIDGET_NODE)
    assert layer, _ownership(world)
    assert [row["beads"] for row in layer] == [["bd-a"]] * len(layer)
    assert "owned by bd-a: " in world["outputs"]["rich"]


@then("it says B owns no finding")
def _b_owns_nothing(world: dict[str, Any]) -> None:
    assert all("bd-b" not in row["beads"] for row in _ownership(world)["findings"])
    lines = [line for line in world["outputs"]["rich"].splitlines() if "bd-b" in line]
    assert lines, world["outputs"]["rich"]
    assert "owns no finding" in lines[0]


@then("the layer finding is unattributed")
def _layer_unattributed(world: dict[str, Any]) -> None:
    layer = _rows(world, rule=_LAYER_RULE, node=_WIDGET_NODE)
    assert layer, _ownership(world)
    assert {row["verdict"] for row in layer} == {"unattributed"}


@then("no finding about the widget is owned by F2")
def _f2_owns_nothing_of_the_widget(world: dict[str, Any]) -> None:
    widget = _rows(world, node=_WIDGET_NODE)
    assert widget, _ownership(world)
    assert all(row["beads"] == [] for row in widget)


@then("the human report names the rule and the base it attributed by")
def _rich_names_the_rule(world: dict[str, Any]) -> None:
    from beadloom.application.gate_ownership import ATTRIBUTION_RULE

    rich = world["outputs"]["rich"]
    assert ATTRIBUTION_RULE in rich
    assert "main..HEAD" in rich
    assert "finding(s), by the files its commits changed" in rich


@then("the GitHub notices name the rule beside each owner")
def _github_names_the_rule(world: dict[str, Any]) -> None:
    github = world["outputs"]["github"]
    owned = [line for line in github.splitlines() if line.startswith("::notice::owned by bd-a:")]
    assert owned, github
    assert owned[0].endswith("finding(s), by the files its commits changed")


@then("the JSON report carries the rule and the base")
def _json_carries_the_rule(world: dict[str, Any]) -> None:
    from beadloom.application.gate_ownership import ATTRIBUTION_RULE

    ownership = _ownership(world)
    assert ownership["rule"] == ATTRIBUTION_RULE
    assert ownership["base"] == "main"
